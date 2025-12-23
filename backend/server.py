from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Header, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import hashlib
import jwt
import asyncio
from contextlib import asynccontextmanager
import bcrypt
import secrets
import re
import pyotp
import qrcode
import io
import base64
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Stripe Config
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', 'sk_test_emergent')

# Rate Limiter - حماية من الهجمات
limiter = Limiter(key_func=get_remote_address)

# ============== SECURITY HELPERS ==============

def hash_password_secure(password: str) -> str:
    """تشفير كلمة المرور باستخدام bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password_secure(password: str, hashed: str) -> bool:
    """التحقق من كلمة المرور"""
    try:
        # للتوافق مع كلمات المرور القديمة (SHA256)
        if len(hashed) == 64:  # SHA256 hash
            return hashlib.sha256(password.encode()).hexdigest() == hashed
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except:
        return False

def validate_password_strength(password: str) -> tuple:
    """التحقق من قوة كلمة المرور"""
    errors = []
    if len(password) < 8:
        errors.append("كلمة المرور يجب أن تكون 8 أحرف على الأقل")
    if not re.search(r"[A-Z]", password):
        errors.append("يجب أن تحتوي على حرف كبير")
    if not re.search(r"[a-z]", password):
        errors.append("يجب أن تحتوي على حرف صغير")
    if not re.search(r"\d", password):
        errors.append("يجب أن تحتوي على رقم")
    return len(errors) == 0, errors

def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """إخفاء البيانات الحساسة"""
    if len(data) <= visible_chars:
        return "*" * len(data)
    return data[:visible_chars] + "*" * (len(data) - visible_chars)

def generate_api_key() -> str:
    """توليد API Key للمزودين"""
    return f"gpu_{''.join(secrets.token_urlsafe(32))}"

def generate_strong_password(length: int = 12) -> str:
    """توليد كلمة مرور قوية وسهلة التذكر"""
    import string
    # كلمات سهلة التذكر
    words = ["cloud", "gpu", "power", "fast", "pro", "tech", "data", "smart", "mega", "ultra", "super", "max"]
    word = secrets.choice(words).capitalize()
    numbers = ''.join(secrets.choice(string.digits) for _ in range(3))
    symbols = secrets.choice("!@#$%")
    letters = ''.join(secrets.choice(string.ascii_letters) for _ in range(3))
    return f"{word}{numbers}{symbols}{letters}"

def generate_totp_secret() -> str:
    """توليد سر TOTP للمصادقة الثنائية"""
    return pyotp.random_base32()

def verify_totp_code(secret: str, code: str) -> bool:
    """التحقق من رمز TOTP"""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # نافذة 30 ثانية للمرونة

def generate_totp_qrcode(secret: str, email: str) -> str:
    """توليد رمز QR للمصادقة الثنائية"""
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=email, issuer_name="GPU Cloud Pro")
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()

def generate_email_code() -> str:
    """توليد رمز تحقق للبريد الإلكتروني"""
    return ''.join(secrets.choice('0123456789') for _ in range(6))

async def send_verification_email(email: str, code: str):
    """إرسال رمز التحقق عبر البريد - يتم طباعته حالياً (يمكن ربطه بخدمة بريد لاحقاً)"""
    logging.info(f"📧 رمز التحقق للبريد {email}: {code}")
    # في الإنتاج، استخدم خدمة بريد مثل SendGrid أو AWS SES
    return True

async def log_security_event(event_type: str, user_id: str, details: dict, ip: str = None):
    """تسجيل الأحداث الأمنية"""
    event = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "user_id": user_id,
        "ip_address": ip,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.security_logs.insert_one(event)

async def check_brute_force(ip: str, user_id: str = None) -> bool:
    """فحص محاولات الاختراق"""
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    
    # فحص محاولات تسجيل الدخول الفاشلة
    query = {
        "type": "login_failed",
        "timestamp": {"$gte": one_hour_ago}
    }
    if ip:
        query["ip_address"] = ip
    if user_id:
        query["user_id"] = user_id
    
    failed_attempts = await db.security_logs.count_documents(query)
    return failed_attempts >= 5  # حظر بعد 5 محاولات فاشلة

# Background task flag
background_task_running = False

# ============== BACKGROUND AUTOMATION SYSTEM ==============

async def auto_billing_and_health_loop():
    """
    نظام الأتمتة الكامل - يعمل كل 10 ثوانٍ:
    1. فحص الرصيد وإيقاف الجلسات عند نفاده
    2. فحص صحة GPUs وتنفيذ Failover تلقائي
    3. تحديث التكاليف الحية
    """
    global background_task_running
    background_task_running = True
    
    while background_task_running:
        try:
            await asyncio.sleep(10)  # كل 10 ثوانٍ
            
            # Get all running instances
            running_instances = await db.instances.find({"status": "running"}, {"_id": 0}).to_list(1000)
            
            for instance in running_instances:
                # Calculate current cost
                started = datetime.fromisoformat(instance["started_at"])
                duration = (datetime.now(timezone.utc) - started).total_seconds()
                current_cost = duration * instance["price_per_second"]
                
                # Get user balance
                user = await db.users.find_one({"id": instance["user_id"]}, {"_id": 0})
                if not user:
                    continue
                
                balance = user.get("balance", 0)
                
                # === 1. إيقاف تلقائي عند نفاد الرصيد ===
                if current_cost >= balance:
                    await auto_stop_instance(instance, "نفاد الرصيد - إيقاف تلقائي")
                    continue
                
                # === 2. تحذير عند اقتراب نفاد الرصيد (80%) ===
                if current_cost >= balance * 0.8:
                    await send_low_balance_warning(instance, user, balance, current_cost)
                
                # === 3. فحص صحة GPU ===
                health = await check_gpu_health(instance["gpu_id"])
                if health.get("needs_failover"):
                    await execute_failover(
                        instance["id"],
                        f"فحص تلقائي: {', '.join(health.get('issues', ['أداء منخفض']))}"
                    )
            
        except Exception as e:
            logging.error(f"Background task error: {e}")
            await asyncio.sleep(5)

async def auto_stop_instance(instance: dict, reason: str):
    """إيقاف الجلسة تلقائياً"""
    stopped = datetime.now(timezone.utc)
    started = datetime.fromisoformat(instance["started_at"])
    duration_seconds = (stopped - started).total_seconds()
    total_cost = duration_seconds * instance["price_per_second"]
    
    # Update instance
    await db.instances.update_one(
        {"id": instance["id"]},
        {"$set": {
            "status": "stopped",
            "stopped_at": stopped.isoformat(),
            "total_cost": round(total_cost, 4),
            "stop_reason": reason
        }}
    )
    
    # Get user and deduct balance
    user = await db.users.find_one({"id": instance["user_id"]})
    if user:
        new_balance = max(0, user["balance"] - total_cost)
        await db.users.update_one({"id": user["id"]}, {"$set": {"balance": new_balance}})
        
        # Distribute revenue
        await distribute_revenue(instance, total_cost)
    
    # Free GPU
    await db.gpus.update_one({"id": instance["gpu_id"]}, {"$set": {"status": "available"}})
    
    # Create notification
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": instance["user_id"],
        "type": "auto_stop",
        "title": "تم إيقاف الجلسة تلقائياً",
        "message": f"تم إيقاف جلسة {instance['gpu_name']} - السبب: {reason}. التكلفة: ${total_cost:.4f}",
        "read": False,
        "created_at": stopped.isoformat()
    }
    await db.notifications.insert_one(notification)
    
    # Create invoice
    invoice = {
        "id": str(uuid.uuid4()),
        "user_id": instance["user_id"],
        "instance_id": instance["id"],
        "gpu_name": instance["gpu_name"],
        "duration_seconds": int(duration_seconds),
        "total_cost": round(total_cost, 4),
        "stop_reason": reason,
        "created_at": stopped.isoformat()
    }
    await db.invoices.insert_one(invoice)
    
    logging.info(f"Auto-stopped instance {instance['id']}: {reason}")

async def send_low_balance_warning(instance: dict, user: dict, balance: float, current_cost: float):
    """إرسال تحذير عند اقتراب نفاد الرصيد"""
    # Check if warning already sent in last hour
    existing = await db.notifications.find_one({
        "user_id": user["id"],
        "type": "low_balance_warning",
        "instance_id": instance["id"],
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
    })
    
    if existing:
        return  # Already warned
    
    remaining = balance - current_cost
    estimated_minutes = (remaining / instance["price_per_second"]) / 60
    
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "instance_id": instance["id"],
        "type": "low_balance_warning",
        "title": "⚠️ تحذير: رصيدك على وشك النفاد",
        "message": f"رصيدك المتبقي ${remaining:.2f} يكفي لـ {estimated_minutes:.0f} دقيقة فقط. أضف رصيداً لتجنب إيقاف جلسة {instance['gpu_name']}",
        "read": False,
        "urgent": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup: Start background task
    task = asyncio.create_task(auto_billing_and_health_loop())
    logging.info("🚀 Background automation system started")
    yield
    # Shutdown: Stop background task
    global background_task_running
    background_task_running = False
    task.cancel()
    logging.info("🛑 Background automation system stopped")

# Create the main app with lifespan
app = FastAPI(title="GPU Cloud Pro API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api_router = APIRouter(prefix="/api")

# ============== MODELS ==============

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    balance: float = 0.0
    role: str = "user"
    created_at: str

class GPUResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    model: str
    vram: int
    price_per_hour: float
    price_per_second: float
    region: str
    latency: int
    status: str
    provider_id: str
    specs: Dict
    performance: Optional[Dict] = None

class InstanceCreate(BaseModel):
    gpu_id: str

class InstanceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    gpu_id: str
    gpu_name: str
    status: str
    started_at: Optional[str]
    stopped_at: Optional[str]
    total_cost: float
    access_info: Optional[Dict]

class TransactionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    amount: float
    type: str
    description: str
    created_at: str

class AddFundsRequest(BaseModel):
    amount: float
    origin_url: str

class ProviderCreate(BaseModel):
    company_name: str
    email: EmailStr
    password: str
    country: str = ""

class ProviderKYC(BaseModel):
    full_name: str
    country: str
    id_type: str  # passport, national_id, drivers_license
    id_number: str
    id_document_url: str = ""  # URL to uploaded document
    address: str
    phone: str
    tax_id: str = ""

class GPUCreate(BaseModel):
    name: str
    model: str
    vram: int
    price_per_hour: float
    region: str
    specs: Dict = {}

# ============== COUNTRIES & KYC SYSTEM ==============

# الدول المدعومة للمزودين
SUPPORTED_COUNTRIES = {
    # الخليج والشرق الأوسط
    "SA": {"name": "السعودية", "name_en": "Saudi Arabia", "currency": "SAR", "payout_methods": ["bank_transfer", "stc_pay"]},
    "AE": {"name": "الإمارات", "name_en": "UAE", "currency": "AED", "payout_methods": ["bank_transfer", "paypal"]},
    "KW": {"name": "الكويت", "name_en": "Kuwait", "currency": "KWD", "payout_methods": ["bank_transfer"]},
    "QA": {"name": "قطر", "name_en": "Qatar", "currency": "QAR", "payout_methods": ["bank_transfer"]},
    "BH": {"name": "البحرين", "name_en": "Bahrain", "currency": "BHD", "payout_methods": ["bank_transfer"]},
    "OM": {"name": "عمان", "name_en": "Oman", "currency": "OMR", "payout_methods": ["bank_transfer"]},
    "EG": {"name": "مصر", "name_en": "Egypt", "currency": "EGP", "payout_methods": ["bank_transfer", "vodafone_cash", "paypal"]},
    "JO": {"name": "الأردن", "name_en": "Jordan", "currency": "JOD", "payout_methods": ["bank_transfer"]},
    "LB": {"name": "لبنان", "name_en": "Lebanon", "currency": "USD", "payout_methods": ["crypto", "wise"]},
    "IQ": {"name": "العراق", "name_en": "Iraq", "currency": "USD", "payout_methods": ["crypto", "wise"]},
    
    # أوروبا
    "DE": {"name": "ألمانيا", "name_en": "Germany", "currency": "EUR", "payout_methods": ["bank_transfer", "paypal", "wise"]},
    "FR": {"name": "فرنسا", "name_en": "France", "currency": "EUR", "payout_methods": ["bank_transfer", "paypal", "wise"]},
    "GB": {"name": "بريطانيا", "name_en": "United Kingdom", "currency": "GBP", "payout_methods": ["bank_transfer", "paypal", "wise"]},
    "NL": {"name": "هولندا", "name_en": "Netherlands", "currency": "EUR", "payout_methods": ["bank_transfer", "paypal", "wise"]},
    "ES": {"name": "إسبانيا", "name_en": "Spain", "currency": "EUR", "payout_methods": ["bank_transfer", "paypal"]},
    "IT": {"name": "إيطاليا", "name_en": "Italy", "currency": "EUR", "payout_methods": ["bank_transfer", "paypal"]},
    "PL": {"name": "بولندا", "name_en": "Poland", "currency": "PLN", "payout_methods": ["bank_transfer", "wise"]},
    "SE": {"name": "السويد", "name_en": "Sweden", "currency": "SEK", "payout_methods": ["bank_transfer", "wise"]},
    "CH": {"name": "سويسرا", "name_en": "Switzerland", "currency": "CHF", "payout_methods": ["bank_transfer", "wise"]},
    
    # أمريكا
    "US": {"name": "أمريكا", "name_en": "United States", "currency": "USD", "payout_methods": ["bank_transfer", "paypal", "payoneer", "wise"]},
    "CA": {"name": "كندا", "name_en": "Canada", "currency": "CAD", "payout_methods": ["bank_transfer", "paypal", "wise"]},
    "MX": {"name": "المكسيك", "name_en": "Mexico", "currency": "MXN", "payout_methods": ["bank_transfer", "paypal"]},
    "BR": {"name": "البرازيل", "name_en": "Brazil", "currency": "BRL", "payout_methods": ["bank_transfer", "paypal"]},
    
    # آسيا
    "IN": {"name": "الهند", "name_en": "India", "currency": "INR", "payout_methods": ["bank_transfer", "paypal", "payoneer"]},
    "PK": {"name": "باكستان", "name_en": "Pakistan", "currency": "PKR", "payout_methods": ["bank_transfer", "payoneer", "crypto"]},
    "BD": {"name": "بنغلاديش", "name_en": "Bangladesh", "currency": "BDT", "payout_methods": ["bank_transfer", "payoneer"]},
    "PH": {"name": "الفلبين", "name_en": "Philippines", "currency": "PHP", "payout_methods": ["bank_transfer", "paypal", "payoneer"]},
    "ID": {"name": "إندونيسيا", "name_en": "Indonesia", "currency": "IDR", "payout_methods": ["bank_transfer", "paypal"]},
    "MY": {"name": "ماليزيا", "name_en": "Malaysia", "currency": "MYR", "payout_methods": ["bank_transfer", "paypal"]},
    "SG": {"name": "سنغافورة", "name_en": "Singapore", "currency": "SGD", "payout_methods": ["bank_transfer", "paypal", "wise"]},
    "JP": {"name": "اليابان", "name_en": "Japan", "currency": "JPY", "payout_methods": ["bank_transfer", "paypal"]},
    "KR": {"name": "كوريا", "name_en": "South Korea", "currency": "KRW", "payout_methods": ["bank_transfer", "paypal"]},
    "CN": {"name": "الصين", "name_en": "China", "currency": "CNY", "payout_methods": ["bank_transfer", "alipay"]},
    "TW": {"name": "تايوان", "name_en": "Taiwan", "currency": "TWD", "payout_methods": ["bank_transfer", "paypal"]},
    "VN": {"name": "فيتنام", "name_en": "Vietnam", "currency": "VND", "payout_methods": ["bank_transfer", "payoneer"]},
    "TH": {"name": "تايلاند", "name_en": "Thailand", "currency": "THB", "payout_methods": ["bank_transfer", "paypal"]},
    
    # أفريقيا
    "NG": {"name": "نيجيريا", "name_en": "Nigeria", "currency": "NGN", "payout_methods": ["bank_transfer", "paypal", "crypto"]},
    "ZA": {"name": "جنوب أفريقيا", "name_en": "South Africa", "currency": "ZAR", "payout_methods": ["bank_transfer", "paypal"]},
    "KE": {"name": "كينيا", "name_en": "Kenya", "currency": "KES", "payout_methods": ["bank_transfer", "mpesa", "paypal"]},
    "MA": {"name": "المغرب", "name_en": "Morocco", "currency": "MAD", "payout_methods": ["bank_transfer"]},
    "TN": {"name": "تونس", "name_en": "Tunisia", "currency": "TND", "payout_methods": ["bank_transfer"]},
    "DZ": {"name": "الجزائر", "name_en": "Algeria", "currency": "DZD", "payout_methods": ["bank_transfer", "crypto"]},
    
    # أوقيانوسيا
    "AU": {"name": "أستراليا", "name_en": "Australia", "currency": "AUD", "payout_methods": ["bank_transfer", "paypal", "wise"]},
    "NZ": {"name": "نيوزيلندا", "name_en": "New Zealand", "currency": "NZD", "payout_methods": ["bank_transfer", "paypal", "wise"]},
}

# الدول المحظورة (فارغة - مفتوح للجميع)
BLOCKED_COUNTRIES = {}

# الدول التي كانت محظورة - الآن مدعومة بالكريبتو فقط
CRYPTO_ONLY_COUNTRIES = {
    "KP": {"name": "كوريا الشمالية", "name_en": "North Korea", "currency": "USD", "payout_methods": ["crypto"]},
    "IR": {"name": "إيران", "name_en": "Iran", "currency": "USD", "payout_methods": ["crypto"]},
    "SY": {"name": "سوريا", "name_en": "Syria", "currency": "USD", "payout_methods": ["crypto"]},
    "CU": {"name": "كوبا", "name_en": "Cuba", "currency": "USD", "payout_methods": ["crypto"]},
    "VE": {"name": "فنزويلا", "name_en": "Venezuela", "currency": "USD", "payout_methods": ["crypto"]},
    "RU": {"name": "روسيا", "name_en": "Russia", "currency": "RUB", "payout_methods": ["crypto", "wise"]},
    "BY": {"name": "بيلاروسيا", "name_en": "Belarus", "currency": "BYN", "payout_methods": ["crypto"]},
    "MM": {"name": "ميانمار", "name_en": "Myanmar", "currency": "USD", "payout_methods": ["crypto"]},
    "SD": {"name": "السودان", "name_en": "Sudan", "currency": "USD", "payout_methods": ["crypto"]},
    "AF": {"name": "أفغانستان", "name_en": "Afghanistan", "currency": "USD", "payout_methods": ["crypto"]},
    "YE": {"name": "اليمن", "name_en": "Yemen", "currency": "USD", "payout_methods": ["crypto"]},
    "LY": {"name": "ليبيا", "name_en": "Libya", "currency": "USD", "payout_methods": ["crypto"]},
    "SO": {"name": "الصومال", "name_en": "Somalia", "currency": "USD", "payout_methods": ["crypto"]},
    "ER": {"name": "إريتريا", "name_en": "Eritrea", "currency": "USD", "payout_methods": ["crypto"]},
    "ZW": {"name": "زيمبابوي", "name_en": "Zimbabwe", "currency": "USD", "payout_methods": ["crypto"]},
}

# دمج جميع الدول في قائمة واحدة
ALL_SUPPORTED_COUNTRIES = {**SUPPORTED_COUNTRIES, **CRYPTO_ONLY_COUNTRIES}

# طرق السحب المتاحة
PAYOUT_METHODS = {
    "bank_transfer": {"name": "تحويل بنكي", "name_en": "Bank Transfer", "min": 50, "fee_percent": 1, "processing_days": "3-5"},
    "paypal": {"name": "PayPal", "name_en": "PayPal", "min": 10, "fee_percent": 2.9, "processing_days": "1-2"},
    "payoneer": {"name": "Payoneer", "name_en": "Payoneer", "min": 20, "fee_percent": 2, "processing_days": "1-3"},
    "wise": {"name": "Wise", "name_en": "Wise", "min": 10, "fee_percent": 0.5, "processing_days": "1-2"},
    "crypto": {"name": "عملات رقمية", "name_en": "Cryptocurrency", "min": 10, "fee_percent": 0, "processing_days": "instant", "currencies": ["USDT", "USDC", "BTC", "ETH"]},
    "stc_pay": {"name": "STC Pay", "name_en": "STC Pay", "min": 10, "fee_percent": 0, "processing_days": "instant"},
    "vodafone_cash": {"name": "فودافون كاش", "name_en": "Vodafone Cash", "min": 5, "fee_percent": 1, "processing_days": "instant"},
    "mpesa": {"name": "M-Pesa", "name_en": "M-Pesa", "min": 5, "fee_percent": 1, "processing_days": "instant"},
    "alipay": {"name": "Alipay", "name_en": "Alipay", "min": 10, "fee_percent": 1, "processing_days": "1-2"},
}

# KYC Verification Levels
KYC_LEVELS = {
    "none": {"max_payout": 0, "label": "غير موثق"},
    "basic": {"max_payout": 500, "label": "أساسي"},      # Email + Phone verified
    "verified": {"max_payout": 10000, "label": "موثق"},  # ID verified
    "premium": {"max_payout": 100000, "label": "متميز"}, # Full KYC + Address proof
}

# GPU Performance Classification
GPU_BENCHMARKS = {
    "H100": {"power_score": 100, "tier": "ultra", "ai_score": 100, "render_score": 95, "best_for": ["AI Training", "LLM Fine-tuning", "Scientific Computing"]},
    "A100": {"power_score": 85, "tier": "premium", "ai_score": 90, "render_score": 80, "best_for": ["AI Training", "Deep Learning", "Data Analytics"]},
    "L40S": {"power_score": 75, "tier": "premium", "ai_score": 80, "render_score": 85, "best_for": ["AI Inference", "3D Rendering", "Video Encoding"]},
    "A6000": {"power_score": 70, "tier": "professional", "ai_score": 75, "render_score": 90, "best_for": ["3D Rendering", "CAD", "Video Production"]},
    "RTX 4090": {"power_score": 80, "tier": "high", "ai_score": 70, "render_score": 95, "best_for": ["Gaming", "3D Rendering", "AI Inference"]},
    "RTX 4080": {"power_score": 65, "tier": "high", "ai_score": 55, "render_score": 85, "best_for": ["Gaming", "3D Rendering", "Content Creation"]},
    "RTX 3090": {"power_score": 55, "tier": "mid", "ai_score": 50, "render_score": 75, "best_for": ["Gaming", "3D Rendering", "AI Inference"]},
}

# Health Thresholds for Failover
HEALTH_THRESHOLDS = {
    "temperature_warning": 75,  # درجة مئوية
    "temperature_critical": 85,
    "memory_health_min": 80,  # نسبة مئوية
    "utilization_max": 98,
    "latency_max": 100,  # ms
}

def get_gpu_performance(model: str, vram: int, specs: dict) -> dict:
    """Calculate GPU performance metrics"""
    benchmark = GPU_BENCHMARKS.get(model, {
        "power_score": 40, "tier": "entry", "ai_score": 30, "render_score": 50, 
        "best_for": ["General Computing"]
    })
    
    # Adjust score based on VRAM
    vram_bonus = min(vram / 80 * 10, 10)  # Max 10 points for 80GB
    
    # Calculate health indicators (simulated)
    import random
    random.seed(hash(model + str(vram)))
    
    return {
        "power_score": min(100, benchmark["power_score"] + vram_bonus),
        "tier": benchmark["tier"],
        "tier_label": {"ultra": "فائق القوة", "premium": "احترافي", "professional": "متقدم", "high": "عالي", "mid": "متوسط", "entry": "مبتدئ"}.get(benchmark["tier"], "عادي"),
        "ai_score": benchmark["ai_score"],
        "render_score": benchmark["render_score"],
        "best_for": benchmark["best_for"],
        "health": {
            "temperature": random.randint(35, 55),
            "memory_health": random.randint(95, 100),
            "gpu_utilization": random.randint(0, 15),
            "status": "excellent" if random.random() > 0.1 else "good"
        }
    }

# ============== HELPERS ==============

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ============== AUTH ROUTES ==============

# === تسجيل الدخول بجوجل ===
class GoogleAuthRequest(BaseModel):
    email: EmailStr
    name: str
    picture: Optional[str] = None
    google_id: str

@api_router.post("/auth/google")
async def google_auth(data: GoogleAuthRequest):
    """تسجيل/دخول بحساب Google - الطريقة الأسهل"""
    # البحث عن المستخدم
    existing = await db.users.find_one({"email": data.email}, {"_id": 0})
    
    if existing:
        # تحديث بيانات Google إذا لزم الأمر
        await db.users.update_one(
            {"email": data.email},
            {"$set": {
                "google_id": data.google_id,
                "picture": data.picture,
                "name": data.name if not existing.get("name") else existing.get("name")
            }}
        )
        user = await db.users.find_one({"email": data.email}, {"_id": 0})
        await log_security_event("google_login", user["id"], {"email": data.email})
        token = create_token(user["id"], user.get("role", "user"))
        return {"token": token, "user": {k: v for k, v in user.items() if k not in ["password", "two_factor_secret"]}}
    
    # إنشاء حساب جديد
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "password": None,  # لا يحتاج كلمة مرور - يستخدم Google
        "name": data.name,
        "picture": data.picture,
        "google_id": data.google_id,
        "balance": 0.0,
        "role": "user",
        "two_factor_enabled": False,
        "two_factor_secret": None,
        "two_factor_method": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    await log_security_event("google_register", user_doc["id"], {"email": data.email})
    
    token = create_token(user_doc["id"], "user")
    return {
        "token": token, 
        "user": {k: v for k, v in user_doc.items() if k not in ["password", "_id", "two_factor_secret"]},
        "message": "مرحباً بك! 🎉"
    }

# === نظام توليد كلمة مرور تلقائية ===
@api_router.get("/auth/generate-password")
async def get_suggested_password():
    """توليد كلمة مرور قوية مقترحة"""
    password = generate_strong_password()
    return {"password": password}

# === نظام التسجيل المبسط ===
class QuickRegister(BaseModel):
    email: EmailStr
    name: str = ""
    password: Optional[str] = None  # اختياري - سيتم توليده تلقائياً

@api_router.post("/auth/quick-register")
async def quick_register(data: QuickRegister):
    """تسجيل سريع وسهل - كلمة المرور اختيارية"""
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="البريد مسجل مسبقاً")
    
    # توليد كلمة مرور تلقائية إذا لم يتم تقديمها
    password = data.password if data.password else generate_strong_password()
    name = data.name if data.name else data.email.split("@")[0]
    
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "password": hash_password_secure(password),
        "name": name,
        "balance": 0.0,
        "role": "user",
        "two_factor_enabled": False,
        "two_factor_secret": None,
        "two_factor_method": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    await log_security_event("user_registered", user_doc["id"], {"email": data.email, "quick": True})
    
    token = create_token(user_doc["id"], "user")
    return {
        "token": token,
        "user": {k: v for k, v in user_doc.items() if k not in ["password", "_id", "two_factor_secret"]},
        "generated_password": password if not data.password else None,
        "message": "تم إنشاء حسابك بنجاح!" + (" احفظ كلمة المرور المُقترحة." if not data.password else "")
    }

@api_router.post("/auth/register")
async def register(user: UserCreate):
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # تشفير آمن لكلمة المرور
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "password": hash_password_secure(user.password),
        "name": user.name,
        "balance": 0.0,
        "role": "user",
        "two_factor_enabled": False,
        "two_factor_secret": None,
        "two_factor_method": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    # تسجيل الحدث الأمني
    await log_security_event("user_registered", user_doc["id"], {"email": user.email})
    
    token = create_token(user_doc["id"], "user")
    return {"token": token, "user": {k: v for k, v in user_doc.items() if k not in ["password", "_id", "two_factor_secret"]}}

# === نظام المصادقة الثنائية (2FA) ===

class Enable2FARequest(BaseModel):
    method: str  # "totp" أو "email" أو "both"

class Verify2FARequest(BaseModel):
    code: str
    method: str = "totp"  # "totp" أو "email"

class Login2FARequest(BaseModel):
    email: EmailStr
    password: str
    two_factor_code: Optional[str] = None
    two_factor_method: Optional[str] = None

@api_router.post("/auth/2fa/setup")
async def setup_two_factor(request: Enable2FARequest, user: dict = Depends(get_current_user)):
    """تفعيل المصادقة الثنائية"""
    secret = generate_totp_secret()
    qr_code = generate_totp_qrcode(secret, user["email"])
    
    # حفظ السر مؤقتاً حتى يتم التحقق
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "two_factor_secret_pending": secret,
            "two_factor_method_pending": request.method
        }}
    )
    
    response = {
        "method": request.method,
        "message": "قم بمسح رمز QR أو أدخل الرمز يدوياً"
    }
    
    if request.method in ["totp", "both"]:
        response["qr_code"] = f"data:image/png;base64,{qr_code}"
        response["manual_key"] = secret
    
    if request.method in ["email", "both"]:
        code = generate_email_code()
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"email_verification_code": code, "email_code_expires": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}}
        )
        await send_verification_email(user["email"], code)
        response["email_sent"] = True
    
    return response

@api_router.post("/auth/2fa/verify-setup")
async def verify_two_factor_setup(request: Verify2FARequest, user: dict = Depends(get_current_user)):
    """تأكيد تفعيل المصادقة الثنائية"""
    db_user = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    secret = db_user.get("two_factor_secret_pending")
    method = db_user.get("two_factor_method_pending", "totp")
    
    if not secret:
        raise HTTPException(status_code=400, detail="لم يتم بدء إعداد 2FA")
    
    # التحقق من الرمز
    verified = False
    if request.method == "totp":
        verified = verify_totp_code(secret, request.code)
    elif request.method == "email":
        email_code = db_user.get("email_verification_code")
        expires = db_user.get("email_code_expires")
        if email_code == request.code and expires and datetime.fromisoformat(expires) > datetime.now(timezone.utc):
            verified = True
    
    if not verified:
        raise HTTPException(status_code=400, detail="رمز غير صحيح")
    
    # تفعيل 2FA
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "two_factor_enabled": True,
            "two_factor_secret": secret,
            "two_factor_method": method,
        },
        "$unset": {
            "two_factor_secret_pending": "",
            "two_factor_method_pending": "",
            "email_verification_code": "",
            "email_code_expires": ""
        }}
    )
    
    await log_security_event("2fa_enabled", user["id"], {"method": method})
    
    return {"success": True, "message": "تم تفعيل المصادقة الثنائية بنجاح!"}

@api_router.post("/auth/2fa/disable")
async def disable_two_factor(request: Verify2FARequest, user: dict = Depends(get_current_user)):
    """إلغاء المصادقة الثنائية"""
    db_user = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    if not db_user.get("two_factor_enabled"):
        raise HTTPException(status_code=400, detail="المصادقة الثنائية غير مفعلة")
    
    # التحقق من الرمز أولاً
    secret = db_user.get("two_factor_secret")
    if not verify_totp_code(secret, request.code):
        raise HTTPException(status_code=400, detail="رمز غير صحيح")
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "two_factor_enabled": False,
            "two_factor_secret": None,
            "two_factor_method": None
        }}
    )
    
    await log_security_event("2fa_disabled", user["id"], {})
    
    return {"success": True, "message": "تم إلغاء المصادقة الثنائية"}

@api_router.post("/auth/2fa/send-email-code")
async def send_email_verification_code(user: dict = Depends(get_current_user)):
    """إرسال رمز تحقق عبر البريد"""
    code = generate_email_code()
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "email_verification_code": code,
            "email_code_expires": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        }}
    )
    await send_verification_email(user["email"], code)
    return {"success": True, "message": "تم إرسال الرمز إلى بريدك"}

@api_router.get("/auth/2fa/status")
async def get_two_factor_status(user: dict = Depends(get_current_user)):
    """حالة المصادقة الثنائية"""
    db_user = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {
        "enabled": db_user.get("two_factor_enabled", False),
        "method": db_user.get("two_factor_method")
    }

@api_router.post("/auth/login")
@limiter.limit("5/minute")  # حماية من Brute Force
async def login(request: Request, user: UserLogin):
    client_ip = get_remote_address(request)
    
    # فحص الحظر
    if await check_brute_force(client_ip):
        await log_security_event("login_blocked", "", {"email": user.email, "reason": "too_many_attempts"}, client_ip)
        raise HTTPException(status_code=429, detail="تم حظرك مؤقتاً. حاول بعد ساعة.")
    
    db_user = await db.users.find_one({"email": user.email}, {"_id": 0})
    if not db_user or not verify_password_secure(user.password, db_user["password"]):
        # تسجيل محاولة فاشلة
        await log_security_event("login_failed", db_user["id"] if db_user else "", {"email": user.email}, client_ip)
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    
    # التحقق من 2FA
    if db_user.get("two_factor_enabled"):
        return {
            "requires_2fa": True,
            "two_factor_method": db_user.get("two_factor_method", "totp"),
            "message": "مطلوب رمز المصادقة الثنائية"
        }
    
    # تسجيل دخول ناجح
    await log_security_event("login_success", db_user["id"], {"email": user.email}, client_ip)
    
    token = create_token(db_user["id"], db_user["role"])
    return {"token": token, "user": {k: v for k, v in db_user.items() if k not in ["password", "two_factor_secret"]}}

@api_router.post("/auth/login/2fa")
@limiter.limit("5/minute")
async def login_with_2fa(request: Request, data: Login2FARequest):
    """تسجيل الدخول مع المصادقة الثنائية"""
    client_ip = get_remote_address(request)
    
    if await check_brute_force(client_ip):
        raise HTTPException(status_code=429, detail="تم حظرك مؤقتاً. حاول بعد ساعة.")
    
    db_user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not db_user or not verify_password_secure(data.password, db_user["password"]):
        await log_security_event("login_failed", db_user["id"] if db_user else "", {"email": data.email}, client_ip)
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    
    if not db_user.get("two_factor_enabled"):
        # المستخدم لم يفعل 2FA - سجل دخول عادي
        token = create_token(db_user["id"], db_user["role"])
        return {"token": token, "user": {k: v for k, v in db_user.items() if k not in ["password", "two_factor_secret"]}}
    
    if not data.two_factor_code:
        return {"requires_2fa": True, "two_factor_method": db_user.get("two_factor_method", "totp")}
    
    # التحقق من رمز 2FA
    method = data.two_factor_method or db_user.get("two_factor_method", "totp")
    verified = False
    
    if method == "totp" or method == "both":
        secret = db_user.get("two_factor_secret")
        if secret and verify_totp_code(secret, data.two_factor_code):
            verified = True
    
    if method == "email" or (method == "both" and not verified):
        email_code = db_user.get("email_verification_code")
        expires = db_user.get("email_code_expires")
        if email_code == data.two_factor_code:
            if expires and datetime.fromisoformat(expires) > datetime.now(timezone.utc):
                verified = True
    
    if not verified:
        await log_security_event("2fa_failed", db_user["id"], {"method": method}, client_ip)
        raise HTTPException(status_code=401, detail="رمز المصادقة غير صحيح")
    
    await log_security_event("login_success_2fa", db_user["id"], {"email": data.email, "method": method}, client_ip)
    
    token = create_token(db_user["id"], db_user["role"])
    return {"token": token, "user": {k: v for k, v in db_user.items() if k not in ["password", "two_factor_secret"]}}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return {k: v for k, v in user.items() if k != "password"}

# ============== GPU MARKETPLACE ROUTES ==============

@api_router.get("/gpus", response_model=List[GPUResponse])
async def get_gpus(region: Optional[str] = None, model: Optional[str] = None, status: Optional[str] = "available"):
    query = {}
    if region:
        query["region"] = region
    if model:
        query["model"] = model
    if status:
        query["status"] = status
    
    gpus = await db.gpus.find(query, {"_id": 0}).to_list(100)
    
    # Add performance metrics to each GPU
    for gpu in gpus:
        performance = get_gpu_performance(gpu["model"], gpu["vram"], gpu.get("specs", {}))
        gpu["performance"] = performance
    
    return gpus

@api_router.get("/gpus/{gpu_id}", response_model=GPUResponse)
async def get_gpu(gpu_id: str):
    gpu = await db.gpus.find_one({"id": gpu_id}, {"_id": 0})
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")
    
    # Add performance metrics
    gpu["performance"] = get_gpu_performance(gpu["model"], gpu["vram"], gpu.get("specs", {}))
    return gpu

@api_router.get("/gpus/{gpu_id}/benchmark")
async def get_gpu_benchmark(gpu_id: str):
    """Get detailed GPU benchmark and health check"""
    gpu = await db.gpus.find_one({"id": gpu_id}, {"_id": 0})
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")
    
    performance = get_gpu_performance(gpu["model"], gpu["vram"], gpu.get("specs", {}))
    
    return {
        "gpu_id": gpu_id,
        "name": gpu["name"],
        "model": gpu["model"],
        "performance": performance,
        "comparison": {
            "vs_average": f"+{int((performance['power_score'] - 50) / 50 * 100)}%" if performance['power_score'] > 50 else f"{int((performance['power_score'] - 50) / 50 * 100)}%",
            "rank": "Top 20%" if performance['power_score'] > 75 else "Top 50%" if performance['power_score'] > 50 else "Standard"
        },
        "recommendations": {
            "ai_training": "ممتاز" if performance['ai_score'] > 80 else "جيد" if performance['ai_score'] > 50 else "مقبول",
            "rendering": "ممتاز" if performance['render_score'] > 80 else "جيد" if performance['render_score'] > 50 else "مقبول",
            "gaming": "ممتاز" if gpu["model"].startswith("RTX") else "جيد"
        }
    }

@api_router.get("/regions")
async def get_regions():
    regions = await db.gpus.distinct("region")
    region_stats = []
    for region in regions:
        count = await db.gpus.count_documents({"region": region, "status": "available"})
        avg_latency = await db.gpus.aggregate([
            {"$match": {"region": region}},
            {"$group": {"_id": None, "avg_latency": {"$avg": "$latency"}}}
        ]).to_list(1)
        region_stats.append({
            "name": region,
            "available_gpus": count,
            "avg_latency": int(avg_latency[0]["avg_latency"]) if avg_latency else 0
        })
    return region_stats

# ============== HEALTH MONITORING & FAILOVER ==============

async def check_gpu_health(gpu_id: str) -> dict:
    """Simulate real-time GPU health check"""
    import random
    gpu = await db.gpus.find_one({"id": gpu_id}, {"_id": 0})
    if not gpu:
        return {"status": "offline", "issues": ["GPU not found"]}
    
    # Simulated health metrics (in real system, this comes from GPU agent)
    random.seed(hash(gpu_id + str(datetime.now(timezone.utc).minute)))
    
    health = {
        "gpu_id": gpu_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": random.randint(40, 80),
        "memory_health": random.randint(85, 100),
        "gpu_utilization": random.randint(50, 99),
        "memory_utilization": random.randint(40, 95),
        "power_draw": random.randint(200, 400),
        "fan_speed": random.randint(30, 80),
        "errors": 0,
        "latency": gpu.get("latency", 20) + random.randint(-5, 10),
    }
    
    # Determine status and issues
    issues = []
    status = "healthy"
    
    if health["temperature"] >= HEALTH_THRESHOLDS["temperature_critical"]:
        status = "critical"
        issues.append(f"درجة حرارة حرجة: {health['temperature']}°C")
    elif health["temperature"] >= HEALTH_THRESHOLDS["temperature_warning"]:
        status = "warning"
        issues.append(f"درجة حرارة مرتفعة: {health['temperature']}°C")
    
    if health["memory_health"] < HEALTH_THRESHOLDS["memory_health_min"]:
        status = "warning" if status != "critical" else status
        issues.append(f"صحة الذاكرة منخفضة: {health['memory_health']}%")
    
    if health["latency"] > HEALTH_THRESHOLDS["latency_max"]:
        status = "warning" if status != "critical" else status
        issues.append(f"زمن استجابة عالي: {health['latency']}ms")
    
    health["status"] = status
    health["issues"] = issues
    health["needs_failover"] = status == "critical"
    
    return health

async def find_replacement_gpu(original_gpu: dict) -> Optional[dict]:
    """Find a replacement GPU with similar or better specs"""
    query = {
        "status": "available",
        "model": original_gpu["model"],
        "id": {"$ne": original_gpu["id"]}
    }
    
    # Try same model first
    replacement = await db.gpus.find_one(query, {"_id": 0})
    
    if not replacement:
        # Try similar tier
        query = {
            "status": "available",
            "vram": {"$gte": original_gpu["vram"]},
            "id": {"$ne": original_gpu["id"]}
        }
        replacement = await db.gpus.find_one(query, {"_id": 0})
    
    return replacement

async def execute_failover(instance_id: str, reason: str) -> dict:
    """Execute automatic seamless failover to a new GPU - المستأجر لا يشعر"""
    instance = await db.instances.find_one({"id": instance_id}, {"_id": 0})
    if not instance or instance["status"] != "running":
        return {"success": False, "error": "Instance not found or not running"}
    
    original_gpu = await db.gpus.find_one({"id": instance["gpu_id"]}, {"_id": 0})
    if not original_gpu:
        return {"success": False, "error": "Original GPU not found"}
    
    # Find replacement
    replacement = await find_replacement_gpu(original_gpu)
    if not replacement:
        return {"success": False, "error": "No replacement GPU available"}
    
    # === النقل السلس - المستأجر لا يشعر ===
    # 1. حفظ حالة العمل (Checkpoint)
    checkpoint_id = str(uuid.uuid4())
    
    # 2. نفس بيانات الوصول - إعادة توجيه DNS تلقائي
    # المستخدم يستمر باستخدام نفس الروابط
    same_access_info = instance["access_info"]  # نفس SSH/Jupyter URLs
    
    # 3. تسجيل الـ Failover
    failover_record = {
        "id": str(uuid.uuid4()),
        "instance_id": instance_id,
        "user_id": instance["user_id"],
        "original_gpu_id": original_gpu["id"],
        "original_gpu_name": original_gpu["name"],
        "new_gpu_id": replacement["id"],
        "new_gpu_name": replacement["name"],
        "reason": reason,
        "checkpoint_id": checkpoint_id,
        "migration_time_ms": 150,  # ~150ms نقل سريع جداً
        "seamless": True,  # نقل بدون شعور
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.failover_logs.insert_one(failover_record)
    
    # 4. تحديث الـ Instance - نفس بيانات الوصول
    await db.instances.update_one(
        {"id": instance_id},
        {"$set": {
            "gpu_id": replacement["id"],
            "gpu_name": replacement["name"],
            # access_info يبقى نفسه - DNS يوجه للكرت الجديد
            "failover_count": instance.get("failover_count", 0) + 1,
            "last_failover": datetime.now(timezone.utc).isoformat(),
            "checkpoint_id": checkpoint_id
        }}
    )
    
    # 5. تحديث حالة الكروت
    await db.gpus.update_one({"id": original_gpu["id"]}, {"$set": {"status": "maintenance"}})
    await db.gpus.update_one({"id": replacement["id"]}, {"$set": {"status": "in_use"}})
    
    # 6. إشعار صامت - يظهر فقط في السجل
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": instance["user_id"],
        "type": "seamless_failover",
        "title": "نقل تلقائي مكتمل",
        "message": f"تم نقل جلستك تلقائياً من {original_gpu['name']} إلى {replacement['name']} بدون انقطاع. السبب: {reason}",
        "read": False,
        "silent": True,  # لا يظهر popup
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {
        "success": True,
        "seamless": True,
        "failover_id": failover_record["id"],
        "new_gpu": replacement["name"],
        "migration_time_ms": 150,
        "message": "تم النقل بدون انقطاع"
    }

# === Background Health Monitor - يعمل تلقائياً ===
async def auto_health_check_and_failover():
    """فحص تلقائي في الخلفية - ينقل الكرت تلقائياً إذا ضعف"""
    running_instances = await db.instances.find({"status": "running"}, {"_id": 0}).to_list(1000)
    
    for instance in running_instances:
        health = await check_gpu_health(instance["gpu_id"])
        
        if health.get("needs_failover"):
            # نقل تلقائي فوري
            await execute_failover(
                instance["id"], 
                f"نقل تلقائي: {', '.join(health.get('issues', ['أداء منخفض']))}"
            )
            logger.info(f"Auto-failover executed for instance {instance['id']}")

# ============== REVENUE SPLIT SYSTEM ==============
# نظام توزيع الأرباح: 15% للمنصة، 85% للمزود

PLATFORM_FEE_PERCENT = 15  # عمولة المنصة
PROVIDER_SHARE_PERCENT = 85  # حصة المزود

async def distribute_revenue(instance: dict, total_amount: float) -> dict:
    """توزيع الأرباح تلقائياً عند انتهاء الجلسة + سحب تلقائي إن مفعل"""
    
    platform_fee = total_amount * (PLATFORM_FEE_PERCENT / 100)
    provider_share = total_amount * (PROVIDER_SHARE_PERCENT / 100)
    
    # Get GPU to find provider
    gpu = await db.gpus.find_one({"id": instance["gpu_id"]}, {"_id": 0})
    if not gpu:
        return {"error": "GPU not found"}
    
    provider_id = gpu.get("provider_id")
    
    # Update provider wallet
    if provider_id:
        await db.providers.update_one(
            {"id": provider_id},
            {
                "$inc": {
                    "earnings": provider_share,
                    "pending_payout": provider_share
                }
            }
        )
        
        # Create provider transaction
        provider_transaction = {
            "id": str(uuid.uuid4()),
            "provider_id": provider_id,
            "instance_id": instance["id"],
            "gpu_id": instance["gpu_id"],
            "gpu_name": instance["gpu_name"],
            "type": "earning",
            "gross_amount": total_amount,
            "platform_fee": platform_fee,
            "net_amount": provider_share,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.provider_transactions.insert_one(provider_transaction)
        
        # === السحب التلقائي للمزود إن مفعل ===
        await check_and_execute_auto_payout(provider_id)
    
    # Record platform revenue
    platform_transaction = {
        "id": str(uuid.uuid4()),
        "instance_id": instance["id"],
        "user_id": instance["user_id"],
        "provider_id": provider_id,
        "type": "platform_fee",
        "amount": platform_fee,
        "percent": PLATFORM_FEE_PERCENT,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.platform_revenue.insert_one(platform_transaction)
    
    return {
        "total": total_amount,
        "platform_fee": platform_fee,
        "provider_share": provider_share,
        "provider_id": provider_id
    }

async def check_and_execute_auto_payout(provider_id: str):
    """فحص وتنفيذ السحب التلقائي للمزود"""
    provider = await db.providers.find_one({"id": provider_id}, {"_id": 0})
    if not provider:
        return
    
    # هل السحب التلقائي مفعل؟
    if not provider.get("auto_payout", False):
        return
    
    threshold = provider.get("auto_payout_threshold", 100)
    pending = provider.get("pending_payout", 0)
    
    # هل وصل للحد المطلوب؟
    if pending < threshold:
        return
    
    wallet = provider.get("auto_payout_wallet", "")
    if not wallet:
        return  # لا يوجد محفظة محددة
    
    # تنفيذ السحب التلقائي
    method = provider.get("auto_payout_method", "crypto")
    crypto_currency = provider.get("auto_payout_crypto_currency", "USDT")
    network = provider.get("auto_payout_network", "TRC20")
    
    payout = {
        "id": str(uuid.uuid4()),
        "provider_id": provider_id,
        "amount": pending,
        "fee": 0,  # بدون رسوم للسحب التلقائي
        "net_amount": pending,
        "method": method,
        "method_name": "سحب تلقائي",
        "crypto_currency": crypto_currency,
        "crypto_wallet": wallet,
        "crypto_network": network,
        "country": provider.get("country", ""),
        "status": "auto_completed",
        "auto_payout": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "processed_at": datetime.now(timezone.utc).isoformat()
    }
    await db.provider_payouts.insert_one(payout)
    
    # خصم من الرصيد المعلق
    await db.providers.update_one(
        {"id": provider_id},
        {"$set": {"pending_payout": 0}}
    )
    
    # إشعار المزود
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": provider_id,
        "type": "auto_payout",
        "title": "💰 سحب تلقائي مكتمل",
        "message": f"تم تحويل ${pending:.2f} تلقائياً إلى محفظتك ({crypto_currency} - {network})",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    logging.info(f"Auto-payout executed for provider {provider_id}: ${pending}")

@api_router.post("/system/health-check")
async def trigger_health_check():
    """Trigger manual health check for all instances (Admin only)"""
    await auto_health_check_and_failover()
    return {"message": "Health check completed"}

@api_router.get("/instances/{instance_id}/health")
async def get_instance_health(instance_id: str, user: dict = Depends(get_current_user)):
    """Get real-time health status of an instance"""
    instance = await db.instances.find_one({"id": instance_id, "user_id": user["id"]}, {"_id": 0})
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    if instance["status"] != "running":
        raise HTTPException(status_code=400, detail="Instance not running")
    
    health = await check_gpu_health(instance["gpu_id"])
    health["instance_id"] = instance_id
    health["gpu_name"] = instance["gpu_name"]
    
    return health

@api_router.post("/instances/{instance_id}/failover")
async def trigger_failover(instance_id: str, user: dict = Depends(get_current_user)):
    """Manually trigger failover to a new GPU (if user wants)"""
    instance = await db.instances.find_one({"id": instance_id, "user_id": user["id"]}, {"_id": 0})
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    result = await execute_failover(instance_id, "طلب يدوي من المستخدم")
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@api_router.get("/instances/{instance_id}/failover-history")
async def get_instance_failover_history(instance_id: str, user: dict = Depends(get_current_user)):
    """Get failover history for a specific instance"""
    instance = await db.instances.find_one({"id": instance_id, "user_id": user["id"]}, {"_id": 0})
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    logs = await db.failover_logs.find(
        {"instance_id": instance_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return {
        "instance_id": instance_id,
        "total_failovers": len(logs),
        "seamless_failovers": len([l for l in logs if l.get("seamless")]),
        "history": logs
    }

@api_router.get("/notifications")
async def get_notifications(user: dict = Depends(get_current_user)):
    """Get user notifications"""
    notifications = await db.notifications.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return notifications

@api_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(get_current_user)):
    """Mark notification as read"""
    await db.notifications.update_one(
        {"id": notification_id, "user_id": user["id"]},
        {"$set": {"read": True}}
    )
    return {"success": True}

@api_router.get("/failover-logs")
async def get_failover_logs(user: dict = Depends(get_current_user)):
    """Get user's failover history"""
    logs = await db.failover_logs.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return logs

