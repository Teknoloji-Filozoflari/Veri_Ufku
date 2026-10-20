"""10005-row format previews and cooperative cancellation; SAS small fixture separate."""

import argparse
import json
import sys
import tempfile
import threading
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase30/large.json")
    )
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
    import fastavro
    import h5py
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.ipc as ipc
    import pyarrow.orc as orc
    import pyarrow.parquet as pq
    import pyreadstat

    import veri_ufku
    from veri_ufku.importers.delimited import Control
    from veri_ufku.importers.native import StructuredSettings
    from veri_ufku.importers.registry import detect, get_adapter
    from veri_ufku.importers.sources import capture_source, unpack
    from veri_ufku.jobs.workers import Canceled

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    count, records = 10005, []
    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase30-large-") as directory:
        root = Path(directory)
        for adapter in (
            "parquet_dataset",
            "arrow_dataset",
            "avro",
            "orc",
            "hdf5",
            "xml",
            "fixed_width",
            "spss",
            "stata",
        ):
            place = root / adapter
            place.mkdir()
            work = place / "work"
            work.mkdir()
            table = pa.table({"value": pa.array(np.arange(count, dtype=np.int64))})
            spec = StructuredSettings(adapter_id=adapter)
            if adapter in ("parquet_dataset", "arrow_dataset"):
                source = place / "dataset"
                source.mkdir()
                if adapter == "parquet_dataset":
                    pq.write_table(table, source / "part.parquet", row_group_size=1024)
                else:
                    with ipc.new_file(source / "part.arrow", table.schema) as writer:
                        writer.write_table(table, max_chunksize=1024)
            elif adapter == "orc":
                source = place / "data.orc"
                orc.write_table(table, source)
            elif adapter == "avro":
                source = place / "data.avro"
                with source.open("wb") as stream:
                    fastavro.writer(
                        stream,
                        {
                            "type": "record",
                            "name": "R",
                            "fields": [{"name": "value", "type": "long"}],
                        },
                        (dict(value=i) for i in range(count)),
                    )
            elif adapter == "hdf5":
                source = place / "data.h5"
                data = np.zeros(count, dtype=[("value", "<i8")])
                data["value"] = np.arange(count)
                with h5py.File(source, "w") as file:
                    file.create_dataset("/table", data=data, chunks=(1024,))
                spec = replace(spec, sheet="/table")
            elif adapter == "xml":
                source = place / "data.xml"
                source.write_text(
                    "<root>"
                    + "".join(
                        f"<record><value>{i}</value></record>" for i in range(count)
                    )
                    + "</root>"
                )
                spec = replace(spec, record_path="/root/record")
            elif adapter == "fixed_width":
                source = place / "data.fwf"
                source.write_text("".join(f"{i:05d}\n" for i in range(count)))
                spec = replace(spec, widths=(5,), column_names=("value",))
            else:
                source = place / ("data.sav" if adapter == "spss" else "data.dta")
                writer = (
                    pyreadstat.write_sav if adapter == "spss" else pyreadstat.write_dta
                )
                writer(pd.DataFrame(dict(value=np.arange(count, dtype=float))), source)
            control = Control()
            snapshot = unpack(capture_source(source, work, control), work, control)
            assert detect(snapshot) == adapter
            started = time.monotonic()
            preview = get_adapter(adapter).preview(snapshot, spec, control)
            assert preview["examined"] == 200 and preview["limited"]
            stop = threading.Event()
            cancel_checks = 0

            class CancelDuringRead(Control):
                def check(self):
                    nonlocal cancel_checks
                    cancel_checks += 1
                    if cancel_checks == 3:
                        stop.set()
                    super().check()

            try:
                get_adapter(adapter).preview(snapshot, spec, CancelDuringRead(stop))
                raise AssertionError("Canceled reader returned a result")
            except Canceled:
                pass
            records.append(
                dict(
                    adapter=adapter,
                    source_rows=count,
                    preview_rows=preview["examined"],
                    displayed_limit=20,
                    cancel_checks=cancel_checks,
                    cancel_result="canceled; no artifact publication",
                    seconds=round(time.monotonic() - started, 4),
                )
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            dict(
                date=datetime.now(UTC).isoformat(),
                package_file=veri_ufku.__file__,
                records=records,
                sas_large_fixture="not measured; actual small sas7bdat tagged-missing fixture tested separately",
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print("PASS: nine 10005-row previews limited200; nine cancel-during-read checks")


if __name__ == "__main__":
    main()
