from django.urls import path

from accounts.views import (
    ActivationView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    PasswordResetView,
    RegistrationView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegistrationView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("activate/", ActivationView.as_view(), name="activate"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset-password/", PasswordResetView.as_view(), name="reset_password"),
]
