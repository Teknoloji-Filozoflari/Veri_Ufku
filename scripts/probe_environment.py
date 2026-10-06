"""Read-only phase 00 environment probe; not the application."""

import importlib.metadata
import json
import os
import platform
import sqlite3
import tempfile
import time
from pathlib import Path


def probe():
    result = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "sqlite": sqlite3.sqlite_version,
        "session": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "packages": {},
    }
    for package in (
        "PySide6",
        "polars",
        "duckdb",
        "scikit-learn",
        "scipy",
        "statsmodels",
        "matplotlib",
        "numpy",
        "pytest",
        "ruff",
    ):
        try:
            result["packages"][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result["packages"][package] = None
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    try:
        from PySide6.QtCore import qVersion
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine

        start = time.monotonic()
        app = QGuiApplication([])
        engine = QQmlApplicationEngine()
        engine.loadData(
            b"import QtQuick\nimport QtQuick.Controls\n"
            b"ApplicationWindow { visible: false; width: 320; height: 200; "
            b'Button { text: "Probe" } }'
        )
        result["qml_probe"] = {
            "qt_runtime": qVersion(),
            "roots": len(engine.rootObjects()),
            "elapsed_ms": round((time.monotonic() - start) * 1000, 2),
            "desktop_test": False,
        }
        # Keep app/engine alive until after the probe; no event loop or user window.
        app.processEvents()
    except ImportError as error:
        result["qml_probe"] = {"unavailable": str(error)}
    with tempfile.TemporaryDirectory(prefix="veri-ufku-mpl-") as cache:
        os.environ["MPLCONFIGDIR"] = cache
        try:
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            from matplotlib.figure import Figure

            figure = Figure(figsize=(1, 1), dpi=100)
            canvas = FigureCanvasAgg(figure)
            canvas.draw()
            result["agg_probe"] = {
                "rgba_bytes": len(canvas.buffer_rgba().tobytes()),
                "analytic_result": False,
            }
        except ImportError as error:
            result["agg_probe"] = {"unavailable": str(error)}
    result["lock_present"] = Path("uv.lock").exists()
    return result


if __name__ == "__main__":
    print(json.dumps(probe(), ensure_ascii=False, indent=2))
