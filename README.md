# Location Advisor Backend

This backend project is a REST API that provides touristic information for a frontend project.
Main source of the information comes from OpenStreetMap through the Overpass API:

* https://www.openstreetmap.org/
* https://overpass-api.de/

It provides places for touristic destinations based on your current location.

This API should provide dynamic information that will be displayed in a frontend project.

## Usage

This project is still in development but already provides functional endpoints ready to use:

### How to Authenticate
Auth endpoint:
```
(POST) /api/v1/api-token-auth/
```
Body Request:
```
{
  "username": "user",
  "password": "user_pass"
}
```
Response:
```
{
    "token": "fbfd14c374618e78bc9bbe1f6a576489a94f61f7"
}
```

### How to use the location service

Get places near a location:
```
(GET) /api/v1/places/?lat=50.1101038&lng=8.6771587
```

When no category is provided, the API searches only categories marked for default search.

The default search radius is `500` meters. Search radius values can be between `1` and `3000` meters.

Get places within a custom radius in meters:
```
(GET) /api/v1/places/?lat=50.1101038&lng=8.6771587&search_radius=250
```

Get known categories available for filtering:
```
(GET) /api/v1/categories/
```

Filter places by a known category slug:
```
(GET) /api/v1/places/?lat=50.1101038&lng=8.6771587&category=parking
```

Use the map interface:
```
(GET) /maps/
```

Example category response:
```json
[
  {
    "slug": "parking",
    "name": "Parking"
  }
]
```

Example places response:
```json
{
  "places": [
    {
      "osm_id": 331124761,
      "osm_type": "node",
      "name": "Heiliger Ludgerus",
      "latitude": 51.9322712,
      "longitude": 6.9442418,
      "category": "wayside-shrine",
      "category_name": "Wayside Shrine",
      "osm_uid": "osm-node-331124761"
    }
  ]
}
```


## Configure the project

This project uses [uv](https://docs.astral.sh/uv/) for Python dependency and virtual environment management.

### Clone the project

First verify your SSH Keys on github configuration
then if you dont have a key that points to your computer follow this tutorial:

* https://docs.github.com/de/developers/overview/managing-deploy-keys

```
$ git clone git@github.com:junior92jr/location-advisor-backend.git
```

### Install dependencies

From the project root, sync the environment:

```bash
make venv
```

### Setting up environment variables

Create a `.env` file in the project root, next to `manage.py`.

Required variables:

```env
SECRET_KEY=django-insecure-local-dev-change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
DATABASE_URL=sqlite:///db.sqlite3
CACHE_LOCATION=.cache
OPEN_STREET_MAP_OVERPASS_URL=https://overpass-api.de/api/interpreter
OPEN_STREET_MAP_USER_AGENT=city-guide-api-demo
OPEN_STREET_MAP_TIMEOUT_IN_SECS=20
OPEN_STREET_MAP_MAX_RETRIES=2
MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
MAP_TILE_ATTRIBUTION=OpenStreetMap contributors.
CACHE_TIMEOUT_IN_SECS=86400
```

Use a real `SECRET_KEY` outside local development.

Supported `DATABASE_URL` examples:

```env
DATABASE_URL=sqlite:///db.sqlite3
DATABASE_URL=postgres://user:password@localhost:5432/city_guide
```

### Local dev: map tiles

The map UI uses Leaflet with Django templates and static files. No Node or frontend build step is required.

For local development, the default tile URL uses OpenStreetMap public tiles:

```env
MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
MAP_TILE_ATTRIBUTION=OpenStreetMap contributors.
```

For production traffic, configure a proper tile provider in `MAP_TILE_URL` and update `MAP_TILE_ATTRIBUTION`.

# Running the project
## Run the project

Once you have everything ok, you can run the project.

```bash
make check

uv run python manage.py migrate

uv run python manage.py runserver
```

## Run tests

Tests are written with pytest.

```bash
make test
```

Run only the places tests:

```bash
uv run pytest places/tests
```

Run formatters and automatic lint fixes:

```bash
make fix
```

Run linting and type checks:

```bash
make check
```

# Build Documentation

Sphinx is configured to build a user friendly site for code documentation.

To build this files run

```
(city_guide) $ cd docs
(city_guide) $ make html
```

They will be build in docs/build/html/ with index.html as the main page.
It can also be accessed from the admin site in the top navigation.

Note: Docstrings ready for Documentation but adding the library is missing.
