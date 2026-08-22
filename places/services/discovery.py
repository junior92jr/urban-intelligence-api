from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import QuerySet
from django.utils import timezone

from geo.models import ServiceArea, build_point
from places.models import AreaScan, DataImport, DiscoveredPlace
from places.services.categories import get_category_by_slug
from places.services.layers import get_layer_filter, place_matches_layer
from places.services.mappers import OpenStreetMapPlace
from places.services.open_street_map import PlaceQueryParams
from places.services.search import search_places_by_location


def category_group_for_slug(category: str | None) -> str:
    if category is None:
        return ""

    place_category = get_category_by_slug(category)

    return place_category.group if place_category is not None else ""


def create_area_scan(
    *,
    service_area: ServiceArea,
    latitude: float,
    longitude: float,
    radius: int,
    user_id: int | None,
    category: str | None = None,
    category_group: str | None = None,
) -> AreaScan:
    return AreaScan.objects.create(
        user_id=user_id,
        service_area=service_area,
        center=build_point(latitude=latitude, longitude=longitude),
        radius=radius,
        category=category or "",
        category_group=category_group or category_group_for_slug(category),
    )


def run_scan(scan: AreaScan) -> int:
    scan.status = AreaScan.Status.RUNNING
    scan.started_at = timezone.now()
    scan.error_message = ""
    scan.save(
        update_fields=[
            "status",
            "started_at",
            "error_message",
            "updated_at",
        ],
    )

    query_params: PlaceQueryParams = {
        "lat": scan.latitude,
        "lng": scan.longitude,
        "search_radius": scan.radius,
    }
    if scan.category:
        query_params["category"] = scan.category
    elif scan.category_group:
        query_params["category_group"] = scan.category_group

    response = search_places_by_location(query_params)
    places = [place for place in response.places if place_matches_scan(place, scan)]
    result_count = upsert_discovered_places(
        service_area=scan.service_area,
        places=places,
    )

    scan.status = AreaScan.Status.COMPLETED
    scan.completed_at = timezone.now()
    scan.result_count = result_count
    scan.save(
        update_fields=[
            "status",
            "completed_at",
            "result_count",
            "updated_at",
        ],
    )

    return result_count


def place_matches_scan(place: OpenStreetMapPlace, scan: AreaScan) -> bool:
    if scan.category:
        return place.category == scan.category

    if scan.category_group:
        return category_group_for_slug(place.category) == scan.category_group

    return True


def fail_scan(scan: AreaScan, error: Exception) -> None:
    scan.status = AreaScan.Status.FAILED
    scan.completed_at = timezone.now()
    scan.error_message = str(error)
    scan.save(
        update_fields=[
            "status",
            "completed_at",
            "error_message",
            "updated_at",
        ],
    )


def run_data_import(data_import: DataImport) -> int:
    data_import.status = DataImport.Status.RUNNING
    data_import.started_at = timezone.now()
    data_import.error_message = ""
    data_import.save(
        update_fields=[
            "status",
            "started_at",
            "error_message",
            "updated_at",
        ],
    )

    query_params: PlaceQueryParams = {
        "lat": data_import.service_area.latitude,
        "lng": data_import.service_area.longitude,
        "search_radius": data_import.radius,
    }
    layer_filter = get_layer_filter(data_import.layer)
    if category := layer_filter.get("category"):
        query_params["category"] = category
    if category_group := layer_filter.get("category_group"):
        query_params["category_group"] = category_group
    response = search_places_by_location(query_params)
    places = [
        place
        for place in response.places
        if place_matches_layer(place, data_import.layer)
    ]
    result_count = upsert_discovered_places(
        service_area=data_import.service_area,
        places=places,
    )

    data_import.status = DataImport.Status.COMPLETED
    data_import.completed_at = timezone.now()
    data_import.result_count = result_count
    data_import.save(
        update_fields=[
            "status",
            "completed_at",
            "result_count",
            "updated_at",
        ],
    )

    return result_count


def fail_data_import(data_import: DataImport, error: Exception) -> None:
    data_import.status = DataImport.Status.FAILED
    data_import.completed_at = timezone.now()
    data_import.error_message = str(error)
    data_import.save(
        update_fields=[
            "status",
            "completed_at",
            "error_message",
            "updated_at",
        ],
    )


def upsert_discovered_places(
    *,
    service_area: ServiceArea,
    places: list[OpenStreetMapPlace],
) -> int:
    fetched_at = timezone.now()

    for place in places:
        category = get_category_by_slug(place.category)
        category_group = category.group if category is not None else ""
        DiscoveredPlace.objects.update_or_create(
            service_area=service_area,
            osm_uid=place.osm_uid,
            defaults={
                "osm_id": place.osm_id,
                "osm_type": place.osm_type,
                "name": place.name,
                "category": place.category,
                "category_name": place.category_name,
                "category_group": category_group,
                "location": build_point(
                    latitude=place.latitude,
                    longitude=place.longitude,
                ),
                "address": place.address or "",
                "website": place.website or "",
                "opening_hours": place.opening_hours or "",
                "fetched_at": fetched_at,
            },
        )

    return len(places)


def nearby_places(
    *,
    service_area: ServiceArea,
    latitude: float,
    longitude: float,
    radius: int,
    category: str | None = None,
    category_group: str | None = None,
) -> QuerySet[DiscoveredPlace]:
    center = build_point(latitude=latitude, longitude=longitude)
    places = DiscoveredPlace.objects.filter(
        service_area=service_area, location__distance_lte=(center, D(m=radius))
    )

    if category:
        places = places.filter(category=category)
    elif category_group:
        places = places.filter(category_group=category_group)

    return places.annotate(distance=Distance("location", center)).order_by(
        "distance",
        "name",
    )
