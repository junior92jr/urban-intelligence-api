import pytest

from places.serializers import RecommendationsQuerySerializer

pytestmark = pytest.mark.django_db


def test_recommendations_query_serializer_accepts_required_coordinates():
    serializer = RecommendationsQuerySerializer(
        data={
            "lat": "50.1101038",
            "lng": "8.6771586",
        }
    )

    assert serializer.is_valid()
    assert serializer.to_query_params() == {
        "lat": 50.1101038,
        "lng": 8.6771586,
        "search_radius": 500,
    }


def test_recommendations_query_serializer_accepts_optional_filters():
    serializer = RecommendationsQuerySerializer(
        data={
            "lat": "50.1101038",
            "lng": "8.6771586",
            "search_radius": "250",
            "category": "parking",
        }
    )

    assert serializer.is_valid()
    assert serializer.to_query_params() == {
        "lat": 50.1101038,
        "lng": 8.6771586,
        "search_radius": 250,
        "category": "parking",
    }


def test_recommendations_query_serializer_accepts_optional_category_group():
    serializer = RecommendationsQuerySerializer(
        data={
            "lat": "50.1101038",
            "lng": "8.6771586",
            "search_radius": "250",
            "category_group": "mobility",
        }
    )

    assert serializer.is_valid()
    assert serializer.to_query_params() == {
        "lat": 50.1101038,
        "lng": 8.6771586,
        "search_radius": 250,
        "category_group": "mobility",
    }


def test_recommendations_query_serializer_rejects_category_and_group():
    serializer = RecommendationsQuerySerializer(
        data={
            "lat": "50.1101038",
            "lng": "8.6771586",
            "category": "parking",
            "category_group": "mobility",
        }
    )

    assert not serializer.is_valid()
    assert "category_group" in serializer.errors


def test_recommendations_query_serializer_accepts_legacy_radius_alias():
    serializer = RecommendationsQuerySerializer(
        data={
            "lat": "50.1101038",
            "lng": "8.6771586",
            "search_radious": "250",
        }
    )

    assert serializer.is_valid()
    assert serializer.to_query_params() == {
        "lat": 50.1101038,
        "lng": 8.6771586,
        "search_radius": 250,
    }


def test_recommendations_query_serializer_rejects_conflicting_radius_values():
    serializer = RecommendationsQuerySerializer(
        data={
            "lat": "50.1101038",
            "lng": "8.6771586",
            "search_radius": "250",
            "search_radious": "500",
        }
    )

    assert not serializer.is_valid()
    assert "search_radius" in serializer.errors


def test_recommendations_query_serializer_requires_coordinates():
    serializer = RecommendationsQuerySerializer(
        data={
            "lat": "50.1101038",
        }
    )

    assert not serializer.is_valid()
    assert "lng" in serializer.errors


def test_recommendations_query_serializer_rejects_invalid_coordinates():
    serializer = RecommendationsQuerySerializer(
        data={
            "lat": "not-a-float",
            "lng": "8.6771586",
        }
    )

    assert not serializer.is_valid()
    assert "lat" in serializer.errors


def test_recommendations_query_serializer_rejects_unknown_category():
    serializer = RecommendationsQuerySerializer(
        data={
            "lat": "50.1101038",
            "lng": "8.6771586",
            "category": "unknown",
        }
    )

    assert not serializer.is_valid()
    assert "category" in serializer.errors


def test_recommendations_query_serializer_rejects_radius_above_city_range():
    serializer = RecommendationsQuerySerializer(
        data={
            "lat": "50.1101038",
            "lng": "8.6771586",
            "search_radius": "3001",
        }
    )

    assert not serializer.is_valid()
    assert "search_radius" in serializer.errors
