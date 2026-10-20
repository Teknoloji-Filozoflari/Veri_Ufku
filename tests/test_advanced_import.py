"""Real small formats, native/metadata roundtrip, bounded parsing and source safety."""

import base64
import gzip
import json
import threading
import zipfile
from dataclasses import replace
from decimal import Decimal

import polars as pl
import pyarrow as pa
import pyarrow.ipc as ipc
import pyarrow.parquet as pq
import pytest
from phase30_fixtures import fixture

from veri_ufku.importers.advanced import ADVANCED_FORMATS
from veri_ufku.importers.delimited import Control, verify_capture
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import detect, get_adapter
from veri_ufku.importers.sources import capture_source, unpack, verify_sources
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def settings(adapter):
    return StructuredSettings(
        adapter_id=adapter,
        **{
            "hdf5": dict(sheet="/tables/observations"),
            "xml": dict(record_path="/root/record"),
            "fixed_width": dict(widths=(3, 7), column_names=("code", "name")),
        }.get(adapter, {}),
    )


def captured(path, workspace, control=None):
    control = control or Control()
    snapshot = unpack(capture_source(path, workspace, control), workspace, control)
    snapshot["strict_source"] = True
    return snapshot


@pytest.mark.parametrize("adapter", ADVANCED_FORMATS)
def test_format_native_metadata_publish_reopen(tmp_path, adapter):
    source = fixture(tmp_path, adapter)
    workspace = tmp_path / "work"
    workspace.mkdir()
    snapshot = captured(source, workspace)
    assert detect(snapshot) == adapter
    importer, spec = get_adapter(adapter), settings(adapter)
    preview = importer.preview(snapshot, spec)
    assert preview["importable"] and preview["examined"] <= 200
    result = importer.import_data(snapshot, spec, workspace, Control())
    original_schema = ipc.read_schema(
        pa.BufferReader(
            base64.b64decode(
                result["settings"]["format_metadata"]["parts"][0]["arrow_schema_base64"]
            )
        )
    )
    assert original_schema.names
    frame = pl.read_parquet(result["path"])
    assert len(frame) == result["accepted"]
    assert frame["__vu_row_id"].n_unique() == len(frame)
    assert frame["__vu_source_record_id"].n_unique() == len(frame)
    assert json.loads(frame["__vu_source_locator"][0])["sha256"]
    if adapter in ("parquet_dataset", "arrow_dataset", "avro"):
        assert frame["amount"][0] == Decimal("1234567890123456.123456")
        assert frame["amount"][1] is None
        assert frame["nested"].to_list() == [[1, None], []]
    if adapter in ("parquet_dataset", "arrow_dataset", "hdf5"):
        assert frame["integer"][0] == 2**64 - 1
    if adapter in ("parquet_dataset", "arrow_dataset"):
        assert frame["when"].cast(pl.Int64)[0] == 1700000000000000001
        assert frame.schema["when"] == pl.Datetime("ns", "Europe/Istanbul")
        assert frame["region"].to_list() == ["001", "001"]
    if adapter == "arrow_dataset":
        assert frame["category"].to_list() == ["Çağrı", "Işıl"]
        assert result["settings"]["format_metadata"]["dictionaries"][0]["values"] == [
            "Çağrı",
            "Işıl",
        ]
        assert pa.types.is_dictionary(original_schema.field("category").type)
        assert original_schema.metadata[b"description"] == b"fixture"
    if adapter == "spss":
        metadata = result["settings"]["format_metadata"]["parts"][0]
        assert frame["code"].to_list() == [1.0, 99.0, None]
        assert metadata["missing_ranges"]["code"] == [{"lo": 99.0, "hi": 99.0}]
        assert metadata["weight_definition"]["source_column"] == "weight"
        assert metadata["value_label_entries"]["code"][1]["label"] == "Yanıt yok"
    if adapter == "stata":
        assert frame["code"].to_list() == [1.0, None, None]
        assert json.loads(frame["__vu_expansion_index"][1]) == {
            "user_missing": {"code": "a"}
        }
        assert frame["__vu_expansion_index"][2] == "{}"
    if adapter == "sas":
        assert frame["var1"].to_list() == [None] and frame["var8"].to_list() == [None]
        missing = json.loads(frame["__vu_expansion_index"][0])["user_missing"]
        assert missing == dict(
            var1="A", var2="B", var3="C", var4="X", var5="Y", var6="Z", var7="_"
        )
        assert "var8" not in missing and frame["var9"].to_list() == [1.0]
    if adapter == "hdf5":
        assert (
            result["settings"]["format_metadata"]["parts"][0]["attributes"][
                "description"
            ]
            == "Kaynak notu"
        )
    if adapter == "xml":
        assert frame["@id"].to_list() == ["001", "002"]
        assert frame["empty"].to_list() == ["", None]
    if adapter == "fixed_width":
        assert frame["code"].to_list() == ["001", "002"]
        assert frame["name"].to_list() == ["Çağrı  ", "Işıl   "]
    store = ProjectStore.create(tmp_path / "project")
    try:
        dataset = store.publish_import(result, portable=True)
        before = store.state
    finally:
        store.close()
    store = ProjectStore.open(tmp_path / "project")
    try:
        assert store.state == before
        assert store.source_statuses()[dataset["source_id"]] == "unchanged"
        assert store.state["datasets"][0]["import_metadata"]["settings"][
            "format_metadata"
        ] == json.loads(json.dumps(result["settings"]["format_metadata"]))
    finally:
        store.close()
    verify_capture(snapshot, Control())
    verify_sources(snapshot, Control())


