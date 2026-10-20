"""Source and installed wheel: recipe replay, drift, inference and delayed targets."""

import argparse
import hashlib
import json
import os
import platform
import socket
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("POLARS_MAX_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
original_connect = socket.socket.connect


def offline(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise RuntimeError("Python TCP denied in phase23 evidence")
    return original_connect(self, address)


socket.socket.connect = offline
import polars as pl  # noqa: E402
from PySide6.QtCore import QObject, QPointF, QUrl  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402
from veri_ufku.modeling.validation import ValidationSpec  # noqa: E402


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record = dict(
        environment="ENV-23",
        evaluated_at=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        platform=platform.platform(),
        package=str(veri_ufku.__file__),
        backend="offscreen/software",
        user_test=False,
        offline="Python TCP blocked parent/spawn; no offline installation claim",
        screenshots=[],
        runs=[],
    )
    with tempfile.TemporaryDirectory(prefix="vu-phase23-") as tmp:
        base = Path(tmp)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, data, ops, c, prep, val, life = (
            engine._projects_resources,
            engine._imports_resources,
            engine._dataset_resources,
            engine._operations_resources,
            engine._recipe_resources,
            engine._preparation_resources,
            engine._validation_resources,
            engine._lifecycle_resources,
        )

        def wait(obj):
            start = time.monotonic()
            while obj.busy:
                app.processEvents()
                QTest.qWait(10)
                assert time.monotonic() - start < 120, obj.message
            assert not obj.errorText, obj.errorText
            return time.monotonic() - start

        def url(path):
            return QUrl.fromLocalFile(str(path)).toString()

        def imported(frame, name):
            path = base / (name + ".parquet")
            frame.write_parquet(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            imports.choose(str(path))
            wait(imports)
            imports.importData()
            wait(imports)
            data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
            wait(data)
            return data.dataset(), path, digest

        try:
            assert projects.create(str(base / "project"))
            for n in (120, 100000):
                frame = pl.DataFrame(
                    dict(
                        x=[float(i % 30) for i in range(n)],
                        y=[float(i % 30) * 3 + 7 for i in range(n)],
                        cat=[" A " if i % 2 else " B " for i in range(n)],
                    )
                )
                old, source, digest = imported(frame, f"old-{n}")
                ids = {
                    col["name"]: col["id"] for col in old["import_metadata"]["columns"]
                }
                ops.previewCleaning(
                    "trim",
                    json.dumps([ids["cat"]]),
                    json.dumps(dict(side="both")),
                    "chain",
                )
                wait(ops)
                ops.apply()
                wait(ops)
                ops.previewOperation("rename", ids["cat"], "category")
                wait(ops)
                ops.apply()
                wait(ops)
                c.selectRecipe(data.dataset()["version_id"])
                assert c.recipeSources, c.errorText
                recipe_path = base / f"recipe-{n}.json"
                c.saveRecipe(url(recipe_path))
                c.openRecipe(url(recipe_path))
                new, new_path, new_hash = imported(frame, f"new-{n}")
                c.mapSource(old["version_id"], new["version_id"])
                state = json.dumps(projects.draft, sort_keys=True)
                elapsed = c.dryRun()
                elapsed = wait(c)
                assert c.canApply, c.result
                assert json.dumps(projects.draft, sort_keys=True) == state
                before = pl.read_parquet(c.result["results"][-1]["path"]).select(
                    "x", "y", "category"
                )
                c.dryRun()
                wait(c)
                assert before.equals(
                    pl.read_parquet(c.result["results"][-1]["path"]).select(
                        "x", "y", "category"
                    )
                )
                window.setProperty("selectedSection", 2)
                for width, height in ((1366, 900), (720, 560)):
                    window.resize(width, height)
                    app.processEvents()
                    QTest.qWait(100)
                    target = window.findChild(QObject, "recipePanel")
                    flick = window.findChild(QObject, "workspace").property(
                        "contentItem"
                    )
                    pos = target.mapToItem(flick, QPointF(0, 0)).y() + flick.property(
                        "contentY"
                    )
                    flick.setProperty(
                        "contentY",
                        max(
                            0,
                            min(
                                pos,
                                flick.property("contentHeight")
                                - flick.property("height"),
                            ),
                        ),
                    )
                    QTest.qWait(100)
                    path = args.output.with_name(
                        args.output.stem + f"-recipe-{n}-{width}.png"
                    )
                    assert window.grabWindow().save(str(path))
                    record["screenshots"].append(str(path))
                c.applyRecipe()
                wait(c)
                applied = data.dataset()
                assert applied["version_id"] != new["version_id"]
                c.compareData(old["version_id"], new["version_id"])
                wait(c)
                assert (
                    c.changeReport["metrics"] is None
                    and len(c.changeReport["columns"]) == 3
                )
                c.saveReport(url(base / f"drift-{n}.json"))
                assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
                assert hashlib.sha256(new_path.read_bytes()).hexdigest() == new_hash
                record["runs"].append(
                    dict(
                        rows=n,
                        dry_seconds=elapsed,
                        same_values=True,
                        atomic_apply=True,
                        full_drift=True,
                        source_preserved=True,
                    )
                )
                if n == 120:
                    window.setProperty("selectedSection", 5)
                    cols = {col["name"]: col["id"] for col in prep.columns}
                    prep.create(
                        json.dumps(
                            dict(
                                purpose="regression",
                                target=cols["y"],
                                features=[cols["x"]],
                                prediction_context="Ölçüm öncesi",
                            )
                        )
                    )
                    wait(prep)
                    protocol = ValidationSpec(
                        prediction_moment="Ölçüm öncesi",
                        availability={
                            cols["x"]: dict(offset_seconds=0, note="Önceden bilinir")
                        },
                    )
                    val.create(json.dumps(protocol.data()))
                    wait(val)
                    saved = next(
                        r for r in projects.draft["results"] if "baseline" in r
                    )
                    life.selectModel(saved["id"])
                    wait(life)
                    training = life.card["dataset_version"]
                    future, _, _ = imported(frame, "future")
                    life.previewData("reject", 32)
                    wait(life)
                    output = base / "prediction.parquet"
                    life.predictData(url(output), "reject", 32)
                    wait(life)
                    assert life.card["dataset_version"] == training
                    c.evaluateTargets(
                        future["version_id"],
                        "__vu_row_id",
                        "__vu_row_id",
                        "vu_prediction",
                        "y",
                    )
                    wait(c)
                    assert (
                        c.changeReport["scored"] == 120
                        and c.changeReport["metrics"] is not None
                    ), c.changeReport
                    assert c.changeReport["training_version"] == training
                    c.saveReport(url(base / "performance.json"))
                    window.findChild(QObject, "lifecycleRetrain").clicked.emit()
                    assert not prep.busy and prep.source_version == ""
                    record["model"] = dict(
                        fit_on_apply=False,
                        training_reference_preserved=True,
                        delayed_scored=120,
                        retrain_explicit=True,
                    )
                root = str(projects.store.root)
                assert projects.closeProject(True)
                assert projects.open(root)
            for context in ("workflow.recipe", "workflow.drift", "workflow.model"):
                engine._learning_resources.openContext(context)
                assert engine._learning_resources.article["id"].startswith("workflow-")
            record["status"] = "passed"
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(
        "PASS Phase23 source/wheel recipe, atomic publication, drift, inference and delayed targets",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase23/source.json")
    )
    run(parser.parse_args())
