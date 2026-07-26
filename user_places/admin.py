from django.contrib import admin

from user_places.models import FavoritePlace


@admin.register(FavoritePlace)
class FavoritePlaceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "user", "category_name", "osm_uid", "created_at")
    list_filter = ("category", "osm_type")
    search_fields = ("name", "user__email", "osm_uid")
    ordering = ("-created_at",)
