"""Separate bounded vector and GeoTIFF readers, local captured inputs only."""

import json
import os
import sqlite3
from importlib.metadata import version
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import rasterio
import shapely
from rasterio.windows import Window

from veri_ufku.geo import FORMATS as FORMATS
from veri_ufku.geo.core import crs, inspect
from veri_ufku.storage.project_model import ProjectError

MAX_FEATURES = 10000


def source_path(snapshot):
    members = snapshot.get("members", [])
    if not members:
        original = Path(snapshot["original"]).suffix.lower()
        if original in (".gpkg", ".geojson"):
            src = Path(snapshot["path"])
            target = src.with_suffix(original)
            if not target.exists():
                os.link(src, target)
            elif target.is_symlink() or not os.path.samefile(src, target):
                raise ProjectError("Captured vector alias changed.")
            return str(target)
        return snapshot["path"]
    shapes = [m for m in members if Path(m["name"]).suffix.lower() == ".shp"]
    if len(shapes) != 1:
        raise ProjectError("Shapefile arşivi tek .shp/.shx/.dbf takımı içermeli.")
    stem = Path(shapes[0]["name"]).stem
    required = {".shp", ".shx", ".dbf"}
    if not required <= {
        Path(m["name"]).suffix.lower() for m in members if Path(m["name"]).stem == stem
    }:
        raise ProjectError("Shapefile .shp/.shx/.dbf bileşenleri eksik.")
    root = Path(snapshot["path"]).with_suffix(".shape-capture")
    root.mkdir(exist_ok=True, mode=0o700)
    for m in members:
        name = Path(m["name"])
        if (
            name.name != m["name"]
            or name.stem != stem
            or name.suffix.lower() not in (".shp", ".shx", ".dbf", ".prj", ".cpg")
        ):
            raise ProjectError("Shapefile bileşen adı/formatı desteklenmiyor.")
        dest = root / name.name
        if not dest.exists():
            dest.write_bytes(Path(m["path"]).read_bytes())
    return str(root / Path(shapes[0]["name"]).name)


def source_guard(path, settings):
    with Path(path).open("rb") as file:
        magic = file.read(16)
    kind = settings.adapter_id
    if kind == "geojson":
        try:
            doc = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as error:
            raise ProjectError("GeoJSON JSON çözümlenemedi.") from error
        if (
            not isinstance(doc, dict)
            or doc.get("type") != "FeatureCollection"
            or not isinstance(doc.get("features"), list)
            or len(doc["features"]) > MAX_FEATURES
        ):
            raise ProjectError(
                "GeoJSON bounded FeatureCollection ister; external URI/document desteklenmez."
            )
    elif kind == "geopackage":
        if not magic.startswith(b"SQLite format 3"):
            raise ProjectError("GeoPackage magic uyuşmuyor.")
        uri = "file:" + quote(str(Path(path).resolve())) + "?mode=ro&immutable=1"
        with sqlite3.connect(uri, uri=True) as db:
            db.execute("PRAGMA query_only=ON")
            try:
                layers = db.execute(
                    "SELECT table_name FROM gpkg_contents WHERE data_type='features'"
                ).fetchall()
            except sqlite3.DatabaseError as error:
                raise ProjectError("GeoPackage feature metadata eksik.") from error
            for (layer,) in layers:
                entry = db.execute(
                    "SELECT type,sql FROM sqlite_master WHERE name=?", (layer,)
                ).fetchone()
                if (
                    not entry
                    or entry[0] != "table"
                    or "VIRTUAL TABLE" in (entry[1] or "").upper()
                ):
                    raise ProjectError(
                        "GeoPackage feature yalnız ordinary table; view/virtual/external ret."
                    )
            if settings.sheet and settings.sheet not in [n for (n,) in layers]:
                raise ProjectError("GeoPackage ordinary feature layer seçin.")
    elif kind == "shapefile" and magic[:4] != b"\x00\x00\x27\x0a":
        raise ProjectError("Shapefile magic uyuşmuyor.")
    elif kind == "geoparquet" and not magic.startswith(b"PAR1"):
        raise ProjectError("GeoParquet magic uyuşmuyor.")


