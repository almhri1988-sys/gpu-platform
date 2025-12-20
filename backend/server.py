from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Header
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
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'gpu_cloud_pro_secret_key_2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Stripe Config
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', 'sk_test_emergent')

# Create the main app
app = FastAPI(title="GPU Cloud Pro API")
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
    model_config = ConfigDict(extra="ignore")
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

class GPUCreate(BaseModel):
    name: str
    model: str
    vram: int
    price_per_hour: float
    region: str
    specs: Dict = {}

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

@api_router.post("/auth/register")
async def register(user: UserCreate):
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "password": hash_password(user.password),
        "name": user.name,
        "balance": 0.0,
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    token = create_token(user_doc["id"], "user")
    return {"token": token, "user": {k: v for k, v in user_doc.items() if k not in ["password", "_id"]}}

@api_router.post("/auth/login")
async def login(user: UserLogin):
    db_user = await db.users.find_one({"email": user.email}, {"_id": 0})
    if not db_user or db_user["password"] != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(db_user["id"], db_user["role"])
    return {"token": token, "user": {k: v for k, v in db_user.items() if k != "password"}}

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
    return gpus

@api_router.get("/gpus/{gpu_id}", response_model=GPUResponse)
async def get_gpu(gpu_id: str):
    gpu = await db.gpus.find_one({"id": gpu_id}, {"_id": 0})
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")
    return gpu

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
    
    # Create transaction
    transaction = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "amount": -total_cost,
        "type": "usage",
        "description": f"GPU usage: {instance['gpu_name']} ({int(duration_seconds)}s)",
        "instance_id": instance_id,
        "created_at": stopped.isoformat()
    }
    await db.transactions.insert_one(transaction)
    
    # Free GPU
    await db.gpus.update_one({"id": instance["gpu_id"]}, {"$set": {"status": "available"}})
    
    # Create invoice
    invoice = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "instance_id": instance_id,
        "gpu_name": instance["gpu_name"],
        "duration_seconds": int(duration_seconds),
        "total_cost": round(total_cost, 4),
        "created_at": stopped.isoformat()
    }
    await db.invoices.insert_one(invoice)
    
    return {
        "message": "Instance stopped",
        "duration_seconds": int(duration_seconds),
        "total_cost": round(total_cost, 4),
        "new_balance": round(max(0, new_balance), 2)
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

@api_router.post("/provider/register")
async def register_provider(data: ProviderCreate):
    existing = await db.providers.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    provider_doc = {
        "id": str(uuid.uuid4()),
        "company_name": data.company_name,
        "email": data.email,
        "password": hash_password(data.password),
        "role": "provider",
        "earnings": 0.0,
        "pending_payout": 0.0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.providers.insert_one(provider_doc)
    token = create_token(provider_doc["id"], "provider")
    return {"token": token, "provider": {k: v for k, v in provider_doc.items() if k not in ["password", "_id"]}}

@api_router.post("/provider/login")
async def login_provider(user: UserLogin):
    provider = await db.providers.find_one({"email": user.email}, {"_id": 0})
    if not provider or provider["password"] != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
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
    
    return {
        "provider": {k: v for k, v in provider.items() if k != "password"},
        "gpus": gpus,
        "total_gpus": len(gpus),
        "active_gpus": len([g for g in gpus if g["status"] == "in_use"])
    }

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
    
    revenue_pipeline = [
        {"$match": {"type": "deposit", "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    revenue = await db.payment_transactions.aggregate(revenue_pipeline).to_list(1)
    
    return {
        "total_users": total_users,
        "total_providers": total_providers,
        "total_gpus": total_gpus,
        "active_instances": active_instances,
        "total_revenue": revenue[0]["total"] if revenue else 0
    }

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
