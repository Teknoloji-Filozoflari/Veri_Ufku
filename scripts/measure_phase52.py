"""Actual source/noneditable Qt registry flow; synthetic data only, no network."""

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
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        PYTHONPATH=str(package),
    )
    import veri_ufku

    assert Path(veri_ufku.__file__).is_relative_to(package)
    import pytest
    import test_experiment_registry_gui as gui

    args.output.mkdir(parents=True, exist_ok=True)
    files = []

    def capture(window, lifecycle, projects, source):
        report = lifecycle.experimentReport
        assert report["comparable"] and report["rows"][0]["folds"]
        from veri_ufku.storage.experiment_store import export

        path = args.output / "registry.json"
        export(projects.store, [report["rows"][0]["run_id"]], path)
        assert "sentinel-password" not in path.read_text()
        from PySide6.QtCore import QObject
        from PySide6.QtTest import QTest

        for width in (1000, 1366):
            window.setWidth(width)
            from PySide6.QtWidgets import QApplication

            QApplication.processEvents()
            item = window.findChild(QObject, "experimentPareto")
            assert item is not None
            parent = item.parentItem()
            while parent is not None:
                if parent.property("contentY") is not None:
                    pos = item.mapToItem(parent.property("contentItem"), 0, 0)
                    parent.setProperty("contentY", max(0, pos.y() - 250))
                    break
                parent = parent.parentItem()
            QTest.qWait(100)
            image = args.output / f"registry-{width}.png"
            assert window.grabWindow().save(str(image))
            files.append(
                dict(
                    path=str(image),
                    sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                )
            )
        files.append(
            dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        )

    gui.CAPTURE = capture
    with tempfile.TemporaryDirectory(prefix="veri-ufku-f52-gui-") as td:
        monkeypatch = pytest.MonkeyPatch()
        try:
            gui.test_real_registry_qml_revision_compare_export_and_final_history(
                Path(td), monkeypatch
            )
        finally:
            monkeypatch.undo()
    (args.output / "walkthrough.json").write_text(
        json.dumps(
            dict(
                id="E52-GUI",
                environment="ENV-52",
                date=datetime.now(UTC).isoformat(),
                package=str(package),
                flow="actual QML train/compare/folds/Pareto, metric revision/status, masked export, final test and subsequent training preserves journal, reopen/help",
                status="passed",
                files=files,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print("PASS actual registry QML workflow", package)


if __name__ == "__main__":
    main()
