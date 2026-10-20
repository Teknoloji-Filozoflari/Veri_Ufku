"""Record actual Qt logo rendering with isolated user state."""

import json
import os
import platform
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def main():
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest

    from veri_ufku.app import create_application

    output = Path(__file__).resolve().parents[1] / "docs/evidence/ui-branding"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="veri-ufku-brand-") as temporary:
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ[f"XDG_{key}_HOME"] = str(Path(temporary) / key)
        app, window, _ = create_application()
        record = {
            "date_utc": datetime.now(UTC).isoformat(),
            "environment": "ENV-UI-BRANDING",
            "python": platform.python_version(),
            "os": platform.platform(),
            "qt_platform": app.platformName(),
            "desktop_file": app.desktopFileName(),
            "window_icon": not window.icon().isNull(),
            "screenshots": [],
        }
        try:
            for width, height in ((1366, 900), (720, 560)):
                window.setWidth(width)
                window.setHeight(height)
                QTest.qWait(300)
                logo = window.findChild(QObject, "applicationLogo")
                assert logo.property("ready")
                assert 0 <= logo.x() and logo.width() == 36
                name = f"{width}-home.png"
                assert window.grabWindow().save(str(output / name))
                record["screenshots"].append(name)
            example = window.findChild(QObject, "learningExampleWindow")
            example.setProperty("visible", True)
            QTest.qWait(300)
            assert example.findChild(QObject, "exampleLogo").property("ready")
            assert not example.icon().isNull()
            assert example.grabWindow().save(str(output / "example.png"))
            record["screenshots"].append("example.png")
            (output / "render.json").write_text(json.dumps(record, indent=2) + "\n")
            print("PASS: Qt logo, both windows, wide/narrow render")
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    main()
