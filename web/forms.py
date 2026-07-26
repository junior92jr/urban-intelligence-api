from typing import cast, override

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from accounts.models import User
from accounts.services.registration import (
    create_password_reset_token,
    register_user,
    reset_password,
)


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")


class RegistrationForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(
        widget=forms.PasswordInput,
        validators=[validate_password],
    )
    password_confirm = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
    )
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    def clean_email(self) -> str:
        email = cast(str, self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account already exists for this email.")

        return email

    @override
    def clean(self) -> dict[str, object] | None:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return None

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Passwords do not match.")

        return cleaned_data

    def register(self) -> tuple[User, str]:
        return register_user(
            email=cast(str, self.cleaned_data["email"]),
            password=cast(str, self.cleaned_data["password"]),
            first_name=cast(str, self.cleaned_data.get("first_name", "")),
            last_name=cast(str, self.cleaned_data.get("last_name", "")),
        )


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()

    def create_reset_token(self) -> str | None:
        return create_password_reset_token(cast(str, self.cleaned_data["email"]))


class ResetPasswordForm(forms.Form):
    token = forms.CharField()
    password = forms.CharField(
        widget=forms.PasswordInput,
        validators=[validate_password],
    )

    def reset_password(self) -> User:
        user = reset_password(
            raw_token=cast(str, self.cleaned_data["token"]),
            password=cast(str, self.cleaned_data["password"]),
        )
        if user is None:
            raise ValidationError("Reset token is invalid or expired.")

        return user


def add_form_error(form: forms.Form, error: ValidationError) -> None:
    form.add_error(None, error)
