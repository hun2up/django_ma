"""
Django settings for web_ma project (Django 5.2.x)

Goals:
- APP_ENV(dev/prod)로 .env 자동 선택
- dev/prod 모두 DATABASE_URL 단일화
- Windows/한글 로케일 환경에서 psycopg2 UnicodeDecodeError 방지용 UTF-8 강제
- 운영에서만 secure cookie / whitenoise manifest 적용
"""

# django_ma/web_ma/settings.py

from __future__ import annotations

import logging
import os
from pathlib import Path

import dj_database_url
from decouple import Config, RepositoryEnv

# =============================================================================
# 0) Base / Env loading
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent


def _read_app_env() -> str:
    """APP_ENV 우선, 없으면 ENV, 없으면 dev."""
    return (os.environ.get("APP_ENV") or os.environ.get("ENV") or "dev").strip().lower()


def _resolve_env_path(app_env: str) -> str:
    """ENV_FILE 지정 시 우선 사용, 아니면 app_env에 따라 기본 .env 선택."""
    env_file = (os.environ.get("ENV_FILE") or "").strip()
    if env_file:
        return env_file
    return ".env.prod" if app_env in ("prod", "production") else ".env.dev"


APP_ENV = _read_app_env()
ENV_PATH = _resolve_env_path(APP_ENV)
config = Config(RepositoryEnv(ENV_PATH))

# -----------------------------------------------------------------------------
# Core flags
# -----------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY")

# DEBUG는 환경변수/설정 혼선을 줄이기 위해 decouple에서만 읽도록 통일
# (필요하면 DJANGO_DEBUG를 .env에 넣어 운영/개발에서 컨트롤)
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)

IS_PROD = APP_ENV in ("prod", "production") and not DEBUG

# =============================================================================
# 1) Hosts / CSRF
# =============================================================================
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,local.ma-support.kr,ma-support.kr",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://local.ma-support.kr,https://ma-support.kr",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# =============================================================================
# 2) Applications
# =============================================================================
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Local apps
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

# =============================================================================
# 3) Middleware
#   - WhiteNoise는 SecurityMiddleware 바로 다음이 권장 구성
# =============================================================================
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

# =============================================================================
# 4) URL / Templates / WSGI
# =============================================================================
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

# =============================================================================
# 5) Database (dev/prod 단일화 + UTF8 강제)
# =============================================================================
DATABASE_URL = config("DATABASE_URL")

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=False,  # 로컬/사내망에서는 False가 편함 (운영 SSL 필요 시 DATABASE_URL로 제어 권장)
    )
}

# ✅ Windows/한글 로케일에서 psycopg2 UnicodeDecodeError 방지
DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"]["options"] = "-c client_encoding=UTF8"

# ✅ 사고 방지: DEBUG 환경에서 운영 DB 키워드 감지 시 차단
if DEBUG and ("django_ma_prod" in DATABASE_URL or "ma_prod" in DATABASE_URL):
    raise RuntimeError("🚨 개발 환경에서 운영 DB 연결 시도 차단!")

# =============================================================================
# 6) Auth / Login
# =============================================================================
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

# =============================================================================
# 7) I18N / Timezone
# =============================================================================
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

DATETIME_FORMAT = "Y-m-d H:i"
DATE_FORMAT = "Y-m-d"

# =============================================================================
# 8) Static / Media
# =============================================================================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# 운영에서만 manifest storage (정적 파일 캐시/무결성)
if IS_PROD:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =============================================================================
# 9) Session / Cookie (운영에서만 secure)
# =============================================================================
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 60 * 60  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

SESSION_COOKIE_SECURE = IS_PROD
CSRF_COOKIE_SECURE = IS_PROD

# =============================================================================
# 10) Redis / Celery
# =============================================================================
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/1")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)

# =============================================================================
# 11) Upload dirs / Limits
# =============================================================================
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

UPLOAD_RESULT_DIR = Path(config("UPLOAD_RESULT_DIR", default=str(MEDIA_ROOT / "upload_results")))
UPLOAD_TEMP_DIR = Path(config("UPLOAD_TEMP_DIR", default=str(MEDIA_ROOT / "upload_temp")))

# =============================================================================
# 12) CKEditor
# =============================================================================
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_CONFIGS = {
    "default": {"toolbar": "full", "height": 420, "width": "100%"}
}

# =============================================================================
# 13) Default PK
# =============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# 14) Logging
# =============================================================================
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
        "django.security": {"handlers": ["file"], "level": "INFO", "propagate": True},
        "accounts.access": {"handlers": ["file"], "level": "INFO", "propagate": False},
    },
}

logging.getLogger("django.server").setLevel(logging.ERROR)
