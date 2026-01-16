"""
Django settings for web_ma project (Django 5.2.x)

- APP_ENV(dev/prod)로 .env 자동 선택
- dev/prod 모두 DATABASE_URL 단일화
- Windows/한글 로케일 환경에서 psycopg2 UnicodeDecodeError 방지용 UTF-8 강제
- 운영에서만 secure cookie/whitenoise manifest 적용
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import dj_database_url
from decouple import Config, RepositoryEnv

# ============================================================
# 0) BASE / ENV LOADING
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

APP_ENV = (os.environ.get("APP_ENV") or os.environ.get("ENV") or "dev").lower()
ENV_FILE = os.environ.get("ENV_FILE")
ENV_PATH = ENV_FILE or (".env.prod" if APP_ENV in ("prod", "production") else ".env.dev")

config = Config(RepositoryEnv(ENV_PATH))

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", cast=bool, default=(APP_ENV not in ("prod", "production")))

# ============================================================
# 1) HOSTS / CSRF
# ============================================================
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "local.ma-support.kr",
    "ma-support.kr",
]

CSRF_TRUSTED_ORIGINS = [
    "https://local.ma-support.kr",
    "https://ma-support.kr",
]

# ============================================================
# 2) APPS
# ============================================================
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Local
    "home",
    "join",
    "board",
    "accounts",
    "commission",
    "dash",
    "manual",
    "partner.apps.PartnerConfig",

    # 3rd party
    "widget_tweaks",
    "django_extensions",
    "ckeditor",
    "ckeditor_uploader",
]

# ============================================================
# 3) MIDDLEWARE
# (WhiteNoise는 SecurityMiddleware 바로 다음 권장)
# ============================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ============================================================
# 4) URL / TEMPLATES / WSGI
# ============================================================
ROOT_URLCONF = "web_ma.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "web_ma.wsgi.application"

# ============================================================
# 5) DATABASE (dev/prod 단일화 + UTF8 강제)
# ============================================================
DATABASE_URL = config("DATABASE_URL")

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=False,  # 로컬 Postgres면 False 권장
    )
}

# ✅ Windows/한글 로케일에서 psycopg2 UnicodeDecodeError 방지
# (libpq 메시지/인코딩 꼬임 방지용)
DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"]["options"] = "-c client_encoding=UTF8"

# ✅ 사고 방지: DEBUG 환경에서 운영DB 키워드 감지 시 차단
if DEBUG and ("django_ma_prod" in DATABASE_URL or "ma_prod" in DATABASE_URL):
    raise RuntimeError("🚨 개발 환경에서 운영 DB 연결 시도 차단!")

# ============================================================
# 6) AUTH / LOGIN
# ============================================================
AUTH_USER_MODEL = "accounts.CustomUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ============================================================
# 7) I18N / TIMEZONE
# ============================================================
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

DATETIME_FORMAT = "Y-m-d H:i"
DATE_FORMAT = "Y-m-d"

# ============================================================
# 8) STATIC / MEDIA
# ============================================================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

if not DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ============================================================
# 9) SESSION / COOKIE (운영에서만 secure)
# ============================================================
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# ============================================================
# 10) REDIS / CELERY (.env 기반)
# ============================================================
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)

# ============================================================
# 11) UPLOAD LIMITS
# ============================================================
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000
UPLOAD_RESULT_DIR = MEDIA_ROOT / "upload_results"
UPLOAD_TEMP_DIR = MEDIA_ROOT / "upload_temp"

# ============================================================
# 12) CKEDITOR
# ============================================================
CKEDITOR_UPLOAD_PATH = "uploads/manual/"
CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "full",
        "height": 420,
        "width": "100%",
    }
}

# ============================================================
# 13) DEFAULT PK
# ============================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================
# 14) LOGGING
# ============================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "access.log",
        },
    },
    "loggers": {
        "django.security": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
        "accounts.access": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

logging.getLogger("django.server").setLevel(logging.ERROR)
