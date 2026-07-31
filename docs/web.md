# Web Interface

Rendered web pages are handled by the `web` app.

## Routes

```text
GET /maps/
GET /favorites/
GET /history/
GET /login/
GET /register/
GET /registration-sent/
GET /activate/?token=<activation-token>
GET /forgot-password/
GET /reset-password/
GET /profile/
```

The map page redirects anonymous users to the login page. Place search starts only after authentication.

The activation link activates the account, signs the user in, and redirects to the map.

## Map Tiles

The map UI uses Leaflet with Django templates and static files. No Node or frontend build step is required.

For local development, the default tile URL uses OpenStreetMap public tiles:

```env
MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
MAP_TILE_ATTRIBUTION=OpenStreetMap contributors.
```

For production traffic, configure a proper tile provider:

```env
MAP_TILE_URL=https://your-tile-provider.example/{z}/{x}/{y}.png
MAP_TILE_ATTRIBUTION=Your tile provider attribution
```

OpenStreetMap public tiles are suitable for local development only.
