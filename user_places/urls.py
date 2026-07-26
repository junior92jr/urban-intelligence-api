from django.urls import path

from user_places.views import FavoritePlaceDestroyView, FavoritePlaceListCreateView

app_name = "user_places"

urlpatterns = [
    path("favorites/", FavoritePlaceListCreateView.as_view(), name="favorites"),
    path(
        "favorites/<str:osm_uid>/",
        FavoritePlaceDestroyView.as_view(),
        name="favorite_detail",
    ),
]