def test_schema_evolution_exact_union_and_incompatible_types(tmp_path):
    root = tmp_path / "parts"
    root.mkdir()
    pq.write_table(
        pa.table({"x": pa.array([2**64 - 1], type=pa.uint64())}), root / "a.parquet"
    )
    pq.write_table(
        pa.table({"x": pa.array([-1], type=pa.int64()), "extra": ["new"]}),
        root / "b.parquet",
    )
    work = tmp_path / "work"
    work.mkdir()
    snapshot = captured(root, work)
    adapter, spec = get_adapter("parquet_dataset"), settings("parquet_dataset")
    blocked = adapter.preview(snapshot, spec)
    assert not blocked["importable"] and blocked["diagnostics"]["schema_blocked"]
    spec = replace(spec, schema_policy="union")
    preview = adapter.preview(snapshot, spec)
    assert (
        preview["importable"]
        and preview["schema"]["types"][0] == "Decimal(precision=20, scale=0)"
    )
    result = adapter.import_data(snapshot, spec, work, Control())
    frame = pl.read_parquet(result["path"])
    assert frame["x"].to_list() == [Decimal(2**64 - 1), Decimal(-1)]
    assert frame["extra"].to_list() == [None, "new"]
    (root / "b.parquet").write_bytes((root / "a.parquet").read_bytes())
    with pytest.raises(ProjectError, match="değişti"):
        verify_sources(snapshot, Control())
    pq.write_table(pa.table({"x": ["text"]}), root / "b.parquet")
    snapshot = captured(root, work)
    assert not adapter.preview(snapshot, spec)["importable"]
    with pytest.raises(ProjectError, match="çatışması"):
        adapter.import_data(snapshot, spec, work, Control())


@pytest.mark.parametrize("name", ["../bad.csv", "/bad.csv", "a\\bad.csv", "C:bad.csv"])
def test_archive_member_paths_rejected(tmp_path, name):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(name, "x\n1\n")
    with pytest.raises(ProjectError, match="yolu"):
        captured(path, tmp_path)


