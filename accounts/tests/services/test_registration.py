import pytest
from django.contrib.auth.hashers import check_password
from rest_framework.authtoken.models import Token

from accounts.models import AccountToken, User
from accounts.services.registration import (
    activate_account,
    create_password_reset_token,
    login_user,
    register_user,
    reset_password,
)
from accounts.services.tokens import hash_account_token

pytestmark = pytest.mark.django_db


def test_register_user_creates_inactive_user_and_activation_token() -> None:
    user, raw_token = register_user(
        email="register@example.com",
        password="N3arby-Places-Key-842!",
        first_name="Ada",
        last_name="Lovelace",
    )
    account_token = AccountToken.objects.get(user=user)

    assert user.email == "register@example.com"
    assert user.first_name == "Ada"
    assert user.last_name == "Lovelace"
    assert user.is_active is False
    assert account_token.purpose == AccountToken.Purpose.ACTIVATION
    assert account_token.token_hash == hash_account_token(raw_token)


def test_activate_account_marks_user_active_and_consumes_token() -> None:
    user, raw_token = register_user(
        email="activate-service@example.com",
        password="N3arby-Places-Key-842!",
    )
    account_token = AccountToken.objects.get(user=user)

    activated_user = activate_account(raw_token)

    user.refresh_from_db()
    account_token.refresh_from_db()

    assert activated_user == user
    assert user.is_active is True
    assert account_token.used_at is not None


def test_activate_account_returns_none_for_invalid_token() -> None:
    assert activate_account("invalid-token") is None


def test_login_user_returns_token_for_valid_active_user() -> None:
    user = User.objects.create_user(
        email="login-service@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )

    token = login_user(
        email="login-service@example.com",
        password="N3arby-Places-Key-842!",
    )

    assert token == Token.objects.get(user=user)


def test_login_user_returns_none_for_invalid_credentials() -> None:
    User.objects.create_user(
        email="invalid-login@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )

    token = login_user(
        email="invalid-login@example.com",
        password="wrong-password",
    )

    assert token is None


def test_create_password_reset_token_returns_token_for_active_user() -> None:
    user = User.objects.create_user(
        email="reset-service@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )

    raw_token = create_password_reset_token("reset-service@example.com")
    account_token = AccountToken.objects.get(user=user)

    assert raw_token is not None
    assert account_token.purpose == AccountToken.Purpose.PASSWORD_RESET
    assert account_token.token_hash == hash_account_token(raw_token)


def test_create_password_reset_token_returns_none_for_inactive_user() -> None:
    User.objects.create_user(
        email="inactive-reset@example.com",
        password="N3arby-Places-Key-842!",
        is_active=False,
    )

    raw_token = create_password_reset_token("inactive-reset@example.com")

    assert raw_token is None


def test_reset_password_updates_password_and_consumes_token() -> None:
    user = User.objects.create_user(
        email="password-service@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    raw_token = create_password_reset_token("password-service@example.com")

    assert raw_token is not None

    reset_user = reset_password(
        raw_token=raw_token,
        password="Fr3sh-Places-Key-842!",
    )
    account_token = AccountToken.objects.get(user=user)

    user.refresh_from_db()

    assert reset_user == user
    assert check_password("Fr3sh-Places-Key-842!", user.password)
    assert account_token.used_at is not None


def test_reset_password_returns_none_for_invalid_token() -> None:
    assert reset_password(raw_token="invalid-token", password="whatever") is None
