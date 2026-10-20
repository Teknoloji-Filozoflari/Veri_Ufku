"""Actual QML/preflight/process/save/reopen in source or installed Linux wheel."""

import argparse
import hashlib
import inspect
import json
import os
import platform
import socket
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
_connect = socket.socket.connect


def offline_connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise OSError("Phase14 offline walkthrough: Python TCP denied")
    return _connect(self, address)


socket.socket.connect = offline_connect

import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
import scipy  # noqa: E402
from measure_phase07 import rss  # noqa: E402
from PySide6.QtCore import QObject, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from scipy import stats  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402
from veri_ufku.statistics.contracts import METHODS  # noqa: E402


def fixture(path):
    if path == "paired":
        return pl.DataFrame(
            dict(
                person=["a", "b", "c", "d", "d", "b", "a", "c"],
                phase=["before"] * 4 + ["after"] * 4,
                x=[10, 20, 30, 40, 44, 22, 11, 33],
            )
        )
    if path == "categorical":
        return pl.DataFrame(
            dict(
                x=["A"] * 40 + ["B"] * 40,
                y=["yes"] * 30 + ["no"] * 10 + ["yes"] * 10 + ["no"] * 30,
            )
        )
    if path == "numeric":
        return pl.DataFrame(dict(x=[-2, -1, 0, 1, 2], y=[-2, 0, -1, 2, 1]))
    if path == "groups":
        return pl.DataFrame(
            dict(x=list(range(1, 16)), g=["A"] * 5 + ["B"] * 5 + ["C"] * 5)
        )
    return pl.DataFrame(dict(x=[1, 2, 3, 4, 3, 4, 5, 7], g=["A"] * 4 + ["B"] * 4))


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record = dict(
        environment="ENV-14",
        date="2026-10-08",
        python=platform.python_version(),
        platform=platform.platform(),
        package=str(veri_ufku.__file__),
        scipy=scipy.__version__,
        numpy=np.__version__,
        polars=pl.__version__,
        backend=os.environ["QT_QPA_PLATFORM"] + "/software",
        user_test=False,
        max_tick_gap_ms=0,
        peak_parent_worker_rss_bytes=0,
        methods={},
        screenshots=[],
        offline_policy="Python TCP denied in parent/spawn; OS interfaces not disabled; fresh XDG",
        cache="developer warm runtime; no minimum hardware claim",
    )
    record["api"] = {
        name: str(inspect.signature(getattr(stats, name)))
        for name in (
            "ttest_ind",
            "ttest_rel",
            "mannwhitneyu",
            "wilcoxon",
            "f_oneway",
            "kruskal",
            "chi2_contingency",
            "fisher_exact",
            "pearsonr",
            "spearmanr",
            "false_discovery_control",
        )
    }
    record["api"]["odds_ratio"] = str(inspect.signature(stats.contingency.odds_ratio))
    assert "equal_var" in inspect.signature(stats.f_oneway).parameters
    assert callable(stats.ttest_ind([1, 2, 3], [2, 3, 4]).confidence_interval)
    assert callable(stats.ttest_rel([1, 2, 3], [2, 4, 6]).confidence_interval)
    assert callable(stats.pearsonr([1, 2, 3, 4], [2, 3, 4, 6]).confidence_interval)
    with tempfile.TemporaryDirectory(
        prefix="vu-phase14-", dir=args.project_temp
    ) as temp:
        base = Path(temp)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        os.environ["MPLCONFIGDIR"] = str(base / "mpl")
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, controller = (
            engine._projects_resources,
            engine._imports_resources,
            engine._statistics_resources,
        )

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
                process = getattr(obj, "process", None)
                record["peak_parent_worker_rss_bytes"] = max(
                    record["peak_parent_worker_rss_bytes"],
                    rss(os.getpid()) + (rss(process.pid) if process else 0),
                )
                assert now - start < 60, (type(obj).__name__, obj.message)
            assert not getattr(obj, "errorText", ""), getattr(obj, "errorText", "")
            return (time.monotonic() - start) * 1000

        def field(name, prop, value):
            obj = window.findChild(QObject, "statistics" + name)
            assert obj is not None, name
            assert obj.setProperty(prop, value)
            return obj

        def shot(label, width):
            window.setWidth(width)
            window.setHeight(800)
            app.processEvents()
            QTest.qWait(150)
            image = args.output.with_name(args.output.stem + "-" + label + ".png")
            assert window.grabWindow().save(str(image))
            record["screenshots"].append(str(image))

        def import_frame(path, frame):
            source = base / (path + ".parquet")
            frame.write_parquet(source)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            imports.choose(str(source))
            wait(imports)
            imports.importData()
            wait(imports)
            engine._dataset_resources.selectDataset(
                projects.draft["datasets"][-1]["dataset_id"]
            )
            wait(engine._dataset_resources)
            window.setProperty("selectedSection", 4)
            app.processEvents()
            return source, digest

        try:
            assert projects.create(str(base / "project"))
            for path, methods in METHODS.items():
                source, digest = import_frame(path, fixture(path))
                cols = {c["name"]: i for i, c in enumerate(controller.columns)}
                for method in methods:
                    field("Settings", "checked", True)
                    field("Path", "currentIndex", list(METHODS).index(path))
                    app.processEvents()
                    field("Method", "currentIndex", list(methods).index(method))
                    field("X", "currentIndex", cols["x"])
                    if path in ("numeric", "categorical"):
                        field("Y", "currentIndex", cols["y"])
                    if path in ("independent", "groups", "paired"):
                        field(
                            "Group",
                            "currentIndex",
                            cols["phase" if path == "paired" else "g"],
                        )
                    if path == "paired":
                        field("Key", "currentIndex", cols["person"])
                        field("Before", "text", "before")
                        field("After", "text", "after")
                    for name, text in (
                        (
                            "Question",
                            "Ölçümler/gruplar arasında fark veya ilişki var mı?",
                        ),
                        ("Hypothesis", "Seçili yöntemin H0 hipotezi; keşifsel örnek"),
                        ("Unit", "puan / kategori: birimsiz"),
                        ("Observation", "Bağımsız kişi"),
                    ):
                        field(name, "text", text)
                    field("Measurement", "checked", True)
                    field("Independent", "checked", True)
                    field("Posthoc", "checked", path == "groups")
                    field("Assumptions", "checked", False)
                    window.findChild(QObject, "statisticsPreflight").clicked.emit()
                    pre_ms = wait(controller)
                    assert controller.preflightCurrent
                    if method == "paired_t":
                        shot("paired-form-720", 720)
                    checkbox = field("Assumptions", "checked", False)
                    window.findChild(QObject, "statisticsQuestion").forceActiveFocus()
                    QTest.qWait(100)
                    checkbox.forceActiveFocus()
                    QTest.qWait(100)
                    QTest.keyClick(window, Qt.Key_Space)
                    assert checkbox.property("checked")
                    if method == "paired_t":
                        shot("paired-preflight-720", 720)
                    button = window.findChild(QObject, "statisticsRun")
                    assert button.property("enabled")
                    button.forceActiveFocus()
                    QTest.qWait(100)
                    QTest.keyClick(window, Qt.Key_Space)
                    ms = wait(controller)
                    result = controller.result
                    assert result["worker_pid"] != os.getpid() and controller.current
                    if method == "welch_t":
                        shot("result-1366", 1366)
                        shot("result-720", 720)
                    record["methods"][method] = dict(
                        primary=result["primary"],
                        n=result["n"],
                        exclusions=result["exclusions"],
                        correction=result["correction"],
                        comparisons=result["comparisons"],
                        preflight_ms=pre_ms,
                        calculate_ms=ms,
                        worker_pid=result["worker_pid"],
                        source_sha256=digest,
                    )
                    window.findChild(QObject, "statisticsSave").clicked.emit()
                    wait(controller)
                    engine._learning_resources.openContext(
                        "statistics." + method.replace("_", "-")
                    )
                    assert engine._learning_resources.article[
                        "id"
                    ] == "statistics-" + method.replace("_", "-")
                assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
            root = str(projects.store.root)
            assert projects.closeProject(True) and projects.open(root)
            analyses = [r for r in projects.draft["results"] if "analysis" in r]
            assert len(analyses) == 11
            for analysis in analyses:
                controller.openSaved(analysis["id"])
                assert not controller.errorText
                assert controller.result["primary"] == analysis["analysis"]["primary"]
            record["saved_reopened"] = len(analyses)
            saved_version = analyses[0]["analysis"]["dataset_version"]
            saved_dataset = next(
                d
                for d in projects.draft["datasets"]
                if d["version_id"] == saved_version
            )
            engine._dataset_resources.selectDataset(saved_dataset["dataset_id"])
            wait(engine._dataset_resources)
            controller.openSaved(analyses[0]["id"])
            controller.save()
            wait(controller)
            record["saved_result_resave"] = True
            window.findChild(QObject, "statisticsSaved").forceActiveFocus()
            QTest.keyClick(window, Qt.Key_F1)
            app.processEvents()
            record["f1_context"] = engine._learning_resources.article["id"]
            assert record["f1_context"] == "statistics"
            assert projects.closeProject(True) and projects.create(
                str(base / "large-project")
            )
            source, digest = import_frame(
                "large", pl.DataFrame(dict(x=range(100000), g=["A", "B"] * 50000))
            )
            cols = {c["name"]: c["id"] for c in controller.columns}
            spec = dict(
                path="independent",
                method="welch_t",
                x=cols["x"],
                group=cols["g"],
                question="Ortalama farkı?",
                hypothesis="Ortalamalar eşit",
                unit="puan",
                observation_unit="bağımsız kayıt",
                independent=True,
                measurement_confirmed=True,
            )
            controller.create(json.dumps(spec), True)
            pre_ms = wait(controller)
            controller.create(json.dumps(dict(spec, assumptions_confirmed=True)), False)
            ms = wait(controller)
            assert controller.result["n"] == [50000, 50000]
            record["large"] = dict(
                rows=100000,
                n=controller.result["n"],
                preflight_ms=pre_ms,
                calculate_ms=ms,
                primary=controller.result["primary"],
            )
            previous = controller.result["result_version"]
            controller.create(json.dumps(dict(spec, assumptions_confirmed=True)), False)
            controller.cancel()
            cancel_ms = wait(controller)
            assert (
                controller.result["result_version"] == previous
                and "İptal" in controller.message
            )
            record["cancel_ms"] = cancel_ms
            record["cancel_previous_result_preserved"] = True
            controller.create(json.dumps(spec), True)
            controller.invalidate()
            wait(controller)
            assert not controller.preflightCurrent
            record["stale_preflight_discarded"] = True
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
            record["all_sources_unchanged"] = True
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print("PHASE14_PASS", args.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--project-temp", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase14/headless.json")
    )
    run(parser.parse_args())
