"""One billion logical cells in sparse HDF5: cost admission before decoding."""

import argparse
import json
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import h5py
import numpy as np
import polars as pl

from veri_ufku.importers.delimited import Control
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import get_adapter
from veri_ufku.importers.sources import capture_source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase34-large-") as directory:
        root = Path(directory)
        path = root / "billion.h5"
        with h5py.File(path, "w") as file:
            dataset = file.create_dataset(
                "measurement",
                shape=(1000, 1000, 1000),
                dtype="f4",
                chunks=(1, 10, 10),
                fillvalue=-999.0,
            )
            dataset.attrs.update(units="kelvin", _FillValue=-999.0)
            for axis, name in enumerate(("time", "latitude", "longitude")):
                coord = file.create_dataset(name, data=np.arange(1000))
                coord.make_scale(name)
                dataset.dims[axis].attach_scale(coord)
                dataset.dims[axis].label = name
            dataset[0, 0, :4] = [273.15, 274.15, 275.15, 276.15]
        work = root / "work"
        work.mkdir()
        snapshot = capture_source(path, work, Control())
        settings = StructuredSettings(
            adapter_id="hdf5_array", array_variable="/measurement"
        )
        adapter = get_adapter("hdf5_array")
        preview = adapter.preview(snapshot, settings, Control())
        cost = preview["settings"]["format_metadata"]["parts"][0]["multidimensional"][
            "cost"
        ]
        assert cost["blocked"] and cost["output_rows"] == 1000000000
        assert not preview["rows"] and not preview["importable"]
        settings = replace(
            settings, array_slice=dict(time=0, latitude=0, longitude=[0, 4, 1])
        )
        result = adapter.import_data(snapshot, settings, work, Control())
        frame = pl.read_parquet(result["path"])
        assert frame.height == 4
        np.testing.assert_allclose(
            frame["value"].to_numpy(), [273.15, 274.15, 275.15, 276.15], rtol=1e-6
        )
        report = dict(
            id="E34-BILLION",
            environment="ENV-34",
            date=datetime.now(UTC).isoformat(),
            source_bytes=path.stat().st_size,
            cost=cost,
            selected_rows=4,
            values=frame["value"].to_list(),
            blocked_before_materialization=True,
            fixture="CC0 sparse HDF5; billion logical cells, four initialized measurements",
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print("PASS: billion-cell preflight, four-cell actual read", flush=True)


if __name__ == "__main__":
    main()
