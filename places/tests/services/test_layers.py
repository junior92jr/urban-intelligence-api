import pytest

from places.models import PlaceImport
from places.services.layers import get_layer_filter


@pytest.mark.parametrize(
    ("layer", "expected_filter"),
    [
        (PlaceImport.Layer.AMENITIES, {"category_group": "food"}),
        (PlaceImport.Layer.DAILY_LIFE, {"category_group": "essentials"}),
        (PlaceImport.Layer.MOBILITY, {"category_group": "mobility"}),
        (PlaceImport.Layer.GREEN, {"category": "park"}),
    ],
)
def test_map_layer_filters_are_translated_for_open_street_map(
    layer: str,
    expected_filter: dict[str, str],
):
    assert get_layer_filter(layer) == expected_filter
