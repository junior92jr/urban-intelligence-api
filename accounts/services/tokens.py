import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.crypto import salted_hmac

from accounts.models import AccountToken, User


def create_account_token(
    user: User,
    purpose: AccountToken.Purpose,
    expires_in: timedelta,
) -> tuple[str, AccountToken]:
    revoke_available_account_tokens(user=user, purpose=purpose)
    raw_token = secrets.token_urlsafe(48)
    account_token = AccountToken.objects.create(
        user=user,
        purpose=purpose,
        token_hash=hash_account_token(raw_token),
        expires_at=timezone.now() + expires_in,
    )

    return raw_token, account_token


def get_available_account_token(
    raw_token: str,
    purpose: AccountToken.Purpose,
) -> AccountToken | None:
    token = (
        AccountToken.objects.select_related("user")
        .filter(
            token_hash=hash_account_token(raw_token),
            purpose=purpose,
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .first()
    )

    return token


def mark_account_token_as_used(token: AccountToken) -> None:
    token.used_at = timezone.now()
    token.save(update_fields=["used_at"])


def revoke_available_account_tokens(
    user: User,
    purpose: AccountToken.Purpose,
) -> None:
    AccountToken.objects.filter(
        user=user,
        purpose=purpose,
        used_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).update(used_at=timezone.now())


def hash_account_token(raw_token: str) -> str:
    return salted_hmac(
        key_salt="accounts.AccountToken",
        value=raw_token,
    ).hexdigest()


def activation_token_lifetime() -> timedelta:
    return timedelta(hours=settings.ACCOUNT_ACTIVATION_TOKEN_TTL_IN_HOURS)


def password_reset_token_lifetime() -> timedelta:
    return timedelta(hours=settings.ACCOUNT_PASSWORD_RESET_TOKEN_TTL_IN_HOURS)
