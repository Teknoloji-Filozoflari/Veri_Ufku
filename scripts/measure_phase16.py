"""Real split/baseline/final journal in source or noneditable Linux wheel."""

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
        environment="ENV-16",
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
        prefix="vu-phase16-", dir=args.project_temp
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
            target = (
                window.findChild(QObject, "validationSummary")
                if "result" in label
                else panel
            )
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
                ("independent", "regression", "random", 240),
                ("independent", "classification", "stratified", 240),
                ("group", "classification", "auto", 240),
                ("time", "regression", "auto", 240),
                ("group_time", "classification", "auto", 240),
                ("independent", "regression", "random", 100000),
            ]:
                frame = pl.DataFrame(
                    dict(
                        x=[float(i) for i in range(n)],
                        cat=["ABC"[i % 3] for i in range(n)],
                        y=[
                            i % 2 if purpose == "classification" else float(i % 7)
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
                            purpose=purpose,
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
                button = window.findChild(QObject, "validationRun")
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
                        purpose=purpose,
                        n=n,
                        split_id=development["plan"]["split_id"],
                        protocol_id=development["plan"]["protocol_id"],
                        cost=development["estimated_cost"],
                        elapsed_seconds=elapsed,
                        metrics=[e["metrics"] for e in development["evaluations"]],
                        packages=development["packages"],
                        source_sha256=source_hash,
                        details_artifact=bool(saved["baseline"].get("details_uri")),
                    )
                )
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
        "--output", type=Path, default=Path("docs/evidence/phase16/headless.json")
    )
    run(parser.parse_args())
