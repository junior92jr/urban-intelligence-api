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
make docker-config
make docker-build
make docker-migrate
make docker-up
```

Open:

```text
http://localhost:8000/
```

Useful commands:

```bash
make docker-test
make docker-logs
make docker-shell
make docker-down
```

PostgreSQL and Redis are available to Django on the internal Docker network. Their host ports are not published by default, which avoids conflicts with local Postgres or Redis installations.

The development env file uses:

```env
DATABASE_URL=postgis://city_guide:city_guide@db:5432/city_guide
REDIS_URL=redis://redis:6379/0
```

You can point Docker commands at another env file when needed:

```bash
make docker-config DOCKER_DEV_ENV=.env.docker.example
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
make docker-prod-config
make docker-prod-check
make docker-prod-static
make docker-prod-migrate
make docker-prod-up
```

Production Docker commands read `.env.prod` by default. To validate against another env file:

```bash
make docker-prod-config DOCKER_PROD_ENV=.env.prod.example
```

Useful production commands:

```bash
make docker-prod-logs
make docker-prod-down
```

The production compose stack uses:

- `nginx`: public HTTP entrypoint and static file serving
- `web`: Gunicorn running Django
- `db`: PostgreSQL with the PostGIS extension available
- `redis`: Redis cache backend

Production startup does not run migrations or collect static files inside every web container. Those lifecycle steps are separate Make targets so scaling the web service does not repeat database or static file operations.

Static files use Django's manifest storage when `DEBUG=False`, so Nginx can serve collected assets with long-lived immutable cache headers.

## Health Checks

Health endpoints are available for Docker and deployment checks:

```text
/health/live/
/health/ready/
```
