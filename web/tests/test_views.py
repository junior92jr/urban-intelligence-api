import re
from pathlib import Path
from typing import Any, cast

import pytest
from chainmock import mocker
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User, UserProfile
from accounts.services.registration import register_user
from geo.models import ServiceArea
from intelligence.models import (
    IntelligenceDataset,
    IntelligenceImport,
    IntelligenceIndicator,
    IntelligenceSource,
)
from intelligence.tasks import run_intelligence_import
from places.models import PlaceImport
from places.tasks import run_place_import
from web import views as web_views

APP_JS_PATH = Path(__file__).resolve().parents[1] / "static/web/app.js"
STYLES_PATH = Path(__file__).resolve().parents[1] / "static/web/styles.css"
ACTIVATION_LINK_PATTERN = re.compile(r"http://testserver/activate/\?token=[^\s<]+")

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def assert_checked_checkbox(response: Any, field_name: str) -> None:
    pattern = rb'<input[^>]*name="' + field_name.encode() + rb'"[^>]*checked[^>]*>'
    assert re.search(pattern, response.content) is not None


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
    assert b"data-favorites-url=" in response.content
    assert b"data-nearby-places-url=" in response.content
    assert b"data-area-scans-url=" in response.content
    assert b"data-area-intelligence-url=" in response.content
    assert b"data-tree-cover-layer-url=" in response.content
    assert b'data-realtime-refresh-enabled="false"' in response.content
    assert b'id="search-form"' in response.content
    assert b"Area Intelligence" in response.content
    assert b"Map features" in response.content
    assert b'id="area-insights"' in response.content
    assert b'id="tree-cover-legend"' in response.content
    assert b'id="tree-cover-toggle-input"' in response.content
    assert b"Nearby places" in response.content
    assert b"Latitude" not in response.content
    assert b"Longitude" not in response.content
    assert b"app-rail" in response.content
    assert b"Sign in to search" not in response.content
    assert b"unpkg.com" not in response.content


def test_map_page_uses_saved_location_preferences(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="web-map-location@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    UserProfile.objects.create(
        user=user,
        service_area=ServiceArea.objects.get(slug="frankfurt-am-main"),
        preferred_radius=800,
    )
    api_client.force_login(user)

    response = api_client.get(reverse("web:map"))

    assert response.status_code == status.HTTP_200_OK
    assert b'data-default-lat="50.1109"' in response.content
    assert b'data-default-lng="8.6821"' in response.content
    assert b'data-default-radius="800"' in response.content
    assert b'value="800"' in response.content
    assert b"800 m" in response.content


def test_map_page_exposes_enabled_realtime_refresh_preference(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="web-map-realtime-refresh@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    UserProfile.objects.create(
        user=user,
        service_area=ServiceArea.objects.get(slug="frankfurt-am-main"),
        realtime_refresh_enabled=True,
    )
    api_client.force_login(user)

    response = api_client.get(reverse("web:map"))

    assert response.status_code == status.HTTP_200_OK
    assert b'data-realtime-refresh-enabled="true"' in response.content


def test_profile_page_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get(reverse("web:profile"))

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"].startswith(str(reverse("web:login")))


def test_favorites_page_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get(reverse("web:favorites"))

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"].startswith(str(reverse("web:login")))


def test_history_page_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get(reverse("web:history"))

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"].startswith(str(reverse("web:login")))


def test_data_imports_page_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get(reverse("web:data_imports"))

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"].startswith(str(reverse("web:login")))


