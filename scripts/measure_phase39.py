"""Run the real dashboard QML workflow, retaining source/wheel export evidence."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tests"))
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    import pytest
    from PySide6.QtCore import QObject, qVersion
    from PySide6.QtTest import QTest
    from test_dashboard_gui import (
        test_dashboard_qml_worker_linkage_save_reopen_export_help,
    )

    import veri_ufku

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E39-GUI",
        environment="ENV-39",
        python=platform.python_version(),
        qt=qVersion(),
        package_file=veri_ufku.__file__,
        started=datetime.now(UTC).isoformat(),
        screenshots=[],
        exports=[],
    )

    def capture(app, window, dashboard, exports):
        for path in exports:
            destination = output / path.name
            shutil.copyfile(path, destination)
            report["exports"].append(
                dict(
                    path=destination.name,
                    bytes=destination.stat().st_size,
                    sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                )
            )
        text = subprocess.run(
            ["pdftotext", str(output / "figure.pdf"), "-"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert (
            "GUI publication caption" in text
            and "kg" in text
            and "Explicit immutable source" in text
        )
        (output / "figure-pdf.txt").write_text(text)
        font_report = subprocess.run(
            ["pdffonts", str(output / "figure.pdf")],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert "DejaVuSerif" in font_report
        (output / "figure-fonts.txt").write_text(font_report)
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                "1",
                "-singlefile",
                "-scale-to",
                "1200",
                "-png",
                str(output / "figure.pdf"),
                str(output / "figure-pdf"),
            ],
            capture_output=True,
            check=True,
        )
        (output / "saved-view.json").write_text(
            json.dumps(dashboard.spec, ensure_ascii=False, indent=2) + "\n"
        )
        (output / "widget-status.json").write_text(
            json.dumps(dashboard.widgets, ensure_ascii=False, indent=2) + "\n"
        )
        for width in (1366, 720):
            window.setWidth(width)
            window.setHeight(900)
            app.processEvents()
            canvas = window.findChild(QObject, "dashboardCanvas")
            container = canvas.parentItem()
            while container is not None:
                if container.property("contentY") is not None:
                    pos = canvas.mapToItem(container.property("contentItem"), 0, 0)
                    container.setProperty("contentY", max(0, pos.y() - 25))
                    break
                container = container.parentItem()
            QTest.qWait(160)
            path = output / f"dashboard-{width}.png"
            assert window.grabWindow().save(str(path))
            report["screenshots"].append(
                dict(
                    path=path.name,
                    width=width,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                )
            )

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase39-") as directory:
        with pytest.MonkeyPatch.context() as patch:
            test_dashboard_qml_worker_linkage_save_reopen_export_help(
                Path(directory), patch, capture
            )
    report.update(
        passed=True,
        seconds=time.monotonic() - started,
        completed=datetime.now(UTC).isoformat(),
        actions="Actual desktop QML widget controls, global filter, linked RowId selection, drill-down, clear, four exports, immutable save/reopen, F1/Escape focus, cancel, stale versions, source bytes preserved",
    )
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print("PASS dashboard QML/source-or-wheel workflow, four exports, two screenshots")


if __name__ == "__main__":
    main()
