"""Early Linux installed wheel/QML/spawn/atomic native import smoke, not source-tree imports."""

import argparse
import os
import tempfile
import time
from pathlib import Path

import polars as pl
from PySide6.QtCore import QObject, QUrl
from PySide6.QtTest import QTest

import veri_ufku
from veri_ufku.app import create_application


def wait(app, imports):
    deadline = time.monotonic() + 30
    while imports.busy and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(10)
    assert not imports.busy, "worker timeout"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--fixtures", required=True, type=Path)
    args = parser.parse_args()
    assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    with tempfile.TemporaryDirectory(prefix="vu-phase06-wheel-") as temporary:
        base = Path(temporary)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        app, window, bridge = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports = engine._projects_resources, engine._imports_resources
        parquet = base / "reference.parquet"
        pl.DataFrame({"nullable": pl.Series([1, None], dtype=pl.Int16)}).write_parquet(
            parquet
        )
        try:
            assert projects.create(str(base / "project"))
            window.setProperty("selectedSection", 1)
            for file, adapter, options, count in (
                (
                    args.fixtures / "nested.json",
                    "json",
                    {
                        "record_path": "/payload/records",
                        "flatten": True,
                        "expand_lists": "/items|/tags",
                    },
                    7,
                ),
                (
                    args.fixtures / "records.ndjson",
                    "jsonl",
                    {"bad_rows": "quarantine"},
                    3,
                ),
                (args.fixtures / "workbook.xlsx", "xlsx", {"sheet": "Diğer"}, 1),
                (parquet, "parquet", {}, 2),
            ):
                original = file.read_bytes()
                dialog = window.findChild(QObject, "csvFileDialog")
                dialog.setProperty("selectedFile", QUrl.fromLocalFile(str(file)))
                dialog.accepted.emit()
                wait(app, imports)
                assert imports.formatId == adapter
                for key, value in options.items():
                    imports.setOption(key, value)
                imports.refreshPreview()
                wait(app, imports)
                assert imports.ready, imports.errorText
                imports.importData(True)
                wait(app, imports)
                assert not imports.errorText, imports.errorText
                assert (
                    projects.draft["datasets"][-1]["import_metadata"]["row_count"]
                    == count
                )
                assert (
                    projects.learning.catalog.article_for("import." + adapter)
                    == "import-" + adapter
                )
                assert file.read_bytes() == original
                print(
                    "INSTALLED_WHEEL_" + adapter.upper() + "_WORKER_IMPORT PASS",
                    flush=True,
                )
            before = projects.draft.copy()
            assert projects.closeProject() and projects.open(str(base / "project"))
            assert projects.draft == before
            print(
                "PHASE06_INSTALLED_WHEEL_REOPEN PASS",
                str(veri_ufku.__file__),
                flush=True,
            )
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
