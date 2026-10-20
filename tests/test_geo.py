"""Spatial reference totals, real format IO, immutable identities and CRS guards."""

import json
import threading
from contextlib import closing
from pathlib import Path

import numpy as np
import polars as pl
import pytest
import shapely
from phase38_fixtures import fixture
from test_dataset import column, prepare

from veri_ufku.charts.contracts import ChartSpec
from veri_ufku.charts.engine import calculate, select
from veri_ufku.charts.export import export
from veri_ufku.charts.plot import render
from veri_ufku.geo.core import crs, geographic_check, geometries, metric, reproject
from veri_ufku.geo.operations import moran
from veri_ufku.geo.readers import FORMATS
from veri_ufku.importers.delimited import Control
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import detect, get_adapter
from veri_ufku.importers.sources import capture_source, unpack, verify_sources
from veri_ufku.jobs.workers import Canceled
from veri_ufku.operations.contracts import build
from veri_ufku.operations.engine import calculate as operate
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import ProjectStore


def captured(tmp, kind, **kwargs):
    source = fixture(tmp, kind, **kwargs)
    work = tmp / "work"
    work.mkdir()
    snap = unpack(capture_source(source, work, Control()), work, Control())
    return source, work, snap


@pytest.mark.parametrize("kind", FORMATS)
def test_real_formats_preview_publication_metadata_source_bytes(tmp_path, kind):
    source, work, snap = captured(tmp_path, kind)
    original = {p: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    assert detect(snap) == kind
    settings = StructuredSettings(
        adapter_id=kind, geo_window=(1, 1, 3, 2) if kind == "geotiff" else ()
    )
    adapter = get_adapter(kind)
    choices = adapter.inspect(snap, settings, Control())
    assert choices["geospatial"]["crs"]
    preview = adapter.preview(snap, settings, Control())
    assert preview["importable"]
    result = adapter.import_data(snap, settings, work, Control())
    data = pl.read_parquet(result["path"])
    meta = result["settings"]["format_metadata"]["parts"][0]["geospatial"]
    if kind == "geotiff":
        assert data["value"].to_list() == [7.0, None, 9.0, 13.0, 14.0, 15.0]
        assert meta["window"] == [1, 1, 3, 2]
        assert meta["unit"] == "kelvin"
        assert data["x"][0] == 500015.0
        assert meta["block_shapes"]
        assert meta["cost"]["full_cells"] == 24
    else:
        assert data["count"].to_list() == [20.0, 40.0, 10.0]
        assert meta["feature_count"] == 3
        assert meta["invalid_count"] == 0
        assert all(g.area == 100 for g in geometries(data["geometry"].to_list()))
    assert data["__vu_row_id"].n_unique() == len(data)
    assert data["__vu_source_record_id"].n_unique() == len(data)
    store = ProjectStore.create(tmp_path / "project", "Geo")
    store.publish_import(result, portable=True)
    store.close()
    store = ProjectStore.open(tmp_path / "project")
    store.close()
    assert all(p.read_bytes() == v for p, v in original.items())


def test_invalid_geometry_panel_no_automatic_repair(tmp_path):
    _, _, snap = captured(tmp_path, "geoparquet", invalid=True)
    adapter = get_adapter("geoparquet")
    settings = StructuredSettings(adapter_id="geoparquet")
    choices = adapter.inspect(snap, settings, Control())
    assert choices["geospatial"]["invalid_count"] == 1
    assert "Self-intersection" in choices["geospatial"]["invalid"][0]["reason"]
    with pytest.raises(ProjectError, match="Geçersiz"):
        geometries(["POLYGON ((0 0,1 1,0 1,1 0,0 0))"])


def test_crs_reference_xy_and_metric_distance():
    gs, details = reproject(
        [shapely.Point(0, 0), shapely.Point(1, 0)], "EPSG:4326", "EPSG:3857"
    )
    assert gs[0].x == 0
    assert gs[1].x == pytest.approx(111319.49079327357)
    assert gs[1].y == 0
    assert details["always_xy"] and not details["network"]
    metric([shapely.Point(500000, 4500000)], crs(32635))
    assert shapely.Point(500000, 4500000).distance(shapely.Point(500003, 4500004)) == 5
    for system in (4326, 3857):
        with pytest.raises(ProjectError, match="projected"):
            metric([shapely.Point(0, 0)], crs(system))
    with pytest.raises(ProjectError, match="kullanım alanı"):
        metric([shapely.Point(0, 0)], crs(32635))
    with pytest.raises(ProjectError, match="Antimeridian"):
        geographic_check([shapely.LineString([(179, 0), (-179, 0)])], crs(4326))
    with pytest.raises(ProjectError, match="eksen"):
        geographic_check([shapely.Point(30, 100)], crs(4326))


def operation_frame(tmp, values=None):
    store, r, work = prepare(
        tmp,
        pl.DataFrame(
            {
                "geometry": values
                or [
                    "POINT (500000 4500000)",
                    "POINT (500003 4500004)",
                    "POINT (500020 4500010)",
                ],
                "value": [1.0, 2.0, 4.0],
            }
        ),
    )
    r["format_metadata"] = {"parts": [{"geospatial": {"crs": crs(32635).to_wkt()}}]}
    return store, r, work


def params(kind, **kwargs):
    return dict(crs="EPSG:32635", **kwargs)


@pytest.mark.parametrize(
    "kind",
    (
        "geo_assign",
        "geo_reproject",
        "geo_repair",
        "geo_buffer",
        "geo_area",
        "geo_distance",
        "geo_clip",
    ),
)
def test_operation_reference_and_preserved_source_identity(tmp_path, kind):
    vals = (
        [
            "POLYGON ((500000 4500000,500010 4500010,500000 4500010,500010 4500000,500000 4500000))"
        ]
        * 3
        if kind == "geo_repair"
        else None
    )
    store, r, work = operation_frame(tmp_path, vals)
    with closing(store):
        p = params(kind)
        g = column(r, "geometry")
        if kind == "geo_reproject":
            p["target_crs"] = "EPSG:4326"
        if kind == "geo_buffer":
            p["distance"] = 10
        if kind in ("geo_area", "geo_distance"):
            p.update(output_id="col:" + uid(), output_name="measurement")
        if kind == "geo_distance":
            p["reference_wkt"] = "POINT (500000 4500000)"
        if kind == "geo_clip":
            p["mask_wkt"] = (
                "POLYGON ((499999 4499999,500010 4499999,500010 4500010,499999 4500010,499999 4499999))"
            )
        original = Path(r["path"]).read_bytes()
        out = operate(r, build(r, kind, [g], p), work)
        after = pl.read_parquet(out["path"])
        before = pl.read_parquet(r["path"])
        assert set(after["__vu_row_id"]) <= set(before["__vu_row_id"])
        assert Path(r["path"]).read_bytes() == original
        if kind == "geo_distance":
            assert after["measurement"].to_list() == [
                0.0,
                5.0,
                pytest.approx(np.sqrt(500)),
            ]
        if kind == "geo_area":
            assert after["measurement"].to_list() == [0.0, 0.0, 0.0]
        if kind == "geo_buffer":
            assert geometries(after["geometry"].to_list())[0].area == pytest.approx(
                313.654849, rel=1e-7
            )
        if kind == "geo_repair":
            assert out["diagnostics"]["repair"]["changed"] == 3
            assert all(g.is_valid for g in geometries(after["geometry"].to_list()))
        if kind == "geo_clip":
            assert len(after) == 2
        if kind == "geo_assign":
            assert after["geometry"].to_list() == before["geometry"].to_list()


def test_spatial_block_plan_no_fold_overlap_and_moran_hand_formula(tmp_path):
    store, r, work = operation_frame(tmp_path)
    with closing(store):
        p = params(
            "geo_block",
            block_size=10.0,
            folds=2,
            seed=42,
            output_id="col:" + uid(),
            output_name="block",
        )
        out = operate(r, build(r, "geo_block", [column(r, "geometry")], p), work)
        plan = out["diagnostics"]["spatial_validation"]
        assert all(
            not set(f["train_row_ids"]) & set(f["validation_row_ids"])
            for f in plan["folds"]
        )
        assert "Random split" in plan["limitation"]
    gs = [
        shapely.Point(500000, 4500000),
        shapely.Point(500001, 4500000),
        shapely.Point(500002, 4500000),
    ]
    p = dict(
        neighbors="distance",
        threshold=1.1,
        standardization="binary",
        seed=42,
        permutations=99,
    )
    out = moran(gs, np.array([1.0, 2.0, 3.0]), crs(32635), p, Control())
    assert out["I"] == 0.0
    assert out["S0"] == 4.0
    assert out["expected"] == -0.5
    assert out == moran(gs, np.array([1.0, 2.0, 3.0]), crs(32635), p, Control())
    with pytest.raises(ProjectError, match="İzole"):
        moran(
            gs, np.array([1.0, 2.0, 3.0]), crs(32635), dict(p, threshold=0.1), Control()
        )


@pytest.mark.parametrize("kind", ("map-point", "map-choropleth", "map-density"))
def test_offline_maps_reference_membership_and_exports(tmp_path, kind):
    vals = (
        [
            shapely.box(500000 + i * 10, 4500000, 500010 + i * 10, 4500010).wkt
            for i in range(3)
        ]
        if kind == "map-choropleth"
        else None
    )
    store, r, work = operation_frame(tmp_path, vals)
    with closing(store):
        opt = dict(geometry=column(r, "geometry"), bins=2, grid_bins=2)
        if kind == "map-choropleth":
            opt.update(
                geo_measure=column(r, "value"),
                geo_classification="manual",
                geo_thresholds=(2.0,),
            )
        result = calculate(r, ChartSpec(kind, **opt), work)
        result = render(result, work)
        assert Path(result["paths"]["png"]).is_file()
        assert result["details"]["geospatial"]["offline"]
        assert select(result, [0])["count"] >= 1
        if kind == "map-density":
            assert sum(p["n"] for p in result["points"]) == 3
        if kind == "map-choropleth":
            assert [p["category"] for p in result["points"]] == [0, 1, 1]
        for ext in ("png", "svg", "pdf"):
            export(result, tmp_path / ("map." + ext), ext, store.root)


def test_geometry_cancel(tmp_path):
    event = threading.Event()
    event.set()
    with pytest.raises(Canceled):
        source = fixture(tmp_path, "geojson")
        work = tmp_path / "work"
        work.mkdir()
        capture_source(source, work, Control(event))


def test_spatial_join_all_boundary_matches_and_crs_rejection(tmp_path):
    store, r, work = operation_frame(tmp_path)
    with closing(store):
        other = dict(r)
        path = tmp_path / "other.parquet"
        data = pl.read_parquet(r["path"]).with_columns(
            pl.Series(
                "geometry",
                [
                    shapely.box(499999, 4499999, 500000, 4500001).wkt,
                    shapely.box(500000, 4499999, 500001, 4500001).wkt,
                    shapely.box(600000, 4500000, 600010, 4500010).wkt,
                ],
            )
        )
        data.write_parquet(path)
        from veri_ufku.importers.delimited import hash_artifact

        other.update(
            path=str(path),
            fingerprint=hash_artifact(path, Control()),
            version_id="dv:" + uid(),
        )
        r["secondary"] = other
        p = params(
            "geo_join",
            secondary_version_id=other["version_id"],
            secondary_geometry=column(r, "geometry"),
            predicate="intersects",
            output_id="col:" + uid(),
            output_name="matches",
        )
        out = operate(r, build(r, "geo_join", [column(r, "geometry")], p), work)
        result = pl.read_parquet(out["path"])
        assert len(json.loads(result["matches"][0])) == 2
        assert out["diagnostics"]["matching"]["multiple"] == 1
        assert out["diagnostics"]["matching"]["unmatched"] == 2
        assert pl.read_parquet(out["lineage_path"]).height == 2
        other["format_metadata"] = {
            "parts": [{"geospatial": {"crs": crs(4326).to_wkt()}}]
        }
        with pytest.raises(ProjectError, match="aynı CRS"):
            operate(r, build(r, "geo_join", [column(r, "geometry")], p), work)


def test_raster_window_metadata_precedes_decode_and_offline_map(tmp_path, monkeypatch):
    import rasterio

    from veri_ufku.geo.readers import raster

    source = fixture(tmp_path, "geotiff")
    settings = StructuredSettings(adapter_id="geotiff", geo_window=(1, 1, 3, 2))
    calls = []
    original = rasterio.open

    class Spy:
        def __init__(self, obj):
            self.obj = obj

        def __getattr__(self, name):
            return getattr(self.obj, name)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.obj.close()

        def read(self, *a, **kw):
            calls.append(kw["window"])
            return self.obj.read(*a, **kw)

    monkeypatch.setattr(rasterio, "open", lambda *a, **kw: Spy(original(*a, **kw)))
    _, meta = raster(source, settings, Control(), False)
    assert not calls
    table, _ = raster(source, settings, Control())
    assert len(calls) == 1 and list(calls[0].flatten()) == [1, 1, 3, 2]
    work = tmp_path / "native"
    work.mkdir()
    store, r, w = prepare(work, pl.from_arrow(table))
    r["format_metadata"] = {"parts": [{"geospatial": meta}]}
    with closing(store):
        result = render(
            calculate(
                r,
                ChartSpec(
                    "map-raster",
                    x=column(r, "x"),
                    y=column(r, "y"),
                    geo_measure=column(r, "value"),
                ),
                w,
            ),
            w,
        )
        assert len(result["points"]) == 5
        assert result["details"]["geospatial"]["nodata_count"] == 1


def test_coordinates_explicit_axis_and_null_control(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"lon": [27.0, 28.0, 29.0], "lat": [40.0, 41.0, 42.0]})
    )
    with closing(store):
        p = dict(crs="EPSG:4326", output_id="col:" + uid(), output_name="geometry")
        out = operate(
            r,
            build(r, "geo_coordinates", [column(r, "lon"), column(r, "lat")], p),
            work,
        )
        assert pl.read_parquet(out["path"])["geometry"][0] == "POINT (27 40)"
        assert out["diagnostics"]["geospatial"]["axis_order"].startswith("x,y")


