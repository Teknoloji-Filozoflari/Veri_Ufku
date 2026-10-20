"""Real desktop resampling slices with export, source/wheel and image evidence."""

import argparse
import hashlib
import json
import os
import platform
import shutil
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
    from test_resampling_gui import (
        CASES,
        test_resampling_qml_unit_fit_save_reopen_export_help,
    )
    from test_unsupervised_gui import visual_find

    import veri_ufku

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E41-GUI",
        environment="ENV-41",
        python=platform.python_version(),
        qt=qVersion(),
        package_file=veri_ufku.__file__,
        started=datetime.now(UTC).isoformat(),
        slices=[],
    )

    def capture(app, window, controller, method, unit, export):
        folder = output / (method + "-" + unit)
        folder.mkdir()
        artifacts = []
        for source in export.iterdir():
            target = folder / source.name
            shutil.copyfile(source, target)
            artifacts.append(
                dict(
                    path=str(target.relative_to(output)),
                    bytes=target.stat().st_size,
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                )
            )
        screenshots = []
        for name in ("resamplingMethod", "resamplingPreflightText", "resamplingResult"):
            item = window.findChild(QObject, name) or visual_find(
                window.contentItem(), name
            )
            container = item.parentItem()
            while container is not None:
                if container.property("contentY") is not None:
                    pos = item.mapToItem(container.property("contentItem"), 0, 0)
                    container.setProperty("contentY", max(0, pos.y() - 25))
                    break
                container = container.parentItem()
            QTest.qWait(120)
            target = folder / (name + ".png")
            assert window.grabWindow().save(str(target))
            screenshots.append(str(target.relative_to(output)))
        report["slices"].append(
            dict(
                method=method,
                unit=unit,
                artifacts=artifacts,
                screenshots=screenshots,
                current=controller.current,
            )
        )

    started = time.monotonic()
    for method, unit in CASES:
        with tempfile.TemporaryDirectory(prefix="veri-ufku-phase41-") as temporary:
            with pytest.MonkeyPatch.context() as patch:
                test_resampling_qml_unit_fit_save_reopen_export_help(
                    Path(temporary), patch, method, unit, capture
                )
        print("PASS", method, unit, flush=True)
    report.update(
        passed=True,
        seconds=time.monotonic() - started,
        finished=datetime.now(UTC).isoformat(),
    )
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        "PASS fourteen resampling GUI slices / export / help / save-reopen", flush=True
    )


if __name__ == "__main__":
    main()
