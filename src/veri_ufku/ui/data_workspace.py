"""Adapter availability for the Veri panel. Uses the single capability registry."""

from veri_ufku.domain.capabilities import CAPABILITIES, availability
from veri_ufku.importers.registry import FORMATS

CORE_FORMATS = ("csv", "tsv", "json", "jsonl", "xlsx", "parquet")
SPECIAL_FORMATS = (
    "geojson",
    "geopackage",
    "shapefile",
    "geoparquet",
    "netcdf",
    "zarr",
    "hdf5",
    "http",
    "s3",
    "postgresql",
    "duckdb",
)


def adapter_rows(names=CORE_FORMATS):
    rows = []
    for name in names:
        key = "import." + name.replace("_", "-")
        cap = CAPABILITIES.get(key)
        if cap is None and name in FORMATS:
            cap = CAPABILITIES.get("import." + name)
        if cap is None:
            rows.append(
                {
                    "id": name,
                    "label": name,
                    "status": "kurulu değil",
                    "installed": False,
                }
            )
            continue
        installed, reason = availability(cap)
        rows.append(
            {
                "id": name,
                "label": name,
                "status": "kurulu" if installed else (reason or "kurulu değil"),
                "installed": bool(installed),
            }
        )
    return rows


def core_adapters():
    return adapter_rows(CORE_FORMATS)


def special_adapters():
    return adapter_rows(SPECIAL_FORMATS)
