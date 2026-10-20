"""Real installed package CPU/QML/spawn/migration/native smoke, stdlib runner."""

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import sys
import tempfile
import time
from pathlib import Path


def spin(app, predicate, seconds=45):
    from PySide6.QtTest import QTest

    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise RuntimeError("Package smoke deadline")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--extra", action="append", default=[])
    p.add_argument("--portal-file", type=Path)
    p.add_argument("--portal-sha256")
    args = p.parse_args()
    record = dict(
        python=platform.python_version(),
        platform=platform.platform(),
        flatpak=Path("/.flatpak-info").is_file(),
        core={},
        extras={},
        portal=dict(status="not-tested"),
        offline_installer="not-tested/unavailable; runtime preinstalled",
    )
    import importlib.metadata as md

    import veri_ufku

    record["package"] = str(Path(veri_ufku.__file__).resolve())
    try:
        if record["flatpak"]:
            assert str(veri_ufku.__file__).startswith("/app/")
            assert all("/home/" not in x and "/.venv/" not in x for x in sys.path)
        from veri_ufku.packaging.environment import scan, validate_report

        report = scan()
        validate_report(report)
        record["environment"] = report
        assert (
            report["groups"]["core"]["status"]
            == "versions-match-not-runtime-validation"
        )
        with tempfile.TemporaryDirectory(prefix="vu-package74-") as temporary:
            base = Path(temporary)
            for k in ("CONFIG", "STATE", "CACHE", "DATA"):
                os.environ["XDG_" + k + "_HOME"] = str(base / k.lower())
            from veri_ufku.app import create_application

            app, window, bridge = create_application()
            engine = app._veri_ufku_resources[0]
            projects, imports = engine._projects_resources, engine._imports_resources
            try:
                import polars as pl

                source = base / "fixture.parquet"
                pl.DataFrame(
                    dict(x=[1.0, 2.0, 3.0, 4.0], y=[2.0, 4.0, 6.0, 8.0])
                ).write_parquet(source)
                before = hashlib.sha256(source.read_bytes()).hexdigest()
                assert projects.create(str(base / "project"))
                imports.choose(str(source))
                spin(app, lambda: not imports.busy)
                assert not imports.errorText, imports.errorText
                imports.importData()
                spin(app, lambda: not imports.busy)
                assert not imports.errorText, imports.errorText
                assert (
                    projects.draft["datasets"][-1]["import_metadata"]["row_count"] == 4
                )
                from veri_ufku.analytics.contracts import ProfileSpec
                from veri_ufku.analytics.dataset import profile
                from veri_ufku.operations.workflow import references

                req = list(references(projects.store, projects.draft).values())[-1]
                col = next(c["id"] for c in req["columns"] if c["name"] == "x")
                pr = profile(req, ProfileSpec(col, sample=False), base)
                assert float(pr["numeric"]["mean"]) == 2.5
                from sklearn.linear_model import LinearRegression

                model = LinearRegression().fit([[1.0], [2.0], [3.0]], [2.0, 4.0, 6.0])
                assert abs(model.predict([[4.0]])[0] - 8.0) < 1e-10
                target = str(projects.store.root)
                spin(app, lambda: not projects.busy)
                assert projects.closeProject(True) and projects.open(target)
                assert hashlib.sha256(source.read_bytes()).hexdigest() == before
                record["core"] = dict(
                    qml=True,
                    worker_import=True,
                    profile_mean=2.5,
                    cpu_prediction=8.0,
                    save_reopen=True,
                    source_unchanged=True,
                )
                if args.portal_file:
                    raw = args.portal_file.read_bytes()
                    assert hashlib.sha256(raw).hexdigest() == args.portal_sha256
                    imports.choose(str(args.portal_file))
                    spin(app, lambda: not imports.busy)
                    assert not imports.errorText, imports.errorText
                    imports.importData()
                    spin(app, lambda: not imports.busy)
                    assert not imports.errorText, imports.errorText
                    record["portal"] = dict(
                        status="actual granted document path read by packaged GUI and worker",
                        rows=projects.draft["datasets"][-1]["import_metadata"][
                            "row_count"
                        ],
                        chooser="document-export grant; human native chooser not tested",
                    )
            finally:
                app._veri_ufku_resources[-1]()
                window.deleteLater()
                app.processEvents()
            # Empty historical schema4 fixture migrates with old manifest preserved, not a reverse migration.
            fixture = Path(__file__).with_name("schema4.json")
            if not fixture.exists():
                fixture = (
                    Path(__file__).resolve().parents[1]
                    / "tests/fixtures/projects/schema4.json"
                )
            from veri_ufku.storage.project_model import (
                SCHEMA_VERSION,
                decode,
                digest,
                encode,
            )
            from veri_ufku.storage.project_store import ProjectStore

            legacy = base / "legacy"
            with __import__("contextlib").closing(ProjectStore.create(legacy)):
                pass
            old = decode(fixture.read_bytes())
            raw = encode(old)
            folder = legacy / "commits" / old["commit_id"]
            folder.mkdir()
            (folder / "manifest.json").write_bytes(raw)
            with sqlite3.connect(legacy / "metadata.sqlite") as db:
                db.execute(
                    "INSERT INTO commits VALUES (?,?,?)",
                    (old["commit_id"], digest(raw), raw),
                )
            (legacy / "ACTIVE").write_bytes(
                encode(
                    dict(
                        commit_id=old["commit_id"],
                        format_version=old["format_version"],
                        manifest_sha256=digest(raw),
                    )
                )
            )
            with __import__("contextlib").closing(
                ProjectStore.open(legacy)
            ) as migrated:
                migrated.save()
                assert migrated.manifest["format_version"] == SCHEMA_VERSION
                assert (folder / "manifest.json").read_bytes() == raw
            record["migration"] = dict(
                from_schema=4,
                to_schema=SCHEMA_VERSION,
                old_manifest_preserved=True,
                scope="small empty schema4 fixture; no downgrade/complex legacy backend guarantee",
            )
            if "geospatial" in args.extra:
                import numpy as np
                import pyogrio
                import pyproj
                import shapely
                from rasterio.io import MemoryFile
                from rasterio.transform import from_origin

                point = pyproj.Transformer.from_crs(
                    4326, 3857, always_xy=True
                ).transform(1, 0)
                assert abs(point[0] - 111319.49079327357) < 1e-6
                assert abs(shapely.area(shapely.box(0, 0, 2, 3)) - 6) < 1e-12
                geo = base / "points.geojson"
                geo.write_text(
                    '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"x":1},"geometry":{"type":"Point","coordinates":[0,0]}}]}'
                )
                meta, table = pyogrio.read_arrow(geo)
                assert table.num_rows == 1
                with MemoryFile() as memory:
                    with memory.open(
                        driver="GTiff",
                        height=2,
                        width=2,
                        count=1,
                        dtype="float32",
                        crs="EPSG:3857",
                        transform=from_origin(0, 2, 1, 1),
                        nodata=-9999,
                    ) as ds:
                        ds.write(np.array([[1, 2], [3, 4]], dtype="float32"), 1)
                    with memory.open() as ds:
                        assert float(ds.read(1).sum()) == 10.0
                record["extras"]["geospatial"] = dict(
                    crs_reference=True,
                    vector_rows=1,
                    raster_sum=10.0,
                    network_grids=pyproj.network.is_network_enabled(),
                    versions={
                        n: md.version(n)
                        for n in ("pyproj", "rasterio", "pyogrio", "shapely")
                    },
                )
            if "arrays" in args.extra:
                import numpy as np
                import xarray as xr
                from pint import UnitRegistry

                f = base / "array.nc"
                data = np.arange(24).reshape(2, 3, 4)
                xr.DataArray(
                    data, dims=("time", "y", "x"), attrs=dict(units="kelvin")
                ).to_netcdf(f, engine="h5netcdf")
                with xr.open_dataarray(f, engine="h5netcdf") as arr:
                    assert (
                        np.array_equal(arr.isel(time=1).values, data[1])
                        and arr.attrs["units"] == "kelvin"
                    )
                assert (
                    abs(
                        UnitRegistry().Quantity(0, "degC").to("kelvin").magnitude
                        - 273.15
                    )
                    < 1e-12
                )
                record["extras"]["arrays"] = dict(
                    lazy_slice=True,
                    unit_offset=True,
                    versions={
                        n: md.version(n) for n in ("h5py", "h5netcdf", "xarray", "pint")
                    },
                )
            if "neural" in args.extra:
                import torch

                torch.set_num_threads(1)
                torch.manual_seed(74)
                x = torch.tensor([[0.0], [1.0], [2.0], [3.0]])
                y = 2 * x
                model = torch.nn.Sequential(
                    torch.nn.Linear(1, 4), torch.nn.Tanh(), torch.nn.Linear(4, 1)
                )
                optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
                initial = float(((model(x) - y) ** 2).mean().detach())
                for _ in range(30):
                    optimizer.zero_grad()
                    loss = ((model(x) - y) ** 2).mean()
                    loss.backward()
                    optimizer.step()
                final = float(((model(x) - y) ** 2).mean().detach())
                assert final < initial
                record["extras"]["neural"] = dict(
                    device="cpu",
                    initial_loss=initial,
                    final_loss=final,
                    version=md.version("torch"),
                    gpu="not-tested",
                    weights_downloaded=False,
                )
        record["status"] = "passed"
    except BaseException as e:
        record.update(status="failed", error_type=type(e).__name__)
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print("PACKAGE74_SMOKE PASS", record["package"], ",".join(args.extra) or "core")


if __name__ == "__main__":
    main()
