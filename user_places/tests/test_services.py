import pytest

from accounts.models import User
from user_places.models import SearchHistory
from user_places.services import SEARCH_HISTORY_LIMIT, record_place_search

pytestmark = pytest.mark.django_db


def test_record_place_search_creates_history_entry() -> None:
    user = User.objects.create_user(
        email="history-service@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )

    history = record_place_search(
        user=user,
        latitude=50.1109,
        longitude=8.6821,
        search_radius=500,
        category="restaurant",
        result_count=4,
    )

    assert history.user == user
    assert history.category == "restaurant"
    assert history.result_count == 4
    assert history.latitude == 50.1109
    assert history.longitude == 8.6821


def test_record_place_search_prunes_old_history_entries() -> None:
    user = User.objects.create_user(
        email="history-prune@example.com",
        password="N3arby-Places-Key-842!",
        is_active=True,
    )

    for index in range(SEARCH_HISTORY_LIMIT + 2):
        record_place_search(
            user=user,
            latitude=50.1109,
            longitude=8.6821,
            search_radius=500,
            category=f"category-{index}",
            result_count=index,
        )

    assert SearchHistory.objects.filter(user=user).count() == SEARCH_HISTORY_LIMIT
    assert not SearchHistory.objects.filter(user=user, category="category-0").exists()
    assert SearchHistory.objects.filter(
        user=user,
        category=f"category-{SEARCH_HISTORY_LIMIT + 1}",
    ).exists()
