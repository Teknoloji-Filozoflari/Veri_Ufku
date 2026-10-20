"""Source or installed wheel: actual array QML/spawn/cancel/plot/reopen."""

import argparse
import hashlib
import json
import os
import platform
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
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo / "tests"))
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    import pytest
    from PySide6.QtCore import QObject, qVersion
    from PySide6.QtTest import QTest
    from test_arrays_gui import test_qml_array_slice_cost_cancel_import_plot_reopen

    import veri_ufku
    from veri_ufku.importers.arrays import ARRAY_FORMATS

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E34-GUI",
        environment="ENV-34",
        python=platform.python_version(),
        qt=qVersion(),
        package_file=veri_ufku.__file__,
        started=datetime.now(UTC).isoformat(),
        cases=[],
        screenshots=[],
    )

    def render(app, window, label, focus_name):
        for width in (1366, 720):
            window.setWidth(width)
            window.setHeight(900 if width == 1366 else 560)
            app.processEvents()
            focus = window.findChild(QObject, focus_name)
            focus.forceActiveFocus()
            container = focus.parentItem()
            while container is not None:
                if container.property("contentY") is not None:
                    position = focus.mapToItem(container.property("contentItem"), 0, 0)
                    container.setProperty("contentY", max(0, position.y() - 150))
                    break
                container = container.parentItem()
            QTest.qWait(120)
            target = output / (label + "-" + str(width) + ".png")
            assert window.grabWindow().save(str(target))
            report["screenshots"].append(
                dict(
                    path=target.name,
                    width=width,
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                )
            )

    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase34-") as directory:
        for adapter in ARRAY_FORMATS:
            work = Path(directory) / adapter
            work.mkdir()
            started = time.monotonic()
            with pytest.MonkeyPatch.context() as patch:
                test_qml_array_slice_cost_cancel_import_plot_reopen(
                    work, patch, adapter, render
                )
            report["cases"].append(
                dict(
                    adapter=adapter,
                    passed=True,
                    seconds=time.monotonic() - started,
                    help="actual F1/Escape x4",
                    actions="cost reject/cancel/import/heatmap/profile/export/save/reopen",
                )
            )
            print("PASS", adapter, flush=True)
    report.update(passed=True, completed=datetime.now(UTC).isoformat())
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
