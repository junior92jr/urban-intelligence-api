from typing import Any, cast, override

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import User, UserProfile
from accounts.services.registration import (
    create_password_reset_token,
    register_user,
    reset_password,
)
from geo.models import ServiceArea, build_point
from intelligence.models import IntelligenceDataset, IntelligenceImport
from places.models import PlaceImport


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


class LocationPreferencesForm(forms.Form):
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    service_area = forms.ModelChoiceField(
        queryset=ServiceArea.objects.none(),
        empty_label=None,
    )
    default_latitude = forms.FloatField(required=False, widget=forms.HiddenInput)
    default_longitude = forms.FloatField(required=False, widget=forms.HiddenInput)
    location_sharing_enabled = forms.BooleanField(required=False)
    realtime_refresh_enabled = forms.BooleanField(required=False)
    preferred_radius = forms.IntegerField(
        min_value=100,
        max_value=3000,
        initial=500,
    )

    def __init__(
        self,
        *args: Any,
        user: User,
        complete_onboarding: bool = False,
        **kwargs: Any,
    ) -> None:
        self.user = user
        self.profile = UserProfile.get_for_user(user)
        self.complete_onboarding = complete_onboarding
        initial = self.initial_data()
        initial.update(cast(dict[str, object], kwargs.get("initial", {})))
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        service_area_field = cast(
            "forms.ModelChoiceField[ServiceArea]",
            self.fields["service_area"],
        )
        service_area_field.queryset = ServiceArea.objects.select_related(
            "country"
        ).filter(
            is_active=True,
            country__is_active=True,
        )

    def initial_data(self) -> dict[str, object]:
        return {
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "service_area": self.profile.service_area,
            "default_latitude": self.profile.default_latitude,
            "default_longitude": self.profile.default_longitude,
            "location_sharing_enabled": self.profile.location_sharing_enabled,
            "realtime_refresh_enabled": self.profile.realtime_refresh_enabled,
            "preferred_radius": self.profile.preferred_radius,
        }

    @override
    def clean(self) -> dict[str, object] | None:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return None

        latitude = cleaned_data.get("default_latitude")
        longitude = cleaned_data.get("default_longitude")
        if (latitude is None) != (longitude is None):
            raise ValidationError("Latitude and longitude must be saved together.")

        return cleaned_data

    def save(self) -> UserProfile:
        if not self.complete_onboarding:
            self.user.first_name = cast(str, self.cleaned_data.get("first_name", ""))
            self.user.last_name = cast(str, self.cleaned_data.get("last_name", ""))
            self.user.save(update_fields=["first_name", "last_name"])

        self.profile.service_area = cast(
            ServiceArea,
            self.cleaned_data["service_area"],
        )
        self.profile.location_sharing_enabled = bool(
            self.cleaned_data.get("location_sharing_enabled"),
        )
        self.profile.realtime_refresh_enabled = bool(
            self.cleaned_data.get("realtime_refresh_enabled"),
        )
        self.profile.preferred_radius = cast(
            int,
            self.cleaned_data.get("preferred_radius", 500),
        )

        latitude = self.cleaned_data.get("default_latitude")
        longitude = self.cleaned_data.get("default_longitude")
        if latitude is not None and longitude is not None:
            self.profile.default_location = build_point(
                latitude=cast(float, latitude),
                longitude=cast(float, longitude),
            )

        if self.complete_onboarding:
            self.profile.onboarding_completed_at = timezone.now()

        self.profile.save()
        return self.profile


class PlaceImportForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = PlaceImport
        fields = ("service_area", "layer", "radius")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        service_area_field = cast(
            "forms.ModelChoiceField[ServiceArea]",
            self.fields["service_area"],
        )
        service_area_field.queryset = ServiceArea.objects.select_related(
            "country",
        ).filter(
            is_active=True,
            country__is_active=True,
        )

    @override
    def save(self, commit: bool = True) -> PlaceImport:
        place_import = cast(PlaceImport, super().save(commit=False))

        if commit:
            place_import.save()

        return place_import


class IntelligenceImportForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = IntelligenceImport
        fields = ("dataset", "service_area")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        dataset_field = cast(
            "forms.ModelChoiceField[IntelligenceDataset]",
            self.fields["dataset"],
        )
        dataset_field.queryset = IntelligenceDataset.objects.select_related(
            "source",
            "indicator",
        ).filter(
            is_active=True,
            source__is_active=True,
            indicator__is_active=True,
        )
        service_area_field = cast(
            "forms.ModelChoiceField[ServiceArea]",
            self.fields["service_area"],
        )
        service_area_field.queryset = ServiceArea.objects.select_related(
            "country",
        ).filter(
            is_active=True,
            country__is_active=True,
        )

    @override
    def clean(self) -> dict[str, object] | None:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return None

        dataset = cleaned_data.get("dataset")
        service_area = cleaned_data.get("service_area")
        if not isinstance(dataset, IntelligenceDataset) or not isinstance(
            service_area,
            ServiceArea,
        ):
            return cleaned_data

        is_tree_cover_density = (
            dataset.source.slug == "copernicus-land-monitoring"
            and dataset.slug == "tree-cover-density-100m"
        )
        if is_tree_cover_density and service_area.boundary is None:
            self.add_error(
                "service_area",
                "This dataset requires a city boundary before it can be imported.",
            )
        if is_tree_cover_density and not (
            settings.OBJECT_STORAGE_ENDPOINT_URL
            and settings.OBJECT_STORAGE_ACCESS_KEY_ID
            and settings.OBJECT_STORAGE_SECRET_ACCESS_KEY
            and settings.OBJECT_STORAGE_BUCKET
        ):
            self.add_error(
                "dataset",
                "Configure cache object storage before importing this dataset.",
            )
        if is_tree_cover_density and not (
            settings.COPERNICUS_S3_ACCESS_KEY_ID
            and settings.COPERNICUS_S3_SECRET_ACCESS_KEY
        ):
            self.add_error(
                "dataset",
                "Configure Copernicus source credentials before importing this dataset.",
            )

        return cleaned_data


def add_form_error(form: forms.Form, error: ValidationError) -> None:
    form.add_error(None, error)
