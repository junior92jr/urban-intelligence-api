import pytest
from rest_framework.test import APIRequestFactory

from accounts.models import User
from user_places.serializers import FavoritePlaceSerializer

pytestmark = pytest.mark.django_db


def test_favorite_place_serializer_creates_user_favorite() -> None:
    user = User.objects.create_user(
        email="favorite-serializer@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    request = APIRequestFactory().post("/api/v1/user-places/favorites/")
    request.user = user
    serializer = FavoritePlaceSerializer(
        data={
            "osm_uid": "osm-node-123",
            "osm_id": 123,
            "osm_type": "node",
            "name": "Cafe Central",
            "category": "cafe",
            "category_name": "Cafe",
            "latitude": 50.1109,
            "longitude": 8.6821,
        },
        context={"request": request},
    )

    assert serializer.is_valid(), serializer.errors
    favorite = serializer.save()

    assert favorite.user == user
    assert favorite.osm_uid == "osm-node-123"
    assert favorite.latitude == 50.1109
    assert favorite.longitude == 8.6821