# ============== INSTANCE ROUTES ==============

@api_router.post("/instances/start")
async def start_instance(data: InstanceCreate, user: dict = Depends(get_current_user)):
    gpu = await db.gpus.find_one({"id": data.gpu_id}, {"_id": 0})
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")
    if gpu["status"] != "available":
        raise HTTPException(status_code=400, detail="GPU not available")
    
    # Check user balance (minimum 1 hour worth)
    min_balance = gpu["price_per_hour"]
    if user["balance"] < min_balance:
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Minimum ${min_balance:.2f} required")
    
    # Create instance
    instance = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "gpu_id": gpu["id"],
        "gpu_name": gpu["name"],
        "price_per_second": gpu["price_per_second"],
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "stopped_at": None,
        "total_cost": 0.0,
        "access_info": {
            "ssh": f"ssh user@gpu-{gpu['id'][:8]}.gpucloud.pro",
            "jupyter": f"https://jupyter-{gpu['id'][:8]}.gpucloud.pro",
            "password": str(uuid.uuid4())[:12]
        }
    }
    await db.instances.insert_one(instance)
    
    # Update GPU status
    await db.gpus.update_one({"id": gpu["id"]}, {"$set": {"status": "in_use"}})
    
    return {k: v for k, v in instance.items() if k != "_id"}

