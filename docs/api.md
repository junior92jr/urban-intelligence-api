# API Reference

## Authentication

Register a new account:

```text
POST /api/v1/accounts/register/
```

Request:

```json
{
  "email": "user@example.com",
  "password": "user_pass"
}
```

Activate an account:

```text
POST /api/v1/accounts/activate/
```

Request:

```json
{
  "token": "account-activation-token"
}
```

Login:

```text
POST /api/v1/accounts/login/
```

Request:

```json
{
  "email": "user@example.com",
  "password": "user_pass"
}
```

Response:

```json
{
  "token": "fbfd14c374618e78bc9bbe1f6a576489a94f61f7",
  "token_type": "Bearer"
}
```

Authenticated requests should send:

```text
Authorization: Bearer fbfd14c374618e78bc9bbe1f6a576489a94f61f7
```

Get the authenticated profile:

```text
GET /api/v1/accounts/me/
```

Logout deletes the current bearer token:

```text
POST /api/v1/accounts/logout/
```

Create a password reset token:

```text
POST /api/v1/accounts/forgot-password/
```

Request:

```json
{
  "email": "user@example.com"
}
```

Reset a password:

```text
POST /api/v1/accounts/reset-password/
```

Request:

```json
{
  "token": "password-reset-token",
  "password": "new_user_pass"
}
```

Account activation and password reset tokens are stored hashed and consumed on use. The API keeps token delivery separate from API authentication. The web registration and password reset flows send email through Django's configured email backend.

## Places

Get places near a location:

```text
GET /api/v1/places/?lat=50.1101038&lng=8.6771587
```

The places endpoint requires authentication. Categories remain public so the UI can prepare filters before search.

When no category is provided, the API searches only categories marked for default search.

The default search radius is `500` meters. Search radius values can be between `1` and `3000` meters.

Get places within a custom radius in meters:

```text
GET /api/v1/places/?lat=50.1101038&lng=8.6771587&search_radius=250
```

Get known categories available for filtering:

```text
GET /api/v1/categories/
```

Filter places by a known category slug:

```text
GET /api/v1/places/?lat=50.1101038&lng=8.6771587&category=parking
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

## User Places

Save an authenticated user's favorite place:

```text
POST /api/v1/user-places/favorites/
```

List saved favorite places:

```text
GET /api/v1/user-places/favorites/
```

Remove a saved favorite place:

```text
DELETE /api/v1/user-places/favorites/<osm_uid>/
```

List recent authenticated place searches:

```text
GET /api/v1/user-places/search-history/
```
