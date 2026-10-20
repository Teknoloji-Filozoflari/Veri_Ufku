"""Phase34 independent exact values, backend read spy and immutable publication."""

import json
import threading
from dataclasses import replace

import h5py
import numpy as np
import polars as pl
import pytest
from phase34_fixtures import fixture

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.arrays import ARRAY_FORMATS, convert_units
from veri_ufku.importers.delimited import Control
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import detect, get_adapter
from veri_ufku.importers.sources import capture_source, unpack, verify_sources
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def captured(source, workspace):
    workspace.mkdir()
    return unpack(capture_source(source, workspace, Control()), workspace, Control())


def spec(adapter, **kwargs):
    return StructuredSettings(
        adapter_id=adapter,
        array_variable="/temperature" if adapter == "hdf5_array" else "temperature",
        array_slice={"time": 1, "latitude": [1, 3, 1], "longitude": [0, 4, 2]},
        **kwargs,
    )


@pytest.mark.parametrize("adapter", ARRAY_FORMATS)
def test_exact_slice_metadata_roundtrip_and_source_identity(tmp_path, adapter):
    source, values = fixture(tmp_path, adapter)
    work = tmp_path / "work"
    snapshot = captured(source, work)
    assert detect(snapshot) == ("hdf5" if adapter == "hdf5_array" else adapter)
    importer = get_adapter(adapter)
    preview = importer.preview(snapshot, spec(adapter), Control())
    assert preview["importable"] and preview["examined"] == 4
    result = importer.import_data(snapshot, spec(adapter), work, Control())
    frame = pl.read_parquet(result["path"])
    assert frame["value"].to_list() == values[1, 1:3, ::2].reshape(-1).tolist()
    assert frame["time"].to_list() == [1] * 4
    assert frame["latitude"].to_list() == [41.0, 41.0, 42.0, 42.0]
    assert frame["longitude"].to_list() == [20.0, 22.0, 20.0, 22.0]
    lineage = [json.loads(v) for v in frame["__vu_expansion_index"]]
    assert lineage[0]["indices"] == dict(time=1, latitude=1, longitude=0)
    assert frame["__vu_source_record_id"].n_unique() == 4
    metadata = result["settings"]["format_metadata"]["parts"][0]["multidimensional"]
    assert metadata["coordinates"]["time"]["attributes"]["calendar"] == "360_day"
    assert (
        metadata["coordinates"]["time"]["attributes"]["units"]
        == "days since 2000-01-01"
    )
    assert metadata["attributes"]["_FillValue"] == -999
    assert metadata["attributes"]["units"] == "degC"
    assert metadata["chunk_layout"] == [1, 2, 2]
    assert metadata["selection"]["longitude"] == [0, 4, 2]
    assert json.loads(json.dumps(metadata, allow_nan=False)) == metadata
    store = ProjectStore.create(tmp_path / "project", "Array")
    try:
        draft = store.state
        store.publish_import(result, portable=True)
        expected = draft["datasets"][-1]["import_metadata"]["settings"][
            "format_metadata"
        ]
        store.close()
        store = ProjectStore.open(tmp_path / "project")
        assert (
            store.state["datasets"][-1]["import_metadata"]["settings"][
                "format_metadata"
            ]
            == expected
        )
    finally:
        store.close()
    verify_sources(snapshot, Control())


@pytest.mark.parametrize("adapter", ARRAY_FORMATS)
def test_preflight_explosion_reads_no_values(tmp_path, adapter, monkeypatch):
    source, _ = fixture(tmp_path, adapter)
    work = tmp_path / "work"
    snapshot = captured(source, work)
    import veri_ufku.importers.arrays as arrays

    monkeypatch.setattr(
        arrays, "batches", lambda *a: pytest.fail("preflight decoded data")
    )
    selection = replace(spec(adapter), array_slice={}, max_rows=1)
    result = get_adapter(adapter).preview(snapshot, selection, Control())
    assert not result["importable"] and not result["rows"]
    cost = result["settings"]["format_metadata"]["parts"][0]["multidimensional"]["cost"]
    assert cost["output_rows"] == 24 and cost["blocked"]
    assert "24 satır" in result["schema"]["warnings"][-1]
    with pytest.raises(ProjectError):
        get_adapter(adapter).import_data(snapshot, selection, work, Control())


@pytest.mark.parametrize("adapter", ("netcdf", "hdf5_array"))
def test_backend_never_reads_full_tensor(tmp_path, adapter, monkeypatch):
    source, _ = fixture(tmp_path, adapter, shape=(12, 13, 14))
    work = tmp_path / "work"
    snapshot = captured(source, work)
    original = h5py.Dataset.__getitem__
    reads = []

    def spy(dataset, key, *args, **kwargs):
        if dataset.name == "/temperature":
            reads.append(key)
            assert isinstance(key, tuple) and len(key) == 3
            assert key[0] == 1 and key[1] in (1, 2)
        return original(dataset, key, *args, **kwargs)

    monkeypatch.setattr(h5py.Dataset, "__getitem__", spy)
    result = get_adapter(adapter).preview(snapshot, spec(adapter), Control())
    assert result["examined"] == 4 and reads


def test_offset_units_dimension_validation_and_decode(tmp_path):
    assert convert_units(np.array([0.0, 10.0]), "degC", "kelvin").tolist() == [
        273.15,
        283.15,
    ]
    assert convert_units(np.array([32.0, 212.0]), "degF", "degC") == pytest.approx(
        [0.0, 100.0]
    )
    with pytest.raises(ProjectError):
        convert_units(np.array([1.0]), "meter", "second")
    source, values = fixture(tmp_path, "netcdf")
    work = tmp_path / "work"
    snapshot = captured(source, work)
    selection = replace(
        spec("netcdf", array_decode=True, array_unit="kelvin"), array_slice={"time": 0}
    )
    result = get_adapter("netcdf").import_data(snapshot, selection, work, Control())
    actual = np.array(pl.read_parquet(result["path"])["value"])
    assert np.isnan(actual[0])
    assert actual[1:] == pytest.approx(values[0].reshape(-1)[1:] * 0.5 + 10 + 273.15)


def test_cancel_timeout_and_hdf_missing_dimensions(tmp_path):
    source, _ = fixture(tmp_path, "hdf5_array")
    work = tmp_path / "work"
    snapshot = captured(source, work)
    event = threading.Event()
    event.set()
    with pytest.raises(Canceled):
        get_adapter("hdf5_array").preview(snapshot, spec("hdf5_array"), Control(event))
    control = Control(budget=replace(ComputeBudget(), max_wall_seconds=0.001))
    control.started -= 1
    with pytest.raises(ProjectError, match="süre"):
        get_adapter("hdf5_array").preview(snapshot, spec("hdf5_array"), control)
    with h5py.File(source, "a") as file:
        file.create_dataset("ambiguous", data=np.ones((2, 3)))
    with pytest.raises(ProjectError, match="dimension scale"):
        from veri_ufku.importers.arrays import info

        info(
            source, replace(spec("hdf5_array"), array_variable="/ambiguous"), Control()
        )
