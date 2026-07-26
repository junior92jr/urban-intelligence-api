from pathlib import Path

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User

APP_JS_PATH = Path(__file__).resolve().parents[1] / "static/web/app.js"

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_map_page_redirects_anonymous_user_to_login(api_client: APIClient) -> None:
    response = api_client.get(reverse("web:map"))

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"].startswith(str(reverse("web:login")))


def test_map_page_renders_search_sidebar_for_authenticated_user(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="web-map@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    api_client.force_login(user)

    response = api_client.get(reverse("web:map"))

    assert response.status_code == status.HTTP_200_OK
    assert b'id="map"' in response.content
    assert b"data-tile-url=" in response.content
    assert b"data-tile-attribution=" in response.content
    assert b'id="search-form"' in response.content
    assert b"Sign in to search" not in response.content
    assert b"unpkg.com" not in response.content


def test_profile_page_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get(reverse("web:profile"))

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"].startswith(str(reverse("web:login")))


@pytest.mark.parametrize(
    ("url_name", "title"),
    [
        ("web:login", b"Sign in"),
        ("web:register", b"Create account"),
        ("web:activate", b"Activate account"),
        ("web:forgot_password", b"Forgot password"),
        ("web:reset_password", b"Reset password"),
    ],
)
def test_account_pages_render(
    api_client: APIClient,
    url_name: str,
    title: bytes,
) -> None:
    response = api_client.get(reverse(url_name))

    assert response.status_code == status.HTTP_200_OK
    assert title in response.content
    assert b"auth-layout" in response.content
    assert b"auth-panel" in response.content


def test_profile_page_renders_for_authenticated_user(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="profile-web@example.com",
        password="N3arby-Places-Key-842!",
        first_name="Profile",
        last_name="Owner",
        is_active=True,
    )
    api_client.force_login(user)

    response = api_client.get(reverse("web:profile"))

    assert response.status_code == status.HTTP_200_OK
    assert b"profile-web@example.com" in response.content
    assert b"map-shell" in response.content
    assert b'id="map"' in response.content
    assert b"data-tile-url=" in response.content
    assert b"auth-layout" not in response.content


def test_map_app_reads_tile_url_from_template_dataset() -> None:
    app_js = APP_JS_PATH.read_text()

    assert "shell.dataset.tileUrl" in app_js
    assert "tile.openstreetmap.org" not in app_js


def test_map_app_shows_radius_circle_only_while_selecting_radius() -> None:
    app_js = APP_JS_PATH.read_text()

    assert "L.circle(getSelectedLocation()" in app_js
    assert 'radiusInput?.addEventListener("input"' in app_js
    assert 'radiusInput?.addEventListener("pointerup"' in app_js
    assert "hideRadiusCircle();" in app_js


def test_map_app_supports_anonymous_sidebar_without_search_form() -> None:
    app_js = APP_JS_PATH.read_text()

    assert "const submitButton = form?.querySelector" in app_js
    assert "if (form !== null)" in app_js
    assert "form?.addEventListener" in app_js
