"""Data-only geographic declarations; native libraries load on explicit use."""

FORMATS = ("geojson", "geopackage", "shapefile", "geoparquet", "geotiff")

CHART_SCHEMAS = {
    "map-point": "WKT Point geometry or explicit numeric x/y + CRS",
    "map-choropleth": "Polygon/MultiPolygon WKT + numeric numerator; count or rate with positive denominator; explicit thresholds",
    "map-density": "Projected metre Point WKT or x/y; grid count or count/m²; no automatic KDE",
    "map-raster": "Verified GeoTIFF window + physical x/y/value; nodata mask, source CRS/affine metadata required",
}

OPERATION_KINDS = {
    "geo_coordinates",
    "geo_assign",
    "geo_reproject",
    "geo_repair",
    "geo_buffer",
    "geo_area",
    "geo_distance",
    "geo_clip",
    "geo_join",
    "geo_block",
    "geo_moran",
}
