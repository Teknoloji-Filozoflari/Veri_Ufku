"""Actual local review/share GUI and immutable note walkthrough, optional wheel."""

import argparse
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    sys.path.insert(1, str(root / "tests"))
    args.output.mkdir(parents=True, exist_ok=True)
    from dataclasses import asdict

    import pytest
    import test_share_gui as cases
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest

    import veri_ufku

    package = Path(veri_ufku.__file__).resolve()
    if args.package_root:
        assert package.is_relative_to(args.package_root.resolve())
    records = []

    def capture(app, window, projects, controller, paths, fork):
        full = fork.exists()
        target = args.output / ("full" if full else "basic")
        target.mkdir(parents=True, exist_ok=True)
        for p in paths:
            (target / p.name).write_bytes(p.read_bytes())
        (target / "diff.json").write_text(
            json.dumps(controller.result, ensure_ascii=False, indent=2) + "\n"
        )
        (target / "review.json").write_text(
            json.dumps(controller.saved, ensure_ascii=False, indent=2) + "\n"
        )
        for width in (1000, 1366):
            window.setWidth(width)
            window.setHeight(900)
            window.findChild(QObject, "sharingRecipe").forceActiveFocus()
            QTest.qWait(300)
            app.processEvents()
            assert window.grabWindow().save(str(target / f"gui-{width}.png"))
        supervisor = app._veri_ufku_resources[0]._resource_supervisor
        records.append(
            dict(
                mode="full" if full else "basic",
                budget=asdict(controller.budget),
                peak_rss_bytes=supervisor.peak_rss_bytes,
                resources=supervisor.report,
                notes=len(controller.saved),
            )
        )

    cases.CAPTURE = capture
    status = pytest.main(
        [
            "-q",
            str(root / "tests/test_share_gui.py"),
            "--junitxml=" + str(args.output / "gui.xml"),
        ]
    )
    (args.output / "measurement.json").write_text(
        json.dumps(
            dict(
                time=datetime.now(UTC).isoformat(),
                python=platform.python_version(),
                platform=platform.platform(),
                package=str(package),
                status=status,
                records=records,
                scope="offscreen/software; no physical/human/AT/minHW claim",
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(status)


if __name__ == "__main__":
    main()
