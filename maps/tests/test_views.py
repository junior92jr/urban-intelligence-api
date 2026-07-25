from pathlib import Path

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

APP_JS_PATH = Path(__file__).resolve().parents[1] / "static/maps/app.js"


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_map_page_renders(api_client: APIClient) -> None:
    response = api_client.get(reverse("maps:index"))

    assert response.status_code == status.HTTP_200_OK
    assert b'id="map"' in response.content
    assert b"data-tile-url=" in response.content
    assert b"data-tile-attribution=" in response.content
    assert b"unpkg.com" not in response.content


def test_map_app_reads_tile_url_from_template_dataset() -> None:
    app_js = APP_JS_PATH.read_text()

    assert "shell.dataset.tileUrl" in app_js
    assert "tile.openstreetmap.org" not in app_js
