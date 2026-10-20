"""CC0 synthetic arrays: native calendar, axes, packing, units and chunks."""

from pathlib import Path

import h5py
import numpy as np
import xarray as xr


def fixture(root, adapter, shape=(2, 3, 4)):
    root = Path(root)
    values = np.arange(np.prod(shape), dtype=np.int16).reshape(shape)
    values[0, 0, 0] = -999
    coordinates = {
        "time": (
            "time",
            np.arange(shape[0], dtype=np.int32),
            dict(units="days since 2000-01-01", calendar="360_day"),
        ),
        "latitude": (
            "latitude",
            np.arange(shape[1], dtype=np.float64) + 40,
            dict(units="degrees_north", standard_name="latitude"),
        ),
        "longitude": (
            "longitude",
            np.arange(shape[2], dtype=np.float64) + 20,
            dict(units="degrees_east", standard_name="longitude"),
        ),
    }
    attributes = dict(
        units="degC",
        _FillValue=-999,
        scale_factor=0.5,
        add_offset=10.0,
        long_name="Synthetic temperature",
    )
    dataset = xr.Dataset(
        {"temperature": (("time", "latitude", "longitude"), values, attributes)},
        coords=coordinates,
        attrs=dict(Conventions="CF-1.12", title="CC0 fixture"),
    )
    if adapter == "netcdf":
        path = root / "cube.nc"
        dataset.to_netcdf(
            path,
            engine="h5netcdf",
            encoding={"temperature": dict(chunksizes=(1, 2, 2))},
        )
    elif adapter == "zarr":
        path = root / "cube.zarr"
        dataset.to_zarr(
            path,
            mode="w",
            zarr_format=2,
            consolidated=False,
            encoding={"temperature": dict(chunks=(1, 2, 2))},
        )
    else:
        path = root / "cube.h5"
        with h5py.File(path, "w") as file:
            file.attrs.update(dataset.attrs)
            var = file.create_dataset("temperature", data=values, chunks=(1, 2, 2))
            var.attrs.update(attributes)
            for axis, (name, (_, data, attrs)) in enumerate(coordinates.items()):
                coord = file.create_dataset(name, data=data)
                coord.attrs.update(attrs)
                coord.make_scale(name)
                var.dims[axis].attach_scale(coord)
                var.dims[axis].label = name
    return path, values
