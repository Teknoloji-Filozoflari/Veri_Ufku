"""Exercise all offline geographic GUI paths in source or installed wheel."""

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
    from test_geo_gui import (
        FORMATS,
        MAPS,
        OPS,
        test_qml_geo_operation_preview_apply_undo,
        test_qml_geo_source_preview_and_reopen,
        test_qml_offline_map_help_export_save_open,
    )

    import veri_ufku

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E38-GUI",
        environment="ENV-38",
        python=platform.python_version(),
        qt=qVersion(),
        package_file=veri_ufku.__file__,
        started=datetime.now(UTC).isoformat(),
        cases=[],
        screenshots=[],
        exports=[],
    )

    def render(app, window, kind):
        resources = app._veri_ufku_resources[0]
        if kind in MAPS:
            result = resources._charts_resources.result
            for fmt in ("png", "svg", "pdf"):
                target = output / f"{kind}.{fmt}"
                shutil.copyfile(result["paths"][fmt], target)
                report["exports"].append(
                    dict(
                        path=target.name,
                        bytes=target.stat().st_size,
                        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                    )
                )
            (output / f"{kind}-input.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            )
            name = "chartCreate"
        elif kind in OPS:
            result = resources._operations_resources.preview
            (output / f"{kind}-preview.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            )
            name = "geoOperationParameters"
        else:
            name = "geoSourceMetadata"
        for width in (1366, 720):
            window.setWidth(width)
            window.setHeight(900 if width == 1366 else 560)
            app.processEvents()
            focus = window.findChild(QObject, name)
            focus.forceActiveFocus()
            container = focus.parentItem()
            while container is not None:
                if container.property("contentY") is not None:
                    pos = focus.mapToItem(container.property("contentItem"), 0, 0)
                    container.setProperty("contentY", max(0, pos.y() - 60))
                    break
                container = container.parentItem()
            QTest.qWait(120)
            target = output / f"{kind}-{width}.png"
            assert window.grabWindow().save(str(target))
            report["screenshots"].append(
                dict(
                    path=target.name,
                    width=width,
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                )
            )

    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase38-") as directory:
        for kinds, test in (
            (FORMATS, test_qml_geo_source_preview_and_reopen),
            (MAPS, test_qml_offline_map_help_export_save_open),
            (OPS, test_qml_geo_operation_preview_apply_undo),
        ):
            for kind in kinds:
                work = Path(directory) / kind
                work.mkdir()
                start = time.monotonic()
                with pytest.MonkeyPatch.context() as patch:
                    test(work, patch, kind, render)
                report["cases"].append(
                    dict(kind=kind, passed=True, seconds=time.monotonic() - start)
                )
                print("PASS", kind, flush=True)
    report.update(passed=True, completed=datetime.now(UTC).isoformat())
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
