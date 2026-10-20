"""Real unfitted preparation UI/worker/history/100k plan in source or installed wheel."""

import argparse
import hashlib
import json
import os
import platform
import socket
import tempfile
import time
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
_connect = socket.socket.connect


def offline(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise OSError("Phase15 Python TCP denied")
    return _connect(self, address)


socket.socket.connect = offline
import polars as pl  # noqa: E402
from measure_phase07 import rss  # noqa: E402
from PySide6.QtCore import QObject, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402
from veri_ufku.operations.cleaning_contracts import defaults  # noqa: E402


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record = dict(
        environment="ENV-15",
        date="2026-10-08",
        python=platform.python_version(),
        platform=platform.platform(),
        package=str(veri_ufku.__file__),
        polars=pl.__version__,
        backend="offscreen/software",
        user_test=False,
        purposes={},
        screenshots=[],
        source_sha256={},
        max_tick_gap_ms=0,
        peak_parent_worker_rss_bytes=0,
        offline_policy="Python TCP denied in parent/spawn; OS interfaces not disabled; fresh XDG",
        cache="warm developer runtime; no minimum hardware claim",
    )
    with tempfile.TemporaryDirectory(
        prefix="vu-phase15-", dir=args.project_temp
    ) as temp:
        base = Path(temp)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, c = (
            engine._projects_resources,
            engine._imports_resources,
            engine._preparation_resources,
        )
        data, ops = engine._dataset_resources, engine._operations_resources

        def wait(obj):
            start = last = time.monotonic()
            while obj.busy:
                app.processEvents()
                QTest.qWait(10)
                now = time.monotonic()
                record["max_tick_gap_ms"] = max(
                    record["max_tick_gap_ms"], (now - last) * 1000
                )
                last = now
                proc = getattr(obj, "process", None)
                record["peak_parent_worker_rss_bytes"] = max(
                    record["peak_parent_worker_rss_bytes"],
                    rss(os.getpid()) + (rss(proc.pid) if proc else 0),
                )
                assert now - start < 60, (type(obj).__name__, obj.message)
            assert not getattr(obj, "errorText", ""), getattr(obj, "errorText", "")
            return (time.monotonic() - start) * 1000

        def field(name, prop, value):
            obj = window.findChild(QObject, "preparation" + name)
            assert obj is not None, name
            assert obj.setProperty(prop, value)
            return obj

        def shot(label, width):
            window.setWidth(width)
            window.setHeight(800)
            app.processEvents()
            QTest.qWait(150)
            path = args.output.with_name(args.output.stem + "-" + label + ".png")
            assert window.grabWindow().save(str(path))
            record["screenshots"].append(str(path))

        def load(name, frame):
            source = base / (name + ".parquet")
            frame.write_parquet(source)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            record["source_sha256"][name] = digest
            imports.choose(str(source))
            wait(imports)
            imports.importData()
            wait(imports)
            data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
            wait(data)
            window.setProperty("selectedSection", 5)
            app.processEvents()
            return source, digest

        try:
            assert projects.create(str(base / "project"))
            source, digest = load(
                "fixture",
                pl.DataFrame(
                    dict(
                        id=list("abcdef"),
                        x=[1.0, None, 3.0, 4.0, 5.0, 7.0],
                        cat=["A", "A", "B", "B", None, "B"],
                        y=[0, 0, 1, 1, None, 1],
                        when=[date(2024, 1, i) for i in range(1, 7)],
                        group=["A", "A", "B", "B", "C", "C"],
                    )
                ),
            )
            cols = {col["name"]: i for i, col in enumerate(c.columns)}
            for purpose, family in [
                ("regression", "linear"),
                ("classification", "tree"),
                ("clustering", "distance"),
                ("anomaly", "tree"),
            ]:
                field("Settings", "checked", True)
                field(
                    "Purpose",
                    "currentIndex",
                    ["regression", "classification", "clustering", "anomaly"].index(
                        purpose
                    ),
                )
                field(
                    "Family",
                    "currentIndex",
                    ["linear", "distance", "tree"].index(family),
                )
                field("Target", "currentIndex", cols["y"])
                field("Group", "currentIndex", cols["group"] + 1)
                field("Time", "currentIndex", cols["when"] + 1)
                window.findChild(QObject, "preparationPanel").setProperty(
                    "chosenFeatures",
                    [
                        col["id"]
                        for col in c.columns
                        if col["name"] in ("x", "cat", "when")
                    ],
                )
                field(
                    "Context",
                    "text",
                    "Kayıt anında x/kategori/tarih biliniyor; eğitim henüz yapılmıyor.",
                )
                if purpose == "regression":
                    shot("form-720", 720)
                window.findChild(QObject, "preparationScan").clicked.emit()
                ms = wait(c)
                result = c.result
                assert (
                    c.current
                    and not result["fitted"]
                    and result["worker_pid"] != os.getpid()
                )
                assert (
                    result["dataset_n"] == 6
                    and result["plan"]["fitted_parameters"] == {}
                )
                record["purposes"][purpose] = dict(
                    family=family,
                    calculate_ms=ms,
                    worker_pid=result["worker_pid"],
                    dataset_n=result["dataset_n"],
                    eligible_n=result["eligible_n"],
                    target=result["target"],
                    plan=result["plan"],
                )
                if purpose == "regression":
                    shot("result-1366", 1366)
                    shot("result-720", 720)
                window.findChild(QObject, "preparationSave").clicked.emit()
                wait(c)
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
            root = str(projects.store.root)
            assert projects.closeProject(True) and projects.open(root)
            plans = [r for r in projects.draft["results"] if "preparation" in r]
            assert len(plans) == 4
            for saved in plans:
                c.openSaved(saved["id"])
                assert c.result["plan"] == saved["preparation"]["plan"]
            record["saved_reopened"] = 4
            field("Saved", "currentIndex", 0).forceActiveFocus()
            QTest.keyClick(window, Qt.Key_F1)
            app.processEvents()
            assert engine._learning_resources.article["id"] == "model-preparation"
            record["f1_context"] = "model-preparation"
            QTest.keyClick(window, Qt.Key_Escape)
            app.processEvents()
            QTest.qWait(200)
            assert not window.property("infoOpen")
            raw = data.dataset()["version_id"]
            ids = {col["name"]: col["id"] for col in c.columns}
            ops.previewCleaning(
                "fill",
                json.dumps([ids["x"]]),
                json.dumps(dict(defaults("fill"), method="mean")),
                "chain",
            )
            wait(ops)
            assert ops.canApply
            ops.apply()
            wait(ops)
            wait(data)
            spec = dict(
                purpose="regression", features=[ids["x"], ids["cat"]], target=ids["y"]
            )
            c.source_version = ""
            c.invalidate()
            c.create(json.dumps(spec))
            wait(c)
            assert c.result["history"]["unresolved_source_operations"]
            assert (
                next(p for p in c.result["columns"] if p["name"] == "x")["null_count"]
                == 0
            )
            record["history_review"] = c.result["history"]
            shot("history-1366", 1366)
            c.selectSource(raw)
            assert not c.errorText
            c.create(json.dumps(dict(spec, history_action="relocate")))
            wait(c)
            assert (
                next(p for p in c.result["columns"] if p["name"] == "x")["null_count"]
                == 1
            )
            assert not c.result["history"]["unresolved_source_operations"]
            assert (
                next(
                    s
                    for s in c.result["plan"]["steps"]
                    if s["kind"] == "impute_numeric"
                )["parameters"]["strategy"]
                == "mean"
            )
            record["history_relocation"] = c.result["history"]
            record["relocation_plan"] = c.result["plan"]
            c.save()
            wait(c)
            assert projects.closeProject(True) and projects.create(
                str(base / "large-project")
            )
            c.source_version = ""
            source, digest = load(
                "large",
                pl.DataFrame(
                    dict(
                        id=range(100000),
                        x=range(100000),
                        cat=["A", "B"] * 50000,
                        y=[0, 1] * 50000,
                    )
                ),
            )
            ids = {col["name"]: col["id"] for col in c.columns}
            spec = dict(
                purpose="classification",
                features=[ids["x"], ids["cat"]],
                target=ids["y"],
                family="tree",
            )
            c.create(json.dumps(spec))
            ms = wait(c)
            assert c.result["dataset_n"] == 100000
            assert c.result["target"]["class_distribution"] == [
                dict(label="0", count=50000),
                dict(label="1", count=50000),
            ]
            record["large"] = dict(
                rows=100000,
                calculate_ms=ms,
                class_distribution=c.result["target"]["class_distribution"],
                plan=c.result["plan"],
            )
            c.save()
            wait(c)
            previous = c.result["plan"]["version_id"]
            c.create(json.dumps(spec))
            c.cancel()
            record["cancel_ms"] = wait(c)
            assert c.result["plan"]["version_id"] == previous and "İptal" in c.message
            record["cancel_previous_plan_preserved"] = True
            c.create(json.dumps(spec))
            c.invalidate()
            wait(c)
            assert not c.current and c.result["plan"]["version_id"] == previous
            record["stale_result_discarded"] = True
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
            record["all_sources_unchanged"] = True
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    args.output.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    print("PHASE15 PASS", args.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase15/headless.json")
    )
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--project-temp")
    run(parser.parse_args())
