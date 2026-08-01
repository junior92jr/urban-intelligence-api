from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AreaScanCreateView,
    AreaScanDetailView,
    CategoryViewSet,
    NearbyPlacesView,
    RecommendationViewSet,
)

app_name = "places"

router = DefaultRouter()

router.register("categories", CategoryViewSet, basename="categories")
router.register("", RecommendationViewSet, basename="places")

urlpatterns = [
    path("places/nearby/", NearbyPlacesView.as_view(), name="nearby"),
    path("places/area-scans/", AreaScanCreateView.as_view(), name="area-scans"),
    path(
        "places/area-scans/<int:pk>/",
        AreaScanDetailView.as_view(),
        name="area-scan-detail",
    ),
    *router.urls,
]