def test_compression_bounds_source_changes_and_cancel(tmp_path):
    path = tmp_path / "sample.xml.gz"
    with gzip.open(path, "wb") as output:
        output.write(b"<root><record><x>001</x></record></root>")
    snapshot = captured(path, tmp_path)
    assert detect(snapshot) == "xml"
    assert get_adapter("xml").preview(snapshot, settings("xml"))["rows"] == [["001"]]
    path.write_bytes(b"changed")
    with pytest.raises(ProjectError, match="değişti"):
        verify_sources(snapshot, Control())
    stop = threading.Event()
    stop.set()
    with pytest.raises(Canceled):
        get_adapter("xml").preview(snapshot, settings("xml"), Control(stop))


def test_xml_entities_hdf_links_large_preview_and_row_limit(tmp_path):
    import h5py

    malicious = tmp_path / "evil.xml"
    malicious.write_text(
        '<!DOCTYPE root [<!ENTITY x SYSTEM "file:///etc/passwd">]><root><record><x>&x;</x></record></root>'
    )
    snapshot = captured(malicious, tmp_path)
    with pytest.raises(Exception, match="DTDForbidden|EntitiesForbidden"):
        get_adapter("xml").preview(snapshot, settings("xml"))
    path = tmp_path / "links.h5"
    with h5py.File(path, "w") as file:
        file["remote"] = h5py.ExternalLink("/etc/passwd", "data")
    snapshot = captured(path, tmp_path)
    with pytest.raises(ProjectError, match="link"):
        get_adapter("hdf5").inspect(snapshot, settings("hdf5"), Control())
    large = tmp_path / "large.xml"
    large.write_text("<root>" + "<record><x>001</x></record>" * 10005 + "</root>")
    snapshot = captured(large, tmp_path)
    preview = get_adapter("xml").preview(snapshot, settings("xml"))
    assert preview["examined"] == 200 and preview["limited"]
    with pytest.raises(ProjectError, match="satır sınırı"):
        get_adapter("xml").import_data(
            snapshot, replace(settings("xml"), max_rows=10000), tmp_path, Control()
        )


def test_archive_duplicates_links_expansion_and_decoded_budget(tmp_path):
    import stat

    from veri_ufku.domain.contracts import ComputeBudget

    path = tmp_path / "bad.zip"
    info = zipfile.ZipInfo("alias.csv")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(info, "/etc/passwd")
    with pytest.raises(ProjectError, match="link"):
        captured(path, tmp_path)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("x.csv", "x\n1\n")
        with pytest.warns(UserWarning):
            archive.writestr("x.csv", "x\n2\n")
    with pytest.raises(ProjectError, match="yinelenen"):
        captured(path, tmp_path)
    path = tmp_path / "bomb.xml.gz"
    with gzip.open(path, "wb") as stream:
        stream.write(b"x" * 100000)
    with pytest.raises(ProjectError, match="boyutu"):
        captured(
            path,
            tmp_path,
            Control(budget=replace(ComputeBudget(), temp_disk_bytes=65536)),
        )


def test_unsupported_types_and_xml_content_are_rejected(tmp_path):
    root = tmp_path / "parts"
    root.mkdir()
    pq.write_table(
        pa.table({"x": pa.array([Decimal("1")], type=pa.decimal256(50, 0))}),
        root / "a.parquet",
    )
    work = tmp_path / "work"
    work.mkdir()
    snapshot = captured(root, work)
    with pytest.raises(ProjectError, match="Decimal"):
        get_adapter("parquet_dataset").preview(snapshot, settings("parquet_dataset"))
    path = tmp_path / "mixed.xml"
    path.write_text("<root><record>before<x>1</x>after</record></root>")
    with pytest.raises(ProjectError, match="mixed-content"):
        get_adapter("xml").preview(captured(path, work), settings("xml"))
    path.write_text("<root><record><x>1</x><x>2</x></record></root>")
    with pytest.raises(ProjectError, match="tekrar"):
        get_adapter("xml").preview(captured(path, work), settings("xml"))


