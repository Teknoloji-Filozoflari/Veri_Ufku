"""Record real offline learning GUI interactions and rendered windows."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import socket
import tempfile
import time
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--desktop", action="store_true")
    args = parser.parse_args()
    if not args.desktop:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault("QT_QUICK_BACKEND", "software")

    def forbid_network(*_args, **_kwargs):
        raise RuntimeError("Learning probe attempted network access")

    socket.create_connection = forbid_network
    urllib.request.urlopen = forbid_network
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtQuick import QQuickItem
    from PySide6.QtTest import QTest

    from veri_ufku.app import create_application

    root = Path(__file__).resolve().parents[1]
    output = root / "docs/evidence"
    mode = "desktop" if args.desktop else "headless"
    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase03-") as directory:
        for name in ("CONFIG", "STATE", "CACHE"):
            os.environ[f"XDG_{name}_HOME"] = str(Path(directory) / name.lower())
        app, window, bridge = create_application()
        learning = app._veri_ufku_resources[-3]
        preferences = app._veri_ufku_resources[-2]

        def wait(predicate):
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                app.processEvents()
                if predicate():
                    return
                QTest.qWait(10)
            raise RuntimeError("Phase03 GUI check timed out")

        def visual_item(item, name):
            if item.objectName() == name:
                return item
            for child in item.childItems():
                found = visual_item(child, name)
                if found:
                    return found
            return None

        report = dict(
            date="2026-10-06",
            mode=mode,
            platform=app.platformName(),
            os=platform.platform(),
            machine=platform.machine(),
            python=platform.python_version(),
            pyside6=importlib.metadata.version("PySide6"),
            lock_sha256=hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
            content_sha256=hashlib.sha256(
                (root / "src/veri_ufku/learning/content/tr.json").read_bytes()
            ).hexdigest(),
            network="Python connection/urlopen fail-fast; renderer uses PlainText, no Qt network or web engine",
            checks=[],
            screenshots=[],
        )

        def capture(name, target=window):
            app.processEvents()
            QTest.qWait(300)
            image = target.grabWindow()
            assert not image.isNull()
            filename = f"phase03-{mode}-{name}.png"
            assert image.save(str(output / filename))
            report["screenshots"].append(filename)

        try:
            wait(lambda: not window.grabWindow().isNull())
            window.setWidth(1366)
            window.setHeight(900)
            window.setProperty("selectedSection", 7)
            search = visual_item(window.contentItem(), "learningSearch")
            search.forceActiveFocus()
            for char in "medyan":
                QTest.keyClick(window, getattr(Qt.Key, "Key_" + char.upper()))
            wait(lambda: learning.query == "medyan")
            assert "mean-median" in [a["id"] for a in learning.results]
            capture("search")
            result = visual_item(window.contentItem(), "learningArticle-mean-median")
            result.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Space)
            wait(lambda: window.property("infoOpen"))
            assert learning.article["id"] == "mean-median"
            for depth in (0, 1, 2):
                learning.setDepth(depth)
                capture(f"depth-{depth}")
            report["checks"].append(
                "Offline keyboard search and article activation; three depths rendered"
            )
            QTest.keyClick(window, Qt.Key.Key_Escape)
            wait(lambda: not window.property("infoOpen"))
            for section, expected in enumerate(
                (
                    "home",
                    "data",
                    "missing",
                    "mean-median",
                    "sample",
                    "prediction",
                    "report",
                    "learn",
                )
            ):
                window.setProperty("selectedSection", section)
                window.findChild(QQuickItem, "helpButton").forceActiveFocus()
                QTest.keyClick(window, Qt.Key.Key_F1)
                wait(lambda: window.property("infoOpen"))
                assert learning.article["id"] == expected
                QTest.keyClick(window, Qt.Key.Key_Escape)
                wait(lambda: not window.property("infoOpen"))
            report["checks"].append(
                "All eight screen contexts resolve to the expected article via F1"
            )
            bridge.start("demo.io")
            job, binding = bridge.job_id, bridge.session.binding
            window.setProperty("selectedSection", 5)
            window.findChild(QQuickItem, "helpButton").clicked.emit()
            learning.openArticle("leakage")
            preferences.setView("advanced")
            learning.setDepth(0)
            capture("critical-advanced")
            focus = window.activeFocusItem()
            print(
                "Critical help focus:",
                window.isActive(),
                focus.objectName() if focus else None,
                flush=True,
            )
            window.requestActivate()
            wait(lambda: window.isActive())
            window.findChild(QQuickItem, "helpCloseButton").forceActiveFocus()
            app.processEvents()
            QTest.keyClick(window, Qt.Key.Key_Escape)
            wait(lambda: not window.property("infoOpen"))
            assert bridge.job_id == job and bridge.session.binding == binding
            report["checks"].append(
                "Help closes without canceling/rebinding the active task; advanced critical warning visible"
            )
            window.setProperty("selectedSection", 7)
            window.findChild(QQuickItem, "helpButton").clicked.emit()
            try_button = visual_item(window.contentItem(), "tryLearningButton")
            try_button.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Space)
            example = window.findChild(QObject, "learningExampleWindow")
            wait(lambda: example.isVisible())
            capture("example", example)
            assert learning.exampleLibrary.projectId.startswith("learning-example:")
            learning.exampleLibrary.setQuery("eksik")
            assert learning.query == "medyan"
            assert bridge.job_id == job and bridge.session.binding == binding
            example.close()
            window.requestActivate()
            QTest.qWait(200)
            QTest.keyClick(window, Qt.Key.Key_Escape)
            wait(lambda: not window.property("infoOpen"))
            report["checks"].append(
                "Separate temporary learning project opens; main search/binding/job unchanged"
            )
            learning.setQuery("")
            learning.setGlossary(True)
            assert len(learning.results) == 9
            learning.setMarksEnabled(True)
            learning.openArticle("leakage")
            learning.toggleBookmark()
            learning.toggleRead()
            capture("glossary-marks")
            for width, height, scale, theme in (
                (720, 560, 1.0, "light"),
                (720, 560, 2.0, "dark"),
            ):
                window.setWidth(width)
                window.setHeight(height)
                preferences.setTextScale(scale)
                preferences.setTheme(theme)
                workspace = window.findChild(QQuickItem, "workspace")
                workspace.property("contentItem").setProperty("contentY", 0)
                capture(f"small-{theme}-{scale}")
                window.findChild(QQuickItem, "helpButton").clicked.emit()
                learning.openArticle("correlation")
                learning.setDepth(1)
                capture(f"drawer-{theme}-{scale}")
                QTest.keyClick(window, Qt.Key.Key_Escape)
                wait(lambda: not window.property("infoOpen"))
                QTest.qWait(250)
            report["checks"].append(
                "Small 720x560 light/dark and 200% text; glossary and drawer rendered"
            )
            wait(lambda: not bridge.active)
            assert bridge.session.manager.snapshot(job).result_for(binding) is not None
            report["checks"].append(
                "Original I/O task completed with its original binding"
            )
        finally:
            bridge.session.manager.shutdown()
            app._veri_ufku_resources[-1]()
            window.close()
        (output / f"phase03-{mode}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )
        print(
            f"PASS: Phase03 {mode}, {len(report['checks'])} checks, {len(report['screenshots'])} screenshots"
        )


if __name__ == "__main__":
    main()
