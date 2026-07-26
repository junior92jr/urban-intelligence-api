from typing import Any, override

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from web.forms import (
    ActivationForm,
    EmailAuthenticationForm,
    ForgotPasswordForm,
    RegistrationForm,
    ResetPasswordForm,
    add_form_error,
)


def get_map_tile_context() -> dict[str, str]:
    return {
        "map_tile_url": settings.MAP_TILE_URL,
        "map_tile_attribution": settings.MAP_TILE_ATTRIBUTION,
    }


class MapView(LoginRequiredMixin, TemplateView):
    template_name = "web/maps/index.html"
    login_url = reverse_lazy("web:login")

    @override
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(get_map_tile_context())

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
        login(self.request, form.get_user())
        return super().form_valid(form)

    @override
    def get_success_url(self) -> str:
        return self.request.POST.get("next") or str(self.success_url)


class RegisterView(FormView):  # type: ignore[type-arg]
    form_class = RegistrationForm
    template_name = "web/accounts/register.html"
    success_url = reverse_lazy("web:activate")

    @override
    def form_valid(self, form: RegistrationForm) -> HttpResponse:
        _, activation_token = form.register()
        messages.success(
            self.request,
            f"Account created. Activation token: {activation_token}",
        )
        return super().form_valid(form)


class ActivateView(FormView):  # type: ignore[type-arg]
    form_class = ActivationForm
    template_name = "web/accounts/activate.html"
    success_url = reverse_lazy("web:map")

    @override
    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        token = self.request.GET.get("token")
        if token is not None:
            initial["token"] = token
        return initial

    @override
    def form_valid(self, form: ActivationForm) -> HttpResponse:
        try:
            user = form.activate()
        except ValidationError as exc:
            add_form_error(form, exc)
            return self.form_invalid(form)

        login(self.request, user)
        messages.success(self.request, "Account activated.")
        return super().form_valid(form)


class ForgotPasswordView(FormView):  # type: ignore[type-arg]
    form_class = ForgotPasswordForm
    template_name = "web/accounts/forgot_password.html"
    success_url = reverse_lazy("web:reset_password")

    @override
    def form_valid(self, form: ForgotPasswordForm) -> HttpResponse:
        reset_token = form.create_reset_token()
        if reset_token is not None:
            messages.success(
                self.request,
                f"Password reset token: {reset_token}",
            )
        else:
            messages.success(
                self.request,
                "If the account exists, a password reset token was created.",
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


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "web/accounts/profile.html"
    login_url = reverse_lazy("web:login")

    @override
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(get_map_tile_context())

        return context


@require_POST
@login_required(login_url=reverse_lazy("web:login"))
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("web:map")