def test_choropleth_rate_denominator_and_quantile_ties(tmp_path):
    polygons = [
        shapely.box(500000 + i * 10, 4500000, 500010 + i * 10, 4500010).wkt
        for i in range(3)
    ]
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "geometry": polygons,
                "count": [20.0, 40.0, 10.0],
                "population": [100.0, 400.0, 100.0],
            }
        ),
    )
    r["format_metadata"] = {"parts": [{"geospatial": {"crs": crs(32635).to_wkt()}}]}
    with closing(store):
        spec = ChartSpec(
            "map-choropleth",
            geometry=column(r, "geometry"),
            geo_measure=column(r, "count"),
            geo_denominator=column(r, "population"),
            geo_measure_mode="rate",
            geo_classification="quantile",
            bins=3,
        )
        result = calculate(r, spec, work)
        assert [p["z"] for p in result["points"]] == [0.2, 0.1, 0.1]
        assert result["details"]["geospatial"]["denominator_column"] == column(
            r, "population"
        )
        path = Path(r["path"])
        df = pl.read_parquet(path).with_columns(
            pl.Series("population", [0.0, 400.0, 100.0])
        )
        df.write_parquet(path)
        from veri_ufku.importers.delimited import hash_artifact

        r["fingerprint"] = hash_artifact(path, Control())
        with pytest.raises(ProjectError, match="pozitif"):
            calculate(r, spec, work)


