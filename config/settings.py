from pathlib import Path

import environ

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent


# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    CACHE_LOCATION=(str, str(BASE_DIR / ".cache")),
    REDIS_URL=(str, ""),
    CELERY_BROKER_URL=(str, ""),
    STATIC_ROOT=(str, str(BASE_DIR / "staticfiles")),
    STATICFILES_STORAGE_BACKEND=(
        str,
        "django.contrib.staticfiles.storage.StaticFilesStorage",
    ),
    DATABASE_URL=(str, f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
    OPEN_STREET_MAP_OVERPASS_URL=(
        str,
        "https://overpass-api.de/api/interpreter",
    ),
    OPEN_STREET_MAP_OVERPASS_URLS=(list, []),
    OPEN_STREET_MAP_USER_AGENT=(str, "city-guide-api-demo"),
    OPEN_STREET_MAP_TIMEOUT_IN_SECS=(float, 20.0),
    OPEN_STREET_MAP_MAX_RETRIES=(int, 3),
    MAP_TILE_URL=(
        str,
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    ),
    MAP_TILE_ATTRIBUTION=(
        str,
        "OpenStreetMap contributors.",
    ),
    EMAIL_BACKEND=(
        str,
        "django.core.mail.backends.console.EmailBackend",
    ),
    EMAIL_HOST=(str, ""),
    EMAIL_PORT=(int, 587),
    EMAIL_HOST_USER=(str, ""),
    EMAIL_HOST_PASSWORD=(str, ""),
    EMAIL_USE_TLS=(bool, True),
    DEFAULT_FROM_EMAIL=(str, "City Guide <noreply@localhost>"),
    CACHE_TIMEOUT_IN_SECS=(int, 86400),
    SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, False),
    SECURE_HSTS_PRELOAD=(bool, False),
    USE_X_FORWARDED_HOST=(bool, False),
    SECURE_PROXY_SSL_HEADER=(bool, False),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)


# Security
SECRET_KEY = env("SECRET_KEY")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")

SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE")

CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE")

SECURE_HSTS_SECONDS = env("SECURE_HSTS_SECONDS")

SECURE_HSTS_INCLUDE_SUBDOMAINS = env("SECURE_HSTS_INCLUDE_SUBDOMAINS")

SECURE_HSTS_PRELOAD = env("SECURE_HSTS_PRELOAD")

USE_X_FORWARDED_HOST = env("USE_X_FORWARDED_HOST")

SECURE_PROXY_SSL_HEADER = None
if env("SECURE_PROXY_SSL_HEADER"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CACHE_LOCATION = Path(str(env("CACHE_LOCATION")))
if not CACHE_LOCATION.is_absolute():
    CACHE_LOCATION = BASE_DIR / CACHE_LOCATION

REDIS_URL = env("REDIS_URL")


# Applications
INSTALLED_APPS = [
    "config.apps.ConfigAppConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.gis",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "accounts",
    "geo",
    "intelligence",
    "web",
    "places",
    "user_places",
]


# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# URLs and application entry points
ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"


# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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


# Database
DATABASES = {
    "default": env.db(),
}


# Cache
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "KEY_PREFIX": "city-guide",
        },
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": CACHE_LOCATION,
        },
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.MinimumLengthValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.CommonPasswordValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.NumericPasswordValidator"),
    },
]


# Internationalization
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files
STATIC_URL = "/static/"

STATIC_ROOT = Path(str(env("STATIC_ROOT")))
if not STATIC_ROOT.is_absolute():
    STATIC_ROOT = BASE_DIR / STATIC_ROOT

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": env("STATICFILES_STORAGE_BACKEND"),
    },
}


# Background tasks
TASKS = {
    "default": {
        "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
    },
}


# Default primary-key type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Authentication
AUTH_USER_MODEL = "accounts.User"

ACCOUNT_ACTIVATION_TOKEN_TTL_IN_HOURS = 24

ACCOUNT_PASSWORD_RESET_TOKEN_TTL_IN_HOURS = 1


# External services
OPEN_STREET_MAP_OVERPASS_URL = env("OPEN_STREET_MAP_OVERPASS_URL")

OPEN_STREET_MAP_OVERPASS_URLS = env("OPEN_STREET_MAP_OVERPASS_URLS") or [
    OPEN_STREET_MAP_OVERPASS_URL
]

OPEN_STREET_MAP_USER_AGENT = env("OPEN_STREET_MAP_USER_AGENT")

OPEN_STREET_MAP_TIMEOUT_IN_SECS = env("OPEN_STREET_MAP_TIMEOUT_IN_SECS")

OPEN_STREET_MAP_MAX_RETRIES = env("OPEN_STREET_MAP_MAX_RETRIES")

MAP_TILE_URL = env("MAP_TILE_URL")

MAP_TILE_ATTRIBUTION = env("MAP_TILE_ATTRIBUTION")

CACHE_TIMEOUT_IN_SECS = env("CACHE_TIMEOUT_IN_SECS")


# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL") or REDIS_URL

CELERY_TASK_IGNORE_RESULT = True

CELERY_TASK_TRACK_STARTED = True

CELERY_TASK_TIME_LIMIT = 120

CELERY_TASK_SOFT_TIME_LIMIT = 90


# Email
EMAIL_BACKEND = env("EMAIL_BACKEND")

EMAIL_HOST = env("EMAIL_HOST")

EMAIL_PORT = env("EMAIL_PORT")

EMAIL_HOST_USER = env("EMAIL_HOST_USER")

EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")

EMAIL_USE_TLS = env("EMAIL_USE_TLS")

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")


# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.BearerTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}
