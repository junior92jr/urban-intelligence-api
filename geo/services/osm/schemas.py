from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class SupportedCity(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    name: str
    country_code: str
    extract_region: str
    osm_relation_id: str | None = None
    city_admin_level: int | None = None
    district_admin_levels: tuple[int, ...] = ()
    neighborhood_admin_levels: tuple[int, ...] = ()


class ArchivedOsmSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    region: str
    snapshot_date: date
    object_key: str
    sha256: str


class MaterializedOsmSource(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    source: ArchivedOsmSource
    path: Path