def test_shapefile_missing_components_and_mutation(tmp_path):
    source = fixture(tmp_path, "shapefile")
    work = tmp_path / "work"
    work.mkdir()
    snap = capture_source(source, work, Control())
    source.with_suffix(".dbf").write_bytes(b"changed")
    with pytest.raises(ProjectError, match="bileşeni değişti"):
        verify_sources(snap, Control())
    lone = tmp_path / "lone.shp"
    lone.write_bytes(source.read_bytes())
    with pytest.raises(ProjectError, match="eksik"):
        capture_source(lone, work, Control())


def test_spatial_blocks_feed_existing_group_validation(tmp_path):
    from veri_ufku.modeling.validation import ValidationSpec, split_plan

    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                geometry=[
                    f"POINT ({500000 + 20 * (i // 2)} {4500000 + i % 2})"
                    for i in range(40)
                ],
                value=list(range(40)),
            )
        ),
    )
    r["format_metadata"] = {"parts": [{"geospatial": {"crs": crs(32635).to_wkt()}}]}
    with closing(store):
        p = params(
            "geo_block",
            block_size=10.0,
            folds=3,
            seed=42,
            output_id="col:" + uid(),
            output_name="spatial_block",
        )
        out = operate(r, build(r, "geo_block", [column(r, "geometry")], p), work)
        frame = pl.read_parquet(out["path"])
        groups = np.array(frame["spatial_block"].to_list())
        row_ids = frame["__vu_row_id"].to_list()
        _, parts = split_plan(
            row_ids,
            np.arange(40, dtype=float),
            groups,
            None,
            ValidationSpec(structure="group", folds=3),
            "group",
            False,
            r["version_id"],
            r["fingerprint"],
        )
        train, val, dev, test, folds = parts
        assert not set(groups[train]) & set(groups[val])
        assert not set(groups[dev]) & set(groups[test])
        assert all(not set(groups[a]) & set(groups[b]) for a, b in folds)


