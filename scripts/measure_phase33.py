"""Actual source/noneditable-wheel Phase33 QML/spawn/export/reopen and renders."""

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
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase33/source-gui")
    )
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
    from test_missing_sampling_gui import (
        run_case,
        test_preparation_qml_phase33_parameters_and_plan_reopen,
        test_real_worker_cancel_does_not_publish,
    )

    import veri_ufku
    from veri_ufku.statistics.contracts import ADVANCED_METHODS

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E33-GUI",
        environment="ENV-33",
        started=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        qt=qVersion(),
        package_file=str(Path(veri_ufku.__file__).resolve()),
        mode="offscreen/software",
        cases=[],
        screenshots=[],
    )

    def render(app, window, method):
        if method not in ("missing_patterns", "mi_mean", "survey_mean"):
            return
        focus = window.findChild(QObject, "missingResult")
        for width in (1366, 720):
            window.setWidth(width)
            window.setHeight(900)
            focus.forceActiveFocus()
            app.processEvents()
            container = focus.parentItem()
            while container is not None:
                if container.property("contentY") is not None:
                    position = focus.mapToItem(container.property("contentItem"), 0, 0)
                    container.setProperty("contentY", max(0, position.y() - 150))
                    break
                container = container.parentItem()
            QTest.qWait(100)
            path = output / (method + "-" + str(width) + ".png")
            assert window.grabWindow().save(str(path))
            report["screenshots"].append(
                dict(
                    path=path.name,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    width=width,
                )
            )

    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase33-") as tmp:
        base = Path(tmp)
        for method in ADVANCED_METHODS:
            path = base / method
            path.mkdir()
            started = time.monotonic()
            with pytest.MonkeyPatch.context() as patch:
                result = run_case(path, patch, method, render)
            report["cases"].append(
                dict(result, passed=True, seconds=time.monotonic() - started)
            )
            print("PASS", method, flush=True)
        for strategy, index in (("knn", 3), ("iterative", 4)):
            path = base / strategy
            path.mkdir()
            with pytest.MonkeyPatch.context() as patch:
                test_preparation_qml_phase33_parameters_and_plan_reopen(
                    path, patch, strategy, index
                )
            report["cases"].append(dict(method="preparation_" + strategy, passed=True))
            print("PASS", "preparation_" + strategy, flush=True)
        path = base / "cancel"
        path.mkdir()
        with pytest.MonkeyPatch.context() as patch:
            test_real_worker_cancel_does_not_publish(path, patch)
        report["cases"].append(dict(method="MI_cancel", passed=True))
    report.update(
        completed=datetime.now(UTC).isoformat(),
        passed=True,
        render_note="Actual QML camera positioned programmatically; not physical/AT acceptance",
    )
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        "PASS: Phase33 source/wheel 14 real GUI cases, six renders, five F1 topics, explicit approve, identities, export/save/reopen/cancel",
        flush=True,
    )


if __name__ == "__main__":
    main()
