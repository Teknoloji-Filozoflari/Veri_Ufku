"""Capture UX v2 module screenshots for README (offscreen Qt, not human UX)."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject  # noqa: E402
from PySide6.QtQuick import QQuickItem  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from veri_ufku.app import create_application  # noqa: E402


def spin(app, predicate, timeout_ms=20000):
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("capture condition timed out")


def visual_item(node, name):
    if node is None:
        return None
    if isinstance(node, QObject) and node.objectName() == name:
        return node
    children = node.childItems() if isinstance(node, QQuickItem) else []
    for child in children:
        found = visual_item(child, name)
        if found is not None:
            return found
    return None


def item(window, name):
    found = window.findChild(QObject, name)
    if found is not None:
        return found
    return visual_item(window.contentItem(), name)


def grab(window, path: Path):
    QTest.qWait(160)
    assert window.grabWindow().save(str(path)), path


def run(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    shots: list[str] = []
    with tempfile.TemporaryDirectory(prefix="vu-readme-") as temp:
        root = Path(temp)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ[f"XDG_{key}_HOME"] = str(root / key.lower())
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects = engine._projects_resources
        imports = engine._imports_resources
        data = engine._dataset_resources
        try:
            assert projects.create(str(root / "project"))
            window.setWidth(1366)
            window.setHeight(860)
            window.show()
            app.processEvents()
            spin(app, lambda: not window.grabWindow().isNull())
            QTest.qWait(200)

            # Boş Veri kahramanı
            spin(app, lambda: item(window, "moduleVeri") is not None)
            veri = item(window, "moduleVeri")
            assert veri is not None
            veri.clicked.emit()
            spin(app, lambda: window.property("veriEmpty"))
            grab(window, output / "01-veri-bos.png")
            shots.append("01-veri-bos")

            source = root / "sample.csv"
            source.write_text(
                "id,amount,category,note\n"
                + "".join(
                    f"{i:04},{10 + (i % 7) * 5},{'A' if i % 2 == 0 else 'B'},"
                    f"{'  x  ' if i % 11 == 0 else 'ok'}\n"
                    for i in range(80)
                ),
                encoding="utf8",
            )
            imports.choose(str(source))
            spin(app, lambda: not imports.busy)
            imports.refreshPreview()
            spin(app, lambda: not imports.busy and imports.ready)
            imports.importData(False)
            spin(app, lambda: not imports.busy and len(data.datasets) > 0)
            assert not imports.errorText, imports.errorText

            # Yüklü Veri tablosu
            veri.clicked.emit()
            spin(
                app,
                lambda: (
                    not window.property("veriEmpty")
                    and item(window, "dataWorkspacePanel") is not None
                ),
            )
            grab(window, output / "02-veri-yuklu.png")
            shots.append("02-veri-yuklu")

            # İncele + tarama
            item(window, "moduleIncele").clicked.emit()
            spin(app, lambda: window.property("inceleOpen"))
            data.computeQuality(True, "dataset", "inspect", "[]", "[]")
            spin(app, lambda: not data.busy and bool(data.qualityResult))
            grab(window, output / "03-incele.png")
            shots.append("03-incele")

            # Görselleştir
            item(window, "moduleGrafik").clicked.emit()
            spin(app, lambda: window.property("gorsellestirOpen"))
            grab(window, output / "04-gorsellestir.png")
            shots.append("04-gorsellestir")

            # Hazırla
            item(window, "moduleHazirla").clicked.emit()
            spin(app, lambda: window.property("hazirlaOpen"))
            window.setProperty("prepareTool", 0)
            app.processEvents()
            grab(window, output / "05-hazirla.png")
            shots.append("05-hazirla")

            # İstatistik
            item(window, "moduleIstatistik").clicked.emit()
            spin(app, lambda: window.property("istatistikOpen"))
            grab(window, output / "06-istatistik.png")
            shots.append("06-istatistik")

            # Model (kuruluysa)
            model_btn = item(window, "moduleModel")
            if model_btn is not None and model_btn.property("visible"):
                model_btn.clicked.emit()
                spin(app, lambda: window.property("modelOpen"))
                grab(window, output / "07-model.png")
                shots.append("07-model")

            # Raporla
            item(window, "moduleRapor").clicked.emit()
            spin(app, lambda: window.property("raporlaOpen"))
            grab(window, output / "08-raporla.png")
            shots.append("08-raporla")
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()

    report = {
        "purpose": "README UX v2 screenshots",
        "human_review": False,
        "size": "1366x860",
        "screenshots": shots,
    }
    (output / "capture.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/evidence/ux-v2/screens"),
    )
    run(parser.parse_args().output)
