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
    DATABASE_URL=(str, f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
    OPEN_STREET_MAP_OVERPASS_URL=(
        str,
        "https://overpass-api.de/api/interpreter",
    ),
    OPEN_STREET_MAP_USER_AGENT=(str, "city-guide-api-demo"),
    OPEN_STREET_MAP_TIMEOUT_IN_SECS=(float, 20.0),
    OPEN_STREET_MAP_MAX_RETRIES=(int, 2),
    MAP_TILE_URL=(
        str,
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    ),
    MAP_TILE_ATTRIBUTION=(
        str,
        "OpenStreetMap contributors.",
    ),
    CACHE_TIMEOUT_IN_SECS=(int, 86400),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)


# Security
SECRET_KEY = env("SECRET_KEY")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

CACHE_LOCATION = Path(str(env("CACHE_LOCATION")))
if not CACHE_LOCATION.is_absolute():
    CACHE_LOCATION = BASE_DIR / CACHE_LOCATION


# Applications
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "accounts",
    "maps",
    "places",
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
STATIC_URL = "static/"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": ("django.contrib.staticfiles.storage.StaticFilesStorage"),
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

OPEN_STREET_MAP_USER_AGENT = env("OPEN_STREET_MAP_USER_AGENT")

OPEN_STREET_MAP_TIMEOUT_IN_SECS = env("OPEN_STREET_MAP_TIMEOUT_IN_SECS")

OPEN_STREET_MAP_MAX_RETRIES = env("OPEN_STREET_MAP_MAX_RETRIES")

MAP_TILE_URL = env("MAP_TILE_URL")

MAP_TILE_ATTRIBUTION = env("MAP_TILE_ATTRIBUTION")

CACHE_TIMEOUT_IN_SECS = env("CACHE_TIMEOUT_IN_SECS")


# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.BearerTokenAuthentication",
    ],
}
