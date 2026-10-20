"""Source/installed-wheel QML Dimension walkthrough and safe exported artifacts."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
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
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest
    from test_dimensions_gui import CASES, test_dimension_desktop_purpose_transform_cv
    from test_unsupervised_gui import visual_find

    import veri_ufku

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E46-GUI",
        environment="ENV-46",
        date=datetime.now(UTC).isoformat(),
        package_file=veri_ufku.__file__,
        cases=[],
    )

    def capture(app, window, c, method, mode, export):
        folder = output / (method + "-" + mode)
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
        for width, height in ((1366, 900), (1000, 720)):
            window.setWidth(width)
            window.setHeight(height)
            for name in (
                "dimensionMethod",
                "dimensionPreview",
                "dimensionLoadings",
                "dimensionPlot",
            ):
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
                QTest.qWait(100)
                target = folder / (name + "-" + str(width) + ".png")
                assert window.grabWindow().save(str(target))
                screenshots.append(str(target.relative_to(output)))
        report["cases"].append(
            dict(
                method=method,
                current=c.current,
                mode=mode,
                diagnostic=c.result["dimension_analysis"]["purpose"],
                artifacts=artifacts,
                screenshots=screenshots,
            )
        )

    for method, mode in CASES:
        with (
            tempfile.TemporaryDirectory(prefix="veri-ufku-f46-") as t,
            pytest.MonkeyPatch.context() as patch,
        ):
            test_dimension_desktop_purpose_transform_cv(
                Path(t), patch, method, mode, capture
            )
        print("PASS", method, mode, flush=True)
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
