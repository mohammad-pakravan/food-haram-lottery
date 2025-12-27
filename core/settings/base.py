"""
Django settings for auth_service project.
"""

import os
from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')

# Application definition
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    
    # Local apps (must be before admin for custom User model)
    'apps.accounts',
    'apps.lottery.apps.LotteryConfig',
    'django_apscheduler',  # For scheduled tasks
    
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_yasg',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.accounts.authentication.CookieJWTAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Fallback to header
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CORS Settings
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if os.getenv('CORS_ALLOWED_ORIGINS') else []
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Cookie Settings
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'False') == 'True'  # True in production with HTTPS
COOKIE_HTTPONLY = True
COOKIE_SAMESITE = 'Lax'  # Can be 'Strict', 'Lax', or 'None'
COOKIE_ACCESS_TOKEN_NAME = 'access_token'
COOKIE_REFRESH_TOKEN_NAME = 'refresh_token'

# KavehNegar API Settings
KAVEHNEGAR_API_KEY = os.getenv('KAVEHNEGAR_API_KEY', '6A684450426861524B3272616D446D686F6E506E724E3250355077536455513652363255514B4F2F3574453D')
KAVEHNEGAR_OTP_TEMPLATE = os.getenv('KAVEHNEGAR_OTP_TEMPLATE', 'haramapp')
KAVEHNEGAR_API_URL = 'https://api.kavenegar.com/v1'

# OTP Settings
OTP_CODE_LENGTH = int(os.getenv('OTP_CODE_LENGTH', '6'))
OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', '5'))
OTP_RATE_LIMIT_COUNT = int(os.getenv('OTP_RATE_LIMIT_COUNT', '3'))
OTP_RATE_LIMIT_MINUTES = int(os.getenv('OTP_RATE_LIMIT_MINUTES', '10'))

# Lottery Settings
LOTTERY_WINNERS_COUNT = int(os.getenv('LOTTERY_WINNERS_COUNT', '8'))
LOTTERY_WINNER_SMS_TEMPLATE = os.getenv('LOTTERY_WINNER_SMS_TEMPLATE', '')
ENABLE_LOTTERY_SCHEDULER = os.getenv('ENABLE_LOTTERY_SCHEDULER', 'False') == 'True'

# APScheduler Settings
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25  # Seconds

# Swagger/OpenAPI Settings
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
        }
    },
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
    'SUPPORTED_SUBMIT_METHODS': ['get', 'post', 'put', 'delete', 'patch'],
    'OPERATIONS_SORTER': 'alpha',
    'TAGS_SORTER': 'alpha',
    'DOC_EXPANSION': 'none',
    'DEEP_LINKING': True,
    'SHOW_EXTENSIONS': True,
    'DEFAULT_MODEL_RENDERING': 'example'
}

