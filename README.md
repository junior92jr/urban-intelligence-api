# City Guide API

City Guide is a Django API and small server-rendered web app for finding nearby places on a map. It uses OpenStreetMap data through the Overpass API, supports authenticated users, and includes favorites and search history.

The project is built as an API-first Django application, with a lightweight Django template UI for exploring the map without a separate frontend repository.

## Quick Start

Local Django with SQLite:

```bash
cp .env.example .env
make venv
uv run python manage.py migrate
uv run python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Docker development with PostgreSQL/PostGIS and Redis:

```bash
cp .env.docker.example .env.docker
make docker-build
make docker-migrate
make docker-up
```

## Documentation

- [Local Setup](docs/setup.md)
- [Docker](docs/docker.md)
- [API Reference](docs/api.md)
- [Web Interface](docs/web.md)

## Core Commands

```bash
make check
make test
make fix
```

Useful Docker commands:

```bash
make docker-config
make docker-test
make docker-logs
make docker-down
```

## Services

- Django 6 REST API
- Django template web UI
- PostgreSQL/PostGIS for Docker development and production
- Redis cache backend when `REDIS_URL` is configured
- OpenStreetMap Overpass API for place search
- Leaflet for the map UI

Production map traffic should use a dedicated tile provider configured with `MAP_TILE_URL` and `MAP_TILE_ATTRIBUTION`. The default OpenStreetMap tile URL is only suitable for local development.
