"""Actual NetCDF3 classic file, CF calendar and bounded selected values."""

import argparse
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl
import xarray as xr

from veri_ufku.importers.delimited import Control
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import detect, get_adapter
from veri_ufku.importers.sources import capture_source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="veri-ufku-netcdf3-") as directory:
        root = Path(directory)
        source = root / "classic.nc"
        values = np.arange(24, dtype=np.int16).reshape(2, 3, 4)
        dataset = xr.Dataset(
            {
                "measurement": (
                    ("time", "latitude", "longitude"),
                    values,
                    dict(units="meter"),
                )
            },
            coords=dict(
                time=(
                    "time",
                    [0, 1],
                    dict(units="days since 2000-01-01", calendar="360_day"),
                ),
                latitude=[40.0, 41.0, 42.0],
                longitude=[20.0, 21.0, 22.0, 23.0],
            ),
        )
        dataset.to_netcdf(source, engine="scipy", format="NETCDF3_CLASSIC")
        work = root / "work"
        work.mkdir()
        snapshot = capture_source(source, work, Control())
        assert detect(snapshot) == "netcdf"
        settings = StructuredSettings(
            adapter_id="netcdf",
            array_variable="measurement",
            array_slice=dict(time=1, latitude=[1, 3, 1], longitude=[0, 4, 2]),
        )
        result = get_adapter("netcdf").import_data(snapshot, settings, work, Control())
        actual = pl.read_parquet(result["path"])["value"].to_list()
        assert actual == [16, 18, 20, 22]
        metadata = result["settings"]["format_metadata"]["parts"][0]["multidimensional"]
        assert metadata["coordinates"]["time"]["attributes"]["calendar"] == "360_day"
        report = dict(
            id="E34-NETCDF3",
            environment="ENV-34",
            date=datetime.now(UTC).isoformat(),
            source_magic=source.read_bytes()[:4].hex(),
            values=actual,
            calendar="360_day",
            passed=True,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print("PASS: actual NetCDF3 classic selected slice and calendar")


if __name__ == "__main__":
    main()
