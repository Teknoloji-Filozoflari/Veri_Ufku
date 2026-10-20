"""Actual synthetic GUI inspection and screenshots; no user data or desktop acceptance."""

import argparse
import hashlib
import json
import os
import platform
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


def run(output, package_root=None):
    output.mkdir(parents=True, exist_ok=True)
    if package_root:
        import sys

        sys.path.insert(0, str(package_root))
    with tempfile.TemporaryDirectory(prefix="vu-inspection-", dir=output) as tmp:
        root = Path(tmp)
        for key in ("CONFIG", "CACHE", "STATE", "DATA"):
            os.environ["XDG_" + key + "_HOME"] = str(root / key.lower())
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        from PySide6.QtCore import QObject, QPointF, qVersion
        from PySide6.QtQuick import QQuickItem
        from PySide6.QtTest import QTest

        import veri_ufku
        from veri_ufku.app import create_application

        if package_root:
            assert Path(veri_ufku.__file__).is_relative_to(package_root)

        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        data = engine._dataset_resources
        guide = engine._guide_resources
        examples = Path(__import__("veri_ufku").__file__).parent / "assets/examples"
        hashes = {
            str(p.relative_to(examples)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in examples.iterdir()
            if p.is_file()
        }
        images = []

        def visual(item, name):
            if item.objectName() == name:
                return item
            for child in item.childItems():
                result = visual(child, name)
                if result:
                    return result

        def wait(controller):
            start = time.monotonic()
            while controller.busy:
                app.processEvents()
                QTest.qWait(10)
                assert time.monotonic() - start < 60
            assert not getattr(controller, "errorText", "")

        def capture(name, target=None):
            app.processEvents()
            QTest.qWait(250)
            view = window.findChild(QQuickItem, "workspace")
            if target:
                item = visual(window.contentItem(), target)
                item.forceActiveFocus()
                app.processEvents()
                QTest.qWait(250)
                flick = view.property("contentItem")
                content = flick.property("contentItem")
                top = item.mapToItem(content, QPointF(0, 0)).y()
                flick.setProperty(
                    "contentY",
                    max(
                        0,
                        min(top - 30, flick.property("contentHeight") - flick.height()),
                    ),
                )
                app.processEvents()
                QTest.qWait(250)
            elif view:
                view.property("contentItem").setProperty("contentY", 0)
            path = output / (name + ".png")
            assert window.grabWindow().save(str(path))
            images.append(str(path))

        try:
            window.setWidth(1366)
            window.setHeight(900)
            capture("home-1366")
            window.setProperty("selectedSection", 1)
            capture("headings-1366")
            guide.createExample("problem", str(root))
            wait(guide)
            guide.close()
            window.setProperty("dataPane", "")
            for pane, button in [
                ("profile", "computeInventory"),
                ("values", "computeValues"),
                ("describe", "computeDescribe"),
            ]:
                visual(window.contentItem(), "dataHeading_" + pane).clicked.emit()
                app.processEvents()
                if pane == "values":
                    data.selectColumn(data.datasetColumns[5]["id"])
                if pane == "profile":
                    deadline = time.monotonic() + 60
                    while data.inventoryResult.get("scope") != "full" or data.busy:
                        app.processEvents()
                        QTest.qWait(10)
                        assert time.monotonic() < deadline
                    assert not data.errorText
                else:
                    window.findChild(QObject, button).clicked.emit()
                    wait(data)
                capture(
                    pane + "-1366",
                    "dataHeading_profile"
                    if pane == "profile"
                    else "describeTable"
                    if pane == "describe"
                    else "uniqueValuesList",
                )
            if window.property("dataPane") != "profile":
                visual(window.contentItem(), "dataHeading_profile").clicked.emit()
            app.processEvents()
            window.findChild(QObject, "columnNoteDescription").setProperty(
                "text",
                "Sentetik mağaza satış tutarı; Türk lirası. Eksik tutar bilinmiyor demektir.",
            )
            wait(data)
            window.findChild(QObject, "saveColumnNote").clicked.emit()
            capture("notes-1366", "columnNoteDescription")
            window.setWidth(720)
            window.setHeight(900)
            engine.rootContext().contextProperty("preferences").setTextScale(2.0)
            capture("notes-720-200", "columnNoteDescription")
            if window.property("dataPane") != "profile":
                visual(window.contentItem(), "dataHeading_profile").clicked.emit()
            app.processEvents()
            window.findChild(QObject, "computeInventory").clicked.emit()
            wait(data)
            capture("profile-720-200", "inventoryTable")
            after = {
                str(p.relative_to(examples)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in examples.iterdir()
                if p.is_file()
            }
            assert after == hashes
            record = dict(
                date=datetime.now(UTC).isoformat(),
                environment="ENV-UI-DATA-INSPECTION",
                python=platform.python_version(),
                package_file=str(Path(veri_ufku.__file__).resolve()),
                qt=qVersion(),
                backend=os.environ["QT_QPA_PLATFORM"],
                synthetic_only=True,
                physical_display=False,
                source_hashes_preserved=after == hashes,
                source_hashes=hashes,
                text_scale=engine.rootContext()
                .contextProperty("preferences")
                .property("textScale"),
                inventory=data.inventoryResult,
                images=images,
            )
            (output / "walkthrough.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n"
            )
            print("DATA INSPECTION GUI PASS", len(images), flush=True)
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()
    run(
        args.output.resolve(),
        args.package_root.resolve() if args.package_root else None,
    )
