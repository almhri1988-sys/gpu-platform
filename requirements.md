# GPU Cloud Pro - منصة تأجير GPU

## المشروع
منصة تأجير وحدات GPU عبر الإنترنت مشابهة لـ RunPod و Vast.ai مع فوترة بالثانية.

## الميزات المُنجزة

### نظام المستخدمين
- ✅ تسجيل حساب جديد
- ✅ تسجيل دخول / خروج
- ✅ لوحة تحكم شخصية
- ✅ عرض الرصيد

### سوق GPUs
- ✅ عرض 10 كروت GPU متاحة (RTX 4090, A100, H100, etc.)
- ✅ 5 مناطق جغرافية (US East, US West, Europe, Asia Pacific, Middle East)
- ✅ فلترة حسب المنطقة والموديل
- ✅ عرض زمن الاستجابة (Latency) لكل GPU
- ✅ عرض المواصفات (CUDA Cores, VRAM, TDP)

### نظام الاستئجار
- ✅ بدء جلسة GPU
- ✅ إيقاف جلسة GPU
- ✅ حساب التكلفة بالثانية
- ✅ عرض بيانات الوصول (SSH, Jupyter, Password) - **محاكاة**
- ✅ سجل الجلسات السابقة

### الفوترة والدفع
- ✅ عرض الرصيد الحالي
- ✅ إضافة رصيد عبر Stripe
- ✅ سجل المعاملات
- ✅ الفواتير التفصيلية
- ✅ خصم تلقائي من الرصيد

### التصميم
- ✅ Dark Mode مع نيون أزرق (#00D4FF)
- ✅ تصميم عصري واحترافي
- ✅ متجاوب مع جميع الشاشات
- ✅ واجهة عربية

## التقنيات المستخدمة
- **Backend**: FastAPI + Python
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Database**: MongoDB
- **Payment**: Stripe (Test Mode)

## APIs الرئيسية
- `POST /api/auth/register` - تسجيل مستخدم
- `POST /api/auth/login` - تسجيل دخول
- `GET /api/auth/me` - معلومات المستخدم
- `GET /api/gpus` - قائمة GPUs
- `GET /api/regions` - المناطق
- `POST /api/instances/start` - بدء جلسة
- `POST /api/instances/{id}/stop` - إيقاف جلسة
- `GET /api/instances` - سجل الجلسات
- `GET /api/billing/transactions` - المعاملات
- `POST /api/payments/create-checkout` - إنشاء دفع

## بيانات الاختبار
- **مستخدم**: test@gpucloud.pro / test123
- **Admin**: admin@gpucloud.pro / admin123

## المهام المستقبلية

### المرحلة 2
- [ ] ربط حقيقي مع مزودي GPU (RunPod API, Vast.ai API)
- [ ] نظام إشعارات البريد الإلكتروني
- [ ] نظام تقييم المزودين
- [ ] لوحة تحكم المزودين
- [ ] نظام السحب للمزودين

### المرحلة 3
- [ ] Health Check Agent لمراقبة GPUs
- [ ] نظام Failover الذكي
- [ ] دعم Docker containers
- [ ] API للمطورين
- [ ] تطبيق موبايل

## ملاحظات
- بيانات الوصول (SSH/Jupyter) **محاكاة** وليست اتصالات حقيقية
- Stripe في وضع الاختبار (Test Mode)
