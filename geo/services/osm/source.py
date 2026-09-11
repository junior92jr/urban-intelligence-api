import hashlib
import tempfile
from pathlib import Path

import httpx
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel, ConfigDict

from geo.services.osm.schemas import (
    ArchivedOsmSource,
    MaterializedOsmSource,
    SupportedCity,
)
from intelligence.services.providers.copernicus import get_cache_storage_client


class SupportedCities(BaseModel):
    model_config = ConfigDict(frozen=True)
    berlin: SupportedCity = SupportedCity(
        slug="berlin",
        name="Berlin",
        country_code="DE",
        extract_region="berlin",
        osm_relation_id="62422",
        city_admin_level=4,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    hamburg: SupportedCity = SupportedCity(
        slug="hamburg",
        name="Hamburg",
        country_code="DE",
        extract_region="hamburg",
        osm_relation_id="62782",
        city_admin_level=4,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    munich: SupportedCity = SupportedCity(
        slug="munich",
        name="Munich",
        country_code="DE",
        extract_region="bayern",
        osm_relation_id="62428",
        city_admin_level=6,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    cologne: SupportedCity = SupportedCity(
        slug="cologne",
        name="Cologne",
        country_code="DE",
        extract_region="nordrhein-westfalen",
        osm_relation_id="62578",
        city_admin_level=6,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    frankfurt_am_main: SupportedCity = SupportedCity(
        slug="frankfurt-am-main",
        name="Frankfurt am Main",
        country_code="DE",
        extract_region="hessen",
        osm_relation_id="62400",
        city_admin_level=6,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    dusseldorf: SupportedCity = SupportedCity(
        slug="dusseldorf",
        name="Düsseldorf",
        country_code="DE",
        extract_region="nordrhein-westfalen",
        osm_relation_id="62539",
        city_admin_level=6,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    leipzig: SupportedCity = SupportedCity(
        slug="leipzig",
        name="Leipzig",
        country_code="DE",
        extract_region="sachsen",
        osm_relation_id="62649",
        city_admin_level=6,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    dresden: SupportedCity = SupportedCity(
        slug="dresden",
        name="Dresden",
        country_code="DE",
        extract_region="sachsen",
        osm_relation_id="191645",
        city_admin_level=6,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    nuremberg: SupportedCity = SupportedCity(
        slug="nuremberg",
        name="Nuremberg",
        country_code="DE",
        extract_region="bayern",
        osm_relation_id="62780",
        city_admin_level=6,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    heidelberg: SupportedCity = SupportedCity(
        slug="heidelberg",
        name="Heidelberg",
        country_code="DE",
        extract_region="baden-wuerttemberg",
        osm_relation_id="62487",
        city_admin_level=6,
        district_admin_levels=(9,),
        neighborhood_admin_levels=(10,),
    )

    @property
    def cities(self) -> tuple[SupportedCity, ...]:
        return (
            self.berlin,
            self.hamburg,
            self.munich,
            self.cologne,
            self.frankfurt_am_main,
            self.dusseldorf,
            self.leipzig,
            self.dresden,
            self.nuremberg,
            self.heidelberg,
        )

    def get(self, slug: str) -> SupportedCity:
        for city in self.cities:
            if city.slug == slug:
                return city

        raise ValueError(f"Unsupported city {slug!r}.")


SUPPORTED_CITIES = SupportedCities()


def get_supported_city(slug: str) -> SupportedCity:
    return SUPPORTED_CITIES.get(slug)


def geofabrik_url(city: SupportedCity) -> str:
    return (
        "https://download.geofabrik.de/europe/germany/"
        f"{city.extract_region}-latest.osm.pbf"
    )


def archived_object_key(city: SupportedCity) -> str:
    snapshot_date = timezone.localdate()
    filename = f"{city.extract_region}-latest.osm.pbf"

    return f"osm/geofabrik/{city.extract_region}/{snapshot_date:%Y-%m-%d}/{filename}"


def archive_latest_extract(city: SupportedCity) -> ArchivedOsmSource:
    snapshot_date = timezone.localdate()
    object_key = archived_object_key(city)
    client = get_cache_storage_client()

    try:
        head = client.head_object(
            Bucket=settings.OBJECT_STORAGE_BUCKET,
            Key=object_key,
        )
        return ArchivedOsmSource(
            region=city.extract_region,
            snapshot_date=snapshot_date,
            object_key=object_key,
            sha256=str(head.get("Metadata", {}).get("sha256", "")),
        )
    except ClientError:
        # A missing object is expected on the first request for a date/region.
        pass

    with httpx.stream(
        "GET",
        geofabrik_url(city),
        timeout=settings.OBJECT_STORAGE_TIMEOUT_IN_SECS,
        follow_redirects=True,
    ) as response:
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(
            suffix=".osm.pbf",
            delete=False,
        ) as handle:
            path = Path(handle.name)
            digest = hashlib.sha256()

            for chunk in response.iter_bytes():
                digest.update(chunk)
                handle.write(chunk)

    try:
        client.upload_file(
            str(path),
            settings.OBJECT_STORAGE_BUCKET,
            object_key,
            ExtraArgs={
                "Metadata": {
                    "sha256": digest.hexdigest(),
                },
            },
        )
    finally:
        path.unlink(missing_ok=True)

    return ArchivedOsmSource(
        region=city.extract_region,
        snapshot_date=snapshot_date,
        object_key=object_key,
        sha256=digest.hexdigest(),
    )


def materialize_archived_extract(
    source: ArchivedOsmSource,
) -> MaterializedOsmSource:
    response = get_cache_storage_client().get_object(
        Bucket=settings.OBJECT_STORAGE_BUCKET,
        Key=source.object_key,
    )

    with tempfile.NamedTemporaryFile(
        suffix=".osm.pbf",
        delete=False,
    ) as handle:
        path = Path(handle.name)
        body = response["Body"]

        try:
            while chunk := body.read(1024 * 1024):
                handle.write(chunk)
        finally:
            body.close()

    return MaterializedOsmSource(
        source=source,
        path=path,
    )
