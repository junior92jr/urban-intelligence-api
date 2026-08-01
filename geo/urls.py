from rest_framework.routers import DefaultRouter

from geo.views import CountryViewSet, ServiceAreaViewSet

app_name = "geo"

router = DefaultRouter()
router.register("countries", CountryViewSet, basename="countries")
router.register("service-areas", ServiceAreaViewSet, basename="service_areas")

urlpatterns = router.urls
