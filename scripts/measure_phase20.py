"""Source/wheel real model package, new-file inference and RowId evidence."""

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

import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
from PySide6.QtCore import QObject, QPointF, QUrl  # noqa: E402
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
        environment="ENV-20",
        evaluated_at=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        platform=platform.platform(),
        package=str(veri_ufku.__file__),
        backend="offscreen/software",
        user_test=False,
        runs=[],
        screenshots=[],
        max_tick_ms=0,
        peak_rss_bytes=0,
    )
    with tempfile.TemporaryDirectory(prefix="vu-phase20-") as temporary:
        base = Path(temporary)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, data, prep, validation, lifecycle = (
            engine._projects_resources,
            engine._imports_resources,
            engine._dataset_resources,
            engine._preparation_resources,
            engine._validation_resources,
            engine._lifecycle_resources,
        )

        def wait(obj):
            start = last = time.monotonic()
            while obj.busy:
                app.processEvents()
                QTest.qWait(10)
                now = time.monotonic()
                record["max_tick_ms"] = max(record["max_tick_ms"], (now - last) * 1000)
                proc = getattr(obj, "process", None)
                record["peak_rss_bytes"] = max(
                    record["peak_rss_bytes"],
                    rss(os.getpid()) + (rss(proc.pid) if proc and proc.pid else 0),
                )
                last = now
                assert now - start < 180, obj.message
            assert not obj.errorText, obj.errorText
            return time.monotonic() - start

        def imported(frame, name):
            source = base / (name + ".parquet")
            frame.write_parquet(source)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            imports.choose(str(source))
            wait(imports)
            imports.importData()
            wait(imports)
            data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
            wait(data)
            return source, digest

        def url(path):
            return QUrl.fromLocalFile(str(path)).toString()

        def shot(tag, target_name):
            for width, height in ((1366, 900), (720, 560)):
                window.resize(width, height)
                app.processEvents()
                QTest.qWait(100)
                target = window.findChild(QObject, target_name)
                flick = window.findChild(QObject, "workspace").property("contentItem")
                pos = target.mapToItem(flick, QPointF(0, 0)).y() + flick.property(
                    "contentY"
                )
                flick.setProperty(
                    "contentY",
                    max(
                        0,
                        min(
                            pos,
                            flick.property("contentHeight") - flick.property("height"),
                        ),
                    ),
                )
                QTest.qWait(100)
                path = args.output.with_name(args.output.stem + f"-{tag}-{width}.png")
                assert window.grabWindow().save(str(path))
                record["screenshots"].append(str(path))

        try:
            assert projects.create(str(base / "project"))
            window.setProperty("selectedSection", 5)
            for purpose in ("regression", "classification"):
                x = np.arange(240, dtype=float) % 20
                frame = pl.DataFrame(
                    dict(
                        x=x,
                        cat=["AB"[i % 2] for i in range(240)],
                        y=3 * x + 7
                        if purpose == "regression"
                        else ["risk" if v >= 10 else "normal" for v in x],
                    )
                )
                source, digest = imported(frame, purpose + "-train")
                cols = {c["name"]: c["id"] for c in prep.columns}
                prep.create(
                    json.dumps(
                        dict(
                            purpose=purpose,
                            target=cols["y"],
                            features=[cols["x"], cols["cat"]],
                            prediction_context="Ölçüm öncesi",
                            scaling="standard",
                        )
                    )
                )
                wait(prep)
                assert not prep.result["blockers"]
                window.findChild(QObject, "validationPanel").setProperty(
                    "availability",
                    {
                        cols[n]: dict(offset_seconds=0, note="Önceden bilinir")
                        for n in ("x", "cat")
                    },
                )
                if purpose == "regression":
                    window.findChild(QObject, "regressionUnit").setProperty(
                        "text", "TL"
                    )
                    button = window.findChild(QObject, "regressionRun")
                else:
                    positive = window.findChild(QObject, "classificationPositive")
                    positive.setProperty(
                        "currentIndex",
                        next(
                            i
                            for i, v in enumerate(
                                prep.report["target"]["class_distribution"]
                            )
                            if v["label"] == "risk"
                        ),
                    )
                    button = window.findChild(QObject, "classificationRun")
                assert button.property("enabled")
                button.clicked.emit()
                wait(validation)
                saved = next(
                    r
                    for r in projects.draft["results"]
                    if r.get("baseline", {}).get("run_id")
                    == validation.result["run_id"]
                )
                lifecycle.selectModel(saved["id"])
                wait(lifecycle)
                card = lifecycle.card
                assert lifecycle.result["worker_pid"] != os.getpid()
                package = base / (purpose + " model #1.vumodel")
                lifecycle.savePackage(url(package))
                wait(lifecycle)
                lifecycle.openPackage(url(package))
                wait(lifecycle)
                assert lifecycle.card == card
                shot(purpose + "-card", "lifecycleCard")
                for n in (6, 100000):
                    # Duplicate measurement content and reordered physical columns.
                    values = np.arange(n, dtype=float) % 20
                    fresh = pl.DataFrame(
                        dict(
                            note=["yeni"] * n,
                            cat=["AB"[i % 2] for i in range(n)],
                            x=values,
                        )
                    ).select("cat", "note", "x")
                    new_source, new_digest = imported(fresh, purpose + f"-new-{n}")
                    lifecycle.previewData("reject", 127)
                    preview_seconds = wait(lifecycle)
                    assert (
                        lifecycle.previewReport["rows"] == n
                        and not lifecycle.previewReport["blockers"]
                    )
                    output = base / (purpose + f"-prediction-{n}.parquet")
                    lifecycle.predictData(url(output), "reject", 127)
                    elapsed = wait(lifecycle)
                    result = pl.read_parquet(output)
                    original = pl.read_parquet(
                        projects.store.path(data.dataset()["snapshot_uri"])
                    )
                    assert result.select(original.columns).equals(original)
                    assert result["__vu_row_id"].n_unique() == n
                    assert lifecycle.outputReport["details"]["fit_calls"] == 0
                    if purpose == "regression":
                        np.testing.assert_allclose(
                            result["vu_prediction"].to_numpy(),
                            3 * values + 7,
                            atol=1e-9,
                        )
                    else:
                        assert result["vu_prediction"].to_list() == [
                            "risk" if v >= 10 else "normal" for v in values
                        ]
                        assert (
                            lifecycle.outputReport["details"]["label_order"]
                            == card["label_order"]
                        )
                    assert (
                        hashlib.sha256(new_source.read_bytes()).hexdigest()
                        == new_digest
                    )
                    record["runs"].append(
                        dict(
                            purpose=purpose,
                            estimator=card["estimator"],
                            rows=n,
                            preview_seconds=preview_seconds,
                            predict_seconds=elapsed,
                            fit_calls=0,
                            worker_pid=lifecycle.result["worker_pid"],
                            source_sha256=new_digest,
                            output_sha256=hashlib.sha256(
                                output.read_bytes()
                            ).hexdigest(),
                        )
                    )
                    if n == 6:
                        shot(purpose + "-preview", "lifecyclePreview")
                        shot(purpose + "-output", "lifecycleOutput")
                    print(f"PASS {purpose} new rows={n} {elapsed:.3f}s", flush=True)
                root = str(projects.store.root)
                assert projects.closeProject(True) and projects.open(root)
                lifecycle.selectModel(saved["id"])
                wait(lifecycle)
                assert lifecycle.card == card
                assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
            for context in (
                "card",
                "importance",
                "unknown-category",
                "new-data",
                "uncertainty",
            ):
                engine._learning_resources.openContext("model." + context)
                assert engine._learning_resources.article["id"] == "model-" + context
            record["status"] = "passed"
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(
        "PASS Phase20 package/reopen/new-file/batch/RowId/source and help", flush=True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase20/source.json")
    )
    run(parser.parse_args())