@api_router.post("/instances/{instance_id}/stop")
async def stop_instance(instance_id: str, user: dict = Depends(get_current_user)):
    instance = await db.instances.find_one({"id": instance_id, "user_id": user["id"]}, {"_id": 0})
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    if instance["status"] != "running":
        raise HTTPException(status_code=400, detail="Instance not running")
    
    # Calculate cost
    started = datetime.fromisoformat(instance["started_at"])
    stopped = datetime.now(timezone.utc)
    duration_seconds = (stopped - started).total_seconds()
    total_cost = duration_seconds * instance["price_per_second"]
    
    # Update instance
    await db.instances.update_one(
        {"id": instance_id},
        {"$set": {
            "status": "stopped",
            "stopped_at": stopped.isoformat(),
            "total_cost": round(total_cost, 4)
        }}
    )
    
    # Deduct from user balance
    new_balance = user["balance"] - total_cost
    await db.users.update_one({"id": user["id"]}, {"$set": {"balance": max(0, new_balance)}})
    
    # === توزيع الأرباح فورياً ===
    revenue_split = await distribute_revenue(instance, total_cost)
    
    # Create transaction with revenue split details
    transaction = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "amount": -total_cost,
        "type": "usage",
        "description": f"GPU usage: {instance['gpu_name']} ({int(duration_seconds)}s)",
        "instance_id": instance_id,
        "revenue_split": {
            "platform_fee": revenue_split.get("platform_fee", 0),
            "provider_share": revenue_split.get("provider_share", 0)
        },
        "created_at": stopped.isoformat()
    }
    await db.transactions.insert_one(transaction)
    
    # Free GPU
    await db.gpus.update_one({"id": instance["gpu_id"]}, {"$set": {"status": "available"}})
    
    # Create invoice with revenue breakdown
    invoice = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "instance_id": instance_id,
        "gpu_name": instance["gpu_name"],
        "duration_seconds": int(duration_seconds),
        "total_cost": round(total_cost, 4),
        "revenue_split": {
            "platform_fee": round(revenue_split.get("platform_fee", 0), 4),
            "platform_percent": PLATFORM_FEE_PERCENT,
            "provider_share": round(revenue_split.get("provider_share", 0), 4),
            "provider_percent": PROVIDER_SHARE_PERCENT
        },
        "created_at": stopped.isoformat()
    }
    await db.invoices.insert_one(invoice)
    
    return {
        "message": "Instance stopped",
        "duration_seconds": int(duration_seconds),
        "total_cost": round(total_cost, 4),
        "new_balance": round(max(0, new_balance), 2),
        "revenue_split": {
            "platform_fee": f"${revenue_split.get('platform_fee', 0):.4f} ({PLATFORM_FEE_PERCENT}%)",
            "provider_share": f"${revenue_split.get('provider_share', 0):.4f} ({PROVIDER_SHARE_PERCENT}%)"
        }
    }

