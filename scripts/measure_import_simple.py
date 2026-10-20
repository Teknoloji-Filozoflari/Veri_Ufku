"""Render the beginner import flow using synthetic data and isolated XDG paths."""

import argparse
import hashlib
import json
import os
import platform
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


def main(output=None):
    output = (output or Path("docs/evidence/ui-import-simple")).resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    from PySide6.QtCore import QObject, qVersion
    from PySide6.QtQuick import QQuickItem
    from PySide6.QtTest import QTest

    from veri_ufku.app import create_application

    with tempfile.TemporaryDirectory(prefix="vu-simple-") as temporary:
        root = Path(temporary)
        for key in ("CONFIG", "STATE", "CACHE", "DATA"):
            os.environ[f"XDG_{key}_HOME"] = str(root / key.lower())
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports = engine._projects_resources, engine._imports_resources
        source = root / "sales.csv"
        source.write_text("id;city;amount\n" + "001;Ankara;1,25\n002;İzmir;2,50\n" * 15)
        original = hashlib.sha256(source.read_bytes()).hexdigest()
        images = []

        def capture(name, width=1366, height=900):
            window.setWidth(width)
            window.setHeight(height)
            app.processEvents()
            QTest.qWait(200)
            window.findChild(QQuickItem, "workspace").property(
                "contentItem"
            ).setProperty("contentY", 0)
            app.processEvents()
            QTest.qWait(100)
            path = output / f"{name}.png"
            assert window.grabWindow().save(str(path))
            images.append(path.name)

        try:
            window.setProperty("selectedSection", 1)
            capture("headings")
            window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 1)
            capture("no-project")
            assert projects.create(str(root / "project"))
            capture("choose-file")
            imports.choose(str(source))
            deadline = time.monotonic() + 30
            while imports.busy:
                app.processEvents()
                QTest.qWait(10)
                assert time.monotonic() < deadline
            assert imports.ready, imports.errorText
            assert imports.model.rowCount() == 20
            capture("preview")
            capture("preview-small", 720, 560)
            window.findChild(QObject, "importAdvancedButton").clicked.emit()
            capture("advanced")
            capture("advanced-small", 720, 560)
            assert hashlib.sha256(source.read_bytes()).hexdigest() == original
            record = {
                "date": datetime.now(UTC).isoformat(),
                "environment": "ENV-UI-IMPORT-SIMPLE",
                "os": platform.platform(),
                "python": platform.python_version(),
                "qt": qVersion(),
                "lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
                "backend": "offscreen/software",
                "source_hash": original,
                "source_preserved": True,
                "displayed_rows": imports.model.rowCount(),
                "preview_types": imports.settings["types"],
                "physical_desktop": False,
                "images": images,
            }
            (output / "walkthrough.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n"
            )
            print("PASS: simple import; 7 screenshots; synthetic source preserved")
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    main(parser.parse_args().output)
