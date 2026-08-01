from typing import ClassVar, Self, override

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects: ClassVar[UserManager] = UserManager()  # pyright: ignore[reportIncompatibleVariableOverride]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        ordering = ("email",)

    @override
    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    service_area = models.ForeignKey(
        "geo.ServiceArea",
        on_delete=models.PROTECT,
        related_name="user_profiles",
        null=True,
        blank=True,
    )
    default_location = gis_models.PointField(srid=4326, null=True, blank=True)
    location_sharing_enabled = models.BooleanField(default=False)
    preferred_radius = models.PositiveIntegerField(default=500)
    realtime_refresh_enabled = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user__email",)

    @classmethod
    def get_for_user(cls, user: AbstractBaseUser) -> Self:
        profile, _ = cls.objects.get_or_create(user=user)
        return profile

    @override
    def __str__(self) -> str:
        return f"{self.user.email} profile"

    @property
    def default_latitude(self) -> float | None:
        if self.default_location is None:
            return None

        return float(self.default_location.y)

    @property
    def default_longitude(self) -> float | None:
        if self.default_location is None:
            return None

        return float(self.default_location.x)

    @property
    def has_completed_onboarding(self) -> bool:
        return self.onboarding_completed_at is not None


class AccountToken(models.Model):
    class Purpose(models.TextChoices):
        ACTIVATION = "activation", "Activation"
        PASSWORD_RESET = "password_reset", "Password reset"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="account_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [  # noqa: RUF012
            models.Index(fields=["token_hash", "purpose"]),
            models.Index(fields=["user", "purpose"]),
        ]
        ordering = ("-created_at",)

    @override
    def __str__(self) -> str:
        return f"{self.user.email} - {self.purpose}"

    @property
    def is_available(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()