@pytest.mark.parametrize(
    ("url_name", "title"),
    [
        ("web:login", b"Sign in"),
        ("web:register", b"Create account"),
        ("web:registration_sent", b"Check your email"),
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


def test_onboarding_page_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get(reverse("web:onboarding"))

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"].startswith(str(reverse("web:login")))


def test_onboarding_page_renders_for_authenticated_user(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="onboarding-render-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    api_client.force_login(user)

    response = api_client.get(reverse("web:onboarding"))

    assert response.status_code == status.HTTP_200_OK
    assert b"Set up your map" in response.content
    assert b"auth-layout" in response.content
    assert b'id="profile-locate-button"' in response.content
    assert b"Germany" in response.content
    assert b"Frankfurt am Main" in response.content


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_register_page_sends_activation_email(api_client: APIClient) -> None:
    response = api_client.post(
        reverse("web:register"),
        {
            "email": "register-web@example.com",
            "password": "N3arby-Places-Key-842!",
            "password_confirm": "N3arby-Places-Key-842!",
            "first_name": "Register",
            "last_name": "Member",
        },
        follow=True,
    )
    outbox = cast(list[Any], vars(mail)["outbox"])

    assert response.status_code == status.HTTP_200_OK
    assert response.redirect_chain == [
        (reverse("web:registration_sent"), status.HTTP_302_FOUND),
    ]
    assert len(outbox) == 1
    assert outbox[0].subject == "Activate your City Guide account"
    assert outbox[0].to == ["register-web@example.com"]
    assert "/activate/?token=" in outbox[0].body
    assert "activation token" not in outbox[0].body.lower()
    assert b"Activation token:" not in response.content
    assert b"Check your email for the activation link." in response.content


def test_register_page_rejects_mismatched_passwords(api_client: APIClient) -> None:
    response = api_client.post(
        reverse("web:register"),
        {
            "email": "mismatch-web@example.com",
            "password": "N3arby-Places-Key-842!",
            "password_confirm": "Different-Places-Key-842!",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert b"Passwords do not match." in response.content
    assert not User.objects.filter(email="mismatch-web@example.com").exists()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_register_activation_email_link_activates_account(
    api_client: APIClient,
) -> None:
    api_client.post(
        reverse("web:register"),
        {
            "email": "register-link-web@example.com",
            "password": "N3arby-Places-Key-842!",
            "password_confirm": "N3arby-Places-Key-842!",
        },
    )
    outbox = cast(list[Any], vars(mail)["outbox"])
    activation_url_match = ACTIVATION_LINK_PATTERN.search(outbox[0].body)
    assert activation_url_match is not None

    response = api_client.get(activation_url_match.group(0))
    user = User.objects.get(email="register-link-web@example.com")

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == reverse("web:onboarding")
    assert user.is_active is True
    assert api_client.get(reverse("web:onboarding")).status_code == status.HTTP_200_OK


def test_activate_page_activates_account_from_email_link(
    api_client: APIClient,
) -> None:
    user, activation_token = register_user(
        email="activate-web@example.com",
        password="N3arby-Places-Key-842!",
    )

    response = api_client.get(
        reverse("web:activate"),
        {"token": activation_token},
    )
    user.refresh_from_db()

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == reverse("web:onboarding")
    assert user.is_active is True
    assert api_client.get(reverse("web:onboarding")).status_code == status.HTTP_200_OK


def test_activate_page_redirects_missing_token_to_login(
    api_client: APIClient,
) -> None:
    response = api_client.get(reverse("web:activate"))

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == reverse("web:login")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_forgot_password_page_sends_reset_email_for_active_user(
    api_client: APIClient,
) -> None:
    User.objects.create_user(
        email="forgot-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )

    response = api_client.post(
        reverse("web:forgot_password"),
        {"email": "forgot-web@example.com"},
        follow=True,
    )
    outbox = cast(list[Any], vars(mail)["outbox"])

    assert response.status_code == status.HTTP_200_OK
    assert len(outbox) == 1
    assert outbox[0].subject == "Reset your City Guide password"
    assert outbox[0].to == ["forgot-web@example.com"]
    assert "/reset-password/?token=" in outbox[0].body
    assert "reset token" not in outbox[0].body.lower()
    assert b"Password reset token:" not in response.content
    assert (
        b"If the account exists, a password reset email was sent." in response.content
    )


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
    assert b"app-shell" in response.content
    assert b"settings-page" in response.content
    assert b"settings-panel" in response.content
    assert b"profile-form" in response.content
    assert b"app-rail" in response.content
    assert b"rail-form" in response.content
    assert b"Sign out" in response.content
    assert b'class="sidebar"' not in response.content
    assert b"map-shell" not in response.content
    assert b'id="map"' not in response.content
    assert b"data-tile-url=" not in response.content
    assert b"auth-layout" not in response.content


def test_profile_page_renders_saved_checkbox_preferences(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="profile-checkboxes-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    UserProfile.objects.create(
        user=user,
        service_area=ServiceArea.objects.get(slug="frankfurt-am-main"),
        location_sharing_enabled=True,
        realtime_refresh_enabled=True,
    )
    api_client.force_login(user)

    response = api_client.get(reverse("web:profile"))

    assert response.status_code == status.HTTP_200_OK
    assert_checked_checkbox(response, "location_sharing_enabled")
    assert_checked_checkbox(response, "realtime_refresh_enabled")


def test_onboarding_page_saves_location_preferences(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="onboarding-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    api_client.force_login(user)
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    mocker(web_views).mock("enqueue_profile_area_scan").called_once()

    response = api_client.post(
        reverse("web:onboarding"),
        {
            "service_area": str(service_area.pk),
            "default_latitude": "50.1109",
            "default_longitude": "8.6821",
            "location_sharing_enabled": "on",
            "realtime_refresh_enabled": "on",
            "preferred_radius": "700",
        },
    )
    profile = UserProfile.objects.get(user=user)

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == reverse("web:map")
    assert profile.service_area == service_area
    assert profile.default_latitude == 50.1109
    assert profile.default_longitude == 8.6821
    assert profile.location_sharing_enabled is True
    assert profile.realtime_refresh_enabled is True
    assert profile.preferred_radius == 700
    assert profile.onboarding_completed_at is not None


def test_login_redirects_new_user_to_onboarding(api_client: APIClient) -> None:
    User.objects.create_user(
        email="login-onboarding-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )

    response = api_client.post(
        reverse("web:login"),
        {
            "username": "login-onboarding-web@example.com",
            "password": "N3arby-Places-Key-842!",
        },
    )

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == reverse("web:onboarding")


def test_profile_page_updates_location_preferences(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="profile-update-web@example.com",
        password="N3arby-Places-Key-842!",
        first_name="Old",
        last_name="Name",
        is_active=True,
    )
    api_client.force_login(user)
    service_area = ServiceArea.objects.get(slug="berlin")
    mocker(web_views).mock("enqueue_profile_area_scan").called_once()

    response = api_client.post(
        reverse("web:profile"),
        {
            "first_name": "New",
            "last_name": "Name",
            "service_area": str(service_area.pk),
            "default_latitude": "52.52",
            "default_longitude": "13.405",
            "location_sharing_enabled": "on",
            "realtime_refresh_enabled": "on",
            "preferred_radius": "900",
        },
        follow=True,
    )
    user.refresh_from_db()
    profile = UserProfile.objects.get(user=user)

    assert response.status_code == status.HTTP_200_OK
    assert response.redirect_chain == [(reverse("web:profile"), status.HTTP_302_FOUND)]
    assert user.first_name == "New"
    assert profile.service_area == service_area
    assert profile.default_latitude == 52.52
    assert profile.default_longitude == 13.405
    assert profile.location_sharing_enabled is True
    assert profile.realtime_refresh_enabled is True
    assert_checked_checkbox(response, "location_sharing_enabled")
    assert_checked_checkbox(response, "realtime_refresh_enabled")


def test_favorites_page_renders_for_authenticated_user(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="favorites-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    api_client.force_login(user)

    response = api_client.get(reverse("web:favorites"))

    assert response.status_code == status.HTTP_200_OK
    assert b"Favorites" in response.content
    assert b'id="favorite-results"' in response.content
    assert b'id="map"' in response.content
    assert b"data-favorites-url=" in response.content
    assert b"app-rail" in response.content


def test_history_page_renders_for_authenticated_user(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="history-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    api_client.force_login(user)

    response = api_client.get(reverse("web:history"))

    assert response.status_code == status.HTTP_200_OK
    assert b"History" in response.content
    assert b'id="history-results"' in response.content
    assert b'id="map"' in response.content
    assert b"data-history-url=" in response.content
    assert b"app-rail" in response.content


def test_data_imports_page_requires_staff_user(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="data-imports-member-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    api_client.force_login(user)

    response = api_client.get(reverse("web:data_imports"))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_data_imports_page_renders_for_staff_user(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="data-imports-staff-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
        is_staff=True,
    )
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    PlaceImport.objects.create(
        service_area=service_area,
        layer=PlaceImport.Layer.AMENITIES,
        radius=8000,
        requested_by=user,
        result_count=12,
    )
    api_client.force_login(user)

    response = api_client.get(reverse("web:data_imports"))

    assert response.status_code == status.HTTP_200_OK
    assert b"Data Imports" in response.content
    assert b"OpenStreetMap" in response.content
    assert b"Start place import" in response.content
    assert b"Map layer" in response.content
    assert b"Green spaces" in response.content
    assert b"Recent place imports" in response.content
    assert b"Frankfurt am Main" in response.content
    assert b"12 places" in response.content
    assert b"imports-panel" in response.content
    assert b"app-rail" in response.content


def test_data_imports_page_starts_open_street_map_import(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="data-imports-submit-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
        is_staff=True,
    )
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    api_client.force_login(user)
    mocker(run_place_import).mock("delay").called_once()

    response = api_client.post(
        reverse("web:data_imports"),
        {
            "import_type": "places",
            "service_area": str(service_area.pk),
            "layer": "amenities",
            "radius": "8000",
        },
    )
    place_import = PlaceImport.objects.get()

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == reverse("web:data_imports")
    assert place_import.status == PlaceImport.Status.PENDING
    assert place_import.service_area == service_area
    assert place_import.layer == PlaceImport.Layer.AMENITIES
    assert place_import.radius == 8000
    assert place_import.requested_by == user


def test_data_imports_page_shows_configured_intelligence_dataset(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="intelligence-imports-empty-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
        is_staff=True,
    )
    api_client.force_login(user)

    response = api_client.get(f"{reverse('web:data_imports')}?type=intelligence")

    assert response.status_code == status.HTTP_200_OK
    assert b"Area intelligence" in response.content
    assert b"Tree Cover Density (100 m)" in response.content


def test_data_imports_page_starts_intelligence_import(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="intelligence-imports-submit-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
        is_staff=True,
    )
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    dataset = IntelligenceDataset.objects.create(
        source=IntelligenceSource.objects.get(slug="open-street-map"),
        indicator=IntelligenceIndicator.objects.get(slug="green-exposure"),
        slug="tree-cover-density",
        name="Tree Cover Density",
    )
    api_client.force_login(user)
    mocker(run_intelligence_import).mock("delay").called_once()

    response = api_client.post(
        reverse("web:data_imports"),
        {
            "import_type": "intelligence",
            "dataset": str(dataset.pk),
            "service_area": str(service_area.pk),
        },
    )
    intelligence_import = IntelligenceImport.objects.get()

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == f"{reverse('web:data_imports')}?type=intelligence"
    assert intelligence_import.status == IntelligenceImport.Status.PENDING
    assert intelligence_import.dataset == dataset
    assert intelligence_import.service_area == service_area
    assert intelligence_import.requested_by == user


def test_data_imports_rejects_tree_cover_density_without_a_city_boundary(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="intelligence-imports-boundary-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
        is_staff=True,
    )
    api_client.force_login(user)
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")
    service_area.boundary = None
    service_area.save(update_fields=["boundary"])
    dataset = IntelligenceDataset.objects.get(slug="tree-cover-density-100m")

    response = api_client.post(
        reverse("web:data_imports"),
        {
            "import_type": "intelligence",
            "dataset": str(dataset.pk),
            "service_area": str(service_area.pk),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert b"This dataset requires a city boundary" in response.content
    assert not IntelligenceImport.objects.filter(dataset=dataset).exists()


@override_settings(OBJECT_STORAGE_BUCKET="")
def test_data_imports_rejects_tree_cover_density_without_object_storage(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="intelligence-imports-storage-web@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
        is_staff=True,
    )
    api_client.force_login(user)
    dataset = IntelligenceDataset.objects.get(slug="tree-cover-density-100m")
    service_area = ServiceArea.objects.get(slug="frankfurt-am-main")

    response = api_client.post(
        reverse("web:data_imports"),
        {
            "import_type": "intelligence",
            "dataset": str(dataset.pk),
            "service_area": str(service_area.pk),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert (
        b"Configure cache object storage before importing this dataset"
        in response.content
    )
    assert not IntelligenceImport.objects.filter(dataset=dataset).exists()


def test_map_app_reads_tile_url_from_template_dataset() -> None:
    app_js = APP_JS_PATH.read_text()

    assert "shell.dataset.tileUrl" in app_js
    assert "tile.openstreetmap.org" not in app_js


def test_map_app_supports_the_copernicus_tree_cover_layer() -> None:
    app_js = APP_JS_PATH.read_text()

    assert "shell.dataset.treeCoverLayerUrl" in app_js
    assert "L.imageOverlay(layer.image_url, layer.bounds" in app_js
    assert "L.geoJSON(treeCoverMapLayer.boundary" in app_js
    assert "treeCoverBoundary.getBounds()" in app_js
    assert "treeCoverToggleInput?.addEventListener" in app_js
    assert "Around ${observation.score}% average tree canopy cover" in app_js


def test_map_app_shows_radius_circle_only_while_selecting_radius() -> None:
    app_js = APP_JS_PATH.read_text()

    assert "L.circle(getSelectedLocation()" in app_js
    assert 'radiusInput?.addEventListener("input"' in app_js
    assert 'radiusInput?.addEventListener("pointerup"' in app_js
    assert "hideRadiusCircle();" in app_js


def test_map_app_supports_anonymous_sidebar_without_search_form() -> None:
    app_js = APP_JS_PATH.read_text()

    assert "const submitButton = form?.querySelector" in app_js
    assert 'document.querySelector(".map-shell, .app-shell")' in app_js
    assert "if (form !== null)" in app_js
    assert "form?.addEventListener" in app_js
    assert "const defaultCenter = getDefaultCenter();" in app_js
    assert (
        'const map = mapElement ? L.map("map").setView(defaultCenter, 13) : null;'
        in app_js
    )
    assert "if (shell !== null)" in app_js


def test_map_app_supports_favorite_toggles() -> None:
    app_js = APP_JS_PATH.read_text()

    assert "shell.dataset.favoritesUrl" in app_js
    assert "toggleFavorite(place" in app_js
    assert "favoriteOsmUids" in app_js
    assert "renderFavoritePlaces" in app_js
    assert "favoritePlaceIcon" in app_js
    assert "createHeartMarkerIcon" in app_js
    assert "getPlaceMarkerIcon" in app_js
    assert "rail-toggle" in app_js
    assert "cityGuide.navCollapsed" in app_js
    assert "applyNavigationState" in app_js
    assert "loadSearchHistory" in app_js
    assert "restoreSearchFromUrl" in app_js
    assert "profileLocateButton" in app_js
    assert "locationSharingInput.checked = true;" in app_js


def test_map_app_refreshes_places_in_background() -> None:
    app_js = APP_JS_PATH.read_text()

    assert (
        'const realtimeRefreshEnabled = shell?.dataset.realtimeRefreshEnabled === "true";'
        in app_js
    )
    assert "if (realtimeRefreshEnabled)" in app_js
    assert "refreshPlacesInBackground(params, searchKey);" in app_js
    assert "let currentRefreshController = null;" in app_js
    assert 'let currentSearchKey = "";' in app_js
    assert "if (searchKey !== currentSearchKey)" in app_js
    assert "await pollAreaScan(scan.id, controller.signal);" in app_js
    assert "submitButton.disabled = false;" in app_js


def test_collapsed_navigation_keeps_toggle_visible() -> None:
    styles = STYLES_PATH.read_text()

    assert "grid-template-columns: 164px minmax(340px, 440px) minmax(0, 1fr);" in styles
    assert "grid-template-columns: 60px minmax(340px, 440px) minmax(0, 1fr);" in styles
    assert '.map-shell[data-nav-collapsed="true"] .rail-link span' in styles
    assert "rail-toggle-icon--collapse" in styles
    assert "rail-toggle-icon--expand" in styles


def test_sidebar_results_scroll_inside_map_shell() -> None:
    styles = STYLES_PATH.read_text()

    assert "height: 100vh;" in styles
    assert "overflow: hidden;" in styles
    assert "overflow-y: auto;" in styles
    assert "overscroll-behavior: contain;" in styles


def test_favorite_button_uses_compact_inline_style() -> None:
    styles = STYLES_PATH.read_text()

    assert ".favorite-button {" in styles
    assert "width: 32px;" in styles
    assert "border-radius: 7px;" in styles


def test_data_import_results_scroll_inside_panel() -> None:
    styles = STYLES_PATH.read_text()

    assert ".imports-panel" in styles
    assert "max-height: min(520px, 52vh);" in styles
    assert "overscroll-behavior: contain;" in styles
    assert "overflow-wrap: anywhere;" in styles


def test_settings_pages_scroll_inside_app_shell() -> None:
    styles = STYLES_PATH.read_text()

    assert (
        ".app-shell {\n  display: grid;\n  grid-template-columns: 164px minmax(0, 1fr);\n  height: 100vh;\n  overflow: hidden;\n}"
        in styles
    )
    assert ".settings-page {\n  min-height: 0;" in styles
    assert "overflow-y: auto;" in styles
    assert ".app-shell {\n    grid-template-columns: 1fr;\n    height: auto;" in styles
    assert (
        ".settings-page {\n    min-height: auto;\n    padding: 20px;\n    overflow: visible;\n  }"
        in styles
    )
