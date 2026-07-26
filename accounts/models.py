from typing import ClassVar, override

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
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
