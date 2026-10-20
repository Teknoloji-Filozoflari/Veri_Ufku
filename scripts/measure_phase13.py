"""Offline first launch and developer GUI walkthrough in source or installed Linux wheel."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

# Executed again by spawn: reject Python TCP in parent and every child, preserve local IPC.
_socket_connect = socket.socket.connect


def offline_connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise OSError("Offline acceptance: TCP disabled")
    return _socket_connect(self, address)


socket.socket.connect = offline_connect

import polars as pl  # noqa: E402
from measure_phase07 import rss  # noqa: E402
from PySide6.QtCore import QObject  # noqa: E402
from PySide6.QtPdf import QPdfDocument  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402
from veri_ufku.exports.data import read_rows  # noqa: E402
from veri_ufku.exports.reports import ASSETS  # noqa: E402


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    record = dict(
        environment="ENV-13",
        date="2026-10-07",
        python=platform.python_version(),
        platform=platform.platform(),
        package=str(veri_ufku.__file__),
        backend="offscreen/software",
        user_test=False,
        n=1,
        max_tick_gap_ms=0,
        peak_parent_worker_rss_bytes=0,
        exports={},
        screenshots=[],
        offline_policy="Python TCP denied in parent/spawn; isolated fresh XDG; QML no remote resources; report resource allowlist/CSP; OS network interfaces not disabled",
        cache="developer warm runtime; no minimum hardware/cold cache claim",
    )
    assert all(
        (ASSETS / p).is_file()
        for p in (
            "fonts/DejaVuSans.ttf",
            "fonts/LICENSE_DEJAVU",
            "examples/sales.csv",
            "examples/problem.csv",
            "examples/sales.parquet",
            "examples/problem.parquet",
            "examples/LICENSE.txt",
            "reports/report.html",
            "reports/report.css",
        )
    )
    record["assets"] = {
        str(p.relative_to(ASSETS)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in ASSETS.rglob("*")
        if p.is_file()
    }
    with tempfile.TemporaryDirectory(
        prefix="vu-phase13-", dir=args.project_temp
    ) as temp:
        base = Path(temp)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        os.environ["MPLCONFIGDIR"] = str(base / "mpl")
        start = time.monotonic()
        app, window, _ = create_application()
        record["fresh_launch_ms"] = (time.monotonic() - start) * 1000
        engine = app._veri_ufku_resources[0]
        projects, imports, data, guide, exports, charts, ops = (
            engine._projects_resources,
            engine._imports_resources,
            engine._dataset_resources,
            engine._guide_resources,
            engine._exports_resources,
            engine._charts_resources,
            engine._operations_resources,
        )

        def wait(controller):
            start = last = time.monotonic()
            while controller.busy:
                app.processEvents()
                QTest.qWait(10)
                now = time.monotonic()
                record["max_tick_gap_ms"] = max(
                    record["max_tick_gap_ms"], (now - last) * 1000
                )
                last = now
                process = getattr(controller, "process", None)
                record["peak_parent_worker_rss_bytes"] = max(
                    record["peak_parent_worker_rss_bytes"],
                    rss(os.getpid()) + (rss(process.pid) if process else 0),
                )
                assert now - start < 60, (
                    type(controller).__name__,
                    getattr(controller, "message", ""),
                )
            assert not getattr(controller, "errorText", ""), getattr(
                controller, "errorText", ""
            )
            return (time.monotonic() - start) * 1000

        def field(name, prop, value):
            obj = window.findChild(QObject, name)
            assert obj, name
            obj.setProperty(prop, value)

        def click(name):
            obj = window.findChild(QObject, name)
            assert obj, name
            obj.clicked.emit()

        try:
            assert not projects.opened and "DejaVu Sans" in app.font().family()
            record["first_launch_packaged_font"] = app.font().family()
            guide.createExample("problem", str(base))
            wait(guide)
            assert data.datasets and data.dataset()["import_metadata"]["row_count"] == 7
            project_root = projects.store.root
            source_hash = hashlib.sha256(
                (ASSETS / "examples/problem.parquet").read_bytes()
            ).hexdigest()
            data.selectColumn(data.datasetColumns[5]["id"])
            data.computeProfile(False, "dataset", 1)
            wait(data)
            data.saveProfile()
            guide.go(2)
            data.computeQuality(False, "dataset", "inspect", "[]", "[]")
            wait(data)
            data.saveQuality()
            guide.go(3)
            field("operationKind", "currentIndex", 3)
            field("cleaningMethod", "currentIndex", 4)
            field("cleaningColumn", "currentIndex", 2)
            click("operationPreview")
            wait(ops)
            assert ops.canApply
            click("operationApply")
            wait(ops)
            guide.go(4)
            field("chartKind", "currentIndex", 0)
            field("chartX", "currentIndex", 5)
            click("chartCreate")
            wait(charts)
            charts.save()
            wait(charts)
            guide.go(5)
            for fmt in ("csv", "json", "jsonl", "parquet", "xlsx", "html", "pdf"):
                output = base / ("cleaned." + fmt)
                report = fmt in ("html", "pdf")
                params = (
                    dict(
                        format=fmt,
                        title="İıŞşÇçĞğÖöÜü — problemli sentetik veri",
                        purpose="Dosyamı anlamak ve seçtiğim temizliği açıklamak",
                    )
                    if report
                    else dict(format=fmt, accept_loss=True)
                )
                exports.create(
                    "report" if report else "data", json.dumps(params), str(output)
                )
                ms = wait(exports)
                assert exports.result["worker_pid"] != os.getpid()
                assert exports.result["rows"] == 7
                if report:
                    assert exports.result["charts_shown"] == 1
                    shutil.copyfile(
                        output,
                        args.output.with_name(args.output.stem + "-example." + fmt),
                    )
                elif fmt == "parquet":
                    assert pl.read_parquet(output).height == 7
                else:
                    assert (
                        len(
                            list(
                                read_rows(
                                    output, fmt, exports.result["output_columns"], "\\N"
                                )
                            )
                        )
                        == 7
                    )
                record["exports"][fmt] = dict(ms=ms, **exports.result)
            projects.request("save")
            wait(projects)
            assert projects.closeProject() and projects.open(str(project_root))
            assert len([r for r in projects.draft["results"] if "export" in r]) == 7
            assert any(
                r.get("capability_id") == "operation.trim"
                for r in projects.draft["operations"]
            )
            record["history_and_receipts_reopened"] = True
            assert (
                hashlib.sha256(
                    (ASSETS / "examples/problem.parquet").read_bytes()
                ).hexdigest()
                == source_hash
            )
            record["synthetic_source_unchanged"] = True
            for width, height, theme, scale in (
                (1366, 900, "dark", 1.0),
                (720, 560, "dark", 1.0),
            ):
                window.setWidth(width)
                window.setHeight(height)
                app.processEvents()
                QTest.qWait(100)
                name = args.output.with_name(
                    args.output.stem + f"-{width}-{theme}-{int(scale * 100)}.png"
                )
                assert window.grabWindow().save(str(name))
                record["screenshots"].append(str(name))
            # Read the actual generated PDF, including its Turkish text and rendered page.
            pdf = QPdfDocument()
            pdf_path = args.output.with_name(args.output.stem + "-example.pdf")
            assert pdf.load(str(pdf_path)) == QPdfDocument.Error.None_
            full = "".join(pdf.getAllText(i).text() for i in range(pdf.pageCount()))
            assert "İıŞşÇçĞğÖöÜü" in full and "Temizleme" in full
            record["pdf_pages"] = pdf.pageCount()
            pdf.render(0, pdf.pagePointSize(0).toSize() * 2).save(
                str(args.output.with_name(args.output.stem + "-pdf-page1.png"))
            )
            pdf.close()
            # Large export remains a process job with a responsive event loop; cancellation preserves state.
            assert projects.closeProject()
            assert projects.create(str(base / "large-project"))
            source = base / "large.parquet"
            pl.DataFrame(
                {"x": range(100000), "text": ["Örnek"] * 100000}
            ).write_parquet(source)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            imports.choose(str(source))
            wait(imports)
            imports.importData()
            wait(imports)
            record["large"] = {}
            for fmt in ("csv", "jsonl", "parquet"):
                target = base / ("large-export." + fmt)
                exports.create(
                    "data", json.dumps(dict(format=fmt, accept_loss=True)), str(target)
                )
                ms = wait(exports)
                assert exports.result["verified_rows"] == 100000
                record["large"][fmt] = dict(
                    ms=ms,
                    rows=exports.result["verified_rows"],
                    bytes=target.stat().st_size,
                )
            cancel_target = base / "canceled.csv"
            exports.create(
                "data",
                json.dumps(dict(format="csv", accept_loss=True)),
                str(cancel_target),
            )
            exports.cancel()
            wait(exports)
            assert not cancel_target.exists()
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
            record["large_source_unchanged"] = True
            record["cancel_no_output"] = True
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print("PHASE13_PASS", args.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--project-temp", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase13-headless.json")
    )
    run(parser.parse_args())
