import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from geo.models import Country, OsmImportRun, ServiceArea, build_point
from geo.services import imports
from geo.services.osm.schemas import GeoJsonFeature, SupportedCity
from geo.services.osm.source import SUPPORTED_CITIES

pytestmark = pytest.mark.django_db


def feature(
    *,
    name: str,
    area_type: str,
    source_id: str,
    parent_source_id: str | None = None,
) -> GeoJsonFeature:
    properties: dict[str, object] = {
        "country_code": "DE",
        "name": name,
        "area_type": area_type,
        "source_id": source_id,
        "osm_element_type": "relation",
        "osm_admin_level": 6 if area_type == "city" else 9,
        "osm_tags": {"wikidata": "Q123"},
    }
    if parent_source_id is not None:
        properties["parent_source_id"] = parent_source_id
        properties["parent_osm_element_type"] = "relation"
    return GeoJsonFeature(
        type="Feature",
        properties=properties,
        geometry={
            "type": "Polygon",
            "coordinates": [
                [[8.0, 50.0], [8.1, 50.0], [8.1, 50.1], [8.0, 50.1], [8.0, 50.0]]
            ],
        },
    )


def test_osm_import_creates_hierarchy_and_atomically_activates_new_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    germany = Country.objects.get(code="DE")
    previous_run = OsmImportRun.objects.create(
        source_object_key="imports/previous.geojson",
        status=OsmImportRun.Status.SUCCEEDED,
        is_active=True,
    )
    ServiceArea.objects.create(
        country=germany,
        import_run=previous_run,
        slug="old-osm-city",
        name="Old OSM city",
        source=ServiceArea.SourceType.OSM,
        source_id="1",
        osm_element_type=ServiceArea.OsmElementType.RELATION,
        center=build_point(latitude=50.0, longitude=8.0),
    )
    osm_import_run = OsmImportRun.objects.create(
        source_object_key="imports/current.geojson",
    )
    source = {
        "type": "FeatureCollection",
        "features": [
            feature(name="Frankfurt", area_type="city", source_id="62400").model_dump(),
            feature(
                name="West",
                area_type="district",
                source_id="62401",
                parent_source_id="62400",
            ).model_dump(),
        ],
    }
    monkeypatch.setattr(
        imports, "download_source", lambda _key: json.dumps(source).encode()
    )

    imported_count = imports.run_osm_import(osm_import_run)
    osm_import_run.refresh_from_db()
    previous_run.refresh_from_db()
    city = ServiceArea.objects.get(import_run=osm_import_run, source_id="62400")
    district = ServiceArea.objects.get(import_run=osm_import_run, source_id="62401")

    assert imported_count == 2
    assert osm_import_run.status == OsmImportRun.Status.SUCCEEDED
    assert osm_import_run.is_active is True
    assert osm_import_run.processed_cities == 1
    assert previous_run.status == OsmImportRun.Status.SUPERSEDED
    assert previous_run.is_active is False
    assert city.boundary is not None
    assert city.center.equals(city.boundary.point_on_surface)
    assert city.bbox == city.boundary.envelope
    assert district.parent == city
    assert district.osm_tags == {"wikidata": "Q123"}


def test_osm_import_rejects_a_source_without_a_city() -> None:
    source = {
        "type": "FeatureCollection",
        "features": [
            feature(name="West", area_type="district", source_id="62401").model_dump()
        ],
    }

    areas = imports.parse_source(json.dumps(source).encode())

    assert all(area.area_type != ServiceArea.AreaType.CITY for area in areas)


@pytest.mark.parametrize(
    "source",
    [
        {"type": "FeatureCollection", "features": {}},
        {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}}],
        },
    ],
)
def test_parse_source_rejects_invalid_geojson_response(
    source: dict[str, object],
) -> None:
    with pytest.raises(
        imports.OsmImportConfigurationError,
        match="GeoJSON FeatureCollection",
    ):
        imports.parse_source(json.dumps(source).encode())


