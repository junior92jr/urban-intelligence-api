from typing import Any, cast, override

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from accounts.models import User, UserProfile
from accounts.services.registration import activate_account
from places.models import DataImport
from places.services.discovery import create_area_scan
from places.tasks import run_area_scan, run_data_import
from web.emails import send_activation_email, send_password_reset_email
from web.forms import (
    DataImportForm,
    EmailAuthenticationForm,
    ForgotPasswordForm,
    LocationPreferencesForm,
    RegistrationForm,
    ResetPasswordForm,
    add_form_error,
)


def get_map_tile_context() -> dict[str, str]:
    return {
        "map_tile_url": settings.MAP_TILE_URL,
        "map_tile_attribution": settings.MAP_TILE_ATTRIBUTION,
    }


def enqueue_profile_area_scan(
    *,
    profile: UserProfile,
    user_id: int,
) -> None:
    if profile.service_area is None:
        return

    latitude = profile.default_latitude
    longitude = profile.default_longitude
    if latitude is None or longitude is None:
        latitude = profile.service_area.latitude
        longitude = profile.service_area.longitude

    scan = create_area_scan(
        service_area=profile.service_area,
        latitude=latitude,
        longitude=longitude,
        radius=profile.preferred_radius,
        user_id=user_id,
    )
    assert scan.pk is not None
    cast(Any, run_area_scan).delay(scan.pk)


class MapView(LoginRequiredMixin, TemplateView):
    template_name = "web/maps/index.html"
    login_url = reverse_lazy("web:login")

    @override
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        assert isinstance(user, AbstractBaseUser)
        profile = UserProfile.get_for_user(user)
        default_latitude = profile.default_latitude
        default_longitude = profile.default_longitude
        if profile.default_location is None and profile.service_area is not None:
            default_latitude = profile.service_area.latitude
            default_longitude = profile.service_area.longitude

        context.update(get_map_tile_context())
        context["active_nav"] = "map"
        context["profile"] = profile
        context["default_latitude"] = default_latitude
        context["default_longitude"] = default_longitude

        return context


class LoginView(FormView):  # type: ignore[type-arg]
    form_class = EmailAuthenticationForm
    template_name = "web/accounts/login.html"
    success_url = reverse_lazy("web:map")

    @override
    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    @override
    def form_valid(self, form: EmailAuthenticationForm) -> HttpResponse:
        user = form.get_user()
        login(self.request, user)
        return super().form_valid(form)

    @override
    def get_success_url(self) -> str:
        user = self.request.user
        if user.is_authenticated:
            assert isinstance(user, AbstractBaseUser)
            if not UserProfile.get_for_user(user).has_completed_onboarding:
                return str(reverse_lazy("web:onboarding"))

        return self.request.POST.get("next") or str(self.success_url)


class RegisterView(FormView):  # type: ignore[type-arg]
    form_class = RegistrationForm
    template_name = "web/accounts/register.html"
    success_url = reverse_lazy("web:registration_sent")

    @override
    def form_valid(self, form: RegistrationForm) -> HttpResponse:
        user, activation_token = form.register()
        send_activation_email(
            request=self.request,
            email=user.email,
            activation_token=activation_token,
        )
        messages.success(
            self.request,
            "Account created. Check your email for the activation link.",
        )
        return super().form_valid(form)


class RegistrationSentView(TemplateView):
    template_name = "web/accounts/registration_sent.html"


class ActivateView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        token = request.GET.get("token")
        if token is None:
            messages.error(request, "Activation link is missing a token.")
            return redirect("web:login")

        user = activate_account(token)
        if user is None:
            messages.error(request, "Activation link is invalid or expired.")
            return redirect("web:login")

        login(request, user)
        messages.success(request, "Account activated.")
        return redirect("web:onboarding")


