from django.urls import path

from .views import (
    ActivateView,
    FavoritesView,
    ForgotPasswordView,
    LoginView,
    MapView,
    ProfileView,
    RegisterView,
    RegistrationSentView,
    ResetPasswordView,
    logout_view,
)

app_name = "web"

urlpatterns = [
    path("maps/", MapView.as_view(), name="map"),
    path("favorites/", FavoritesView.as_view(), name="favorites"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path(
        "registration-sent/",
        RegistrationSentView.as_view(),
        name="registration_sent",
    ),
    path("activate/", ActivateView.as_view(), name="activate"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    path("profile/", ProfileView.as_view(), name="profile"),
]
