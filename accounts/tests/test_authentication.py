import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory

from accounts.authentication import BearerTokenAuthentication
from accounts.models import User

pytestmark = pytest.mark.django_db


def test_bearer_token_authentication_uses_bearer_keyword() -> None:
    assert BearerTokenAuthentication.keyword == "Bearer"


def test_bearer_token_authentication_accepts_bearer_token() -> None:
    user = User.objects.create_user(
        email="bearer@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    token = Token.objects.create(user=user)
    request = APIRequestFactory().get(
        "/",
        HTTP_AUTHORIZATION=f"Bearer {token.key}",
    )

    authentication_result = BearerTokenAuthentication().authenticate(request)

    assert authentication_result is not None
    authenticated_user, authenticated_token = authentication_result
    assert authenticated_user == user
    assert authenticated_token == token


def test_bearer_token_authentication_ignores_token_keyword() -> None:
    user = User.objects.create_user(
        email="token-keyword@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )
    token = Token.objects.create(user=user)
    request = APIRequestFactory().get(
        "/",
        HTTP_AUTHORIZATION=f"Token {token.key}",
    )

    authentication_result = BearerTokenAuthentication().authenticate(request)

    assert authentication_result is None
