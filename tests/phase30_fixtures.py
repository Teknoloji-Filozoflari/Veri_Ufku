"""Synthetic CC0 small fixtures; SAS fixtures retain their upstream license."""

import struct
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import fastavro
import h5py
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc
import pyarrow.orc as orc
import pyarrow.parquet as pq
import pyreadstat


def fixture(root, adapter):
    root = Path(root)
    if adapter in ("parquet_dataset", "arrow_dataset", "orc"):
        table = pa.table(
            {
                "integer": pa.array([2**64 - 1, None], type=pa.uint64()),
                "amount": pa.array(
                    [Decimal("1234567890123456.123456"), None],
                    type=pa.decimal128(30, 6),
                ),
                "when": pa.array(
                    [1700000000000000001, None],
                    type=pa.timestamp("ns", "Europe/Istanbul"),
                ),
                "nested": pa.array([[1, None], []], type=pa.list_(pa.int64())),
            }
        )
        if adapter == "orc":
            # ORC stores signed integers; UInt64 cannot be represented by ORC.
            table = table.set_column(
                0, "integer", pa.array([2**63 - 1, None], type=pa.int64())
            )
            path = root / "native.orc"
            orc.write_table(table, path)
            return path
        path = root / adapter / "region=001" / "part-0.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        if adapter == "arrow_dataset":
            path = path.with_suffix(".arrow")
            categories = pa.DictionaryArray.from_arrays(
                pa.array([0, 1], type=pa.int8()), pa.array(["Çağrı", "Işıl"])
            )
            table = table.append_column("category", categories)
            with ipc.new_file(
                path, table.schema.with_metadata({b"description": b"fixture"})
            ) as writer:
                writer.write_table(table)
        else:
            pq.write_table(table, path)
        return root / adapter
    if adapter == "avro":
        path = root / "sample.avro"
        spec = {
            "type": "record",
            "name": "R",
            "fields": [
                {"name": "integer", "type": "long"},
                {
                    "name": "amount",
                    "type": [
                        "null",
                        {
                            "type": "bytes",
                            "logicalType": "decimal",
                            "precision": 30,
                            "scale": 6,
                        },
                    ],
                },
                {
                    "name": "group",
                    "type": {"type": "enum", "name": "Group", "symbols": ["A", "B"]},
                },
                {
                    "name": "nested",
                    "type": {"type": "array", "items": ["null", "long"]},
                },
                {
                    "name": "when",
                    "type": {"type": "long", "logicalType": "local-timestamp-micros"},
                },
            ],
        }
        with path.open("wb") as stream:
            fastavro.writer(
                stream,
                spec,
                [
                    dict(
                        integer=2**63 - 1,
                        amount=Decimal("1234567890123456.123456"),
                        group="A",
                        nested=[1, None],
                        when=datetime(2020, 1, 1),
                    ),
                    dict(
                        integer=-(2**63),
                        amount=None,
                        group="B",
                        nested=[],
                        when=datetime(2020, 1, 2),
                    ),
                ],
                codec="deflate",
            )
        return path
    if adapter == "hdf5":
        path = root / "sample.h5"
        data = np.array(
            [(2**64 - 1, b"001", 1.25), (0, b"002", 2.5)],
            dtype=[("integer", "<u8"), ("code", "S3"), ("amount", "<f8")],
        )
        with h5py.File(path, "w") as file:
            dataset = file.create_dataset(
                "/tables/observations", data=data, chunks=(1,), compression="gzip"
            )
            dataset.attrs["description"] = "Kaynak notu"
            file.attrs["unit"] = "puan"
        return path
    if adapter == "xml":
        path = root / "sample.xml"
        path.write_text(
            '<root><record id="001"><amount>1.25</amount><empty /></record><record id="002"><amount>2.50</amount></record></root>'
        )
        return path
    if adapter == "fixed_width":
        path = root / "sample.fwf"
        path.write_text("001Çağrı  \n002Işıl   \n")
        return path
    if adapter == "spss":
        path = root / "sample.sav"
        pyreadstat.write_sav(
            pd.DataFrame(dict(code=[1.0, 99.0, None], weight=[1.0, 2.0, 3.0])),
            path,
            column_labels={"code": "Kategori kodu"},
            variable_value_labels={"code": {1.0: "Evet", 99.0: "Yanıt yok"}},
            missing_ranges={"code": [99.0]},
            variable_measure={"code": "nominal"},
        )
        raw = bytearray(path.read_bytes())
        raw[76:80] = struct.pack("<i", 2)
        path.write_bytes(raw)
        return path
    if adapter == "stata":
        path = root / "sample.dta"
        pyreadstat.write_dta(
            pd.DataFrame(dict(code=[1.0, "a", None], group=[1.0, 2.0, 1.0])),
            path,
            missing_user_values={"code": ["a"]},
            variable_value_labels={"group": {1.0: "Evet", 2.0: "Hayır"}},
            column_labels={"group": "Kategori"},
        )
        return path
    if adapter == "sas":
        return Path(__file__).parent / "fixtures/phase30/missing_test.sas7bdat"
    raise ValueError(adapter)
