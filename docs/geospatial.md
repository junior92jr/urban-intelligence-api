# Geospatial Data

City Guide uses GeoDjango and PostGIS as the foundation for spatial features. Production data starts from this shape, so new spatial features should build on the database `location` points rather than treating coordinates as plain floats.

## Stored User Places

Favorites and search history store coordinates in Django's built-in `PointField`. The API and web UI still exchange `latitude` and `longitude`, but those values are mapped at the serializer/service edge.

The migration `user_places.0003_use_postgis_location_points` creates:

```text
user_places_favoriteplace.location
user_places_searchhistory.location
```

Each point uses SRID `4326` and is stored as:

```text
SRID=4326;POINT(longitude latitude)
```

Both columns have Django-declared GiST indexes, so later features can query efficiently by distance, containment, and overlap.

On PostgreSQL/PostGIS, `location` is a `geometry(Point,4326)` column. The Docker database image enables PostGIS during database initialization through `docker/postgres/initdb/01-enable-postgis.sql`.

GeoDjango requires native GDAL/GEOS/PROJ libraries. Docker includes them, and macOS developers can install them with:

```bash
brew install gdal geos proj
```

## Why This Shape

This keeps the API stable:

```json
{
  "latitude": 50.1109,
  "longitude": 8.6821
}
```

And it gives the database a real spatial point for future features:

- favorites near the current map center
- search history clustered by area
- places inside city districts
- BI layers such as transit, crime, weather, and traffic overlays
- neighborhood scoring and coverage analysis
