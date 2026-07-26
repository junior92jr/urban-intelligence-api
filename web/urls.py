from django.urls import path

from .views import MapView

app_name = "web"

urlpatterns = [
    path("", MapView.as_view(), name="index"),
]
