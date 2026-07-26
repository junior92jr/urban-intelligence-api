from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import AccountToken, User
from accounts.services.tokens import (
    create_account_token,
    get_available_account_token,
    hash_account_token,
    mark_account_token_as_used,
)

pytestmark = pytest.mark.django_db


def test_hash_account_token_is_stable_and_does_not_expose_raw_token() -> None:
    raw_token = "activation-token"

    token_hash = hash_account_token(raw_token)

    assert token_hash == hash_account_token(raw_token)
    assert token_hash != raw_token


def test_create_account_token_stores_hashed_token() -> None:
    user = User.objects.create_user(
        email="token@example.com",
        password="N3arby-Places-Key-842!",
    )

    raw_token, account_token = create_account_token(
        user=user,
        purpose=AccountToken.Purpose.ACTIVATION,
        expires_in=timedelta(hours=1),
    )

    assert account_token.token_hash == hash_account_token(raw_token)
    assert account_token.token_hash != raw_token
    assert account_token.expires_at > timezone.now()


def test_get_available_account_token_returns_matching_unexpired_token() -> None:
    user = User.objects.create_user(
        email="available@example.com",
        password="N3arby-Places-Key-842!",
    )
    raw_token, account_token = create_account_token(
        user=user,
        purpose=AccountToken.Purpose.ACTIVATION,
        expires_in=timedelta(hours=1),
    )

    found_token = get_available_account_token(
        raw_token=raw_token,
        purpose=AccountToken.Purpose.ACTIVATION,
    )

    assert found_token == account_token


def test_get_available_account_token_ignores_expired_tokens() -> None:
    user = User.objects.create_user(
        email="expired@example.com",
        password="N3arby-Places-Key-842!",
    )
    raw_token, _ = create_account_token(
        user=user,
        purpose=AccountToken.Purpose.ACTIVATION,
        expires_in=timedelta(seconds=-1),
    )

    found_token = get_available_account_token(
        raw_token=raw_token,
        purpose=AccountToken.Purpose.ACTIVATION,
    )

    assert found_token is None


def test_mark_account_token_as_used_makes_token_unavailable() -> None:
    user = User.objects.create_user(
        email="used@example.com",
        password="N3arby-Places-Key-842!",
    )
    raw_token, account_token = create_account_token(
        user=user,
        purpose=AccountToken.Purpose.PASSWORD_RESET,
        expires_in=timedelta(hours=1),
    )

    mark_account_token_as_used(account_token)

    assert (
        get_available_account_token(
            raw_token=raw_token,
            purpose=AccountToken.Purpose.PASSWORD_RESET,
        )
        is None
    )


def test_create_account_token_revokes_existing_available_tokens_for_same_purpose() -> (
    None
):
    user = User.objects.create_user(
        email="revoke@example.com",
        password="N3arby-Places-Key-842!",
    )
    _, old_token = create_account_token(
        user=user,
        purpose=AccountToken.Purpose.PASSWORD_RESET,
        expires_in=timedelta(hours=1),
    )

    create_account_token(
        user=user,
        purpose=AccountToken.Purpose.PASSWORD_RESET,
        expires_in=timedelta(hours=1),
    )

    old_token.refresh_from_db()

    assert old_token.used_at is not None
