from typing import Any, cast, override

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import User, UserProfile
from accounts.services import (
    activate_account,
    create_password_reset_token,
    login_user,
    register_user,
    reset_password,
)
from geo.serializers import ServiceAreaSerializer


class ProfileSerializer(serializers.ModelSerializer[User]):
    service_area = serializers.SerializerMethodField()
    default_latitude = serializers.SerializerMethodField()
    default_longitude = serializers.SerializerMethodField()
    location_sharing_enabled = serializers.SerializerMethodField()
    preferred_radius = serializers.SerializerMethodField()
    onboarding_completed = serializers.SerializerMethodField()

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "service_area",
            "default_latitude",
            "default_longitude",
            "location_sharing_enabled",
            "preferred_radius",
            "onboarding_completed",
        )

    def get_profile(self, user: User) -> UserProfile:
        return UserProfile.get_for_user(user)

    def get_service_area(self, user: User) -> dict[str, object] | None:
        service_area = self.get_profile(user).service_area
        if service_area is None:
            return None

        return dict(ServiceAreaSerializer(service_area).data)

    def get_default_longitude(self, user: User) -> float | None:
        return self.get_profile(user).default_longitude

    def get_default_latitude(self, user: User) -> float | None:
        return self.get_profile(user).default_latitude

    def get_location_sharing_enabled(self, user: User) -> bool:
        return self.get_profile(user).location_sharing_enabled

    def get_preferred_radius(self, user: User) -> int:
        return self.get_profile(user).preferred_radius

    def get_onboarding_completed(self, user: User) -> bool:
        return self.get_profile(user).has_completed_onboarding


class RegistrationSerializer(serializers.Serializer[dict[str, Any]]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account already exists for this email."
            )

        return value

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def register(self) -> tuple[User, str]:
        validated_data = cast(dict[str, str], self.validated_data)
        user, activation_token = register_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )

        return user, activation_token


class LoginSerializer(serializers.Serializer[dict[str, Any]]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    @override
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        token = login_user(
            email=cast(str, attrs["email"]),
            password=cast(str, attrs["password"]),
        )
        if token is None:
            raise serializers.ValidationError(
                "Unable to log in with these credentials."
            )

        attrs["token"] = token.key
        return attrs


class ActivationSerializer(serializers.Serializer[dict[str, Any]]):
    token = serializers.CharField()

    @override
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user = activate_account(cast(str, attrs["token"]))
        if user is None:
            raise serializers.ValidationError("Activation token is invalid or expired.")

        attrs["user"] = user
        return attrs


class ForgotPasswordSerializer(serializers.Serializer[dict[str, Any]]):
    email = serializers.EmailField()

    def create_reset_token(self) -> str | None:
        reset_token = create_password_reset_token(
            cast(str, self.validated_data["email"]),
        )
        if reset_token is None:
            return None

        return reset_token


class PasswordResetSerializer(serializers.Serializer[dict[str, Any]]):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    @override
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user = reset_password(
            raw_token=cast(str, attrs["token"]),
            password=cast(str, attrs["password"]),
        )
        if user is None:
            raise serializers.ValidationError("Reset token is invalid or expired.")

        attrs["user"] = user
        return attrs
