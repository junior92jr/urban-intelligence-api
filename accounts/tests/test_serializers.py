import pytest
from rest_framework.authtoken.models import Token

from accounts.models import AccountToken, User
from accounts.serializers import (
    ActivationSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    PasswordResetSerializer,
    ProfileSerializer,
    RegistrationSerializer,
)
from accounts.services.registration import create_password_reset_token
from accounts.services.tokens import (
    activation_token_lifetime,
    create_account_token,
)

pytestmark = pytest.mark.django_db


def test_registration_serializer_registers_user() -> None:
    serializer = RegistrationSerializer(
        data={
            "email": "serializer@example.com",
            "password": "N3arby-Places-Key-842!",
            "first_name": "Ada",
        },
    )

    assert serializer.is_valid() is True
    user, activation_token = serializer.register()

    assert user.email == "serializer@example.com"
    assert user.first_name == "Ada"
    assert activation_token


def test_registration_serializer_rejects_duplicate_email() -> None:
    User.objects.create_user(
        email="duplicate@example.com",
        password="N3arby-Places-Key-842!",
    )
    serializer = RegistrationSerializer(
        data={
            "email": "duplicate@example.com",
            "password": "N3arby-Places-Key-842!",
        },
    )

    assert serializer.is_valid() is False
    assert "email" in serializer.errors


def test_registration_serializer_rejects_weak_password() -> None:
    serializer = RegistrationSerializer(
        data={
            "email": "weak@example.com",
            "password": "123",
        },
    )

    assert serializer.is_valid() is False
    assert "password" in serializer.errors


def test_login_serializer_adds_token_to_validated_data() -> None:
    user = User.objects.create_user(
        email="login-serializer@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    serializer = LoginSerializer(
        data={
            "email": "login-serializer@example.com",
            "password": "N3arby-Places-Key-842!",
        },
    )

    assert serializer.is_valid() is True
    assert serializer.validated_data["token"] == Token.objects.get(user=user).key


def test_login_serializer_rejects_invalid_credentials() -> None:
    User.objects.create_user(
        email="bad-login-serializer@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    serializer = LoginSerializer(
        data={
            "email": "bad-login-serializer@example.com",
            "password": "wrong-password",
        },
    )

    assert serializer.is_valid() is False
    assert "non_field_errors" in serializer.errors


def test_profile_serializer_returns_public_profile_fields() -> None:
    user = User.objects.create_user(
        email="profile-serializer@example.com",
        password="N3arby-Places-Key-842!",
        first_name="Profile",
        last_name="Owner",
    )

    assert ProfileSerializer(user).data == {
        "id": user.pk,
        "email": "profile-serializer@example.com",
        "first_name": "Profile",
        "last_name": "Owner",
        "full_name": "Profile Owner",
    }


def test_activation_serializer_consumes_valid_token() -> None:
    user = User.objects.create_user(
        email="activation-serializer@example.com",
        password="N3arby-Places-Key-842!",
    )
    raw_token, account_token = create_account_token(
        user=user,
        purpose=AccountToken.Purpose.ACTIVATION,
        expires_in=activation_token_lifetime(),
    )
    serializer = ActivationSerializer(data={"token": raw_token})

    assert serializer.is_valid() is True

    account_token.refresh_from_db()
    user.refresh_from_db()

    assert serializer.validated_data["user"] == user
    assert user.is_active is True
    assert account_token.used_at is not None


def test_activation_serializer_rejects_invalid_token() -> None:
    serializer = ActivationSerializer(data={"token": "invalid-token"})

    assert serializer.is_valid() is False
    assert "non_field_errors" in serializer.errors


def test_forgot_password_serializer_creates_reset_token() -> None:
    User.objects.create_user(
        email="forgot-serializer@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    serializer = ForgotPasswordSerializer(
        data={"email": "forgot-serializer@example.com"},
    )

    assert serializer.is_valid() is True
    assert serializer.create_reset_token() is not None


def test_password_reset_serializer_consumes_valid_token() -> None:
    user = User.objects.create_user(
        email="password-serializer@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    raw_token = create_password_reset_token("password-serializer@example.com")
    serializer = PasswordResetSerializer(
        data={
            "token": raw_token,
            "password": "Fr3sh-Places-Key-842!",
        },
    )

    assert raw_token is not None
    assert serializer.is_valid() is True

    user.refresh_from_db()

    assert serializer.validated_data["user"] == user
    assert user.check_password("Fr3sh-Places-Key-842!") is True


def test_password_reset_serializer_rejects_invalid_token() -> None:
    serializer = PasswordResetSerializer(
        data={
            "token": "invalid-token",
            "password": "Fr3sh-Places-Key-842!",
        },
    )

    assert serializer.is_valid() is False
    assert "non_field_errors" in serializer.errors
