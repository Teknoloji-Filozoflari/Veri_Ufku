"""Real source/noneditable wheel QML, fit/mark/reopen, full limits and render evidence."""

import argparse
import hashlib
import json
import os
import platform
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("POLARS_MAX_THREADS", "2")

import polars as pl  # noqa: E402
from PySide6.QtCore import QObject  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402


def visual_find(item, name):
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = visual_find(child, name)
        if found is not None:
            return found
    return None


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
        environment="ENV-19",
        evaluated_at=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        platform=platform.platform(),
        package=str(veri_ufku.__file__),
        runs=[],
        screenshots=[],
        max_tick_ms=0,
        peak_rss_bytes=0,
    )
    with tempfile.TemporaryDirectory(prefix="vu-phase19-") as temporary:
        base = Path(temporary)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports = engine._projects_resources, engine._imports_resources
        c = engine._unsupervised_resources
        assert projects.create(str(base / "project"))

        def spin(predicate, timeout=180):
            start = time.monotonic()
            last = start
            while time.monotonic() - start < timeout:
                app.processEvents()
                now = time.monotonic()
                record["max_tick_ms"] = max(record["max_tick_ms"], (now - last) * 1000)
                last = now
                total = rss(os.getpid())
                if c.process and c.process.pid:
                    total += rss(c.process.pid)
                record["peak_rss_bytes"] = max(record["peak_rss_bytes"], total)
                if predicate():
                    return
                QTest.qWait(10)
            raise AssertionError("Phase19 timed out")

        def shot(tag, width, height):
            window.resize(width, height)
            QTest.qWait(100)
            app.processEvents()
            path = args.output.parent / (args.output.stem + "-" + tag + f"-{width}.png")
            assert window.grabWindow().save(str(path))
            record["screenshots"].append(str(path))

        try:
            window.setProperty("selectedSection", 5)
            for method, n in (
                ("kmeans", 240),
                ("dbscan", 240),
                ("isolation_forest", 240),
                ("iqr", 240),
                ("kmeans", 100000),
                ("dbscan", 3000),
                ("isolation_forest", 100000),
                ("iqr", 100000),
            ):
                source = base / f"{method}-{n}.parquet"
                # Two narrow separated measurement regions and rare far-away records.
                values = [(i % 20) / 100 + (0 if i < n // 2 else 10) for i in range(n)]
                values[-1] = 100.0
                pl.DataFrame(dict(x=values, note=["kaynak"] * n)).write_parquet(source)
                original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                imports.choose(str(source))
                spin(lambda: not imports.busy)
                imports.importData()
                spin(lambda: not imports.busy)
                assert not imports.errorText, imports.errorText
                engine._dataset_resources.selectDataset(
                    projects.draft["datasets"][-1]["dataset_id"]
                )
                spin(lambda: not projects.busy)
                assert c.data.dataset()["import_metadata"]["row_count"] == n
                purpose = window.findChild(QObject, "preparationPurpose")
                purpose.setProperty(
                    "currentIndex", 2 if method in ("kmeans", "dbscan") else 3
                )
                panel = window.findChild(QObject, "unsupervisedPanel")
                feature_id = next(col["id"] for col in c.columns if col["name"] == "x")
                panel.setProperty("chosenFeatures", [feature_id])
                window.findChild(QObject, "unsupervisedMethod").setProperty(
                    "currentIndex", int(method in ("dbscan", "iqr"))
                )
                window.findChild(QObject, "unsupervisedClusters").setProperty(
                    "text", "2"
                )
                window.findChild(QObject, "unsupervisedEps").setProperty("text", "0.1")
                window.findChild(QObject, "unsupervisedNeighbors").setProperty(
                    "text", "5"
                )
                start = time.monotonic()
                assert window.findChild(QObject, "unsupervisedRun").property("enabled")
                window.findChild(QObject, "unsupervisedRun").clicked.emit()
                spin(lambda: not c.busy)
                assert not c.errorText, c.errorText
                assert c.result["worker_pid"] != os.getpid() and c.current
                assert c.report["rows"] == n and c.report["spec"]["method"] == method
                if method == "dbscan":
                    assert (
                        not c.report["new_data"]["native_support"]
                        and c.report["noise_count"] > 0
                    )
                if method in ("isolation_forest", "iqr"):
                    assert c.report["flagged_count"] > 0
                ident = c.record_id
                row = dict(
                    method=method,
                    rows=n,
                    seconds=time.monotonic() - start,
                    worker_pid=c.result["worker_pid"],
                    silhouette=c.report["silhouette"],
                    flagged_count=c.report["flagged_count"],
                    noise_count=c.report["noise_count"],
                    source_sha256=original_hash,
                )
                if n == 240:
                    # FocusScroll reveals the actual result below settings before capture.
                    button = window.findChild(QObject, "unsupervisedTransfer")
                    button.forceActiveFocus()
                    QTest.qWait(100)
                    shot(method, 1366, 900)
                    button.forceActiveFocus()
                    shot(method, 720, 560)
                window.findChild(QObject, "unsupervisedTransfer").clicked.emit()
                spin(lambda: not c.busy)
                assert not c.errorText, c.errorText
                d = projects.draft["datasets"][-1]
                source_dataset = next(
                    d
                    for d in projects.draft["datasets"]
                    if d["version_id"] == c.report["dataset_version"]
                )
                old = pl.read_parquet(
                    projects.store.path(source_dataset["snapshot_uri"])
                )
                marked = pl.read_parquet(projects.store.path(d["snapshot_uri"]))
                assert marked.height == n and marked.select(old.columns).equals(old)
                root = str(projects.store.root)
                assert projects.closeProject(True) and projects.open(root)
                c.openSaved(ident)
                spin(lambda: not c.busy)
                assert not c.errorText and c.report["spec"]["method"] == method
                assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
                row["marked_version"] = d["version_id"]
                record["runs"].append(row)
                print(f"PASS {method} rows={n} {row['seconds']:.3f}s", flush=True)
            learning = engine._learning_resources
            for key in ("cluster", "distance", "noise", "score", "evaluation"):
                learning.openContext("unsupervised." + key)
                assert learning.article["id"] == "unsupervised-" + key
            record["status"] = "passed"
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(
        "PASS: Phase19 real QML/fit/mark/reopen/source preservation and offline help",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase19/headless.json")
    )
    run(parser.parse_args())
