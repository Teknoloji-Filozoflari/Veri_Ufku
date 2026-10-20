"""Real backend read witness, extra dimensions and conservative rejection."""

import json
from contextlib import closing
from dataclasses import replace

import h5py
import numpy as np
import polars as pl
import pytest
import xarray as xr
from phase34_fixtures import fixture
from test_arrays import captured, spec
from test_dataset import column, prepare

from veri_ufku.charts.contracts import ChartSpec
from veri_ufku.charts.engine import calculate
from veri_ufku.importers.arrays import check_zarr_storage, inspect
from veri_ufku.importers.delimited import Control
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import get_adapter
from veri_ufku.storage.project_model import ProjectError


def test_zarr_backend_lazy_selection(tmp_path, monkeypatch):
    from xarray.backends.zarr import ZarrArrayWrapper

    source, _ = fixture(tmp_path, "zarr", shape=(12, 13, 14))
    snapshot = captured(source, tmp_path / "work")
    original = ZarrArrayWrapper._getitem
    reads = []

    def spy(wrapper, key):
        if wrapper.shape == (12, 13, 14):
            reads.append(key)
            assert key[0] == 1 and key[1] in (1, 2)
        return original(wrapper, key)

    monkeypatch.setattr(ZarrArrayWrapper, "_getitem", spy)
    result = get_adapter("zarr").preview(snapshot, spec("zarr"), Control())
    assert result["examined"] == 4 and reads


@pytest.mark.parametrize("adapter", ("netcdf", "zarr"))
def test_five_dimensions_auxiliary_coordinates_and_channel_ensemble(tmp_path, adapter):
    shape = (2, 2, 2, 3, 4)
    values = np.arange(np.prod(shape)).reshape(shape)
    dims = ("ensemble", "channel", "time", "latitude", "longitude")
    ds = xr.Dataset(
        {
            "measurement": (dims, values, dict(units="meter", coordinates="height")),
            "height": (("latitude", "longitude"), np.arange(12).reshape(3, 4)),
        },
        coords={d: np.arange(n) for d, n in zip(dims, shape, strict=True)},
    )
    source = tmp_path / ("five.nc" if adapter == "netcdf" else "five.zarr")
    if adapter == "netcdf":
        ds.to_netcdf(source, engine="h5netcdf")
    else:
        ds.to_zarr(source, mode="w", zarr_format=3, consolidated=False)
    work = tmp_path / "work"
    snapshot = captured(source, work)
    settings = StructuredSettings(
        adapter_id=adapter,
        array_variable="measurement",
        array_slice=dict(ensemble=1, channel=0, time=1),
    )
    result = get_adapter(adapter).import_data(snapshot, settings, work, Control())
    frame = pl.read_parquet(result["path"])
    assert frame["value"].to_list() == values[1, 0, 1].reshape(-1).tolist()
    assert frame["ensemble"].to_list() == [1] * 12
    assert frame["channel"].to_list() == [0] * 12
    assert frame["height"].to_list() == list(range(12))
    assert result["settings"]["format_metadata"]["parts"][0]["multidimensional"][
        "dimensions"
    ] == list(dims)


def test_unknown_unit_and_bad_selection_rejected(tmp_path):
    source, _ = fixture(tmp_path, "netcdf")
    snapshot = captured(source, tmp_path / "work")
    for selectors in (
        dict(time=-1),
        dict(time=[0, 100, 1]),
        dict(time=[0, 1, 0]),
        dict(person=0),
    ):
        with pytest.raises(ProjectError):
            get_adapter("netcdf").preview(
                snapshot, replace(spec("netcdf"), array_slice=selectors), Control()
            )
    with pytest.raises(ProjectError, match="Birim"):
        get_adapter("netcdf").preview(
            snapshot, spec("netcdf", array_decode=True, array_unit="meter"), Control()
        )
    with pytest.raises(ProjectError, match="fill/scale"):
        get_adapter("netcdf").preview(
            snapshot, spec("netcdf", array_unit="kelvin"), Control()
        )


def test_plain_table_cannot_claim_array_plot(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame(dict(latitude=[1, 2], value=[3, 4]))
    )
    with closing(store), pytest.raises(ProjectError, match="tensor"):
        calculate(
            request,
            ChartSpec(
                "array-profile",
                x=column(request, "latitude"),
                y=column(request, "value"),
            ),
            work,
        )


def test_hdf_external_and_zarr_pickle_and_source_changes(tmp_path):
    source, _ = fixture(tmp_path, "hdf5_array")
    with h5py.File(source, "a") as file:
        file["remote"] = h5py.ExternalLink("other.h5", "/x")
    with pytest.raises(ProjectError, match="link"):
        inspect(source, spec("hdf5_array"), Control())
    zroot = tmp_path / "hostile.zarr"
    zroot.mkdir()
    (zroot / ".zarray").write_text(json.dumps(dict(filters=[dict(id="pickle")])))
    with pytest.raises(ProjectError, match="pickle"):
        check_zarr_storage(zroot)
    source, _ = fixture(tmp_path, "netcdf")
    snapshot = captured(source, tmp_path / "work")
    with source.open("ab") as output:
        output.write(b"changed")
    with pytest.raises(ProjectError, match="değişti"):
        get_adapter("netcdf").preview(snapshot, spec("netcdf"), Control())
