from typing import Any

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import (
    ActivationSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    PasswordResetSerializer,
    RegistrationSerializer,
)


class RegistrationView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, activation_token = serializer.register()

        return Response(
            {
                "id": user.pk,
                "email": user.email,
                "activation_token": activation_token,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            {
                "token": serializer.validated_data["token"],
                "token_type": "Bearer",
            },
        )


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        if isinstance(request.auth, Token):
            request.auth.delete()

        return Response({"detail": "Logged out."})


class ActivationView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        serializer = ActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({"detail": "Account activated."})


class ForgotPasswordView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_token = serializer.create_reset_token()
        response: dict[str, Any] = {
            "detail": "If the account exists, a password reset token was created.",
        }

        if reset_token is not None:
            response["reset_token"] = reset_token

        return Response(response)


class PasswordResetView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({"detail": "Password reset."})
