"""Run every composition through source or installed-wheel QML and retain real exports."""

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
    from test_composition_gui import (
        CASES,
        test_qml_composition_help_worker_exports_and_reopen,
    )

    import veri_ufku

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E37-GUI",
        environment="ENV-37",
        python=platform.python_version(),
        qt=qVersion(),
        package_file=veri_ufku.__file__,
        started=datetime.now(UTC).isoformat(),
        cases=[],
        screenshots=[],
        exports=[],
    )

    def render(app, window, kind, name, result):
        for fmt in ("png", "svg", "pdf"):
            target = output / f"{kind}.{fmt}"
            shutil.copyfile(result["paths"][fmt], target)
            report["exports"].append(
                dict(
                    path=target.name,
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                    bytes=target.stat().st_size,
                )
            )
        # Text and rasterize the actual PDF with system Poppler, not a signature-only check.
        text = subprocess.run(
            ["pdftotext", str(output / f"{kind}.pdf"), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert (
            f"sample {result['used_n']}/{result['population_n']}" in text
            and "DPI=" in text
        )
        # The renderer may extract font ligatures separately; identity is checked in saved JSON and SVG.
        assert result["dataset_version"] in (output / f"{kind}.svg").read_text()
        (output / f"{kind}-pdf.txt").write_text(text)
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                "1",
                "-singlefile",
                "-scale-to",
                "1000",
                "-png",
                str(output / f"{kind}.pdf"),
                str(output / f"{kind}-pdf"),
            ],
            check=True,
            capture_output=True,
        )
        (output / f"{kind}-input.json").write_text(
            json.dumps(
                {
                    k: result[k]
                    for k in (
                        "spec",
                        "points",
                        "details",
                        "used_n",
                        "population_n",
                        "provenance",
                    )
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
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

    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase37-") as directory:
        for kind in CASES:
            work = Path(directory) / kind
            work.mkdir()
            start = time.monotonic()
            with pytest.MonkeyPatch.context() as patch:
                test_qml_composition_help_worker_exports_and_reopen(
                    work, patch, kind, render
                )
            report["cases"].append(
                dict(
                    kind=kind,
                    passed=True,
                    seconds=time.monotonic() - start,
                    actions="actual F1/Escape + worker + PNG/SVG/PDF export + save/reopen; ECDF title/cancel; error-bar log rejection",
                )
            )
            print("PASS", kind, flush=True)
    report.update(passed=True, completed=datetime.now(UTC).isoformat())
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
