# Local Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python dependency and virtual environment management.

## Install

```bash
make venv
```

The local virtual environment is mainly for local formatting and lightweight editing tools. GeoDjango commands, tests, and type checks run through Docker by default because the app uses PostGIS point fields.

If you want to run full Django/GeoDjango commands directly on macOS, install the native geospatial libraries first:

```bash
brew install gdal geos proj
```

## Environment

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Runtime env files are ignored by Git. The tracked example files document the expected configuration:

- `.env.example`: local Django without Docker
- `.env.docker.example`: Docker development
- `.env.prod.example`: production-style Docker commands

Keep the env files at the repository root. This works naturally with `manage.py`, Docker Compose, and the Makefile.

## Local `.env`

```env
SECRET_KEY=django-insecure-local-dev-change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
DATABASE_URL=sqlite:///db.sqlite3
CACHE_LOCATION=.cache
REDIS_URL=
STATIC_ROOT=staticfiles
STATICFILES_STORAGE_BACKEND=django.contrib.staticfiles.storage.StaticFilesStorage
OPEN_STREET_MAP_OVERPASS_URL=https://overpass-api.de/api/interpreter
OPEN_STREET_MAP_USER_AGENT=city-guide-api-demo
OPEN_STREET_MAP_TIMEOUT_IN_SECS=20
OPEN_STREET_MAP_MAX_RETRIES=2
MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
MAP_TILE_ATTRIBUTION=OpenStreetMap contributors.
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=City Guide <noreply@localhost>
CACHE_TIMEOUT_IN_SECS=86400
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
USE_X_FORWARDED_HOST=False
SECURE_PROXY_SSL_HEADER=False
```

Use a real `SECRET_KEY` outside local development.

Supported database URLs:

```env
DATABASE_URL=sqlite:///db.sqlite3
DATABASE_URL=postgres://user:password@localhost:5432/city_guide
DATABASE_URL=postgis://user:password@localhost:5432/city_guide
```

Set `REDIS_URL` to use Redis-backed caching. Leave it empty to use the local file cache:

```env
REDIS_URL=redis://localhost:6379/0
```

## Run

Docker is the recommended development runtime:

```bash
cp .env.docker.example .env.docker
make migrate
make up
```

For non-Docker local development, install GDAL/GEOS/PROJ first and then run:

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

If port `8000` is busy:

```bash
uv run python manage.py runserver 8001
```

For deployment-style static collection:

```bash
uv run python manage.py collectstatic --noinput
```

## Checks And Tests

```bash
make check
make test
make fix
```

`make check` uses local Ruff checks, then runs type checks in Docker. `make test` runs the test suite in Docker against the Docker database.

Run only the places tests in Docker:

```bash
DJANGO_ENV_FILE=.env.docker docker compose --env-file .env.docker run --rm web pytest places/tests
```

## Account Emails

The default email backend prints activation and password reset emails in the terminal where `runserver` is running.

For Gmail SMTP in production, configure:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-address@gmail.com
EMAIL_HOST_PASSWORD=your-google-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=City Guide <your-address@gmail.com>
```

Gmail requires an app password for SMTP when two-step verification is enabled.
