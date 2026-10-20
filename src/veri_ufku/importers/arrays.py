"""Local, read-only multidimensional sources; metadata precedes bounded decoding.

No pandas cartesian expansion and no implicit dimension inference from tables.
Time is deliberately kept in its encoded CF calendar/units representation.
"""

import itertools
import json
import math
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

import numpy as np
import pyarrow as pa

from veri_ufku.importers.advanced_readers import hdf_keys, json_safe
from veri_ufku.packaging.optional import LazyModule
from veri_ufku.storage.project_model import ProjectError

h5py = LazyModule("h5py", "arrays")
xr = LazyModule("xarray", "arrays")

ARRAY_FORMATS = ("netcdf", "zarr", "hdf5_array")
MAX_CHUNK = 16 * 1024**2


@lru_cache(maxsize=1)
def units():
    from pint import UnitRegistry

    return UnitRegistry(autoconvert_offset_to_baseunit=False)


def convert_units(values, source, target):
    """Pint Quantity constructor handles affine absolute temperature correctly."""
    try:
        return units().Quantity(values, source).to(target).magnitude
    except Exception as error:
        raise ProjectError("Birim bilinmiyor veya boyutlar uyuşmuyor.") from error


def dtype_for(dtype):
    dtype = np.dtype(dtype)
    if dtype.kind not in "biufSU" or dtype.names or dtype.subdtype:
        raise ProjectError("Array yalnız skaler sayı/bool/sabit metin destekler.")
    return pa.string() if dtype.kind == "U" else pa.from_numpy_dtype(dtype)


def attrs(value):
    # HDF structural references are not scalar CF metadata; dimensions are
    # recorded separately, without serializing opaque pointers.
    return json_safe(
        {
            k: v.tolist() if isinstance(v, np.ndarray) else v
            for k, v in value.items()
            if k not in ("DIMENSION_LIST", "REFERENCE_LIST")
        }
    )


@contextmanager
def opened(path, adapter, control):
    path = Path(path)
    if path.is_symlink() or not path.exists():
        raise ProjectError("Array kaynağı yerel ve gerçek dosya/klasör olmalı.")
    if adapter == "hdf5_array":
        hdf_keys(path, control)  # Reject links, virtual and external storage.
        with h5py.File(path, "r") as file:
            check_hdf_storage(file)
            yield file
        return
    options = dict(
        chunks=None,
        decode_cf=False,
        decode_times=False,
        mask_and_scale=False,
        create_default_indexes=False,
    )
    if adapter == "zarr":
        check_zarr_storage(path)
        dataset = xr.open_zarr(str(path), consolidated=False, **options)
    else:
        with path.open("rb") as stream:
            magic = stream.read(8)
        engine = "scipy" if magic.startswith(b"CDF") else "h5netcdf"
        if engine == "h5netcdf":
            hdf_keys(path, control)
            with h5py.File(path, "r") as file:
                check_hdf_storage(file)
        dataset = xr.open_dataset(path, engine=engine, cache=False, **options)
    try:
        if len(dataset.variables) > 256:
            raise ProjectError("Array değişken sayısı256 sınırını aştı.")
        yield dataset
    finally:
        dataset.close()


def check_hdf_storage(file):
    def check(name, obj):
        if not isinstance(obj, h5py.Dataset):
            return
        plist = obj.id.get_create_plist()
        if any(
            plist.get_filter(i)[0] not in (1, 2, 3) for i in range(plist.get_nfilters())
        ):
            raise ProjectError("HDF5 özel filtre/plugin desteklenmez.")
        if obj.chunks and math.prod(obj.chunks) * obj.dtype.itemsize > MAX_CHUNK:
            raise ProjectError("Array tek chunk16MiB sınırını aştı.")

    file.visititems(check)


def check_zarr_storage(path):
    allowed = {"blosc", "zstd", "gzip", "bytes", "crc32c", "transpose", "shuffle"}
    for metadata in path.rglob("*"):
        if metadata.is_symlink():
            raise ProjectError("Zarr symlink desteklenmez.")
        if metadata.name not in (".zarray", ".zattrs", ".zgroup", "zarr.json"):
            continue
        if metadata.stat().st_size > 262144:
            raise ProjectError("Zarr metadata256KiB sınırını aştı.")
        item = json.loads(metadata.read_text())
        codecs = item.get("codecs", []) + (item.get("filters") or [])
        if item.get("compressor"):
            codecs.append(item["compressor"])
        if any(c.get("name", c.get("id")) not in allowed for c in codecs):
            raise ProjectError("Zarr özel codec/object/pickle desteklenmez.")
        chunks = item.get("chunks") or item.get("chunk_grid", {}).get(
            "configuration", {}
        ).get("chunk_shape")
        if chunks and (
            len(chunks) > 8
            or any(type(n) is not int or n < 1 for n in chunks)
            or math.prod(chunks) * 8 > MAX_CHUNK
        ):
            raise ProjectError("Zarr chunk16MiB veya8 boyut sınırını aştı.")


