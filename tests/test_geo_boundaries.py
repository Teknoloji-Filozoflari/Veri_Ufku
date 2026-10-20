"""Independent regressions for geometry dimensions, angular units and raster data."""

from contextlib import closing
from decimal import Decimal
from pathlib import Path

import numpy as np
import polars as pl
import pytest
import rasterio
import shapely
from phase38_fixtures import fixture
from rasterio.transform import from_origin
from test_dataset import column, prepare

from veri_ufku.charts.contracts import ChartSpec
from veri_ufku.charts.engine import calculate
from veri_ufku.geo.core import (
    crs,
    geographic_check,
    geometries,
    numeric_values,
    reproject,
)
from veri_ufku.geo.operations import moran
from veri_ufku.geo.readers import raster
from veri_ufku.importers.delimited import Control
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.operations.contracts import build
from veri_ufku.operations.engine import calculate as operate
from veri_ufku.storage.project_model import ProjectError, uid


def test_measured_geometry_never_silently_loses_m():
    wkt = "POINT M (27 40 123)"
    with pytest.raises(ProjectError, match="M"):
        geometries([wkt])
    with pytest.raises(ProjectError, match="M"):
        reproject([shapely.from_wkt(wkt)], 4326, 32635)


def test_geographic_limits_use_crs_angular_units():
    # NTF (Paris) uses grads: 99 grad = 89.1 degrees, 101 grad = 90.9.
    system = crs(4807)
    geographic_check([shapely.Point(0, 99)], system)
    with pytest.raises(ProjectError, match="eksen"):
        geographic_check([shapely.Point(0, 101)], system)
    # 190 grad = 171 degrees; a 190-grad edge does not cross the limit.
    geographic_check([shapely.LineString([(0, 0), (190, 0)])], system)


def test_collection_points_do_not_form_an_antimeridian_edge():
    geographic_check(
        [shapely.from_wkt("GEOMETRYCOLLECTION (MULTIPOINT ((179 0), (-179 0)))")],
        crs(4326),
    )
    with pytest.raises(ProjectError, match="Antimeridian"):
        geographic_check(
            [
                shapely.from_wkt(
                    "GEOMETRYCOLLECTION (GEOMETRYCOLLECTION (LINESTRING (179 0, -179 0)))"
                )
            ],
            crs(4326),
        )


@pytest.mark.parametrize("dtype", ["complex64", "complex128"])
def test_complex_raster_never_discards_imaginary_values(tmp_path, dtype):
    source = tmp_path / "complex.tif"
    with rasterio.open(
        source,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype=dtype,
        crs="EPSG:32635",
        transform=from_origin(500000, 4500000, 10, 10),
    ) as dataset:
        dataset.write(np.full((1, 2, 2), 3 + 4j, dtype=dtype))
    original = source.read_bytes()
    settings = StructuredSettings(adapter_id="geotiff")
    _, metadata = raster(source, settings, Control(), decode=False)
    assert metadata["raster"]
    with pytest.raises(ProjectError, match="complex"):
        raster(source, settings, Control())
    assert source.read_bytes() == original


@pytest.mark.parametrize("scale", [1e-200, 1e200, 1e307])
def test_moran_is_invariant_to_scale_without_float_overflow(scale):
    gs = [shapely.Point(500000 + i, 4500000) for i in range(3)]
    parameters = dict(
        neighbors="distance",
        threshold=1.01,
        standardization="binary",
        permutations=0,
        seed=42,
    )
    report = moran(
        gs, np.array([1.0, 2.0, 4.0]) * scale, crs(32635), parameters, Control()
    )
    assert report["I"] == pytest.approx(-1 / 28)
    assert report["S0"] == 4


def test_moran_preserves_representable_differences_at_large_offset():
    gs = [shapely.Point(500000 + i, 4500000) for i in range(3)]
    parameters = dict(
        neighbors="distance",
        threshold=1.01,
        standardization="binary",
        permutations=0,
        seed=42,
    )
    values = np.array([2**53, 2**53 + 2, 2**53 + 6], dtype=float)
    # Exact Float64 differences [0,2,6] give the same I as [1,2,4].
    assert moran(gs, values, crs(32635), parameters, Control())["I"] == pytest.approx(
        -1 / 28
    )


def test_spatial_numeric_conversion_accepts_exact_values_and_rejects_overflow():
    assert numeric_values([2**53, Decimal("0.125"), 1.5]) == [float(2**53), 0.125, 1.5]
    with pytest.raises(ProjectError, match="Float64"):
        numeric_values([10**400])


def test_integer_coordinates_require_lossless_float64(tmp_path):
    store, request, work = prepare(tmp_path, pl.DataFrame({"x": [2**53 + 1], "y": [0]}))
    with closing(store):
        original = Path(request["path"]).read_bytes()
        spec = build(
            request,
            "geo_coordinates",
            [column(request, "x"), column(request, "y")],
            dict(crs="EPSG:3857", output_id="col:" + uid(), output_name="geometry"),
        )
        with pytest.raises(ProjectError, match="hassasiyet"):
            operate(request, spec, work)
        assert Path(request["path"]).read_bytes() == original


@pytest.mark.parametrize(
    "values",
    [
        [2**53, 2**53 + 1, 2**53 + 2],
        [Decimal("0.1"), Decimal("0.2"), Decimal("0.4")],
    ],
)
def test_moran_measurement_never_silently_rounds_exact_values(tmp_path, values):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "geometry": [f"POINT ({500000 + i} 4500000)" for i in range(3)],
                "measure": values,
            }
        ),
    )
    with closing(store):
        spec = build(
            request,
            "geo_moran",
            [column(request, "geometry"), column(request, "measure")],
            dict(
                crs="EPSG:32635",
                neighbors="distance",
                threshold=1.01,
                standardization="binary",
                permutations=0,
                seed=42,
            ),
        )
        with pytest.raises(ProjectError, match="hassasiyet"):
            operate(request, spec, work)


def test_moran_measurement_requires_numeric_column(tmp_path):
    store, request, _ = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "geometry": [f"POINT ({500000 + i} 4500000)" for i in range(3)],
                "measure": ["1", "2", "4"],
            }
        ),
    )
    with closing(store), pytest.raises(ProjectError, match="sayısal"):
        build(
            request,
            "geo_moran",
            [column(request, "geometry"), column(request, "measure")],
            dict(
                crs="EPSG:32635",
                neighbors="distance",
                threshold=1.01,
                standardization="binary",
                permutations=0,
                seed=42,
            ),
        )


@pytest.mark.parametrize(
    "mapping",
    [
        {"x": "raster_col", "y": "raster_row", "geo_measure": "value"},
        {"x": "x", "y": "y", "geo_measure": "raster_row"},
    ],
)
def test_raster_map_rejects_other_columns_as_captured_pixels(tmp_path, mapping):
    source = fixture(tmp_path, "geotiff")
    table, meta = raster(source, StructuredSettings(adapter_id="geotiff"), Control())
    native = tmp_path / "native"
    native.mkdir()
    store, request, work = prepare(native, pl.from_arrow(table))
    request["format_metadata"] = {"parts": [{"geospatial": meta}]}
    with closing(store), pytest.raises(ProjectError, match="Raster"):
        calculate(
            request,
            ChartSpec(
                "map-raster",
                **{key: column(request, value) for key, value in mapping.items()},
            ),
            work,
        )