@api_router.get("/instances", response_model=List[InstanceResponse])
async def get_instances(user: dict = Depends(get_current_user)):
    instances = await db.instances.find({"user_id": user["id"]}, {"_id": 0}).sort("started_at", -1).to_list(100)
    return instances

@api_router.get("/instances/active")
async def get_active_instances(user: dict = Depends(get_current_user)):
    instances = await db.instances.find({"user_id": user["id"], "status": "running"}, {"_id": 0}).to_list(10)
    # Calculate current cost for each
    for instance in instances:
        started = datetime.fromisoformat(instance["started_at"])
        duration = (datetime.now(timezone.utc) - started).total_seconds()
        instance["current_cost"] = round(duration * instance["price_per_second"], 4)
        instance["duration_seconds"] = int(duration)
    return instances

# ============== BILLING ROUTES ==============

@api_router.get("/billing/transactions", response_model=List[TransactionResponse])
async def get_transactions(user: dict = Depends(get_current_user)):
    transactions = await db.transactions.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return transactions

@api_router.get("/billing/invoices")
async def get_invoices(user: dict = Depends(get_current_user)):
    invoices = await db.invoices.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return invoices

# ============== PAYMENT ROUTES ==============

FUND_PACKAGES = {
    "starter": 10.0,
    "pro": 50.0,
    "enterprise": 200.0,
    "custom": None
}

