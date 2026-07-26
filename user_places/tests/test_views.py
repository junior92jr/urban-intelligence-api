import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from user_places.models import FavoritePlace, SearchHistory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def favorite_payload(osm_uid: str = "osm-node-123") -> dict[str, object]:
    return {
        "osm_uid": osm_uid,
        "osm_id": 123,
        "osm_type": "node",
        "name": "Cafe Central",
        "category": "cafe",
        "category_name": "Cafe",
        "latitude": 50.1109,
        "longitude": 8.6821,
    }


def test_favorites_require_authentication(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/user-places/favorites/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_search_history_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/user-places/search-history/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_favorite_place(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="favorite@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    api_client.force_authenticate(user=user)

    response = api_client.post(
        "/api/v1/user-places/favorites/",
        favorite_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert FavoritePlace.objects.filter(user=user, osm_uid="osm-node-123").exists()


def test_create_favorite_place_is_idempotent_for_same_user(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="favorite-idempotent@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    api_client.force_authenticate(user=user)

    first_response = api_client.post(
        "/api/v1/user-places/favorites/",
        favorite_payload(),
        format="json",
    )
    second_response = api_client.post(
        "/api/v1/user-places/favorites/",
        favorite_payload(),
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED
    assert FavoritePlace.objects.filter(user=user, osm_uid="osm-node-123").count() == 1


def test_list_favorite_places_returns_only_authenticated_user_places(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="favorite-list@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    other_user = User.objects.create_user(
        email="favorite-other@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    FavoritePlace.objects.create(user=user, **favorite_payload("osm-node-123"))
    FavoritePlace.objects.create(
        user=other_user,
        **favorite_payload("osm-node-456"),
    )
    api_client.force_authenticate(user=user)

    response = api_client.get("/api/v1/user-places/favorites/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]["osm_uid"] == "osm-node-123"
    assert len(response.json()) == 1


def test_delete_favorite_place(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="favorite-delete@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    FavoritePlace.objects.create(user=user, **favorite_payload("osm-node-123"))
    api_client.force_authenticate(user=user)

    response = api_client.delete("/api/v1/user-places/favorites/osm-node-123/")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not FavoritePlace.objects.filter(user=user, osm_uid="osm-node-123").exists()


def test_list_search_history_returns_only_authenticated_user_searches(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="history-list@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    other_user = User.objects.create_user(
        email="history-other@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    SearchHistory.objects.create(
        user=user,
        latitude=50.1109,
        longitude=8.6821,
        search_radius=500,
        category="restaurant",
        result_count=3,
    )
    SearchHistory.objects.create(
        user=other_user,
        latitude=51.0,
        longitude=9.0,
        search_radius=300,
        category="cafe",
        result_count=1,
    )
    api_client.force_authenticate(user=user)

    response = api_client.get("/api/v1/user-places/search-history/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["category"] == "restaurant"
    assert response.json()[0]["result_count"] == 3
