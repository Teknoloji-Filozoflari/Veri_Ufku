"""Render the Phase02 shell at real Qt sizes; record headless/desktop separately."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import tempfile
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--desktop", action="store_true")
    args = parser.parse_args()
    if not args.desktop:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtQuick import QQuickItem
    from PySide6.QtTest import QTest

    from veri_ufku.app import create_application

    root = Path(__file__).resolve().parents[1]
    output = root / "docs/evidence"
    mode = "desktop" if args.desktop else "headless"
    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase02-") as directory:
        for name in ("CONFIG", "STATE", "CACHE"):
            os.environ[f"XDG_{name}_HOME"] = str(Path(directory) / name.lower())
        app, window, bridge = create_application()
        preferences = app._veri_ufku_resources[-2]

        def wait(predicate, timeout=8):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                app.processEvents()
                if predicate():
                    return
                QTest.qWait(10)
            raise RuntimeError("Phase02 GUI check timed out")

        def click(item):
            point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=point.toPoint())
            app.processEvents()

        def visual_item(item, name):
            if item.objectName() == name:
                return item
            for child in item.childItems():
                found = visual_item(child, name)
                if found:
                    return found
            return None

        report = {
            "date": "2026-10-06",
            "mode": mode,
            "platform": app.platformName(),
            "os": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "pyside6": importlib.metadata.version("PySide6"),
            "lock_sha256": hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
            "checks": [],
            "screenshots": [],
        }
        try:
            wait(lambda: not window.grabWindow().isNull())
            for width, height, scale, theme, section in [
                (1366, 900, 1.0, "light", 0),
                (1366, 900, 1.0, "dark", 0),
                (720, 560, 1.0, "light", 0),
                (720, 560, 1.0, "dark", 0),
                (1024, 768, 1.25, "system", 1),
                (1024, 768, 1.5, "light", 3),
                (720, 560, 2.0, "dark", 0),
            ]:
                window.setWidth(width)
                window.setHeight(height)
                preferences.setTextScale(scale)
                preferences.setTheme(theme)
                window.setProperty("selectedSection", section)
                QTest.qWait(150)
                image = window.grabWindow()
                assert not image.isNull()
                name = f"phase02-{mode}-{width}-{theme}-{scale}-{section}.png"
                assert image.save(str(output / name))
                report["screenshots"].append(name)
                workspace = window.findChild(QQuickItem, "workspace")
                assert workspace.width() >= 320
                report["checks"].append(
                    {
                        "size": [window.width(), window.height()],
                        "scale": scale,
                        "theme": theme,
                        "section": section,
                        "workspace_width": workspace.width(),
                        "workspace_height": workspace.height(),
                    }
                )
            preferences.setTextScale(1.0)
            window.setWidth(1366)
            window.setHeight(900)
            window.setProperty("selectedSection", 0)
            QTest.qWait(100)
            help_button = window.findChild(QQuickItem, "helpButton")
            click(help_button)
            wait(lambda: window.property("infoOpen"))
            assert window.findChild(QQuickItem, "dockedInformation").isVisible()
            QTest.qWait(100)
            name = f"phase02-{mode}-information.png"
            assert window.grabWindow().save(str(output / name))
            report["screenshots"].append(name)
            QTest.keyClick(window, Qt.Key.Key_Escape)
            wait(lambda: not window.property("infoOpen"))
            assert help_button.hasActiveFocus()
            nav = visual_item(window.contentItem(), "nav0")
            nav.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Down)
            QTest.keyClick(window, Qt.Key.Key_Space)
            wait(lambda: window.property("selectedSection") == 1)
            QTest.keyClick(window, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier)
            wait(lambda: window.property("selectedSection") == 0)
            report["checks"].append({"keyboard_navigation_and_help_focus": "passed"})
            window.setWidth(720)
            window.setHeight(560)
            QTest.qWait(100)
            click(help_button)
            wait(lambda: window.property("infoOpen"))
            QTest.qWait(300)
            name = f"phase02-{mode}-small-information.png"
            assert window.grabWindow().save(str(output / name))
            report["screenshots"].append(name)
            QTest.keyClick(window, Qt.Key.Key_Escape)
            wait(lambda: not window.property("infoOpen"))
            report["checks"].append({"small_information_escape": "passed"})
            window.setWidth(1366)
            window.setHeight(900)
            window.setProperty("selectedSection", 1)
            window.setProperty("showDemo", True)
            preferences.setView("advanced")
            bridge.start("demo.unknown")
            wait(lambda: bridge.stateCode == "running")
            for state in ("loading", "canceled", "error"):
                if state == "canceled":
                    bridge.cancel()
                    wait(lambda: not bridge.active)
                elif state == "error":
                    bridge.start("demo.failure")
                    wait(lambda: not bridge.active)
                QTest.qWait(80)
                notice = window.findChild(QQuickItem, "taskNotice")
                assert notice.property("kind") == state
                name = f"phase02-{mode}-{state}.png"
                assert window.grabWindow().save(str(output / name))
                report["screenshots"].append(name)
                report["checks"].append({"shared_state": state, "result": "passed"})
            print(json.dumps(report, indent=2), flush=True)
            (output / f"phase02-{mode}.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
        finally:
            bridge.session.manager.shutdown()
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    main()
