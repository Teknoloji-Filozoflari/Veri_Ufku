"""Isolated real registry→Qt→spawn→save/reopen walkthrough and screenshots."""

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase29/gui")
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase29-") as directory:
        root = Path(directory)
        for key in ("CONFIG", "STATE", "CACHE", "DATA"):
            os.environ["XDG_" + key + "_HOME"] = str(root / key.lower())
        from PySide6.QtCore import QObject, QPointF, Qt
        from PySide6.QtTest import QTest

        from veri_ufku.app import create_application

        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports = engine._projects_resources, engine._imports_resources
        workspace, stats = engine._workspace_resources, engine._statistics_resources
        preferences = app._veri_ufku_resources[-2]

        def spin(predicate):
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                app.processEvents()
                if predicate():
                    return
                QTest.qWait(10)
            raise RuntimeError("GUI walkthrough timeout")

        def capture(name, advanced, width):
            preferences.setView("advanced" if advanced else "beginner")
            window.setWidth(width)
            window.setHeight(850)
            app.processEvents()
            panel = window.findChild(QObject, "commonResultPanel")
            scroll = window.findChild(QObject, "workspace").property("contentItem")
            # Scroll the shared result into view, retaining real Qt geometry.
            y = panel.mapToScene(QPointF(0, 0)).y() + scroll.property("contentY") - 130
            scroll.setProperty("contentY", max(0, y))
            QTest.qWait(250)
            assert window.grabWindow().save(str(args.output / (name + ".png")))
            return dict(
                name=name,
                width=width,
                view=preferences.view,
                result_id=workspace.selected["id"],
            )

        try:
            assert projects.create(str(root / "project"))
            source = root / "pairs.csv"
            source.write_text("x,y\n-2,-2\n-1,0\n0,-1\n1,2\n2,1\n")
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            imports.choose(str(source))
            spin(lambda: not imports.busy)
            imports.importData()
            spin(lambda: not imports.busy)
            assert not imports.errorText
            preferences.setView("advanced")
            runs = []
            for method in ("pearson", "spearman"):
                QTest.keyClick(window, Qt.Key_K, Qt.ControlModifier)
                app.processEvents()
                assert window.findChild(QObject, "commandPalette").property("visible")
                workspace.search(method)
                workspace.activate("statistics." + method)
                app.processEvents()
                assert not window.findChild(QObject, "commandPalette").property(
                    "visible"
                )
                cols = {c["name"]: c["id"] for c in stats.columns}
                spec = dict(
                    path="numeric",
                    method=method,
                    x=cols["x"],
                    y=cols["y"],
                    question=method + " ilişki",
                    hypothesis="İlişki yok",
                    unit="puan",
                    observation_unit="kişi",
                    independent=True,
                    measurement_confirmed=True,
                )
                stats.create(json.dumps(spec), True)
                spin(lambda: not stats.busy)
                stats.create(json.dumps(dict(spec, assumptions_confirmed=True)), False)
                spin(lambda: not stats.busy)
                assert not stats.errorText
                ident = stats.result["result_version"]
                assert abs(stats.result["primary"]["effect"]["value"] - 0.8) < 1e-12
                stats.save()
                spin(lambda: not stats.busy)
                workspace.pin(ident)
                workspace.favorite("statistics." + method)
                workspace.savePreset(method, json.dumps(spec))
                workspace.compare(ident)
                runs.append(
                    dict(
                        method=method,
                        result_id=ident,
                        value=stats.result["primary"]["effect"]["value"],
                    )
                )
            shots = [
                capture("expert-wide", True, 1366),
                capture("beginner-wide", False, 1366),
                capture("expert-narrow", True, 720),
            ]
            path = str(projects.store.root)
            assert projects.closeProject(True) and projects.open(path)
            assert len(workspace.tabs) == 2 and len(workspace.presets) == 2
            workspace.selectResult(runs[0]["result_id"])
            assert (
                source.read_bytes()
                and hashlib.sha256(source.read_bytes()).hexdigest() == before
            )
            result = dict(
                runs=runs,
                screenshots=shots,
                source_sha256_before=before,
                source_sha256_after=hashlib.sha256(source.read_bytes()).hexdigest(),
                reopened_tabs=[t["id"] for t in workspace.tabs],
                preset_names=[p["name"] for p in workspace.presets],
                backend="offscreen/software",
                physical_desktop_acceptance=False,
            )
            (args.output / "walkthrough.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            )
            print(
                "PASS: two registry methods, palette, immutable IDs, save/reopen and three GUI renders"
            )
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    main()
