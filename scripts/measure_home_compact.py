"""Capture actual home/dialog layouts and folder-only create/open from source or wheel."""

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
from PySide6.QtCore import QObject, QUrl  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import veri_ufku  # noqa: E402
from veri_ufku.app import create_application  # noqa: E402


def run(args):
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = dict(
        environment="ENV-UI-HOME-COMPACT",
        date="2026-10-08",
        package=str(veri_ufku.__file__),
        backend="offscreen/software",
        user_test=False,
        screenshots=[],
    )
    with tempfile.TemporaryDirectory(prefix="vu-home-") as temp:
        base = Path(temp)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects = engine._projects_resources

        def wait(test):
            deadline = time.monotonic() + 20
            while not test():
                app.processEvents()
                QTest.qWait(10)
                assert time.monotonic() < deadline

        def field(name):
            obj = window.findChild(QObject, name)
            assert obj is not None, name
            return obj

        def shot(name, width):
            window.setWidth(width)
            window.setHeight(800)
            app.processEvents()
            QTest.qWait(120)
            path = args.output.with_name(args.output.stem + "-" + name + ".png")
            assert window.grabWindow().save(str(path))
            result["screenshots"].append(str(path))

        try:
            shot("home-1366", 1366)
            shot("home-720", 720)
            assert window.findChild(QObject, "projectPathField") is None
            field("newProjectButton").clicked.emit()
            shot("new-project-720", 720)
            assert not field("confirmProjectPathButton").property("enabled")
            field("chooseProjectLocationButton").clicked.emit()
            parent = base / "Klasör #1"
            parent.mkdir()
            (parent / "İş projesi").mkdir()
            (parent / ".gizli").mkdir()
            picker = field("projectLocationPicker")
            picker.setProperty("currentFolder", QUrl.fromLocalFile(str(parent)))
            wait(lambda: not engine._folders_resources.busy)
            wait(lambda: field("projectLocationPickerList").property("count") == 1)
            field("projectLocationPickerHidden").setProperty("checked", True)
            wait(lambda: field("projectLocationPickerList").property("count") == 2)
            field("projectLocationPickerSearch").setProperty("text", "İş")
            wait(lambda: field("projectLocationPickerList").property("count") == 1)
            shot("folder-picker-720", 720)
            shot("folder-picker-1366", 1366)
            picker.setProperty("selectedFolder", QUrl.fromLocalFile(str(parent)))
            field("projectLocationPickerChoose").clicked.emit()
            field("confirmProjectPathButton").clicked.emit()
            wait(lambda: not projects.busy)
            assert projects.opened and not projects.errorText
            projects.setName("Araştırma projem")
            projects.request("save")
            wait(lambda: not projects.busy)
            assert projects.recentProjects[0]["name"] == "Araştırma projem"
            saved = projects.store.root
            assert saved == parent / "Yeni_Proje"
            shot("recent-names-1366", 1366)
            assert projects.closeProject(True)
            field("openProjectButton").clicked.emit()
            open_picker = field("openProjectFolderPicker")
            open_picker.setProperty("currentFolder", QUrl.fromLocalFile(str(saved)))
            open_picker.setProperty("selectedFolder", QUrl.fromLocalFile(str(saved)))
            wait(lambda: not engine._folders_resources.busy)
            field("openProjectFolderPickerChoose").clicked.emit()
            wait(lambda: not projects.busy)
            assert projects.opened and projects.name == "Araştırma projem"
            result.update(
                folder_only=True,
                encoded_unicode_path=True,
                search_and_hidden=True,
                created_and_reopened=True,
                recent_name=projects.recentProjects[0]["name"],
                buttons={
                    name: field(name).property("width")
                    for name in [
                        "newProjectButton",
                        "openProjectButton",
                        "openFileButton",
                        "sampleButton",
                        "saveProjectButton",
                    ]
                },
            )
            assert all(w <= 340 for w in result["buttons"].values())
            engine._learning_resources.openContext("project")
            assert engine._learning_resources.article["content_version"] == 17
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("HOME COMPACT PASS", args.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/evidence/ui-home-compact/headless.json"),
    )
    parser.add_argument("--package-root", type=Path)
    run(parser.parse_args())
