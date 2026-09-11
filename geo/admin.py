from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar

from django.contrib import admin
from django.contrib.gis import admin as gis_admin

from geo.models import Country, OsmImportRun, ServiceArea

if TYPE_CHECKING:
    _CountryModelAdmin = admin.ModelAdmin[Country]
    _OsmImportRunModelAdmin = admin.ModelAdmin[OsmImportRun]
    _ServiceAreaModelAdmin = admin.ModelAdmin[ServiceArea]
else:
    _CountryModelAdmin = admin.ModelAdmin
    _OsmImportRunModelAdmin = admin.ModelAdmin
    _ServiceAreaModelAdmin = gis_admin.GISModelAdmin


@admin.register(Country)
class CountryAdmin(_CountryModelAdmin):
    list_display = ("code", "name", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("sort_order", "name")


@admin.register(ServiceArea)
class ServiceAreaAdmin(_ServiceAreaModelAdmin):
    list_display = (
        "name",
        "country",
        "area_type",
        "population",
        "is_active",
        "sort_order",
    )
    autocomplete_fields = ("country", "parent", "import_run")
    list_editable = ("is_active", "sort_order")
    list_filter = ("country", "area_type", "is_active")
    prepopulated_fields: ClassVar[dict[str, Sequence[str]]] = {"slug": ("name",)}
    search_fields = ("name", "slug", "country__name", "country__code")
    ordering = ("country__sort_order", "sort_order", "name")


@admin.register(OsmImportRun)
class OsmImportRunAdmin(_OsmImportRunModelAdmin):
    list_display = (
        "id",
        "status",
        "is_active",
        "total_cities",
        "processed_cities",
        "created_at",
    )
    list_filter = ("status", "is_active")
    search_fields = ("source_object_key", "source_sha256")
    readonly_fields = ("created_at",)
