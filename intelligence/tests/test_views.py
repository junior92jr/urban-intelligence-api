from collections.abc import Iterable
from datetime import timedelta
from io import BytesIO
from typing import cast
from unittest.mock import Mock

import pytest
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User, UserProfile
from geo.models import ServiceArea
from intelligence.models import (
    AreaIndicatorObservation,
    IntelligenceIndicator,
    IntelligenceSource,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def authenticated_api_client() -> APIClient:
    user = User.objects.create_user(
        email="intelligence@example.com",
        password="Ar3a-Intelligence-Key-842!",
        is_active=True,
    )
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


def test_area_intelligence_returns_latest_observation_for_user_service_area(
    authenticated_api_client: APIClient,
) -> None:
    user = User.objects.get(email="intelligence@example.com")
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    UserProfile.objects.create(user=user, service_area=service_area)
    indicator = IntelligenceIndicator.objects.get(slug="walkability")
    source = IntelligenceSource.objects.get(slug="open-street-map")
    AreaIndicatorObservation.objects.create(
        service_area=service_area,
        indicator=indicator,
        source=source,
        score=72,
        methodology="Pedestrian network coverage",
        observed_at=timezone.now() - timedelta(days=1),
    )
    AreaIndicatorObservation.objects.create(
        service_area=service_area,
        indicator=indicator,
        source=source,
        score=88,
        methodology="Pedestrian network coverage",
        observed_at=timezone.now(),
    )

    response = authenticated_api_client.get("/api/v1/places/area-intelligence/")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["service_area"] == {
        "slug": "frankfurt-am-main",
        "name": "Frankfurt am Main",
    }
    mobility = next(group for group in payload["groups"] if group["slug"] == "mobility")
    walkability = next(
        indicator
        for indicator in mobility["indicators"]
        if indicator["slug"] == "walkability"
    )
    assert walkability["observation"]["score"] == 88
    assert walkability["observation"]["source"] == {
        "name": "OpenStreetMap",
        "attribution": "OpenStreetMap contributors",
    }
    assert [group["slug"] for group in payload["groups"]] == ["mobility"]


def test_area_intelligence_requires_a_service_area(
    authenticated_api_client: APIClient,
) -> None:
    response = authenticated_api_client.get("/api/v1/places/area-intelligence/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "service_area": "Complete onboarding before viewing area intelligence."
    }


def test_tree_cover_map_layer_returns_summary_boundary_and_private_image_urls(
    authenticated_api_client: APIClient,
) -> None:
    user = User.objects.get(email="intelligence@example.com")
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    UserProfile.objects.create(user=user, service_area=service_area)
    indicator = IntelligenceIndicator.objects.get(slug="green-exposure")
    source = IntelligenceSource.objects.get(slug="copernicus-land-monitoring")
    AreaIndicatorObservation.objects.create(
        service_area=service_area,
        indicator=indicator,
        source=source,
        score=20,
        observed_at=timezone.now(),
        details={
            "map_layer": {
                "title": "Tree cover",
                "layers": [
                    {
                        "object_key": "copernicus/tree-cover-density/frankfurt.png",
                        "bounds": [[50.0, 8.5], [50.2, 8.8]],
                    }
                ],
            }
        },
    )

    response = authenticated_api_client.get(
        "/api/v1/places/area-intelligence/tree-cover-density/"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["summary"] == (
        "Around 20% average tree canopy cover across Frankfurt am Main."
    )
    assert response.json()["boundary"]["type"] == "MultiPolygon"
    assert response.json()["layers"] == [
        {
            "bounds": [[50.0, 8.5], [50.2, 8.8]],
            "image_url": (
                "http://testserver/api/v1/places/area-intelligence/"
                "tree-cover-density/layers/0/"
            ),
        }
    ]


def test_tree_cover_map_layer_image_streams_the_private_overlay(
    authenticated_api_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.get(email="intelligence@example.com")
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    UserProfile.objects.create(user=user, service_area=service_area)
    indicator = IntelligenceIndicator.objects.get(slug="green-exposure")
    source = IntelligenceSource.objects.get(slug="copernicus-land-monitoring")
    AreaIndicatorObservation.objects.create(
        service_area=service_area,
        indicator=indicator,
        source=source,
        score=20,
        observed_at=timezone.now(),
        details={
            "map_layer": {
                "layers": [
                    {
                        "object_key": "copernicus/tree-cover-density/frankfurt.png",
                        "bounds": [[50.0, 8.5], [50.2, 8.8]],
                    }
                ]
            }
        },
    )
    storage_client = Mock()
    storage_client.get_object.return_value = {"Body": BytesIO(b"tree-cover-png")}
    monkeypatch.setattr(
        "intelligence.views.get_cache_storage_client",
        lambda: storage_client,
    )

    response = authenticated_api_client.get(
        "/api/v1/places/area-intelligence/tree-cover-density/layers/0/"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"] == "image/png"
    streaming_response = cast(StreamingHttpResponse, response)
    streaming_content = cast(Iterable[bytes], streaming_response.streaming_content)
    assert b"".join(streaming_content) == b"tree-cover-png"
    storage_client.get_object.assert_called_once()
