"""Actual eight-model QML walkthrough; supports noneditable installed wheel."""

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
    from test_statistical_models_gui import (
        test_substage_real_gui_fit_diagnostic_prediction_save_reopen_help,
    )
    from test_unsupervised_gui import visual_find

    import veri_ufku
    from veri_ufku.statistics.model_contracts import MODEL_METHODS

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E40-GUI",
        environment="ENV-40",
        python=platform.python_version(),
        qt=qVersion(),
        package_file=veri_ufku.__file__,
        started=datetime.now(UTC).isoformat(),
        models=[],
    )

    def capture(app, window, controller, method):
        folder = output / method
        folder.mkdir()
        artifacts = []
        for key, source in controller.result["paths"].items():
            path = Path(source)
            target = folder / path.name
            shutil.copyfile(path, target)
            artifacts.append(
                dict(
                    kind=key,
                    path=str(target.relative_to(output)),
                    bytes=target.stat().st_size,
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                )
            )
        screenshots = []
        for name in ("modelsMethod", "modelsSummary", "modelsDiagnostic"):
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
        report["models"].append(
            dict(
                method=method,
                artifacts=artifacts,
                screenshots=screenshots,
                prediction=controller.result["model_support"],
            )
        )

    started = time.monotonic()
    for method in MODEL_METHODS:
        with tempfile.TemporaryDirectory(prefix="veri-ufku-phase40-") as temporary:
            with pytest.MonkeyPatch.context() as patch:
                test_substage_real_gui_fit_diagnostic_prediction_save_reopen_help(
                    Path(temporary), patch, method, capture
                )
        print("PASS", method, flush=True)
    report.update(
        passed=True,
        seconds=time.monotonic() - started,
        finished=datetime.now(UTC).isoformat(),
    )
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        "PASS eight real GUI model slices, artifacts, help, prediction, save/reopen",
        flush=True,
    )


if __name__ == "__main__":
    main()
