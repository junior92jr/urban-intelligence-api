import pytest

from accounts.models import User

pytestmark = pytest.mark.django_db


def test_create_user_normalizes_email_and_hashes_password() -> None:
    user = User.objects.create_user(
        email="Member@EXAMPLE.COM",
        password="N3arby-Places-Key-842!",
    )

    assert user.email == "Member@example.com"
    assert user.check_password("N3arby-Places-Key-842!") is True
    assert user.is_staff is False
    assert user.is_superuser is False


def test_create_user_requires_email() -> None:
    with pytest.raises(ValueError, match="Users must have an email address."):
        User.objects.create_user(email="", password="N3arby-Places-Key-842!")


def test_create_superuser_sets_required_flags() -> None:
    user = User.objects.create_superuser(
        email="admin@example.com",
        password="N3arby-Places-Key-842!",
    )

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True


def test_create_superuser_rejects_missing_staff_flag() -> None:
    with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
        User.objects.create_superuser(
            email="admin@example.com",
            password="N3arby-Places-Key-842!",
            is_staff=False,
        )


def test_create_superuser_rejects_missing_superuser_flag() -> None:
    with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
        User.objects.create_superuser(
            email="admin@example.com",
            password="N3arby-Places-Key-842!",
            is_superuser=False,
        )
