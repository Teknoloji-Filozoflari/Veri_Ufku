"""Actual isolated Qt renders and bounded startup observations, not human UX tests."""

import argparse
import json
import os
import platform
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from veri_ufku.app import create_application  # noqa: E402


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="vu-ui-review-") as temp:
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ[f"XDG_{key}_HOME"] = str(Path(temp) / key.lower())
        started = time.monotonic()
        app, window, _ = create_application()
        app.processEvents()
        QTest.qWait(100)
        first_frame = time.monotonic() - started
        engine = app._veri_ufku_resources[0]
        preferences = engine.rootContext().contextProperty("preferences")
        report = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "backend": os.environ["QT_QPA_PLATFORM"],
            "first_frame_seconds": first_frame,
            "human_review": False,
            "startup_qobjects": len(window.findChildren(QObject)),
            "rss_start_kib": int(
                Path("/proc/self/status").read_text().split("VmRSS:")[1].split()[0]
            ),
            "screenshots": [],
        }
        try:
            for name, section, width, theme, scale in (
                ("home", 0, 1366, "dark", 1.0),
                ("data", 1, 1366, "dark", 1.0),
                ("prepare", 2, 1366, "dark", 1.0),
                ("charts", 3, 1366, "dark", 1.0),
                ("statistics", 4, 1366, "dark", 1.0),
                ("models", 5, 1366, "dark", 1.0),
                ("reports", 6, 1366, "dark", 1.0),
                ("learn", 7, 1366, "dark", 1.0),
                ("home-light", 0, 1366, "light", 1.0),
                ("home-narrow", 0, 720, "dark", 1.0),
                ("home-large-text", 0, 720, "dark", 2.0),
            ):
                preferences.setTheme(theme)
                preferences.setTextScale(scale)
                window.setWidth(width)
                window.setHeight(900)
                window.setProperty("selectedSection", section)
                app.processEvents()
                QTest.qWait(120)
                assert window.grabWindow().save(str(output / f"{name}.png"))
                report["screenshots"].append(name)
            preferences.setTextScale(1.0)
            window.findChild(QObject, "displayButton").clicked.emit()
            QTest.qWait(120)
            assert window.grabWindow().save(str(output / "preferences.png"))
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
        (output / "measurement.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    run(parser.parse_args().output)
