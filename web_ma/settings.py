"""
Django settings for web_ma project.
(2분기 자동 전환형: Render(dev) + Oracle(prod))
"""

import os
import logging
from pathlib import Path
from decouple import Config, RepositoryEnv
import dj_database_url

# -----------------------------------------------------
# 📁 기본 경로 설정
# -----------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------
# ⚙️ 환경 파일(.env) 자동 선택
# DJANGO_ENV=prod → .env.prod / 기본값: .env.dev
# -----------------------------------------------------
env_mode = os.environ.get("DJANGO_ENV", "dev")
env_file = BASE_DIR / (".env.prod" if env_mode == "prod" else ".env.dev")

if not env_file.exists():
    raise FileNotFoundError(f"환경 파일을 찾을 수 없습니다: {env_file}")

config = Config(RepositoryEnv(env_file))

# -----------------------------------------------------
# 🔑 보안 키 및 기본 설정
# -----------------------------------------------------
SECRET_KEY = config("SECRET_KEY", default="unsafe-default-key")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = [h.strip() for h in config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")]
ENV = config("ENV", default="dev")

# -----------------------------------------------------
# 📦 Installed Apps
# -----------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "widget_tweaks",
    "django_extensions",
    # ✅ 프로젝트 앱들
    "home",
    "join",
    "board",
    "accounts",
    "commission",
    "dash",
    "partner.apps.PartnerConfig",
]

# -----------------------------------------------------
# 🧱 Middleware
# -----------------------------------------------------
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

# -----------------------------------------------------
# 📚 Templates
# -----------------------------------------------------
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
    },
]

WSGI_APPLICATION = "web_ma.wsgi.application"

# -----------------------------------------------------
# 🗄️ Database
# -----------------------------------------------------
DATABASE_URL = config("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=not DEBUG)
    }
else:
    # fallback (로컬 DB)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# -----------------------------------------------------
# 🔐 Password Validation
# -----------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.CustomUser"

# -----------------------------------------------------
# 🌍 Locale / Timezone
# -----------------------------------------------------
LANGUAGE_CODE = config("LANGUAGE_CODE", default="ko-kr")
TIME_ZONE = config("TIME_ZONE", default="Asia/Seoul")
USE_I18N = True
USE_L10N = True
USE_TZ = True

DATETIME_FORMAT = "Y-m-d H:i"
DATE_FORMAT = "Y-m-d"

# -----------------------------------------------------
# 🖼️ Static & Media Files
# -----------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

if not DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------------------------------
# 🔒 Session & CSRF Settings
# -----------------------------------------------------
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True
SESSION_ENGINE = "django.contrib.sessions.backends.db"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SECURE_SSL_REDIRECT = True

# -----------------------------------------------------
# 🔁 Celery / Redis
# -----------------------------------------------------
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# -----------------------------------------------------
# 🚪 Login / Logout Redirects
# -----------------------------------------------------
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# -----------------------------------------------------
# 🪵 Logging
# -----------------------------------------------------
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
        "django.security.*": {
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

# -----------------------------------------------------
# ✅ 요약
# -----------------------------------------------------
print(f"🔧 Django 환경: {env_mode.upper()} / DEBUG={DEBUG}")
print(f"📦 Loaded .env file: {env_file}")
