"""Installed wheel/resources/QML + spawned CSV import, using frozen runtime deps."""

import argparse
import os
import tempfile
import time
from pathlib import Path

from PySide6.QtTest import QTest

import veri_ufku
from veri_ufku.app import create_application

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", required=True, type=Path)
    args = parser.parse_args()
    assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    with tempfile.TemporaryDirectory(prefix="vu-wheel-") as temporary:
        base = Path(temporary)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        app, window, bridge = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports = engine._projects_resources, engine._imports_resources
        try:
            assert projects.learning.catalog.article_for("import.csv") == "import-csv"
            assert projects.create(str(base / "project"))
            source = base / "fixture.csv"
            source.write_text("kimlik;ad\n001;Çağrı\n001;Çağrı\n", encoding="utf8")
            original = source.read_bytes()
            imports.choose(str(source))
            for action in ("preview", "import"):
                if action == "import":
                    imports.importData(True)
                deadline = time.monotonic() + 20
                while imports.busy and time.monotonic() < deadline:
                    app.processEvents()
                    QTest.qWait(10)
                assert not imports.busy and not imports.errorText, imports.errorText
                if action == "preview":
                    assert imports.ready
            assert projects.draft["datasets"][0]["import_metadata"]["row_count"] == 2
            assert projects.store.manifest["format_version"] == 4
            assert source.read_bytes() == original
            assert projects.closeProject() and projects.open(str(base / "project"))
            assert projects.draft["datasets"][0]["import_metadata"]["row_count"] == 2
            print("PHASE05_INSTALLED_WHEEL_IMPORT PASS", str(veri_ufku.__file__))
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