def hdf_variables(file):
    result = {}
    file.visititems(
        lambda name, obj: (
            result.update({"/" + name: obj})
            if isinstance(obj, h5py.Dataset) and obj.ndim >= 1
            else None
        )
    )
    return result


def description(file, adapter, variable):
    if adapter == "hdf5_array":
        var = hdf_variables(file).get(variable)
        if var is None:
            raise ProjectError("Array değişkenini açıkça seçin.")
        dims, coordinates = [], {}
        for i, dim in enumerate(var.dims):
            scales = list(dim.values())
            if len(scales) != 1:
                raise ProjectError("HDF5 her eksende tek açık dimension scale ister.")
            scale = scales[0]
            name = dim.label or scale.name.rsplit("/", 1)[-1]
            if scale.ndim != 1 or len(scale) != var.shape[i] or name in dims:
                raise ProjectError("HDF5 dimension scale uzunluğu/adı geçersiz.")
            dims.append(name)
            coordinates[name] = scale
        metadata = dict(root_attributes=attrs(file.attrs))
        chunks = var.chunks
        for obj in (var, *coordinates.values()):
            plist = obj.id.get_create_plist()
            if any(
                plist.get_filter(i)[0] not in (1, 2, 3)
                for i in range(plist.get_nfilters())
            ):
                raise ProjectError("HDF5 özel filtre/plugin desteklenmez.")
        coord_dims = {name: (name,) for name in coordinates}
    else:
        if variable not in file.data_vars:
            raise ProjectError("Array ölçüm değişkenini açıkça seçin.")
        var = file[variable]
        dims = list(var.dims)
        # decode_cf=False intentionally leaves auxiliary coordinates as variables.
        coord_names = set(dims) | set(str(var.attrs.get("coordinates", "")).split())
        coordinates = {
            n: file[n]
            for n in sorted(coord_names)
            if n in file and set(file[n].dims) <= set(dims)
        }
        coord_dims = {name: tuple(obj.dims) for name, obj in coordinates.items()}
        metadata = dict(root_attributes=attrs(file.attrs))
        chunks = var.encoding.get("chunksizes") or var.encoding.get("chunks")
    if not 1 <= len(dims) <= 8 or any(n.startswith("__vu_") for n in dims):
        raise ProjectError("Array1–8 açık boyut ister; ayrılmış ad kullanılamaz.")
    dtype_for(var.dtype)
    if chunks and math.prod(chunks) * var.dtype.itemsize > MAX_CHUNK:
        raise ProjectError("Array tek chunk16MiB sınırını aştı.")
    for name, obj in coordinates.items():
        dtype_for(obj.dtype)
        if name.startswith("__vu_"):
            raise ProjectError("Koordinat ayrılmış sütun adı kullanıyor.")
    metadata.update(
        schema_version=1,
        origin="verified-array-adapter",
        adapter=adapter,
        variable=variable,
        dimensions=dims,
        shape=list(var.shape),
        dtype=str(var.dtype),
        attributes=attrs(var.attrs),
        chunk_layout=list(chunks) if chunks else None,
        coordinates={
            name: dict(
                dimensions=list(coord_dims[name]),
                shape=list(obj.shape),
                dtype=str(obj.dtype),
                attributes=attrs(obj.attrs),
            )
            for name, obj in coordinates.items()
        },
        time_policy="raw CF value + units/calendar; no Gregorian assumption",
        fill_policy="raw values retained; explicit decode only",
    )
    return var, dims, coordinates, coord_dims, metadata


def selection(shape, dims, selectors):
    if set(selectors) - set(dims):
        raise ProjectError("Kesit bilinmeyen boyut içeriyor.")
    result = []
    for dim, length in zip(dims, shape, strict=True):
        value = selectors.get(dim, [0, length, 1])
        if type(value) is int:
            value = [value, value + 1, 1]
        if (
            not isinstance(value, (list, tuple))
            or len(value) != 3
            or any(type(v) is not int for v in value)
        ):
            raise ProjectError("Kesit indeks veya [başlangıç,bitiş,adım] olmalı.")
        start, stop, step = value
        if not 0 <= start < stop <= length or step < 1:
            raise ProjectError("Kesit kaynak boyut sınırlarının dışında.")
        result.append(range(start, stop, step))
    return result


