"""Actual source/noneditable NLP GUI paths, synthetic fixtures, no network."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = args.package_root or ROOT / "src"
    sys.path.insert(0, str(package))
    sys.path.insert(1, str(ROOT / "tests"))
    os.environ.update(
        PYTHONPATH=str(package),
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
    )
    import veri_ufku

    assert Path(veri_ufku.__file__).is_relative_to(package)
    import pytest
    import test_nlp_gui as cases
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest

    args.output.mkdir(parents=True, exist_ok=True)
    records = []

    def capture(app, window, projects, c, method):
        folder = args.output / method
        folder.mkdir(exist_ok=True)
        value = c.result
        path = folder / "run.json"
        path.write_text(
            json.dumps(
                {k: v for k, v in value.items() if k != "worker_pid"},
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
            )
            + "\n"
        )
        from veri_ufku.storage.experiment_store import export

        exported = folder / "registry.json"
        export(projects.store, [value["run_id"]], exported)
        assert "Scheduled and known" not in exported.read_text()
        files = []
        for width in (1000, 1366):
            window.setWidth(width)
            app.processEvents()
            item = window.findChild(QObject, "nlpReport")
            parent = item.parentItem()
            while parent is not None:
                if parent.property("contentY") is not None:
                    position = item.mapToItem(parent.property("contentItem"), 0, 0)
                    parent.setProperty("contentY", max(0, position.y() - 20))
                    break
                parent = parent.parentItem()
            QTest.qWait(100)
            image = folder / f"nlp-{width}.png"
            assert window.grabWindow().save(str(image))
            files.append(
                dict(
                    path=str(image.relative_to(args.output)),
                    sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                )
            )
        files.extend(
            dict(
                path=str(f.relative_to(args.output)),
                sha256=hashlib.sha256(f.read_bytes()).hexdigest(),
            )
            for f in (path, exported)
        )
        records.append(
            dict(
                method=method,
                status="passed",
                run_id=value["run_id"],
                run_status=value["status"],
                document_count=value["rows"],
                provenance=value["advanced"]["provenance"],
                files=files,
            )
        )

    cases.CAPTURE = capture
    for method in cases.METHODS:
        with tempfile.TemporaryDirectory(prefix="veri-ufku-f55-") as td:
            patch = pytest.MonkeyPatch()
            try:
                cases.test_real_nlp_gui(Path(td), patch, method)
            finally:
                patch.undo()
        print("PASS", method, flush=True)
    (args.output / "walkthrough.json").write_text(
        json.dumps(
            dict(
                id="E55-GUI",
                environment="ENV-55",
                date=datetime.now(UTC).isoformat(),
                package=str(package),
                scope="Actual NLP QML/spawn/local safe bundle/topic human naming/annotation revision/export/offset/embeddings/sentiment/active pool/retrieval/offline model-deleted reopen/help;CPU/offscreen/software",
                cases=records,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
