# City Guide API

City Guide is a Django API and small server-rendered web app for finding nearby places on a map. It uses OpenStreetMap data through the Overpass API, persists discovered places in PostGIS, supports authenticated users, and includes favorites and search history.

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
make migrate
make up
```

## Documentation

- [Local Setup](docs/setup.md)
- [Docker](docs/docker.md)
- [API Reference](docs/api.md)
- [Web Interface](docs/web.md)
- [Geospatial Data](docs/geospatial.md)

## Core Commands

```bash
make check
make test
make fix
```

Useful Docker commands:

```bash
make migrate
make logs
make down
```

## Services

- Django 6 REST API
- Django template web UI
- PostgreSQL/PostGIS for Docker development and production
- Redis cache backend and Celery broker when `REDIS_URL` is configured
- Celery worker for background place discovery
- OpenStreetMap Overpass API for background place refreshes
- Leaflet for the map UI

Production map traffic should use a dedicated tile provider configured with `MAP_TILE_URL` and `MAP_TILE_ATTRIBUTION`. The default OpenStreetMap tile URL is only suitable for local development.
