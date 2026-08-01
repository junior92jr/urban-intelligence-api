# Docker

The Docker setup is organized for local development first, while keeping a clear production shape.

## File Layout

```text
Dockerfile
compose.yml
compose.override.yml
compose.prod.yml
docker/
  nginx/
  postgres/
  web/
```

The root Compose files are the project entrypoints:

- `compose.yml`: shared services and topology
- `compose.override.yml`: local development overrides, loaded automatically by Docker Compose
- `compose.prod.yml`: production-oriented overrides, loaded explicitly

Service-specific configuration lives under `docker/`.

## Development

Docker development runs Django with PostgreSQL/PostGIS and Redis:

```bash
cp .env.docker.example .env.docker
make migrate
make up
```

The Docker image includes the native GeoDjango stack:

- GDAL
- GEOS
- PROJ
- PostgreSQL/PostGIS client/runtime libraries

Open:

```text
http://localhost:8000/
```

Useful commands:

```bash
make check
make test
make logs
make shell
make down
```

Run one-off commands inside the development `web` container:

```bash
make migrations
make manage createsuperuser
make manage showmigrations
```

PostgreSQL and Redis are available to Django on the internal Docker network. Their host ports are not published by default, which avoids conflicts with local Postgres or Redis installations.

The development env file uses:

```env
DATABASE_URL=postgis://city_guide:city_guide@db:5432/city_guide
REDIS_URL=redis://redis:6379/0
```

You can point Docker commands at another env file when needed:

```bash
make check DOCKER_ENV=.env.docker.example
```

Validate the development Compose config directly when needed:

```bash
DJANGO_ENV_FILE=.env.docker docker compose --env-file .env.docker config --quiet
```

## Production Shape

Production-oriented Docker files are included, but they still need real deployment secrets before use:

```bash
cp .env.prod.example .env.prod
```

Edit `.env.prod` with real values first. At minimum, set:

- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `REDIS_URL`
- email settings
- `MAP_TILE_URL`
- `MAP_TILE_ATTRIBUTION`

Run production-style checks and release tasks explicitly:

```bash
DJANGO_ENV_FILE=.env.prod docker compose -f compose.yml -f compose.prod.yml --env-file .env.prod config --quiet
DJANGO_ENV_FILE=.env.prod docker compose -f compose.yml -f compose.prod.yml --env-file .env.prod run --rm web python manage.py check --deploy
DJANGO_ENV_FILE=.env.prod docker compose -f compose.yml -f compose.prod.yml --env-file .env.prod run --rm web python manage.py collectstatic --noinput
DJANGO_ENV_FILE=.env.prod docker compose -f compose.yml -f compose.prod.yml --env-file .env.prod run --rm web python manage.py migrate --noinput
DJANGO_ENV_FILE=.env.prod docker compose -f compose.yml -f compose.prod.yml --env-file .env.prod up --build -d
```

To validate against another env file:

```bash
DJANGO_ENV_FILE=.env.prod.example docker compose -f compose.yml -f compose.prod.yml --env-file .env.prod.example config --quiet
```

Useful production commands:

```bash
DJANGO_ENV_FILE=.env.prod docker compose -f compose.yml -f compose.prod.yml --env-file .env.prod logs -f
DJANGO_ENV_FILE=.env.prod docker compose -f compose.yml -f compose.prod.yml --env-file .env.prod down
```

The production compose stack uses:

- `nginx`: public HTTP entrypoint and static file serving
- `web`: Gunicorn running Django
- `db`: PostgreSQL with the PostGIS extension available
- `redis`: Redis cache backend

Production startup does not run migrations or collect static files inside every web container. Run those lifecycle steps explicitly so scaling the web service does not repeat database or static file operations.

Static files use Django's manifest storage when `DEBUG=False`, so Nginx can serve collected assets with long-lived immutable cache headers.

## Health Checks

Health endpoints are available for Docker and deployment checks:

```text
/health/live/
/health/ready/
```
