"""Real classification comparison/curves/final journal in source or noneditable Linux wheel."""

import argparse
import hashlib
import json
import os
import platform
import tempfile
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import polars as pl  # noqa: E402
from PySide6.QtCore import QObject, QPointF  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402


def rss(pid):
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError):
        pass
    return 0


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record = dict(
        environment="ENV-18",
        evaluated_at=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        platform=platform.platform(),
        package=str(veri_ufku.__file__),
        backend="offscreen/software",
        user_test=False,
        runs=[],
        screenshots=[],
        max_tick_gap_ms=0,
        peak_parent_worker_rss_bytes=0,
        limit_note="Geliştirici makinesi, sıcak runtime; minimum donanım/insan masaüstü kabulü değildir.",
    )
    with tempfile.TemporaryDirectory(
        prefix="vu-phase18-", dir=args.project_temp
    ) as temporary:
        base = Path(temporary)
        for key in ("CONFIG", "CACHE", "STATE"):
            os.environ[f"XDG_{key}_HOME"] = str(base / key.lower())
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, p, c = (
            engine._projects_resources,
            engine._imports_resources,
            engine._preparation_resources,
            engine._validation_resources,
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
                proc = getattr(obj, "process", None)
                record["peak_parent_worker_rss_bytes"] = max(
                    record["peak_parent_worker_rss_bytes"],
                    rss(os.getpid()) + (rss(proc.pid) if proc and proc.pid else 0),
                )
                last = now
                assert now - start < 120, obj.message
            assert not getattr(obj, "errorText", ""), getattr(obj, "errorText", "")
            return time.monotonic() - start

        def shot(label, width):
            window.setWidth(width)
            window.setHeight(800)
            app.processEvents()
            QTest.qWait(100)
            # Bring the new panel into view in the shared scrolling workspace.
            panel = window.findChild(QObject, "validationPanel")

            def visual_find(item, name):
                if item.objectName() == name:
                    return item
                for child in item.childItems():
                    found = visual_find(child, name)
                    if found:
                        return found
                return None

            target = (
                window.findChild(QObject, "classificationScope")
                if "result" in label
                else panel
            )
            if "matrix" in label:
                target = visual_find(
                    window.contentItem(), "classificationConfusionMatrix"
                )
            if "curve" in label:
                target = visual_find(window.contentItem(), "classificationCurve")
            assert target, label
            flick = window.findChild(QObject, "workspace").property("contentItem")
            position = target.mapToItem(flick, QPointF(0, 0)).y() + flick.property(
                "contentY"
            )
            flick.setProperty(
                "contentY",
                max(
                    0,
                    min(
                        position,
                        flick.property("contentHeight") - flick.property("height"),
                    ),
                ),
            )
            path = args.output.with_name(args.output.stem + "-" + label + ".png")
            assert window.grabWindow().save(str(path))
            record["screenshots"].append(str(path))

        try:
            assert projects.create(str(base / "project"))
            for structure, purpose, method, n in [
                ("independent", "binary", "stratified", 240),
                ("independent", "multiclass", "stratified", 240),
                ("group_time", "binary", "auto", 240),
                ("independent", "binary", "stratified", 20000),
                ("independent", "binary", "stratified", 100000),
            ]:
                frame = pl.DataFrame(
                    dict(
                        x=[float(i % 8) for i in range(n)],
                        cat=["ABC"[i % 3] for i in range(n)],
                        y=[
                            ("risk" if i % 8 >= 6 else "normal")
                            if purpose == "binary"
                            else ("C" if i % 8 >= 6 else "B" if i % 8 >= 4 else "A")
                            for i in range(n)
                        ],
                        group=[f"g{i // 4:06}" for i in range(n)],
                        when=[date(2024, 1, 1) + timedelta(days=i) for i in range(n)],
                    )
                )
                source = base / (structure + purpose + str(n) + ".parquet")
                frame.write_parquet(source)
                source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                imports.choose(str(source))
                wait(imports)
                imports.importData()
                wait(imports)
                data = engine._dataset_resources
                data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
                wait(data)
                cols = {x["name"]: x["id"] for x in p.columns}
                p.create(
                    json.dumps(
                        dict(
                            purpose="classification",
                            target=cols["y"],
                            features=[cols["x"], cols["cat"]],
                            group=cols["group"]
                            if structure in ("group", "group_time")
                            else "",
                            time=cols["when"]
                            if structure in ("time", "group_time")
                            else "",
                            prediction_context="Cihaz çalıştırılmadan önce",
                            numeric_imputation="mean",
                            scaling="standard",
                            selection="variance",
                        )
                    )
                )
                wait(p)
                assert not p.result["blockers"]
                window.findChild(QObject, "preparationSettings").setProperty(
                    "checked", False
                )
                window.setProperty("selectedSection", 5)
                app.processEvents()
                panel = window.findChild(QObject, "validationPanel")
                panel.setProperty(
                    "availability",
                    {
                        cols[i]: dict(
                            offset_seconds=0, note="Cihazı çalıştırmadan önce mevcut"
                        )
                        for i in ("x", "cat")
                    },
                )
                window.findChild(QObject, "validationMethod").setProperty(
                    "currentIndex",
                    1 if method == "random" else 2 if method == "stratified" else 0,
                )
                positive = window.findChild(QObject, "classificationPositive")
                if purpose == "binary":
                    positive.setProperty(
                        "currentIndex",
                        next(
                            i
                            for i, v in enumerate(
                                p.report["target"]["class_distribution"]
                            )
                            if v["label"] == "risk"
                        ),
                    )
                window.findChild(QObject, "classificationThresholdMode").setProperty(
                    "currentIndex", 2 if purpose == "binary" else 0
                )
                window.findChild(QObject, "classificationCost").setProperty(
                    "text", "Kaçırılan kayıt daha maliyetli"
                )
                if n == 100000:
                    panel_spec = dict(
                        structure="independent",
                        method="stratified",
                        prediction_moment="Ölçüm öncesi",
                        availability={
                            cols[i]: dict(offset_seconds=0, note="Önceden mevcut")
                            for i in ("x", "cat")
                        },
                    )
                    c.createClassification(
                        json.dumps(panel_spec),
                        json.dumps(
                            dict(
                                candidates=["baseline", "logistic"],
                                positive_class="risk",
                                threshold_mode="validation_f1",
                                cost_note="Kaçırılan kayıt daha maliyetli",
                            )
                        ),
                    )
                    button = None
                else:
                    button = window.findChild(QObject, "classificationRun")
                if button:
                    assert button.property("enabled")
                    button.clicked.emit()
                elapsed = wait(c)
                assert (
                    c.result["status"] == "completed"
                    and c.result["worker_pid"] != os.getpid()
                )
                development = c.result
                saved = next(
                    r
                    for r in projects.draft["results"]
                    if r.get("baseline", {}).get("run_id") == development["run_id"]
                )
                record["runs"].append(
                    dict(
                        structure=structure,
                        purpose="classification",
                        n=n,
                        split_id=development["plan"]["split_id"],
                        protocol_id=development["plan"]["protocol_id"],
                        cost=development["estimated_cost"],
                        elapsed_seconds=elapsed,
                        metrics=[e["metrics"] for e in development["evaluations"]],
                        classes=development["classes"],
                        decision={
                            k: v
                            for k, v in development["decision"].items()
                            if k != "validation_row_ids"
                        },
                        confusion_matrix=development["decision_validation"][
                            "confusion_matrix"
                        ],
                        per_class=development["decision_validation"]["per_class"],
                        packages=development["packages"],
                        selected_model=development["selected_model"],
                        comparison=[
                            dict(model=c["model"], cv_f1=c["cv_f1"])
                            for c in development["comparison"]
                        ],
                        source_sha256=source_hash,
                        details_artifact=bool(saved["baseline"].get("details_uri")),
                    )
                )
                if purpose == "multiclass":
                    shot("multiclass-result-1366", 1366)
                    shot("multiclass-matrix-720", 720)
                if structure == "group_time":
                    window.findChild(QObject, "validationSettings").setProperty(
                        "checked", False
                    )
                    for number in range(2):
                        c.openRun(saved["id"])
                        wait(c)
                        window.findChild(QObject, "validationTestConsent").setProperty(
                            "checked", True
                        )
                        window.findChild(QObject, "validationTest").clicked.emit()
                        wait(c)
                        assert (
                            c.result["mode"] == "final"
                            and c.result["plan"] == development["plan"]
                        )
                    assert len(c.testHistory) == 2
                    record["test_history"] = c.testHistory
                    shot("result-720", 720)
                    shot("result-1366", 1366)
                    shot("matrix-1366", 1366)
                    shot("curve-720", 720)
                    window.findChild(QObject, "classificationC").setProperty(
                        "currentIndex", 2
                    )
                    window.findChild(
                        QObject, "classificationThresholdMode"
                    ).setProperty("currentIndex", 1)
                    window.findChild(QObject, "classificationThreshold").setProperty(
                        "text", "0.35"
                    )
                    window.findChild(QObject, "classificationPositive").setProperty(
                        "currentIndex", 1 - positive.property("currentIndex")
                    )
                    window.findChild(QObject, "classificationRun").clicked.emit()
                    wait(c)
                    assert c.result["interpretation"] == "exploratory"
                    assert c.choiceHistory[-1]["classification"]["C"] == 10
                    record["retuning_after_test"] = c.choiceHistory[-1]
                    c.openRun(saved["id"])
                    wait(c)
                    learning = engine._learning_resources
                    for ctx in (
                        "model.classification",
                        "classification.positive",
                        "classification.metrics",
                        "classification.threshold",
                        "classification.probability",
                    ):
                        learning.openContext(ctx)
                        assert learning.article["id"] == ctx.replace(".", "-")
                    record["offline_help"] = True
                if n == 100000:
                    assert saved["baseline"].get("details_uri")
                    c.openRun(saved["id"])
                    wait(c)
                    assert c.result["plan"] == development["plan"]
                assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
            root = str(projects.store.root)
            assert projects.closeProject(True) and projects.open(root)
            assert len(c.testHistory) == 2
            record["reopened_journal"] = True
            record["choice_history"] = c.choiceHistory
        finally:
            projects.draft = projects.saved
            window.close()
            app.processEvents()
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--project-temp", default="/tmp")
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase18/headless.json")
    )
    run(parser.parse_args())
