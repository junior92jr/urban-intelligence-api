from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework.authtoken.models import Token

from accounts.models import AccountToken, User
from accounts.services.tokens import (
    activation_token_lifetime,
    create_account_token,
    get_available_account_token,
    mark_account_token_as_used,
    password_reset_token_lifetime,
)


@transaction.atomic
def register_user(
    *,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
) -> tuple[User, str]:
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_active=False,
    )
    raw_activation_token, _ = create_account_token(
        user=user,
        purpose=AccountToken.Purpose.ACTIVATION,
        expires_in=activation_token_lifetime(),
    )

    return user, raw_activation_token


@transaction.atomic
def activate_account(raw_token: str) -> User | None:
    account_token = get_available_account_token(
        raw_token=raw_token,
        purpose=AccountToken.Purpose.ACTIVATION,
    )
    if account_token is None:
        return None

    user = account_token.user
    user.is_active = True
    user.save(update_fields=["is_active"])
    mark_account_token_as_used(account_token)

    return user


def login_user(*, email: str, password: str) -> Token | None:
    user = authenticate(username=email, password=password)
    if user is None:
        return None

    token, _ = Token.objects.get_or_create(user=user)
    return token


def create_password_reset_token(email: str) -> str | None:
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        return None

    raw_reset_token, _ = create_account_token(
        user=user,
        purpose=AccountToken.Purpose.PASSWORD_RESET,
        expires_in=password_reset_token_lifetime(),
    )

    return raw_reset_token


@transaction.atomic
def reset_password(*, raw_token: str, password: str) -> User | None:
    account_token = get_available_account_token(
        raw_token=raw_token,
        purpose=AccountToken.Purpose.PASSWORD_RESET,
    )
    if account_token is None:
        return None

    user = account_token.user
    user.set_password(password)
    user.save(update_fields=["password"])
    mark_account_token_as_used(account_token)

    return user
