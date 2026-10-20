"""Real isolated format→Qt→spawn→native snapshot→reopen source/wheel walkthrough."""

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
        "--output", type=Path, default=Path("docs/evidence/phase30/gui")
    )
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    repository = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repository / "tests"))
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
    from phase30_fixtures import fixture
    from PySide6.QtCore import QObject, Qt, qVersion
    from PySide6.QtTest import QTest

    import veri_ufku
    from veri_ufku.app import create_application
    from veri_ufku.importers.advanced import ADVANCED_FORMATS
    from veri_ufku.storage.project_store import source_fingerprint

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase30-") as directory:
        root = Path(directory)
        for name in ("CONFIG", "STATE", "CACHE", "DATA"):
            os.environ["XDG_" + name + "_HOME"] = str(root / name.lower())
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports = engine._projects_resources, engine._imports_resources
        learning = engine._learning_resources
        runs, images = [], []

        def spin(predicate):
            deadline = time.monotonic() + 30
            while not predicate():
                app.processEvents()
                QTest.qWait(10)
                if time.monotonic() > deadline:
                    raise RuntimeError("Phase30 GUI walkthrough timeout")

        def capture(name, width):
            window.setWidth(width)
            window.setHeight(900)
            app.processEvents()
            scroll = window.findChild(QObject, "workspace").property("contentItem")
            scroll.setProperty("contentY", 0)
            QTest.qWait(150)
            path = output / (name + ".png")
            assert window.grabWindow().save(str(path))
            images.append(path.name)

        try:
            assert projects.create(str(root / "project"))
            window.setProperty("selectedSection", 1)
            window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 1)
            for adapter in ADVANCED_FORMATS:
                place = root / adapter
                place.mkdir()
                source = fixture(place, adapter)
                fingerprint = source_fingerprint(source)
                started = time.monotonic()
                imports.choose(str(source))
                spin(lambda: not imports.busy)
                assert imports.formatId == adapter
                if adapter == "hdf5":
                    assert not imports.settings["sheet"]
                    imports.setOption("sheet", "/tables/observations")
                elif adapter == "xml":
                    imports.setOption("record_path", "/root/record")
                elif adapter == "fixed_width":
                    imports.setOption("widths", "3,7")
                    imports.setOption("column_names", "code|name")
                if adapter in ("hdf5", "xml", "fixed_width"):
                    imports.refreshPreview()
                    spin(lambda: not imports.busy)
                assert imports.ready, imports.errorText
                window.findChild(QObject, "csvImportPanel").setProperty(
                    "detailsOpen", True
                )
                if adapter in (
                    "parquet_dataset",
                    "arrow_dataset",
                    "hdf5",
                    "xml",
                    "spss",
                ):
                    capture(adapter + "-wide", 1366)
                    capture(adapter + "-narrow", 720)
                preview_count = imports.result["examined"]
                # Read real contextual help without changing the preview or
                # publishing a dataset. Escape returns focus to its control.
                preview_before = json.loads(json.dumps(imports.result))
                project_before = json.loads(json.dumps(projects.draft))
                schema = window.findChild(QObject, "schemaPolicy")
                schema.forceActiveFocus()
                QTest.keyClick(window, Qt.Key.Key_F1)
                spin(lambda: window.property("infoOpen"))
                assert learning.article["id"] == "import-schema-evolution"
                QTest.keyClick(window, Qt.Key.Key_Escape)
                spin(lambda: not window.property("infoOpen"))
                assert schema.hasActiveFocus()
                assert imports.result == preview_before
                assert projects.draft == project_before
                imports.importData(True)
                spin(lambda: not imports.busy)
                assert not imports.errorText, imports.errorText
                dataset = projects.draft["datasets"][-1]
                assert source_fingerprint(source) == fingerprint
                runs.append(
                    dict(
                        adapter=adapter,
                        requirement="F30-S001..004",
                        dataset_version=dataset["version_id"],
                        accepted=dataset["import_metadata"]["row_count"],
                        preview_examined=preview_count,
                        fingerprint=fingerprint,
                        metadata_preserved=bool(
                            dataset["import_metadata"]["settings"]["format_metadata"]
                        ),
                        seconds=round(time.monotonic() - started, 3),
                        contextual_help="import-schema-evolution; F1/Escape",
                    )
                )
            help_articles = []
            for context in (
                "import-phase30",
                "import-partition",
                "import-schema-evolution",
                "import-category-labels",
                "import-decimal-precision",
            ):
                before_help = json.loads(json.dumps(projects.draft))
                assert learning.openContext(context)
                assert learning.article["id"] == context
                assert learning.article["example"]["before"]
                assert learning.article["example"]["after"]
                QTest.keyClick(window, Qt.Key.Key_Escape)
                spin(lambda: not window.property("infoOpen"))
                assert projects.draft == before_help
                help_articles.append(context)
            before = json.loads(json.dumps(projects.draft))
            assert projects.closeProject() and projects.open(str(root / "project"))
            assert projects.draft == before
            record = dict(
                date=datetime.now(UTC).isoformat(),
                environment="ENV-30-HEADLESS",
                python=platform.python_version(),
                qt=qVersion(),
                os=platform.platform(),
                package_file=veri_ufku.__file__,
                backend="offscreen/software",
                physical_desktop_acceptance=False,
                help_articles=help_articles,
                runs=runs,
                images=images,
                reopened_datasets=len(projects.draft["datasets"]),
                lock_sha256=hashlib.sha256(
                    (repository / "uv.lock").read_bytes()
                ).hexdigest(),
            )
            (output / "walkthrough.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n"
            )
            print(
                "PASS: ten real formats, metadata, source hashes, ten renders and reopen"
            )
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    main()