def test_nested_schema_evolution_timezone_conflict_and_no_float_promotion(tmp_path):
    root, work = tmp_path / "parts", tmp_path / "work"
    root.mkdir()
    work.mkdir()
    pq.write_table(
        pa.table({"s": pa.array([dict(a=1)], type=pa.struct([("a", pa.int32())]))}),
        root / "a.parquet",
    )
    pq.write_table(
        pa.table(
            {
                "s": pa.array(
                    [dict(a=2, b="new")],
                    type=pa.struct([("a", pa.int64()), ("b", pa.string())]),
                )
            }
        ),
        root / "b.parquet",
    )
    adapter, spec = (
        get_adapter("parquet_dataset"),
        replace(settings("parquet_dataset"), schema_policy="union"),
    )
    result = adapter.import_data(captured(root, work), spec, work, Control())
    assert pl.read_parquet(result["path"])["s"].to_list() == [
        dict(a=1, b=None),
        dict(a=2, b="new"),
    ]
    for left, right in (
        (pa.int64(), pa.float64()),
        (pa.timestamp("ns", "UTC"), pa.timestamp("ns", "Europe/Istanbul")),
    ):
        pq.write_table(pa.table({"x": pa.array([1], type=left)}), root / "a.parquet")
        pq.write_table(pa.table({"x": pa.array([1], type=right)}), root / "b.parquet")
        assert not adapter.preview(captured(root, work), spec)["importable"]


def test_sas_numeric_dates_and_hdf_enum_metadata(tmp_path):
    from pathlib import Path

    import h5py
    import numpy as np

    work = tmp_path / "work"
    work.mkdir()
    source = Path(__file__).parent / "fixtures/phase30/sample.sas7bdat"
    result = get_adapter("sas").import_data(
        captured(source, work), settings("sas"), work, Control()
    )
    frame = pl.read_parquet(result["path"])
    assert frame["mydate"].to_list() == [21310.0, -29093.0, 0.0, -137696.0, None]
    assert (
        result["settings"]["format_metadata"]["parts"][0]["original_variable_types"][
            "mydate"
        ]
        == "YYMMDD10"
    )
    source = tmp_path / "enum.h5"
    dt = np.dtype([("category", h5py.enum_dtype({"LOW": 1, "HIGH": 2}, basetype="u1"))])
    with h5py.File(source, "w") as file:
        file.create_dataset("table", data=np.array([(1,), (2,)], dtype=dt))
    result = get_adapter("hdf5").import_data(
        captured(source, work),
        replace(settings("hdf5"), sheet="/table"),
        work,
        Control(),
    )
    assert result["settings"]["format_metadata"]["parts"][0]["enums"] == dict(
        category=dict(HIGH=2, LOW=1)
    )
    assert pl.read_parquet(result["path"])["category"].to_list() == [1, 2]


def test_publication_changed_source_preserves_previous_commit(tmp_path):
    source = fixture(tmp_path, "xml")
    work = tmp_path / "work"
    work.mkdir()
    result = get_adapter("xml").import_data(
        captured(source, work), settings("xml"), work, Control()
    )
    store = ProjectStore.create(tmp_path / "project")
    before = store.commit_id
    source.write_text("<root><record><x>changed</x></record></root>")
    try:
        with pytest.raises(ProjectError, match="değişti"):
            store.publish_import(result)
        assert store.commit_id == before and not store.state["datasets"]
    finally:
        store.close()


def test_stata_character_missing_preserves_blank_and_source_semantics(tmp_path):
    import pandas as pd
    import pyreadstat

    source = tmp_path / "blank.dta"
    pyreadstat.write_dta(pd.DataFrame(dict(name=["Çağrı", ""])), source)
    work = tmp_path / "work"
    work.mkdir()
    result = get_adapter("stata").import_data(
        captured(source, work), settings("stata"), work, Control()
    )
    frame = pl.read_parquet(result["path"])
    assert frame["name"].to_list() == ["Çağrı", ""]
    assert json.loads(frame["__vu_expansion_index"][1]) == {
        "system_missing": {"name": "blank"}
    }