def test_osm_import_supersedes_only_the_active_run_for_its_city(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    previous_munich_run = OsmImportRun.objects.create(
        source_object_key="imports/munich-previous.geojson",
        city_slug="munich",
        status=OsmImportRun.Status.SUCCEEDED,
        is_active=True,
    )
    hamburg_run = OsmImportRun.objects.create(
        source_object_key="imports/hamburg.geojson",
        city_slug="hamburg",
        status=OsmImportRun.Status.SUCCEEDED,
        is_active=True,
    )
    munich_run = OsmImportRun.objects.create(
        source_object_key="imports/munich-current.geojson",
        city_slug="munich",
    )
    source = {
        "type": "FeatureCollection",
        "features": [
            feature(name="Munich", area_type="city", source_id="62428").model_dump()
        ],
    }
    monkeypatch.setattr(
        imports,
        "archive_latest_extract",
        lambda _city: SimpleNamespace(
            object_key="osm/geofabrik/bayern/test/bayern.osm.pbf",
            sha256="test-sha256",
        ),
    )
    monkeypatch.setattr(
        imports,
        "materialize_archived_extract",
        lambda _source: SimpleNamespace(path=tmp_path / "munich.osm.pbf"),
    )
    monkeypatch.setattr(
        imports,
        "extract_city_hierarchy_geojson",
        lambda _city, _path: json.dumps(source).encode(),
    )

    imports.run_osm_import(munich_run)
    previous_munich_run.refresh_from_db()
    hamburg_run.refresh_from_db()
    munich_run.refresh_from_db()

    assert previous_munich_run.status == OsmImportRun.Status.SUPERSEDED
    assert previous_munich_run.is_active is False
    assert hamburg_run.status == OsmImportRun.Status.SUCCEEDED
    assert hamburg_run.is_active is True
    assert munich_run.is_active is True


def test_available_slug_truncates_at_database_limit_and_resolves_collisions() -> None:
    germany = Country.objects.get(code="DE")
    base_slug = "a" * 260
    first_slug = imports.available_slug(
        country=germany,
        base_slug=base_slug,
        run_id=42,
    )
    ServiceArea.objects.create(
        country=germany,
        slug=first_slug,
        name="First long-name area",
        center=build_point(latitude=50.0, longitude=8.0),
    )

    second_slug = imports.available_slug(
        country=germany,
        base_slug=base_slug,
        run_id=42,
    )
    ServiceArea.objects.create(
        country=germany,
        slug=second_slug,
        name="Second long-name area",
        center=build_point(latitude=50.1, longitude=8.0),
    )
    third_slug = imports.available_slug(
        country=germany,
        base_slug=base_slug,
        run_id=42,
    )

    assert first_slug == "a" * 250
    assert second_slug.endswith("-import-42")
    assert third_slug.endswith("-import-42-2")
    assert len(second_slug) <= 250
    assert len(third_slug) <= 250


def osm_feature(
    *,
    name: str | None,
    osm_id: str | None,
    admin_level: str,
    coordinates: list[list[float]],
    osm_way_id: str | None = None,
    other_tags: str = '"wikidata"=>"Q123"',
) -> GeoJsonFeature:
    return GeoJsonFeature(
        type="Feature",
        properties={
            "osm_id": osm_id,
            "osm_way_id": osm_way_id,
            "name": name,
            "admin_level": admin_level,
            "boundary": "administrative",
            "other_tags": other_tags,
        },
        geometry={
            "type": "Polygon",
            "coordinates": [coordinates],
        },
    )


def square(
    min_longitude: float,
    min_latitude: float,
    max_longitude: float,
    max_latitude: float,
) -> list[list[float]]:
    return [
        [min_longitude, min_latitude],
        [max_longitude, min_latitude],
        [max_longitude, max_latitude],
        [min_longitude, max_latitude],
        [min_longitude, min_latitude],
    ]


def test_extract_city_hierarchy_uses_configured_levels_and_assigns_parents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    city = SupportedCity(
        slug="frankfurt-am-main",
        name="Frankfurt am Main",
        country_code="DE",
        extract_region="hessen",
        osm_relation_id="62400",
        city_admin_level=6,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    def fake_run_ogr_geojson(
        _pbf_path: object,
        where: str,
        *,
        spatial_filter: tuple[float, float, float, float] | None = None,
    ) -> list[GeoJsonFeature]:
        if "admin_level" in where:
            assert spatial_filter == (0.0, 0.0, 10.0, 10.0)
        if "osm_id = '62400'" in where:
            return [
                osm_feature(
                    name="Frankfurt am Main",
                    osm_id="62400",
                    admin_level="6",
                    coordinates=square(0, 0, 10, 10),
                )
            ]
        if "admin_level IN ('9')" in where:
            return [
                osm_feature(
                    name="Innenstadt I",
                    osm_id="111",
                    admin_level="9",
                    coordinates=square(0, 0, 5, 10),
                ),
                osm_feature(
                    name="Outside",
                    osm_id="999",
                    admin_level="9",
                    coordinates=square(20, 20, 30, 30),
                ),
            ]
        if "admin_level IN ('10')" in where:
            return [
                osm_feature(
                    name="Altstadt",
                    osm_id=None,
                    osm_way_id="222",
                    admin_level="10",
                    coordinates=square(1, 1, 2, 2),
                )
            ]
        return []

    monkeypatch.setattr(imports, "run_ogr_geojson", fake_run_ogr_geojson)

    source = imports.extract_city_hierarchy_geojson(city, Path("hessen.osm.pbf"))
    areas = imports.parse_source(source)

    assert [(area.name, area.area_type) for area in areas] == [
        ("Frankfurt am Main", ServiceArea.AreaType.CITY),
        ("Innenstadt I", ServiceArea.AreaType.DISTRICT),
        ("Altstadt", ServiceArea.AreaType.NEIGHBORHOOD),
    ]
    assert areas[1].parent_identity == ("relation", "62400")
    assert areas[2].osm_element_type == ServiceArea.OsmElementType.WAY
    assert areas[2].source_id == "222"
    assert areas[2].parent_identity == ("relation", "111")
    assert areas[2].osm_tags == {"wikidata": "Q123"}


def test_extract_city_hierarchy_requires_one_district_parent_for_neighborhoods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    city = SupportedCity(
        slug="frankfurt-am-main",
        name="Frankfurt am Main",
        country_code="DE",
        extract_region="hessen",
        osm_relation_id="62400",
        city_admin_level=6,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    def fake_run_ogr_geojson(
        _pbf_path: object,
        where: str,
        *,
        spatial_filter: tuple[float, float, float, float] | None = None,
    ) -> list[GeoJsonFeature]:
        if "admin_level" in where:
            assert spatial_filter == (0.0, 0.0, 10.0, 10.0)
        if "osm_id = '62400'" in where:
            return [
                osm_feature(
                    name="Frankfurt am Main",
                    osm_id="62400",
                    admin_level="6",
                    coordinates=square(0, 0, 10, 10),
                )
            ]
        if "admin_level IN ('9')" in where:
            return [
                osm_feature(
                    name="North",
                    osm_id="111",
                    admin_level="9",
                    coordinates=square(0, 0, 5, 10),
                ),
                osm_feature(
                    name="South",
                    osm_id="112",
                    admin_level="9",
                    coordinates=square(0, 0, 5, 10),
                ),
            ]
        if "admin_level IN ('10')" in where:
            return [
                osm_feature(
                    name="Altstadt",
                    osm_id="222",
                    admin_level="10",
                    coordinates=square(1, 1, 2, 2),
                )
            ]
        return []

    monkeypatch.setattr(imports, "run_ogr_geojson", fake_run_ogr_geojson)

    with pytest.raises(
        imports.OsmImportConfigurationError,
        match="Each neighborhood must have at most one district parent",
    ):
        imports.extract_city_hierarchy_geojson(city, Path("hessen.osm.pbf"))


def test_supported_cities_have_stable_relation_and_hierarchy_configuration() -> None:
    expected_relation_ids = {
        "berlin": "62422",
        "hamburg": "62782",
        "munich": "62428",
        "cologne": "62578",
        "frankfurt-am-main": "62400",
        "dusseldorf": "62539",
        "leipzig": "62649",
        "dresden": "191645",
        "nuremberg": "62780",
        "heidelberg": "62487",
    }

    assert {
        city.slug: city.osm_relation_id for city in SUPPORTED_CITIES.cities
    } == expected_relation_ids
    for city in SUPPORTED_CITIES.cities:
        assert city.city_admin_level == (4 if city.slug in {"berlin", "hamburg"} else 6)
        assert city.district_admin_levels == (9,)
        assert city.neighborhood_admin_levels == (10,)


def test_extract_city_uses_relation_id_despite_localized_osm_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    city = next(city for city in SUPPORTED_CITIES.cities if city.slug == "munich")

    def fake_run_ogr_geojson(
        _pbf_path: object,
        where: str,
        *,
        spatial_filter: tuple[float, float, float, float] | None = None,
    ) -> list[GeoJsonFeature]:
        assert spatial_filter is None
        assert "osm_id = '62428'" in where
        return [
            osm_feature(
                name="München",
                osm_id="62428",
                admin_level="6",
                coordinates=square(0, 0, 10, 10),
            )
        ]

    monkeypatch.setattr(imports, "run_ogr_geojson", fake_run_ogr_geojson)

    areas = imports.parse_source(
        imports.extract_city_geojson(city, Path("bayern.osm.pbf"))
    )

    assert areas[0].name == "München"
    assert areas[0].source_id == "62428"


@pytest.mark.parametrize(
    ("name", "other_tags", "expected_name"),
    [
        ("Explicit name", '"official_name"=>"Official name"', "Explicit name"),
        (None, '"official_name"=>"Official name"', "Official name"),
        (None, '"name:prefix"=>"Bezirksteil", "ref"=>"15.4"', "Bezirksteil 15.4"),
    ],
)
def test_normalize_osm_feature_resolves_boundary_names(
    name: str | None,
    other_tags: str,
    expected_name: str,
) -> None:
    city = next(city for city in SUPPORTED_CITIES.cities if city.slug == "munich")
    normalized = imports.normalize_osm_feature(
        city,
        osm_feature(
            name=name,
            osm_id="52208",
            admin_level="10",
            coordinates=square(0, 0, 1, 1),
            other_tags=other_tags,
        ),
        "neighborhood",
    )

    assert imports.feature_properties(normalized)["name"] == expected_name


def test_normalize_osm_feature_rejects_boundary_without_a_usable_name() -> None:
    city = next(city for city in SUPPORTED_CITIES.cities if city.slug == "munich")

    with pytest.raises(imports.OsmImportConfigurationError, match="name or reference"):
        imports.normalize_osm_feature(
            city,
            osm_feature(
                name=None,
                osm_id="52208",
                admin_level="10",
                coordinates=square(0, 0, 1, 1),
            ),
            "neighborhood",
        )


def test_extract_city_hierarchy_assigns_unmatched_neighborhood_to_city(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    city = next(city for city in SUPPORTED_CITIES.cities if city.slug == "munich")

    def fake_run_ogr_geojson(
        _pbf_path: object,
        where: str,
        *,
        spatial_filter: tuple[float, float, float, float] | None = None,
    ) -> list[GeoJsonFeature]:
        if "osm_id = '62428'" in where:
            return [
                osm_feature(
                    name="München",
                    osm_id="62428",
                    admin_level="6",
                    coordinates=square(0, 0, 10, 10),
                )
            ]
        if "admin_level IN ('9')" in where:
            return []
        return [
            osm_feature(
                name="Bezirksteil 15.4",
                osm_id="52208",
                admin_level="10",
                coordinates=square(1, 1, 2, 2),
            )
        ]

    monkeypatch.setattr(imports, "run_ogr_geojson", fake_run_ogr_geojson)

    areas = imports.parse_source(
        imports.extract_city_hierarchy_geojson(city, Path("bayern.osm.pbf"))
    )

    assert areas[1].area_type == ServiceArea.AreaType.NEIGHBORHOOD
    assert areas[1].parent_identity == ("relation", "62428")
