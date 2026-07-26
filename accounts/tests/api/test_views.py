import pytest
from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APIRequestFactory

from accounts.authentication import BearerTokenAuthentication
from accounts.models import AccountToken, User
from accounts.services.tokens import (
    activation_token_lifetime,
    create_account_token,
    hash_account_token,
    password_reset_token_lifetime,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_register_creates_inactive_user_and_activation_token(
    api_client: APIClient,
) -> None:
    response = api_client.post(
        "/api/v1/accounts/register/",
        {
            "email": "new@example.com",
            "password": "N3arby-Places-Key-842!",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
        format="json",
    )

    user = User.objects.get(email="new@example.com")
    account_token = AccountToken.objects.get(user=user)
    activation_token = response.json()["activation_token"]

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {
        "id": user.pk,
        "email": "new@example.com",
        "activation_token": activation_token,
    }
    assert user.first_name == "Ada"
    assert user.last_name == "Lovelace"
    assert user.is_active is False
    assert account_token.purpose == AccountToken.Purpose.ACTIVATION
    assert account_token.token_hash == hash_account_token(activation_token)
    assert account_token.token_hash != activation_token


def test_activate_account_marks_user_active(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="activate@example.com",
        password="N3arby-Places-Key-842!",
        is_active=False,
    )
    raw_token, account_token = create_account_token(
        user=user,
        purpose=AccountToken.Purpose.ACTIVATION,
        expires_in=activation_token_lifetime(),
    )

    response = api_client.post(
        "/api/v1/accounts/activate/",
        {"token": raw_token},
        format="json",
    )

    user.refresh_from_db()
    account_token.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"detail": "Account activated."}
    assert user.is_active is True
    assert account_token.used_at is not None


def test_account_tokens_revoke_older_unused_tokens_for_same_purpose() -> None:
    user = User.objects.create_user(
        email="tokens@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    _, old_token = create_account_token(
        user=user,
        purpose=AccountToken.Purpose.PASSWORD_RESET,
        expires_in=password_reset_token_lifetime(),
    )

    create_account_token(
        user=user,
        purpose=AccountToken.Purpose.PASSWORD_RESET,
        expires_in=password_reset_token_lifetime(),
    )

    old_token.refresh_from_db()

    assert old_token.used_at is not None


def test_login_returns_bearer_token_for_active_user(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="login@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )

    response = api_client.post(
        "/api/v1/accounts/login/",
        {
            "email": "login@example.com",
            "password": "N3arby-Places-Key-842!",
        },
        format="json",
    )
    token_key = response.json()["token"]
    request = APIRequestFactory().get(
        "/",
        HTTP_AUTHORIZATION=f"Bearer {token_key}",
    )

    authentication_result = BearerTokenAuthentication().authenticate(request)

    assert authentication_result is not None
    authenticated_user, _ = authentication_result

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["token_type"] == "Bearer"
    assert authenticated_user == user


def test_logout_deletes_current_bearer_token(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="logout@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    token = Token.objects.create(user=user)

    response = api_client.post(
        "/api/v1/accounts/logout/",
        HTTP_AUTHORIZATION=f"Bearer {token.key}",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"detail": "Logged out."}
    assert Token.objects.filter(pk=token.pk).exists() is False


def test_logout_requires_authentication(api_client: APIClient) -> None:
    response = api_client.post("/api/v1/accounts/logout/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_profile_returns_authenticated_user(api_client: APIClient) -> None:
    user = User.objects.create_user(
        email="me@example.com",
        password="N3arby-Places-Key-842!",
        first_name="Map",
        last_name="Reader",
        is_active=True,
    )
    token = Token.objects.create(user=user)

    response = api_client.get(
        "/api/v1/accounts/me/",
        HTTP_AUTHORIZATION=f"Bearer {token.key}",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": user.pk,
        "email": "me@example.com",
        "first_name": "Map",
        "last_name": "Reader",
        "full_name": "Map Reader",
    }


def test_forgot_password_returns_reset_token_for_active_user(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="reset@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )

    response = api_client.post(
        "/api/v1/accounts/forgot-password/",
        {"email": "reset@example.com"},
        format="json",
    )
    reset_token = AccountToken.objects.get(
        user=user,
        purpose=AccountToken.Purpose.PASSWORD_RESET,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "detail": "If the account exists, a password reset token was created.",
        "reset_token": response.json()["reset_token"],
    }
    assert reset_token.token_hash == hash_account_token(response.json()["reset_token"])


def test_forgot_password_is_generic_for_unknown_email(api_client: APIClient) -> None:
    response = api_client.post(
        "/api/v1/accounts/forgot-password/",
        {"email": "unknown@example.com"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "detail": "If the account exists, a password reset token was created.",
    }


def test_reset_password_updates_password_and_consumes_token(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(
        email="password@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    raw_token, account_token = create_account_token(
        user=user,
        purpose=AccountToken.Purpose.PASSWORD_RESET,
        expires_in=password_reset_token_lifetime(),
    )

    response = api_client.post(
        "/api/v1/accounts/reset-password/",
        {
            "token": raw_token,
            "password": "Fr3sh-Places-Key-842!",
        },
        format="json",
    )

    user.refresh_from_db()
    account_token.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"detail": "Password reset."}
    assert check_password("Fr3sh-Places-Key-842!", user.password)
    assert account_token.used_at is not None
