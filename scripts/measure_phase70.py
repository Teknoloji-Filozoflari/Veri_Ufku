"""Real GUI report/export walkthrough and PDF render, source or installed wheel."""

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
    import pytest
    import test_report_builder_gui as cases
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtPdf import QPdfDocument

    import veri_ufku

    package = Path(veri_ufku.__file__).resolve()
    if args.package_root:
        assert package.is_relative_to(args.package_root.resolve())
    records = []

    def capture(app, window, projects, c):
        target = args.output / (
            "model"
            if any(b["kind"] == "model-card" for b in c.result["blocks"])
            else "basic"
        )
        target.mkdir(parents=True, exist_ok=True)
        v = projects.store.state["results"][-1]["scientific_report"]
        for name, ref in v["file_refs"].items():
            (target / name).write_bytes(projects.store.path(ref["uri"]).read_bytes())
        for width in (1000, 1366):
            window.setWidth(width)
            window.setHeight(900)
            window.findChild(
                __import__("PySide6.QtCore", fromlist=["QObject"]).QObject,
                "reportBuilderRecipe",
            ).forceActiveFocus()
            from PySide6.QtTest import QTest

            QTest.qWait(250)
            app.processEvents()
            assert window.grabWindow().save(str(target / f"gui-{width}.png"))
        pdf = QPdfDocument()
        assert pdf.load(str(target / "report.pdf")) == QPdfDocument.Error.None_
        rendered = pdf.render(0, QSize(1000, 1414))
        page = QImage(rendered.size(), QImage.Format.Format_RGB32)
        page.fill(QColor("white"))
        painter = QPainter(page)
        painter.drawImage(0, 0, rendered)
        painter.end()
        page.save(str(target / "pdf-page-1.png"))
        records.append(
            dict(
                run_id=c.result["run_id"],
                review_hash=c.result["review_hash"],
                pdf_pages=c.result["pdf_pages"],
                budget=__import__("dataclasses").asdict(c.budget),
                resources=app._veri_ufku_resources[0]._resource_supervisor.report,
                peak_rss_bytes=app._veri_ufku_resources[
                    0
                ]._resource_supervisor.peak_rss_bytes,
            )
        )

    cases.CAPTURE = capture
    code = pytest.main(
        [
            "-q",
            str(root / "tests/test_report_builder_gui.py"),
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
                records=records,
                status=code,
                scope="offscreen software GUI; no physical/human/AT/minHW claim",
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
