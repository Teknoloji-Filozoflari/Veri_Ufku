"""Actual GDAL vector and GeoTIFF fixtures, plus hand-checkable local coordinates."""

import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import rasterio
import shapely
from pyproj import CRS
from rasterio.transform import from_origin


def fixture(root, kind, points=False, invalid=False):
    root = Path(root)
    gs = (
        [
            shapely.Point(500000, 4500000),
            shapely.Point(500003, 4500004),
            shapely.Point(500020, 4500010),
        ]
        if points
        else [
            shapely.box(500000, 4500000, 500010, 4500010),
            shapely.box(500010, 4500000, 500020, 4500010),
            shapely.box(500020, 4500000, 500030, 4500010),
        ]
    )
    if invalid:
        gs[0] = shapely.Polygon(
            [
                (500000, 4500000),
                (500010, 4500010),
                (500000, 4500010),
                (500010, 4500000),
                (500000, 4500000),
            ]
        )
    table = pa.table(
        {
            "source_id": ["a", "b", "c"],
            "count": [20.0, 40.0, 10.0],
            "population": [100.0, 400.0, 100.0],
            "wkb_geometry": shapely.to_wkb(gs).tolist(),
        }
    )
    if kind == "geotiff":
        path = root / "grid.tif"
        data = np.arange(24, dtype="float32").reshape(4, 6)
        data[1, 2] = -9999
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            width=6,
            height=4,
            count=1,
            dtype="float32",
            crs="EPSG:32635",
            transform=from_origin(500000, 4500000, 10, 10),
            nodata=-9999,
        ) as ds:
            ds.write(data, 1)
            ds.set_band_unit(1, "kelvin")
        return path
    if kind == "geoparquet":
        geo = dict(
            version="1.1.0",
            primary_column="wkb_geometry",
            columns={
                "wkb_geometry": dict(
                    encoding="WKB",
                    geometry_types=["Point" if points else "Polygon"],
                    crs=CRS.from_epsg(32635).to_json_dict(),
                )
            },
        )
        table = table.replace_schema_metadata({b"geo": json.dumps(geo).encode()})
        path = root / "features.parquet"
        pq.write_table(table, path)
        return path
    ext, driver = {
        "geojson": (".geojson", "GeoJSON"),
        "geopackage": (".gpkg", "GPKG"),
        "shapefile": (".shp", "ESRI Shapefile"),
    }[kind]
    path = root / ("features" + ext)
    pyogrio.write_arrow(
        table,
        path,
        driver=driver,
        geometry_name="wkb_geometry",
        geometry_type="Point" if points else "Polygon",
        crs="EPSG:32635",
        layer="features" if kind == "geopackage" else None,
    )
    return path
