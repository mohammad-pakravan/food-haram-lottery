# Django Auth Service

سرویس احراز هویت Django با استفاده از OTP و API کاوه نگار

## ویژگی‌ها

- احراز هویت با شماره تلفن و کد OTP
- ثبت نام و ورود بدون نیاز به رمز عبور
- یکپارچه‌سازی با API کاوه نگار برای ارسال SMS
- JWT Authentication
- Rate limiting برای جلوگیری از spam
- پشتیبانی از Docker و Docker Compose
- مستندات Swagger/OpenAPI کامل

## ساختار پروژه

```
auth_service/
├── compose/
│   ├── dev/
│   │   ├── Dockerfile
│   │   └── entrypoint.sh
│   └── prod/
│       ├── Dockerfile
│       ├── nginx.conf
│       └── gunicorn.conf.py
├── core/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── admin.py
│   │   └── permissions.py
│   └── __init__.py
├── manage.py
├── requirements.txt
├── docker-compose.yml
├── .env
└── README.md
```

## نصب و راه‌اندازی

### پیش‌نیازها

- Python 3.11+
- PostgreSQL (یا SQLite برای توسعه)
- Docker و Docker Compose (اختیاری)

### نصب محلی

1. کلون کردن پروژه:
```bash
git clone <repository-url>
cd haram-lottary
```

2. ایجاد محیط مجازی:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. نصب dependencies:
```bash
pip install -r requirements.txt
```

4. کپی کردن فایل `.env.example` به `.env` و تنظیم متغیرهای محیطی:
```bash
cp .env.example .env
```

5. اجرای migrations:
```bash
python manage.py migrate
```

6. ایجاد superuser (اختیاری):
```bash
python manage.py createsuperuser
```

7. اجرای سرور:
```bash
python manage.py runserver
```

### نصب با Docker

1. کپی کردن فایل `.env.example` به `.env` و تنظیم متغیرهای محیطی

2. اجرای با Docker Compose:
```bash
docker-compose up --build
```

سرور در آدرس `http://localhost:8000` در دسترس خواهد بود.

## مستندات API (Swagger)

پس از راه‌اندازی پروژه، می‌توانید از مستندات Swagger استفاده کنید:

- **Swagger UI**: `http://localhost:8000/swagger/`
- **ReDoc**: `http://localhost:8000/redoc/`
- **JSON Schema**: `http://localhost:8000/swagger.json`
- **YAML Schema**: `http://localhost:8000/swagger.yaml`

در Swagger UI می‌توانید:
- تمام endpointها را مشاهده کنید
- مستقیماً API را تست کنید
- با استفاده از دکمه "Authorize" JWT token را وارد کنید
- نمونه request و response را ببینید

## تنظیمات

### متغیرهای محیطی مهم

- `SECRET_KEY`: کلید مخفی Django
- `KAVEHNEGAR_API_KEY`: کلید API کاوه نگار
- `KAVEHNEGAR_OTP_TEMPLATE`: نام قالب پیامک OTP
- `OTP_CODE_LENGTH`: طول کد OTP (پیش‌فرض: 6)
- `OTP_EXPIRY_MINUTES`: زمان انقضای کد OTP (پیش‌فرض: 5 دقیقه)

## API Endpoints

### 1. درخواست OTP
```
POST /api/accounts/request-otp/
Body: {
    "phone_number": "09123456789",
    "purpose": "register"  // or "login"
}
```

### 2. تایید OTP و احراز هویت
```
POST /api/accounts/verify-otp/
Body: {
    "phone_number": "09123456789",
    "code": "123456",
    "purpose": "register"  // or "login"
}
Response: {
    "access": "jwt-access-token",
    "refresh": "jwt-refresh-token",
    "user": {
        "id": 1,
        "phone_number": "09123456789",
        "is_phone_verified": true,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
}
```

### 3. مشاهده پروفایل
```
GET /api/accounts/profile/
Headers: {
    "Authorization": "Bearer <access-token>"
}
```

### 4. ویرایش پروفایل
```
PATCH /api/accounts/profile/
Headers: {
    "Authorization": "Bearer <access-token>"
}
Body: {
    // Fields to update
}
```

## Flow احراز هویت

### ثبت نام:
1. کاربر شماره تلفن را ارسال می‌کند → `POST /api/accounts/request-otp/` با `purpose: "register"`
2. سیستم کد OTP تولید می‌کند و از طریق کاوه نگار ارسال می‌کند
3. کاربر کد OTP را ارسال می‌کند → `POST /api/accounts/verify-otp/` با `purpose: "register"`
4. سیستم کد را تایید می‌کند و کاربر جدید ایجاد می‌کند
5. JWT token بازگردانده می‌شود

### ورود:
1. کاربر شماره تلفن را ارسال می‌کند → `POST /api/accounts/request-otp/` با `purpose: "login"`
2. سیستم بررسی می‌کند که کاربر وجود دارد
3. کد OTP تولید و ارسال می‌شود
4. کاربر کد OTP را ارسال می‌کند → `POST /api/accounts/verify-otp/` با `purpose: "login"`
5. سیستم کد را تایید می‌کند
6. JWT token بازگردانده می‌شود

## امنیت

- کدهای OTP در دیتابیس hash می‌شوند
- Rate limiting برای جلوگیری از spam
- کدهای OTP یکبار مصرف هستند
- کدهای OTP پس از مدت زمان مشخص منقضی می‌شوند
- استفاده از JWT برای احراز هویت

## توسعه

### اجرای تست‌ها
```bash
python manage.py test
```

### ساخت migrations جدید
```bash
python manage.py makemigrations
```

### اعمال migrations
```bash
python manage.py migrate
```

## Production

برای اجرا در production:

1. تنظیم `DJANGO_ENV=prod` در `.env`
2. تنظیم `DEBUG=False`
3. تنظیم `ALLOWED_HOSTS`
4. استفاده از PostgreSQL
5. تنظیم SSL/TLS
6. استفاده از Gunicorn و Nginx

## مجوز

این پروژه تحت مجوز MIT منتشر شده است.

