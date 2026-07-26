from django.urls import path

from user_places.views import (
    FavoritePlaceDestroyView,
    FavoritePlaceListCreateView,
    SearchHistoryListView,
)

app_name = "user_places"

urlpatterns = [
    path("favorites/", FavoritePlaceListCreateView.as_view(), name="favorites"),
    path(
        "favorites/<str:osm_uid>/",
        FavoritePlaceDestroyView.as_view(),
        name="favorite_detail",
    ),
    path("search-history/", SearchHistoryListView.as_view(), name="search_history"),
]
