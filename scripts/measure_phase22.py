"""Real source/wheel offline text, classification fold, privacy, QML and 100k evidence."""

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
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("POLARS_MAX_THREADS", "2")
original_connect = socket.socket.connect


def offline_connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise RuntimeError("Offline evidence: Python TCP denied")
    return original_connect(self, address)


socket.socket.connect = offline_connect

import polars as pl  # noqa: E402
from PySide6.QtCore import QObject, QPointF  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.analytics.text import TextSpec  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402
from veri_ufku.modeling.classification import settings  # noqa: E402
from veri_ufku.modeling.validation import ValidationSpec  # noqa: E402


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record = dict(
        environment="ENV-22",
        evaluated_at=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        platform=platform.platform(),
        package=str(veri_ufku.__file__),
        backend="offscreen/software",
        user_test=False,
        offline_policy="Python TCP denied in parent and spawn; OS interfaces not disabled; no offline installation claim",
        runs=[],
        screenshots=[],
        max_tick_ms=0,
    )
    with tempfile.TemporaryDirectory(prefix="vu-phase22-") as temporary:
        base = Path(temporary)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, data, c = (
            engine._projects_resources,
            engine._imports_resources,
            engine._dataset_resources,
            engine._text_resources,
        )

        def wait(obj):
            start = last = time.monotonic()
            while obj.busy:
                app.processEvents()
                QTest.qWait(10)
                now = time.monotonic()
                record["max_tick_ms"] = max(record["max_tick_ms"], (now - last) * 1000)
                last = now
                assert now - start < 180, obj.message
            assert not obj.errorText, obj.errorText
            return time.monotonic() - start

        try:
            assert projects.create(str(base / "project"))
            window.setProperty("selectedSection", 5)
            window.findChild(QObject, "modelPath").setProperty("currentIndex", 2)
            for n in (120, 100000):
                source = base / f"text-{n}.parquet"
                texts = [
                    ("IŞIK sıcak SAKLI987" if i % 2 else "yağmur soğuk")
                    for i in range(n)
                ]
                if n == 120:
                    texts[0] = None
                    texts[2] = ""
                    texts[4] = " \t"
                frame = pl.DataFrame(
                    dict(
                        text=texts,
                        label=["sıcak" if i % 2 else "soğuk" for i in range(n)],
                    )
                )
                frame.write_parquet(source)
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                imports.choose(str(source))
                wait(imports)
                imports.importData()
                wait(imports)
                data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
                wait(data)
                d = data.dataset()
                cols = {
                    col["name"]: col["id"] for col in d["import_metadata"]["columns"]
                }
                s = TextSpec(cols["text"], preview=n == 120, similarity=n == 120)
                c.restoreRequested.emit(json.dumps(s.data()))
                c.create(json.dumps(s.data()))
                elapsed = wait(c)
                assert c.current and c.result["worker_pid"] != os.getpid()
                assert c.report["candidate_vocab"] == 5
                saved = c.record_id
                assert not next(
                    r["text_analysis"]
                    for r in projects.draft["results"]
                    if r["id"] == saved
                )["previews"]
                assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
                record["runs"].append(
                    dict(
                        rows=n,
                        seconds=elapsed,
                        worker_pid=c.result["worker_pid"],
                        null=c.report["null_text"],
                        empty=c.report["empty_text"],
                        whitespace=c.report["whitespace_text"],
                        candidate_vocab=c.report["candidate_vocab"],
                        retained_vocab=c.report["retained_vocab"],
                        source_sha256=digest,
                        raw_preview_persisted=False,
                    )
                )
                if n == 120:
                    for width, height in ((1366, 900), (720, 560)):
                        window.resize(width, height)
                        app.processEvents()
                        QTest.qWait(150)
                        for tag, target_name in (
                            ("settings", "textPanel"),
                            ("frequencies", "textFrequencyGraph"),
                        ):
                            target = window.findChild(QObject, target_name)
                            flick = window.findChild(QObject, "workspace").property(
                                "contentItem"
                            )
                            pos = target.mapToItem(
                                flick, QPointF(0, 0)
                            ).y() + flick.property("contentY")
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
                            QTest.qWait(150)
                            shot = args.output.with_name(
                                args.output.stem + f"-{tag}-{width}.png"
                            )
                            assert window.grabWindow().save(str(shot))
                            record["screenshots"].append(str(shot))
                    prep = engine._preparation_resources
                    validation = engine._validation_resources
                    prep.create(
                        json.dumps(
                            dict(
                                purpose="classification",
                                features=[cols["text"]],
                                target=cols["label"],
                                family="linear",
                                text=TextSpec(cols["text"]).data(),
                                prediction_context="Metin önceden bilinir",
                            )
                        )
                    )
                    wait(prep)
                    assert not prep.result["blockers"]
                    protocol = ValidationSpec(
                        prediction_moment="Metin önceden bilinir",
                        availability={
                            cols["text"]: dict(offset_seconds=0, note="Önceden bilinir")
                        },
                    )
                    validation.createClassification(
                        json.dumps(protocol.data()),
                        json.dumps(
                            settings(
                                dict(
                                    candidates=["baseline", "logistic", "forest"],
                                    positive_class="sıcak",
                                )
                            )
                        ),
                    )
                    wait(validation)
                    assert validation.result["selected_model"] == "logistic"
                    membership = validation.result["plan"]["membership"]
                    test_ids = set(membership["test"])
                    for comparison in validation.result["comparison"]:
                        for evaluation in comparison["evaluations"]:
                            assert not set(evaluation["fit_row_ids"]) & test_ids
                    compared_candidates = [
                        row["model"] for row in validation.result["comparison"]
                    ]
                    validation.evaluateTest()
                    wait(validation)
                    assert validation.result["mode"] == "final"
                    record["classification"] = dict(
                        selected="logistic",
                        compared_candidates=compared_candidates,
                        final_journal=True,
                        text_fold_fit=True,
                        package_available=False,
                    )
                wait(projects)
                root = str(projects.store.root)
                assert projects.closeProject(True), projects.errorText
                assert projects.open(root), projects.errorText
                data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
                wait(data)
                c.openSaved(saved)
                wait(c)
                assert c.current and not c.report["previews"]
                print(f"PASS offline text rows={n} {elapsed:.3f}s", flush=True)
            for context in (
                "text.tokens",
                "text.language",
                "text.tfidf",
                "text.similarity",
            ):
                engine._learning_resources.openContext(context)
                assert engine._learning_resources.article["id"].startswith("text-")
            for path in base.rglob("*.log"):
                assert "SAKLI987" not in path.read_text(errors="replace")
            record["status"] = "passed"
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(
        "PASS Phase22 offline local text, Turkish, training vocab, privacy and reopen",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase22/source.json")
    )
    run(parser.parse_args())