def vector(path, settings, control):
    control.check()
    if Path(path).stat().st_size > min(256 * 1024**2, control.budget.ram_bytes // 4):
        raise ProjectError("Vektör kaynak boyutu admission sınırını aştı.")
    source_guard(path, settings)
    if settings.adapter_id == "geoparquet":
        file = pq.ParquetFile(path)
        if file.metadata.num_rows > MAX_FEATURES:
            raise ProjectError("Vektör10000 feature sınırı; açık dış kesit gerekir.")
        try:
            geo = json.loads(file.schema_arrow.metadata[b"geo"])
            name = settings.geo_geometry or geo["primary_column"]
            column = geo["columns"][name]
        except Exception as error:
            raise ProjectError(
                "GeoParquet geo metadata/geometry column eksik."
            ) from error
        if (
            geo.get("version") not in ("1.0.0", "1.1.0")
            or column.get("edges", "planar") != "planar"
        ):
            raise ProjectError(
                "GeoParquet 1.0/1.1 planar edges gerekir; spherical geometri desteklenmez."
            )
        if column.get("encoding") != "WKB":
            raise ProjectError("GeoParquet yalnız WKB encoding desteklenir.")
        system = column.get("crs", "OGC:CRS84")
        table = file.read()
        gs = shapely.from_wkb(table[name].to_pylist())
        metadata = dict(
            geoparquet=geo,
            source_geometry_column=name,
            source_ids=list(range(len(table))),
        )
    else:
        info = pyogrio.read_info(path, layer=settings.sheet or None)
        expected = {
            "geojson": "GeoJSON",
            "geopackage": "GPKG",
            "shapefile": "ESRI Shapefile",
        }[settings.adapter_id]
        if info["driver"] != expected:
            raise ProjectError("Seçilen vektör driver kaynakla uyuşmuyor.")
        if info["features"] > MAX_FEATURES:
            raise ProjectError("Vektör10000 feature sınırı aşıldı.")
        meta, table = pyogrio.read_arrow(
            path,
            layer=settings.sheet or None,
            max_features=MAX_FEATURES + 1,
            return_fids=True,
        )
        if len(table) > MAX_FEATURES:
            raise ProjectError("Vektör10000 feature sınırı aşıldı.")
        name = meta["geometry_name"] or "wkb_geometry"
        if name not in table.column_names:
            raise ProjectError("Vektör geometri alanı yok.")
        system = meta.get("crs")
        gs = shapely.from_wkb(table[name].to_pylist())
        fid = meta.get("fid_column")
        metadata = dict(
            driver=expected,
            source_geometry_column=name,
            source_ids=table[fid].to_pylist()
            if fid and fid in table.column_names
            else list(range(len(table))),
            layer=settings.sheet or None,
        )
        if settings.adapter_id == "geojson":
            system = system or "OGC:CRS84"
    if not system:
        system = settings.geo_crs or None
    if system:
        system = crs(system).to_wkt()
    fields = [n for n in table.column_names if n != name]
    if "geometry" in fields:
        raise ProjectError("geometry adı kaynak attribute ile çakışıyor.")
    table = table.select(fields).append_column(
        "geometry",
        pa.array(shapely.to_wkt(gs, rounding_precision=-1).tolist(), type=pa.string()),
    )
    metadata.update(
        inspect(table["geometry"].to_pylist(), system),
        feature_count=len(table),
        versions={n: version(n) for n in ("shapely", "pyproj", "pyogrio")},
        source_encoding="WKB/driver geometry → lossless coordinate WKT; explicit representation, no repair/reprojection",
    )
    control.check()
    if table.nbytes > control.budget.ram_bytes // 4:
        raise ProjectError("Decoded vektör RAM sınırı.")
    return table, metadata


def raster(path, settings, control, decode=True):
    control.check()
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        GDAL_PAM_ENABLED="NO",
        PROJ_NETWORK="OFF",
    ):
        with rasterio.open(path, "r", driver="GTiff") as ds:
            if ds.driver != "GTiff" or any(
                Path(p).resolve() != Path(path).resolve() for p in ds.files
            ):
                raise ProjectError(
                    "Raster yalnız self-contained GeoTIFF; dış sidecar desteklenmez."
                )
            band = settings.geo_band
            if not 1 <= band <= ds.count:
                raise ProjectError("Raster band sınır dışında.")
            window = settings.geo_window or [
                0,
                0,
                min(128, ds.width),
                min(128, ds.height),
            ]
            if len(window) != 4 or any(type(v) is not int for v in window):
                raise ProjectError(
                    "Raster window [col,row,width,height] tam sayılar ister."
                )
            col, row, w, h = window
            if (
                min(col, row) < 0
                or min(w, h) < 1
                or col + w > ds.width
                or row + h > ds.height
            ):
                raise ProjectError("Raster kesit sınır dışında.")
            if w * h > 65536 or w * h * 160 > control.budget.ram_bytes // 4:
                raise ProjectError(
                    "Raster kesit65536 hücre/RAM sınırını aştı; tüm raster açılmadı."
                )
            blocks = ds.block_shapes
            if (
                max(
                    a * b * np.dtype(ds.dtypes[i]).itemsize
                    for i, (a, b) in enumerate(blocks)
                )
                > control.budget.ram_bytes // 4
            ):
                raise ProjectError("Raster tek decoded block RAM sınırını aşıyor.")
            system = ds.crs.to_wkt() if ds.crs else settings.geo_crs or None
            if system:
                system = crs(system).to_wkt()
            bounds = ds.window_bounds(Window(*window))
            metadata = dict(
                crs=system,
                authority=crs(system).to_string() if system else None,
                axis_order="x,y; pixel center",
                geometry_types={},
                extent=list(bounds),
                full_extent=list(ds.bounds),
                nodata=str(ds.nodata) if ds.nodata is not None else None,
                invalid=[],
                invalid_count=0,
                width=ds.width,
                height=ds.height,
                bands=ds.count,
                band=band,
                window=window,
                transform=list(ds.transform),
                block_shapes=[list(x) for x in blocks],
                unit=ds.units[band - 1],
                tags=ds.tags(),
                cost=dict(
                    cells=w * h,
                    full_cells=ds.width * ds.height,
                    bytes=w * h * np.dtype(ds.dtypes[band - 1]).itemsize,
                    block_read_notice="Window reads intersecting blocks; not guaranteed exact byte IO.",
                ),
                raster=True,
                versions={n: version(n) for n in ("rasterio", "pyproj")},
            )
            schema = pa.schema(
                [
                    ("x", pa.float64()),
                    ("y", pa.float64()),
                    ("value", pa.float64()),
                    ("raster_row", pa.int64()),
                    ("raster_col", pa.int64()),
                ]
            )
            if not decode:
                return schema, metadata
            if ds.dtypes[band - 1] in ("int64", "uint64"):
                raise ProjectError(
                    "64-bit integer raster Float64 tabloya sessizce dönüştürülmez: precision kaybı olabilir; bu dtype desteklenmiyor. Kaynak korunur."
                )
            if np.dtype(ds.dtypes[band - 1]).kind == "c":
                raise ProjectError(
                    "complex raster Float64 tabloya dönüştürülemez; sanal bileşen kaybına izin verilmez. Kaynak korunur."
                )
            data = ds.read(band, window=Window(*window), masked=True)
            rows, cols = np.meshgrid(
                np.arange(row, row + h), np.arange(col, col + w), indexing="ij"
            )
            xs, ys = rasterio.transform.xy(
                ds.transform, rows.ravel(), cols.ravel(), offset="center"
            )
            raw = data.astype(float).ravel()
            mask = np.ma.getmaskarray(data).ravel() | ~np.isfinite(raw.data)
            table = pa.Table.from_arrays(
                [
                    pa.array(np.asarray(xs).ravel()),
                    pa.array(np.asarray(ys).ravel()),
                    pa.array(raw.data, mask=mask),
                    pa.array(rows.ravel()),
                    pa.array(cols.ravel()),
                ],
                schema=schema,
            )
            metadata["nodata_cells"] = int(mask.sum())
            control.check()
            return table, metadata


def read(path, settings, control):
    return (
        raster(path, settings, control)
        if settings.adapter_id == "geotiff"
        else vector(path, settings, control)
    )


def info(path, settings, control):
    if settings.adapter_id == "geotiff":
        return raster(path, settings, control, False)
    table, metadata = vector(path, settings, control)
    return table.schema, metadata


def batches(path, settings, control):
    table, _ = read(path, settings, control)
    for batch in table.to_batches(max_chunksize=1024):
        control.check()
        yield pa.Table.from_batches([batch]), [{} for _ in range(len(batch))]


def choices(path, settings, control):
    _, metadata = info(path, settings, control)
    layers = (
        [str(x[0]) for x in pyogrio.list_layers(path)]
        if settings.adapter_id == "geopackage"
        else []
    )
    return dict(
        sheets=layers,
        geospatial=metadata,
        format_notice="Yerel/read-only capture; WKT representation; kaynak kimlik/bytes korunur. CRS atama reproject değildir. Raster açık window; ağ yok.",
    )
