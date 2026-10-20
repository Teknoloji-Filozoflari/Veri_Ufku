"""Actual bounded privacy GUI/export/cleanup walkthrough, source or installed wheel."""

import argparse
import json
import os
import platform
import sys
from dataclasses import asdict
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
    import pytest
    import test_privacy_gui as cases
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest

    import veri_ufku

    package = Path(veri_ufku.__file__).resolve()
    if args.package_root:
        assert package.is_relative_to(args.package_root.resolve())
    records = []

    def capture(app, window, projects, c, export):
        (args.output / "redacted.zip").write_bytes(export.read_bytes())
        for width in (1000, 1366):
            window.setWidth(width)
            window.setHeight(900)
            window.findChild(QObject, "privacyScan").forceActiveFocus()
            QTest.qWait(300)
            app.processEvents()
            assert window.grabWindow().save(str(args.output / f"gui-{width}.png"))
        supervisor = app._veri_ufku_resources[0]._resource_supervisor
        records.append(
            dict(
                budget=asdict(c.budget),
                peak_rss_bytes=supervisor.peak_rss_bytes,
                resources=supervisor.report,
                reviews=len(c.saved),
                cleanup=c.result,
                events=[
                    r["privacy_event"]["kind"]
                    for r in projects.draft["results"]
                    if "privacy_event" in r
                ],
                pii_dependencies=json.loads(c.dependenciesText),
            )
        )

    cases.CAPTURE = capture
    status = pytest.main(
        [
            "-q",
            str(root / "tests/test_privacy_gui.py"),
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
                scope="offscreen/software/default2GiB; not physical/human/AT/minHW; live Secret Service unavailable",
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(status)


if __name__ == "__main__":
    main()
