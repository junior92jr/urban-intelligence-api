from accounts.models import User
from user_places.models import SearchHistory, build_point

SEARCH_HISTORY_LIMIT = 50


def record_place_search(
    *,
    user: User,
    latitude: float,
    longitude: float,
    search_radius: int,
    category: str,
    result_count: int,
) -> SearchHistory:
    history = SearchHistory.objects.create(
        user=user,
        location=build_point(latitude=latitude, longitude=longitude),
        search_radius=search_radius,
        category=category,
        result_count=result_count,
    )
    prune_search_history(user=user)

    return history


def prune_search_history(*, user: User) -> None:
    stale_ids = SearchHistory.objects.filter(user=user).values_list(
        "id",
        flat=True,
    )[SEARCH_HISTORY_LIMIT:]
    SearchHistory.objects.filter(id__in=stale_ids).delete()