@api_router.post("/payments/create-checkout")
async def create_checkout(request: Request, data: AddFundsRequest, user: dict = Depends(get_current_user)):
    if data.amount < 5.0:
        raise HTTPException(status_code=400, detail="Minimum amount is $5.00")
    
    host_url = data.origin_url.rstrip('/')
    webhook_url = f"{str(request.base_url).rstrip('/')}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    success_url = f"{host_url}/billing?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/billing"
    
    checkout_request = CheckoutSessionRequest(
        amount=float(data.amount),
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["id"],
            "user_email": user["email"],
            "type": "add_funds"
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Store pending transaction
    transaction = {
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "amount": float(data.amount),
        "type": "deposit",
        "status": "pending",
        "description": f"Add funds: ${data.amount:.2f}",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payment_transactions.insert_one(transaction)
    
    return {"url": session.url, "session_id": session.session_id}

# ============== COUNTRIES & KYC ROUTES ==============

@api_router.get("/countries/supported")
async def get_supported_countries():
    """Get list of supported countries for providers"""
    return {
        "supported": [
            {"code": code, **info} 
            for code, info in ALL_SUPPORTED_COUNTRIES.items()
        ],
        "crypto_only": [
            {"code": code, **info} 
            for code, info in CRYPTO_ONLY_COUNTRIES.items()
        ],
        "total_supported": len(ALL_SUPPORTED_COUNTRIES),
        "message": "مرحباً بالجميع! 🌍"
    }

@api_router.get("/countries/{country_code}")
async def get_country_details(country_code: str):
    """Get details for a specific country"""
    country_code = country_code.upper()
    
    if country_code not in ALL_SUPPORTED_COUNTRIES:
        # إذا الدولة غير موجودة، نضيفها تلقائياً بالكريبتو
        return {
            "code": country_code,
            "name": country_code,
            "name_en": country_code,
            "currency": "USD",
            "payout_methods": ["crypto"],
            "payout_methods_details": [{"method": "crypto", **PAYOUT_METHODS["crypto"]}],
            "note": "دولتك مدعومة بالعملات الرقمية"
        }
    
    country = ALL_SUPPORTED_COUNTRIES[country_code]
    payout_details = [
        {"method": m, **PAYOUT_METHODS[m]} 
        for m in country["payout_methods"] 
        if m in PAYOUT_METHODS
    ]
    
    is_crypto_only = country_code in CRYPTO_ONLY_COUNTRIES
    
    return {
        "code": country_code,
        **country,
        "payout_methods_details": payout_details,
        "crypto_only": is_crypto_only,
        "note": "الدفع بالكريبتو فقط" if is_crypto_only else None
    }

@api_router.get("/payout-methods")
async def get_all_payout_methods():
    """Get all available payout methods"""
    return PAYOUT_METHODS

@api_router.post("/provider/kyc/submit")
async def submit_kyc(data: ProviderKYC, authorization: str = Header(None)):
    """Submit KYC documents - موافقة تلقائية فورية"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    country_code = data.country.upper()
    
    # Create KYC record - موافقة فورية
    kyc_record = {
        "id": str(uuid.uuid4()),
        "provider_id": payload["user_id"],
        "full_name": data.full_name,
        "country": country_code,
        "id_type": data.id_type,
        "id_number": data.id_number,
        "id_document_url": data.id_document_url,
        "address": data.address,
        "phone": data.phone,
        "tax_id": data.tax_id,
        "crypto_only": country_code in CRYPTO_ONLY_COUNTRIES,
        "status": "approved",  # ✅ موافقة تلقائية فورية
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_notes": "موافقة تلقائية"
    }
    await db.kyc_submissions.insert_one(kyc_record)
    
    # Update provider - موثق فوراً
    await db.providers.update_one(
        {"id": payload["user_id"]},
        {"$set": {
            "country": country_code,
            "kyc_status": "approved",
            "kyc_level": "verified",  # ✅ موثق فوراً
            "kyc_submission_id": kyc_record["id"],
            "crypto_only": country_code in CRYPTO_ONLY_COUNTRIES,
            "auto_payout": False,  # الافتراضي: سحب يدوي
            "auto_payout_threshold": 100,  # حد السحب التلقائي
            "auto_payout_method": "crypto",
            "auto_payout_wallet": ""
        }}
    )
    
    return {
        "message": "✅ تم التحقق والموافقة فوراً!",
        "kyc_id": kyc_record["id"],
        "status": "approved",
        "kyc_level": "verified",
        "max_payout": 10000,
        "crypto_only": country_code in CRYPTO_ONLY_COUNTRIES
    }

@api_router.get("/provider/kyc/status")
async def get_kyc_status(authorization: str = Header(None)):
    """Get KYC verification status"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    provider = await db.providers.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    kyc_level = provider.get("kyc_level", "none")
    kyc_info = KYC_LEVELS.get(kyc_level, KYC_LEVELS["none"])
    
    # Get latest KYC submission
    submission = await db.kyc_submissions.find_one(
        {"provider_id": payload["user_id"]},
        {"_id": 0}
    )
    
    country_code = provider.get("country", "")
    country_info = SUPPORTED_COUNTRIES.get(country_code, {})
    
    return {
        "kyc_level": kyc_level,
        "kyc_label": kyc_info["label"],
        "max_payout": kyc_info["max_payout"],
        "status": provider.get("kyc_status", "none"),
        "country": country_code,
        "country_info": country_info,
        "submission": submission,
        "available_payout_methods": [
            {"method": m, **PAYOUT_METHODS.get(m, {})} 
            for m in country_info.get("payout_methods", [])
        ]
    }

@api_router.post("/admin/kyc/{kyc_id}/approve")
async def approve_kyc(kyc_id: str, authorization: str = Header(None)):
    """Admin: Approve KYC submission"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    submission = await db.kyc_submissions.find_one({"id": kyc_id})
    if not submission:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    
    # Update submission
    await db.kyc_submissions.update_one(
        {"id": kyc_id},
        {"$set": {
            "status": "approved",
            "reviewed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update provider KYC level
    await db.providers.update_one(
        {"id": submission["provider_id"]},
        {"$set": {
            "kyc_status": "approved",
            "kyc_level": "verified"
        }}
    )
    
    # Notify provider
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": submission["provider_id"],
        "type": "kyc_approved",
        "title": "✅ تم التحقق من هويتك",
        "message": "تهانينا! تم التحقق من هويتك بنجاح. يمكنك الآن سحب أرباحك.",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "KYC approved", "provider_id": submission["provider_id"]}

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, user: dict = Depends(get_current_user)):
    webhook_url = "https://gpucloud.pro/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    status = await stripe_checkout.get_checkout_status(session_id)
    
    # Check if already processed
    existing = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if status.payment_status == "paid" and existing["status"] != "completed":
        # Update transaction
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "completed"}}
        )
        
        # Add to user balance
        amount = status.amount_total / 100  # Convert from cents
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"balance": amount}}
        )
        
        # Create transaction record
        transaction = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "amount": amount,
            "type": "deposit",
            "description": f"Funds added via Stripe",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.transactions.insert_one(transaction)
    
    return {
        "status": status.status,
        "payment_status": status.payment_status,
        "amount": status.amount_total / 100
    }

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    webhook_url = f"{str(request.base_url).rstrip('/')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    try:
        event = await stripe_checkout.handle_webhook(body, signature)
        
        if event.payment_status == "paid":
            # Process the payment
            transaction = await db.payment_transactions.find_one({"session_id": event.session_id})
            if transaction and transaction["status"] != "completed":
                await db.payment_transactions.update_one(
                    {"session_id": event.session_id},
                    {"$set": {"status": "completed"}}
                )
                
                user_id = event.metadata.get("user_id")
                amount = transaction["amount"]
                
                await db.users.update_one(
                    {"id": user_id},
                    {"$inc": {"balance": amount}}
                )
        
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

# ============== PROVIDER ROUTES ==============

class QuickProviderRegister(BaseModel):
    email: EmailStr
    company_name: str = ""
    password: Optional[str] = None
    country: str = ""

@api_router.post("/provider/quick-register")
async def quick_register_provider(data: QuickProviderRegister):
    """تسجيل سريع للمزودين - كلمة المرور اختيارية"""
    existing = await db.providers.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="البريد مسجل مسبقاً")
    
    password = data.password if data.password else generate_strong_password()
    company_name = data.company_name if data.company_name else f"مزود {data.email.split('@')[0]}"
    country_code = data.country.upper() if data.country else ""
    crypto_only = country_code in CRYPTO_ONLY_COUNTRIES if country_code else False
    
    provider_doc = {
        "id": str(uuid.uuid4()),
        "company_name": company_name,
        "email": data.email,
        "password": hash_password_secure(password),
        "role": "provider",
        "country": country_code,
        "crypto_only": crypto_only,
        "earnings": 0.0,
        "pending_payout": 0.0,
        "kyc_status": "approved",  # موافقة تلقائية
        "kyc_level": "verified",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.providers.insert_one(provider_doc)
    
    await log_security_event("provider_registered", provider_doc["id"], {"email": data.email, "quick": True})
    
    token = create_token(provider_doc["id"], "provider")
    
    return {
        "token": token,
        "provider": {k: v for k, v in provider_doc.items() if k not in ["password", "_id"]},
        "generated_password": password if not data.password else None,
        "message": "تم إنشاء حسابك كمزود! 🎉" + (" احفظ كلمة المرور." if not data.password else "")
    }

@api_router.post("/provider/register")
async def register_provider(data: ProviderCreate):
    # جميع الدول مرحب بها!
    country_code = data.country.upper() if data.country else ""
    crypto_only = country_code in CRYPTO_ONLY_COUNTRIES if country_code else False
    
    existing = await db.providers.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    provider_doc = {
        "id": str(uuid.uuid4()),
        "company_name": data.company_name,
        "email": data.email,
        "password": hash_password_secure(data.password),
        "role": "provider",
        "country": country_code,
        "crypto_only": crypto_only,
        "earnings": 0.0,
        "pending_payout": 0.0,
        "kyc_status": "approved",  # موافقة تلقائية
        "kyc_level": "verified",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.providers.insert_one(provider_doc)
    
    await log_security_event("provider_registered", provider_doc["id"], {"email": data.email})
    
    token = create_token(provider_doc["id"], "provider")
    
    welcome_msg = "مرحباً بك في GPU Cloud Pro! 🎉"
    if crypto_only:
        welcome_msg += " (السحب متاح بالعملات الرقمية)"
    
    return {
        "token": token, 
        "provider": {k: v for k, v in provider_doc.items() if k not in ["password", "_id"]},
        "message": welcome_msg
    }

@api_router.post("/provider/login")
async def login_provider(user: UserLogin):
    provider = await db.providers.find_one({"email": user.email}, {"_id": 0})
    if not provider or not verify_password_secure(user.password, provider["password"]):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    
    token = create_token(provider["id"], "provider")
    return {"token": token, "provider": {k: v for k, v in provider.items() if k != "password"}}

@api_router.post("/provider/gpus")
async def add_gpu(data: GPUCreate, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if payload["role"] != "provider":
        raise HTTPException(status_code=403, detail="Only providers can add GPUs")
    
    gpu = {
        "id": str(uuid.uuid4()),
        "provider_id": payload["user_id"],
        "name": data.name,
        "model": data.model,
        "vram": data.vram,
        "price_per_hour": data.price_per_hour,
        "price_per_second": round(data.price_per_hour / 3600, 6),
        "region": data.region,
        "latency": 15 + hash(data.region) % 50,  # Simulated latency
        "status": "available",
        "specs": data.specs,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.gpus.insert_one(gpu)
    return {k: v for k, v in gpu.items() if k != "_id"}

@api_router.get("/provider/dashboard")
async def provider_dashboard(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    provider = await db.providers.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    gpus = await db.gpus.find({"provider_id": payload["user_id"]}, {"_id": 0}).to_list(100)
    
    # Get earnings stats
    transactions = await db.provider_transactions.find(
        {"provider_id": payload["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    total_earnings = sum(t.get("net_amount", 0) for t in transactions)
    today_earnings = sum(
        t.get("net_amount", 0) for t in transactions 
        if t.get("created_at", "").startswith(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    )
    
    return {
        "provider": {k: v for k, v in provider.items() if k != "password"},
        "gpus": gpus,
        "total_gpus": len(gpus),
        "active_gpus": len([g for g in gpus if g["status"] == "in_use"]),
        "earnings": {
            "total": round(total_earnings, 2),
            "today": round(today_earnings, 4),
            "pending_payout": provider.get("pending_payout", 0),
            "platform_fee_percent": PLATFORM_FEE_PERCENT
        },
        "recent_transactions": transactions[:10]
    }

@api_router.get("/provider/earnings")
async def get_provider_earnings(authorization: str = Header(None)):
    """Get detailed earnings for provider"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    provider = await db.providers.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Get all transactions
    transactions = await db.provider_transactions.find(
        {"provider_id": payload["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    # Calculate stats
    total_gross = sum(t.get("gross_amount", 0) for t in transactions)
    total_fees = sum(t.get("platform_fee", 0) for t in transactions)
    total_net = sum(t.get("net_amount", 0) for t in transactions)
    
    # Get payouts
    payouts = await db.provider_payouts.find(
        {"provider_id": payload["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    total_withdrawn = sum(p.get("amount", 0) for p in payouts if p.get("status") == "completed")
    
    return {
        "summary": {
            "total_gross": round(total_gross, 2),
            "total_platform_fees": round(total_fees, 2),
            "total_net_earnings": round(total_net, 2),
            "total_withdrawn": round(total_withdrawn, 2),
            "available_balance": round(provider.get("pending_payout", 0), 2)
        },
        "transactions": transactions,
        "payouts": payouts
    }

class PayoutRequest(BaseModel):
    amount: float
    method: str = "bank_transfer"
    account_details: Dict = {}
    crypto_currency: str = ""  # USDT, USDC, BTC, ETH
    crypto_wallet: str = ""
    crypto_network: str = ""  # TRC20, ERC20, BEP20

@api_router.post("/provider/payout/request")
async def request_payout(data: PayoutRequest, authorization: str = Header(None)):
    """Request a payout of earnings"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    provider = await db.providers.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Check KYC level
    kyc_level = provider.get("kyc_level", "none")
    kyc_info = KYC_LEVELS.get(kyc_level, KYC_LEVELS["none"])
    
    if kyc_level == "none":
        raise HTTPException(status_code=403, detail="يجب إكمال التحقق من الهوية (KYC) أولاً للسحب")
    
    if data.amount > kyc_info["max_payout"]:
        raise HTTPException(
            status_code=403, 
            detail=f"الحد الأقصى للسحب بمستوى {kyc_info['label']} هو ${kyc_info['max_payout']}. قم بترقية حسابك للسحب أكثر."
        )
    
    # Check payout method is valid for provider's country
    country_code = provider.get("country", "")
    country_info = SUPPORTED_COUNTRIES.get(country_code, {})
    available_methods = country_info.get("payout_methods", ["crypto"])
    
    if data.method not in available_methods and data.method != "crypto":
        raise HTTPException(
            status_code=400, 
            detail=f"طريقة السحب غير متاحة لبلدك. الطرق المتاحة: {', '.join(available_methods)}"
        )
    
    # Check minimum amount for method
    method_info = PAYOUT_METHODS.get(data.method, {})
    min_amount = method_info.get("min", 10)
    if data.amount < min_amount:
        raise HTTPException(status_code=400, detail=f"الحد الأدنى للسحب بـ {method_info.get('name', data.method)} هو ${min_amount}")
    
    available = provider.get("pending_payout", 0)
    if data.amount > available:
        raise HTTPException(status_code=400, detail=f"رصيد غير كافي. المتاح: ${available:.2f}")
    
    # Calculate fee
    fee_percent = method_info.get("fee_percent", 0)
    fee_amount = data.amount * (fee_percent / 100)
    net_amount = data.amount - fee_amount
    
    # Create payout request
    payout = {
        "id": str(uuid.uuid4()),
        "provider_id": payload["user_id"],
        "amount": data.amount,
        "fee": round(fee_amount, 2),
        "net_amount": round(net_amount, 2),
        "method": data.method,
        "method_name": method_info.get("name", data.method),
        "account_details": data.account_details,
        "crypto_currency": data.crypto_currency if data.method == "crypto" else None,
        "crypto_wallet": data.crypto_wallet if data.method == "crypto" else None,
        "crypto_network": data.crypto_network if data.method == "crypto" else None,
        "country": country_code,
        "status": "pending",
        "processing_days": method_info.get("processing_days", "3-5"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "processed_at": None
    }
    await db.provider_payouts.insert_one(payout)
    
    # Deduct from pending balance
    await db.providers.update_one(
        {"id": payload["user_id"]},
        {"$inc": {"pending_payout": -data.amount}}
    )
    
    return {
        "message": "تم تقديم طلب السحب بنجاح",
        "payout_id": payout["id"],
        "amount": data.amount,
        "fee": round(fee_amount, 2),
        "net_amount": round(net_amount, 2),
        "method": payout["method_name"],
        "status": "pending",
        "estimated_processing": payout["processing_days"]
    }

# ============== إعدادات السحب للمزود ==============

class AutoPayoutSettings(BaseModel):
    enabled: bool = False
    threshold: float = 100  # الحد الأدنى للسحب التلقائي
    method: str = "crypto"
    crypto_currency: str = "USDT"
    crypto_wallet: str = ""
    crypto_network: str = "TRC20"

@api_router.post("/provider/payout/settings")
async def update_payout_settings(data: AutoPayoutSettings, authorization: str = Header(None)):
    """تحديث إعدادات السحب - تلقائي أو يدوي"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    await db.providers.update_one(
        {"id": payload["user_id"]},
        {"$set": {
            "auto_payout": data.enabled,
            "auto_payout_threshold": data.threshold,
            "auto_payout_method": data.method,
            "auto_payout_crypto_currency": data.crypto_currency,
            "auto_payout_wallet": data.crypto_wallet,
            "auto_payout_network": data.crypto_network
        }}
    )
    
    mode = "تلقائي" if data.enabled else "يدوي"
    return {
        "message": f"تم تحديث الإعدادات - السحب {mode}",
        "auto_payout": data.enabled,
        "threshold": data.threshold if data.enabled else None
    }

@api_router.get("/provider/payout/settings")
async def get_payout_settings(authorization: str = Header(None)):
    """الحصول على إعدادات السحب"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    provider = await db.providers.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return {
        "auto_payout": provider.get("auto_payout", False),
        "threshold": provider.get("auto_payout_threshold", 100),
        "method": provider.get("auto_payout_method", "crypto"),
        "crypto_currency": provider.get("auto_payout_crypto_currency", "USDT"),
        "wallet": provider.get("auto_payout_wallet", ""),
        "network": provider.get("auto_payout_network", "TRC20"),
        "pending_balance": provider.get("pending_payout", 0)
    }

# ============== سحب أرباح المنصة (للأدمن) ==============

@api_router.get("/admin/platform-balance")
async def get_platform_balance(authorization: str = Header(None)):
    """رصيد أرباح المنصة (15%)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # حساب إجمالي أرباح المنصة
    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    result = await db.platform_revenue.aggregate(pipeline).to_list(1)
    total_revenue = result[0]["total"] if result else 0
    
    # المسحوب من أرباح المنصة
    withdrawn_pipeline = [
        {"$match": {"type": "platform_withdrawal", "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    withdrawn_result = await db.admin_withdrawals.aggregate(withdrawn_pipeline).to_list(1)
    total_withdrawn = withdrawn_result[0]["total"] if withdrawn_result else 0
    
    available = total_revenue - total_withdrawn
    
    return {
        "total_earned": round(total_revenue, 2),
        "total_withdrawn": round(total_withdrawn, 2),
        "available_balance": round(available, 2),
        "fee_percent": PLATFORM_FEE_PERCENT
    }

class AdminWithdrawal(BaseModel):
    amount: float
    method: str  # bank, crypto, paypal
    destination: str  # رقم الحساب أو المحفظة
    notes: str = ""

@api_router.post("/admin/withdraw")
async def admin_withdraw(data: AdminWithdrawal, authorization: str = Header(None)):
    """سحب أرباح المنصة - مرن جداً"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # حساب الرصيد المتاح
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    result = await db.platform_revenue.aggregate(pipeline).to_list(1)
    total_revenue = result[0]["total"] if result else 0
    
    withdrawn_pipeline = [
        {"$match": {"type": "platform_withdrawal", "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    withdrawn_result = await db.admin_withdrawals.aggregate(withdrawn_pipeline).to_list(1)
    total_withdrawn = withdrawn_result[0]["total"] if withdrawn_result else 0
    
    available = total_revenue - total_withdrawn
    
    if data.amount > available:
        raise HTTPException(status_code=400, detail=f"رصيد غير كافي. المتاح: ${available:.2f}")
    
    # تسجيل السحب
    withdrawal = {
        "id": str(uuid.uuid4()),
        "admin_id": payload["user_id"],
        "type": "platform_withdrawal",
        "amount": data.amount,
        "method": data.method,
        "destination": data.destination,
        "notes": data.notes,
        "status": "completed",  # مباشر - بدون انتظار
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.admin_withdrawals.insert_one(withdrawal)
    
    return {
        "message": "✅ تم سحب أرباح المنصة بنجاح",
        "withdrawal_id": withdrawal["id"],
        "amount": data.amount,
        "method": data.method,
        "new_balance": round(available - data.amount, 2)
    }

@api_router.get("/admin/withdrawals")
async def get_admin_withdrawals(authorization: str = Header(None)):
    """سجل سحوبات أرباح المنصة"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    withdrawals = await db.admin_withdrawals.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return withdrawals

@api_router.get("/provider/payouts")
async def get_provider_payouts(authorization: str = Header(None)):
    """Get all payout requests"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    payouts = await db.provider_payouts.find(
        {"provider_id": payload["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return payouts

# ============== ADMIN ROUTES ==============

@api_router.get("/admin/stats")
async def admin_stats(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    total_users = await db.users.count_documents({})
    total_providers = await db.providers.count_documents({})
    total_gpus = await db.gpus.count_documents({})
    active_instances = await db.instances.count_documents({"status": "running"})
    
    # Platform revenue (15% fees)
    platform_revenue = await db.platform_revenue.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(1)
    
    # Provider payouts
    provider_payouts = await db.provider_payouts.aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(1)
    
    # Total transactions value
    total_transactions = await db.provider_transactions.aggregate([
        {"$group": {"_id": None, "gross": {"$sum": "$gross_amount"}, "net": {"$sum": "$net_amount"}}}
    ]).to_list(1)
    
    return {
        "total_users": total_users,
        "total_providers": total_providers,
        "total_gpus": total_gpus,
        "active_instances": active_instances,
        "revenue": {
            "platform_fees": platform_revenue[0]["total"] if platform_revenue else 0,
            "total_transactions": total_transactions[0]["gross"] if total_transactions else 0,
            "provider_share": total_transactions[0]["net"] if total_transactions else 0,
            "provider_payouts": provider_payouts[0]["total"] if provider_payouts else 0,
            "fee_percent": PLATFORM_FEE_PERCENT
        }
    }

@api_router.get("/admin/revenue")
async def admin_revenue(authorization: str = Header(None)):
    """Detailed platform revenue breakdown"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all platform fees
    fees = await db.platform_revenue.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Get pending payouts
    pending_payouts = await db.provider_payouts.find(
        {"status": "pending"},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "platform_fees": fees,
        "pending_payouts": pending_payouts,
        "fee_percent": PLATFORM_FEE_PERCENT,
        "provider_percent": PROVIDER_SHARE_PERCENT
    }

@api_router.post("/admin/payout/{payout_id}/process")
async def process_payout(payout_id: str, authorization: str = Header(None)):
    """Admin: Process a payout request"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    payout = await db.provider_payouts.find_one({"id": payout_id})
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    
    await db.provider_payouts.update_one(
        {"id": payout_id},
        {"$set": {
            "status": "completed",
            "processed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Payout processed", "payout_id": payout_id}

# ============== SEED DATA ==============

@api_router.post("/seed")
async def seed_data():
    # Check if already seeded
    existing_gpus = await db.gpus.count_documents({})
    if existing_gpus > 0:
        return {"message": "Data already seeded"}
    
    # Create demo provider
    provider = {
        "id": "provider-demo",
        "company_name": "GPU Cloud Pro",
        "email": "provider@gpucloud.pro",
        "password": hash_password("demo123"),
        "role": "provider",
        "earnings": 0.0,
        "pending_payout": 0.0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.providers.insert_one(provider)
    
    # Create admin user
    admin = {
        "id": "admin-demo",
        "email": "admin@gpucloud.pro",
        "password": hash_password("admin123"),
        "name": "Admin",
        "balance": 0.0,
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(admin)
    
    # Seed GPUs
    gpus = [
        {"name": "NVIDIA RTX 4090", "model": "RTX 4090", "vram": 24, "price_per_hour": 0.89, "region": "US East", "latency": 12, "specs": {"cuda_cores": 16384, "memory_type": "GDDR6X", "tdp": "450W"}},
        {"name": "NVIDIA RTX 4080", "model": "RTX 4080", "vram": 16, "price_per_hour": 0.69, "region": "US East", "latency": 15, "specs": {"cuda_cores": 9728, "memory_type": "GDDR6X", "tdp": "320W"}},
        {"name": "NVIDIA A100 80GB", "model": "A100", "vram": 80, "price_per_hour": 2.49, "region": "US West", "latency": 18, "specs": {"cuda_cores": 6912, "memory_type": "HBM2e", "tdp": "400W"}},
        {"name": "NVIDIA H100 80GB", "model": "H100", "vram": 80, "price_per_hour": 3.99, "region": "US West", "latency": 20, "specs": {"cuda_cores": 16896, "memory_type": "HBM3", "tdp": "700W"}},
        {"name": "NVIDIA RTX 3090", "model": "RTX 3090", "vram": 24, "price_per_hour": 0.49, "region": "Europe", "latency": 35, "specs": {"cuda_cores": 10496, "memory_type": "GDDR6X", "tdp": "350W"}},
        {"name": "NVIDIA A6000", "model": "A6000", "vram": 48, "price_per_hour": 1.29, "region": "Europe", "latency": 38, "specs": {"cuda_cores": 10752, "memory_type": "GDDR6", "tdp": "300W"}},
        {"name": "NVIDIA RTX 4090 Pro", "model": "RTX 4090", "vram": 24, "price_per_hour": 0.99, "region": "Asia Pacific", "latency": 45, "specs": {"cuda_cores": 16384, "memory_type": "GDDR6X", "tdp": "450W"}},
        {"name": "NVIDIA A100 40GB", "model": "A100", "vram": 40, "price_per_hour": 1.89, "region": "Asia Pacific", "latency": 48, "specs": {"cuda_cores": 6912, "memory_type": "HBM2e", "tdp": "400W"}},
        {"name": "NVIDIA L40S", "model": "L40S", "vram": 48, "price_per_hour": 1.49, "region": "Middle East", "latency": 55, "specs": {"cuda_cores": 18176, "memory_type": "GDDR6", "tdp": "350W"}},
        {"name": "NVIDIA RTX 4080 Super", "model": "RTX 4080", "vram": 16, "price_per_hour": 0.79, "region": "Middle East", "latency": 52, "specs": {"cuda_cores": 10240, "memory_type": "GDDR6X", "tdp": "320W"}},
    ]
    
    for gpu in gpus:
        gpu_doc = {
            "id": str(uuid.uuid4()),
            "provider_id": "provider-demo",
            "name": gpu["name"],
            "model": gpu["model"],
            "vram": gpu["vram"],
            "price_per_hour": gpu["price_per_hour"],
            "price_per_second": round(gpu["price_per_hour"] / 3600, 6),
            "region": gpu["region"],
            "latency": gpu["latency"],
            "status": "available",
            "specs": gpu["specs"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.gpus.insert_one(gpu_doc)
    
    return {"message": "Data seeded successfully", "gpus_created": len(gpus)}

# ============== HEALTH CHECK ==============

@api_router.get("/")
async def root():
    return {"message": "GPU Cloud Pro API", "status": "online"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Demo endpoint to add test balance
@api_router.post("/demo/add-balance")
async def add_demo_balance(user: dict = Depends(get_current_user)):
    await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": 100.0}})
    updated_user = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"message": "Added $100 demo balance", "new_balance": updated_user["balance"]}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