class ForgotPasswordView(FormView):  # type: ignore[type-arg]
    form_class = ForgotPasswordForm
    template_name = "web/accounts/forgot_password.html"
    success_url = reverse_lazy("web:reset_password")

    @override
    def form_valid(self, form: ForgotPasswordForm) -> HttpResponse:
        reset_token = form.create_reset_token()
        if reset_token is not None:
            send_password_reset_email(
                request=self.request,
                email=cast(str, form.cleaned_data["email"]),
                reset_token=reset_token,
            )

        messages.success(
            self.request,
            "If the account exists, a password reset email was sent.",
        )
        return super().form_valid(form)


class ResetPasswordView(FormView):  # type: ignore[type-arg]
    form_class = ResetPasswordForm
    template_name = "web/accounts/reset_password.html"
    success_url = reverse_lazy("web:login")

    @override
    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        token = self.request.GET.get("token")
        if token is not None:
            initial["token"] = token
        return initial

    @override
    def form_valid(self, form: ResetPasswordForm) -> HttpResponse:
        try:
            form.reset_password()
        except ValidationError as exc:
            add_form_error(form, exc)
            return self.form_invalid(form)

        messages.success(self.request, "Password reset.")
        return super().form_valid(form)


class OnboardingView(LoginRequiredMixin, FormView):  # type: ignore[type-arg]
    form_class = LocationPreferencesForm
    template_name = "web/accounts/onboarding.html"
    login_url = reverse_lazy("web:login")
    success_url = reverse_lazy("web:map")

    @override
    def dispatch(
        self,
        request: HttpRequest,
        *args: object,
        **kwargs: object,
    ) -> HttpResponseBase:
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        user = request.user
        assert isinstance(user, AbstractBaseUser)
        if UserProfile.get_for_user(user).has_completed_onboarding:
            return redirect("web:map")

        return super().dispatch(request, *args, **kwargs)

    @override
    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["complete_onboarding"] = True
        return kwargs

    @override
    def form_valid(self, form: LocationPreferencesForm) -> HttpResponse:
        profile = form.save()
        assert self.request.user.pk is not None
        enqueue_profile_area_scan(profile=profile, user_id=self.request.user.pk)
        messages.success(self.request, "Your map preferences are ready.")
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, FormView):  # type: ignore[type-arg]
    form_class = LocationPreferencesForm
    template_name = "web/accounts/profile.html"
    login_url = reverse_lazy("web:login")
    success_url = reverse_lazy("web:profile")

    @override
    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    @override
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["active_nav"] = "profile"

        return context

    @override
    def form_valid(self, form: LocationPreferencesForm) -> HttpResponse:
        profile = form.save()
        assert self.request.user.pk is not None
        enqueue_profile_area_scan(profile=profile, user_id=self.request.user.pk)
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


class FavoritesView(LoginRequiredMixin, TemplateView):
    template_name = "web/user_places/favorites.html"
    login_url = reverse_lazy("web:login")

    @override
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(get_map_tile_context())
        context["active_nav"] = "favorites"

        return context


class HistoryView(LoginRequiredMixin, TemplateView):
    template_name = "web/user_places/history.html"
    login_url = reverse_lazy("web:login")

    @override
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(get_map_tile_context())
        context["active_nav"] = "history"

        return context


class DataImportsView(LoginRequiredMixin, UserPassesTestMixin, FormView):  # type: ignore[type-arg]
    form_class = DataImportForm
    template_name = "web/data_imports/index.html"
    login_url = reverse_lazy("web:login")
    success_url = reverse_lazy("web:data_imports")

    @override
    def test_func(self) -> bool:
        user = self.request.user
        return isinstance(user, User) and user.is_staff

    @override
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["active_nav"] = "data_imports"
        context["data_imports"] = DataImport.objects.select_related(
            "service_area",
            "service_area__country",
            "requested_by",
        )[:20]

        return context

    @override
    def form_valid(self, form: DataImportForm) -> HttpResponse:
        data_import = form.save(commit=False)
        user = self.request.user
        assert isinstance(user, User)
        data_import.requested_by = user
        data_import.save()
        assert data_import.pk is not None
        cast(Any, run_data_import).delay(data_import.pk)
        messages.success(self.request, "OpenStreetMap data import started.")

        return super().form_valid(form)


@require_POST
@login_required(login_url=reverse_lazy("web:login"))
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("web:map")