def plan(file, settings, control):
    var, dims, coords, coord_dims, meta = description(
        file, settings.adapter_id, settings.array_variable
    )
    ranges = selection(var.shape, dims, settings.array_slice)
    selected_coords = settings.array_coordinates or tuple(coords)
    if set(selected_coords) - set(coords):
        raise ProjectError("Seçilen koordinat kaynakta yok.")
    count = math.prod(map(len, ranges))
    # Table estimate includes lineage strings, decoded native values and Arrow
    # buffers. It is conservative, not a compressed-file-size prediction.
    row_bytes = (
        512
        + var.dtype.itemsize
        + sum(max(32, coords[n].dtype.itemsize * 4) for n in selected_coords)
    )
    estimated = count * (row_bytes + 16 * len(dims))
    blocked = count > settings.max_rows or estimated > min(
        control.budget.ram_bytes // 4, control.budget.temp_disk_bytes // 2
    )
    fields = [pa.field("index_" + d, pa.int64()) for d in dims]
    fields += [pa.field(n, dtype_for(coords[n].dtype)) for n in selected_coords]
    fields += [
        pa.field(
            "value",
            pa.float64()
            if settings.array_decode or settings.array_unit
            else dtype_for(var.dtype),
        )
    ]
    if len({f.name for f in fields}) != len(fields):
        raise ProjectError("Array koordinat/ölçüm/indeks sütun adı çakışıyor.")
    if settings.array_unit:
        convert_units(
            np.array([0.0, 1.0]), var.attrs.get("units", ""), settings.array_unit
        )
    source_unit = var.attrs.get("units", "")
    try:
        units().Unit(source_unit)
        unit_validation = "validated by Pint" if source_unit else "not declared"
    except Exception:
        unit_validation = "unknown; raw metadata retained; conversion unavailable"
    meta.update(
        selection={
            d: [r.start, r.stop, r.step] for d, r in zip(dims, ranges, strict=True)
        },
        selected_coordinates=list(selected_coords),
        output_unit=settings.array_unit or var.attrs.get("units", ""),
        unit_validation=unit_validation,
        decoded=settings.array_decode,
        aggregation="none",
        cost=dict(
            output_rows=count,
            estimated_bytes=estimated,
            full_tensor_cells=math.prod(var.shape),
            blocked=blocked,
            estimate_policy="decoded values + conservative lineage/buffer overhead",
        ),
    )
    return pa.schema(fields), meta, (var, dims, coords, coord_dims, ranges)


def info(path, settings, control):
    with opened(path, settings.adapter_id, control) as file:
        schema, meta, _ = plan(file, settings, control)
        return schema, {"multidimensional": meta}


def inspect(path, settings, control):
    with opened(path, settings.adapter_id, control) as file:
        variables = (
            hdf_variables(file)
            if settings.adapter_id == "hdf5_array"
            else file.data_vars
        )
        return dict(
            array_variables=list(variables),
            format_notice="Boyut/koordinat seçimini ve kesit maliyetini inceleyin. Takvim ham CF değeridir; kaynak değişmez.",
        )


def decoded(values, attributes, settings):
    if not settings.array_decode and not settings.array_unit:
        return values
    if settings.array_unit and not settings.array_decode:
        raise ProjectError("Birim dönüşümü için fill/scale çözümünü açıkça açın.")
    values = np.asarray(values, dtype=float)
    for name in ("_FillValue", "missing_value"):
        for fill in np.atleast_1d(attributes.get(name, [])):
            values = np.where(values == fill, np.nan, values)
    values = values * attributes.get("scale_factor", 1) + attributes.get(
        "add_offset", 0
    )
    if settings.array_unit:
        values = convert_units(values, attributes.get("units", ""), settings.array_unit)
    return values


def batches(path, settings, control):
    with opened(path, settings.adapter_id, control) as file:
        schema, meta, (var, dims, coords, coord_dims, ranges) = plan(
            file, settings, control
        )
        if meta["cost"]["blocked"]:
            raise ProjectError(
                "Array tablo boyutu bütçeyi aşıyor; daha küçük kesit seçin."
            )
        # Read only a bounded contiguous segment of the last dimension. No
        # .values/.load on an unsliced DataArray, including preview.
        for prefix in itertools.product(*ranges[:-1]):
            last = ranges[-1]
            for offset in range(0, len(last), 200):
                control.check()
                indices = last[offset : offset + 200]
                key = prefix + (slice(indices.start, indices.stop, indices.step),)
                values = np.asarray(
                    var[key]
                    if settings.adapter_id == "hdf5_array"
                    else var.isel(dict(zip(dims, key, strict=True))).values
                ).reshape(-1)
                values = decoded(values, var.attrs, settings)
                rows, lineage = [], []
                for j, value in zip(indices, values, strict=True):
                    position = dict(zip(dims, (*prefix, j), strict=True))
                    row = {"index_" + d: position[d] for d in dims}
                    for name in meta["selected_coordinates"]:
                        coord = coords[name]
                        ck = tuple(position[d] for d in coord_dims[name])
                        scalar = (
                            coord[ck]
                            if settings.adapter_id == "hdf5_array"
                            else coord.isel(
                                dict(zip(coord_dims[name], ck, strict=True))
                            ).values
                        )
                        row[name] = np.asarray(scalar).item()
                    row["value"] = value.item() if hasattr(value, "item") else value
                    rows.append(row)
                    lineage.append(
                        {"variable": settings.array_variable, "indices": position}
                    )
                yield pa.Table.from_pylist(rows, schema=schema), lineage
