from django.urls import path
from rest_framework.routers import DefaultRouter

from intelligence.views import AreaIntelligenceView

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
    path(
        "places/area-intelligence/",
        AreaIntelligenceView.as_view(),
        name="area-intelligence",
    ),
    path("places/nearby/", NearbyPlacesView.as_view(), name="nearby"),
    path("places/area-scans/", AreaScanCreateView.as_view(), name="area-scans"),
    path(
        "places/area-scans/<int:pk>/",
        AreaScanDetailView.as_view(),
        name="area-scan-detail",
    ),
    *router.urls,
]