@pytest.mark.parametrize("change", ["spherical", "version", "encoding"])
def test_geoparquet_unsupported_semantics_rejected(tmp_path, change):
    import pyarrow.parquet as pq

    source = fixture(tmp_path, "geoparquet")
    table = pq.read_table(source)
    metadata = dict(table.schema.metadata)
    geo = json.loads(metadata[b"geo"])
    col = geo["columns"][geo["primary_column"]]
    if change == "version":
        geo["version"] = "9.0.0"
    else:
        col["edges" if change == "spherical" else "encoding"] = (
            "spherical" if change == "spherical" else "point"
        )
    metadata[b"geo"] = json.dumps(geo).encode()
    pq.write_table(table.replace_schema_metadata(metadata), source)
    work = tmp_path / "work"
    work.mkdir()
    snap = unpack(capture_source(source, work, Control()), work, Control())
    with pytest.raises(ProjectError, match="GeoParquet"):
        get_adapter("geoparquet").preview(
            snap, StructuredSettings(adapter_id="geoparquet"), Control()
        )


@pytest.mark.parametrize("dtype", ["int64", "uint64"])
def test_raster_wide_integer_precision_never_silently_lost(tmp_path, dtype):
    import rasterio
    from rasterio.transform import from_origin

    path = tmp_path / "wide.tif"
    values = np.full((1, 2, 2), 2**53 + 1, dtype=dtype)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype=dtype,
        crs="EPSG:32635",
        transform=from_origin(500000, 4500000, 10, 10),
    ) as ds:
        ds.write(values)
    original = path.read_bytes()
    work = tmp_path / "work"
    work.mkdir()
    snap = unpack(capture_source(path, work, Control()), work, Control())
    settings = StructuredSettings(adapter_id="geotiff")
    choices = get_adapter("geotiff").inspect(snap, settings, Control())
    assert choices["geospatial"]["raster"]
    with pytest.raises(ProjectError, match="precision"):
        get_adapter("geotiff").preview(snap, settings, Control())
    assert path.read_bytes() == original and not list(work.rglob("dataset.parquet"))
