# Copernicus Imports

The first supported Copernicus dataset is the 100 m Tree Cover Density layer. It
is imported as a GeoTIFF and aggregated inside each `ServiceArea.boundary` to
create a dated `green-exposure` observation.

The importer reads the public Copernicus catalogue, selects the newest source
tiles intersecting a service-area boundary, then caches those GeoTIFFs in
private S3-compatible object storage. Configure the Copernicus S3 source and
the private cache:

```dotenv
OBJECT_STORAGE_ENDPOINT_URL=http://minio:9000
OBJECT_STORAGE_ACCESS_KEY_ID=city-guide
OBJECT_STORAGE_SECRET_ACCESS_KEY=city-guide-minio-dev
OBJECT_STORAGE_REGION=us-east-1
OBJECT_STORAGE_BUCKET=city-guide-data
OBJECT_STORAGE_TIMEOUT_IN_SECS=120
COPERNICUS_S3_ENDPOINT_URL=https://eodata.dataspace.copernicus.eu
COPERNICUS_S3_ACCESS_KEY_ID=your-copernicus-access-key
COPERNICUS_S3_SECRET_ACCESS_KEY=your-copernicus-secret-key
COPERNICUS_S3_REGION=default
```

The local Docker stack starts MinIO and creates `city-guide-data` automatically.
It is a private cache; no manual uploads are required. The importer records the
catalogue source and immutable cached object keys with each completed import.

The supported German cities are seeded with official municipality boundaries
from BKG VG250 (reference date 2026-01-01, licence
[dl-de/by-2-0](https://www.govdata.de/dl-de/by-2-0)). Imports for any newly
created service area still require a polygon boundary; city centres alone are
not sufficient for a meaningful area-level observation.

Dataset details: [Copernicus Tree Cover Density 100 m](https://land.copernicus.eu/en/products/high-resolution-layer-forests-and-tree-cover/tree-cover-density-2018-present-raster-100-m-europe-yearly)
