"""
Base Django settings — shared across all environments.
Override per environment in development.py / production.py.
"""
from datetime import timedelta
from pathlib import Path
import environ
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging as _logging

env = environ.Env()

# Base directory: apps/api/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file
# Try root .env first, then local .env
ROOT_DIR = BASE_DIR.parent.parent
if (ROOT_DIR / ".env").exists():
    env.read_env(ROOT_DIR / ".env")
elif (BASE_DIR / ".env").exists():
    env.read_env(BASE_DIR / ".env")
elif (BASE_DIR / ".env.development").exists():
    env.read_env(BASE_DIR / ".env.development")

# Security
SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost"])

# ─── Apps ────────────────────────────────────────────────────────────────────
DJANGO_APPS = [
    "daphne",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "django_celery_beat",
    "channels",
]
LOCAL_APPS = [
    "core",
    "users.apps.UsersConfig",
    "scans.apps.ScansConfig",
    "notifications.apps.NotificationsConfig",
    "websockets.apps.WebsocketsConfig",
    "billing.apps.BillingConfig",
    "reports.apps.ReportsConfig",
    "ai.apps.AIConfig",
    "integrations.apps.IntegrationsConfig",
    "bounty.apps.BountyConfig",
    "marketplace.apps.MarketplaceConfig",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── AI Engine ───────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")

# ─── Sentry Error Tracking ───────────────────────────────────────────────────
SENTRY_DSN = env("SENTRY_DSN", default="")
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", default="development")
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.2)

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        integrations=[
            DjangoIntegration(
                transaction_style="url",
                middleware_spans=True,
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
            RedisIntegration(),
            LoggingIntegration(
                level=_logging.INFO,
                event_level=_logging.ERROR,
            ),
        ],
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,  # GDPR: nunca enviar dados pessoais
        attach_stacktrace=True,
        # Filtrar transações de health/metrics para não poluir
        traces_sampler=lambda ctx: 0.0
            if ctx.get("wsgi_environ", {}).get("PATH_INFO", "") in ("/health/", "/health/ready/", "/metrics/")
            else SENTRY_TRACES_SAMPLE_RATE,
    )

# ─── Middleware ───────────────────────────────────────────────────────────────
# ─── Templates ────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "reports" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

MIDDLEWARE = [
    "core.middleware.PrometheusMiddleware",  # first: measure total latency
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ─── Auth ────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

# ─── Database ────────────────────────────────────────────────────────────────
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://hackscan:hackscan_password@localhost:5432/hackscan_db",
    )
}

# ─── Cache / Redis ───────────────────────────────────────────────────────────
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# ─── DRF ─────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "users.authentication.CustomJWTAuthentication",
        "users.authentication.APIKeyAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# ─── JWT ─────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),   # curto — segurança
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,       # novo refresh a cada uso
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",                # RS256 em produção via env
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Override to RS256 in production when keys are set
_jwt_private_key = env("JWT_PRIVATE_KEY", default="")
_jwt_public_key = env("JWT_PUBLIC_KEY", default="")
if _jwt_private_key and _jwt_public_key:
    SIMPLE_JWT["ALGORITHM"] = "RS256"
    SIMPLE_JWT["SIGNING_KEY"] = _jwt_private_key
    SIMPLE_JWT["VERIFYING_KEY"] = _jwt_public_key

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://127.0.0.1:3000"],
)

# ─── Email ───────────────────────────────────────────────────────────────────
EMAIL_HOST = env("EMAIL_HOST", default="smtp.sendgrid.net")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@hackscan.pro")

# ─── Static ──────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ─── i18n ────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "pt"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Celery ──────────────────────────────────────────────────────────────────
CELERY_BROKER_URL          = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND      = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT      = ["json"]
CELERY_TASK_SERIALIZER     = "json"
CELERY_RESULT_SERIALIZER   = "json"
CELERY_TIMEZONE            = "UTC"
CELERY_TASK_TRACK_STARTED  = True
CELERY_TASK_TIME_LIMIT     = 600   # 10 min hard limit per scan
CELERY_TASK_SOFT_TIME_LIMIT = 540  # 9 min soft limit

# ─── Stripe ──────────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY       = env("STRIPE_SECRET_KEY", default="sk_test_placeholder")
STRIPE_PUBLISHABLE_KEY  = env("STRIPE_PUBLISHABLE_KEY", default="pk_test_placeholder")
STRIPE_WEBHOOK_SECRET   = env("STRIPE_WEBHOOK_SECRET", default="whsec_placeholder")

# Frontend URL (used for email links, upsell redirects, etc.)
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# ─── Storage (MinIO / S3) ───────────────────────────────────────────────────
AWS_ACCESS_KEY_ID       = env("AWS_ACCESS_KEY_ID", default="hackscan_admin")
AWS_SECRET_ACCESS_KEY   = env("AWS_SECRET_ACCESS_KEY", default="hackscan_password")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="hackscan-reports")
AWS_S3_ENDPOINT_URL     = env("AWS_S3_ENDPOINT_URL", default="http://localhost:9000")
AWS_S3_REGION_NAME      = env("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_FILE_OVERWRITE   = False

# ─── Logging & Structlog ─────────────────────────────────────────────────────
import uuid
import structlog


def _add_request_id(logger, method_name, event_dict):
    """Inject a request_id for log correlation (use X-Request-ID header if present)."""
    if "request_id" not in event_dict:
        event_dict["request_id"] = str(uuid.uuid4())[:8]
    return event_dict


def _add_service_context(logger, method_name, event_dict):
    """Tag every log line with the service name."""
    event_dict.setdefault("service", "hackerscan-api")
    return event_dict


# ── Django LOGGING dict ──────────────────────────────────────────────────────
_shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.UnicodeDecoder(),
    _add_request_id,
    _add_service_context,
    structlog.processors.format_exc_info,
    structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            "foreign_pre_chain": _shared_processors[:-1],  # sans wrap_for_formatter
        },
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=DEBUG),
            ],
            "foreign_pre_chain": _shared_processors[:-1],
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console" if DEBUG else "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "hackerscan": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ── Structlog configuration ──────────────────────────────────────────────────
structlog.configure(
    processors=_shared_processors,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
