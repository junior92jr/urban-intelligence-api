from typing import NotRequired, TypedDict

from places.models import PlaceImport
from places.services.categories import get_category_by_slug
from places.services.mappers import OpenStreetMapPlace


class LayerFilter(TypedDict):
    category: NotRequired[str]
    category_group: NotRequired[str]


def get_layer_filter(layer: str) -> LayerFilter:
    filters: dict[str, LayerFilter] = {
        PlaceImport.Layer.AMENITIES: {"category_group": "food"},
        PlaceImport.Layer.DAILY_LIFE: {"category_group": "essentials"},
        PlaceImport.Layer.MOBILITY: {"category_group": "mobility"},
        PlaceImport.Layer.GREEN: {"category": "park"},
    }

    return filters[layer]


def place_matches_layer(place: OpenStreetMapPlace, layer: str) -> bool:
    layer_filter = get_layer_filter(layer)

    if "category" in layer_filter:
        return place.category == layer_filter["category"]

    category = get_category_by_slug(place.category)
    category_group = layer_filter.get("category_group")
    assert category_group is not None

    return category is not None and category.group == category_group
