"""Developer QTest walkthrough and Qt accessibility probe; never a user/AT test."""

import argparse
import hashlib
import json
import os
import platform
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


def run(output, package_root=None, walkthrough=True):
    # Fixtures only: initial folder and XDG are isolated; actions use actual keys.
    with tempfile.TemporaryDirectory(prefix="vu25-", dir=output.parent) as tmp:
        root = Path(tmp)
        for key in ("CONFIG", "CACHE", "STATE"):
            os.environ["XDG_" + key + "_HOME"] = str(root / key.lower())
        if package_root:
            import sys

            sys.path.insert(0, str(package_root))
        from PySide6.QtCore import QObject, QPointF, Qt, QUrl, qVersion
        from PySide6.QtGui import QAccessible
        from PySide6.QtQuick import QQuickItem
        from PySide6.QtTest import QTest

        from veri_ufku.app import create_application

        app, window, bridge = create_application()
        engine = app._veri_ufku_resources[0]
        preferences = app._veri_ufku_resources[-2]
        QAccessible.setActive(True)
        actions, scenarios, screenshots = [], [], []

        def spin(predicate, timeout=30000):
            deadline = time.monotonic() + timeout / 1000
            while time.monotonic() < deadline:
                app.processEvents()
                if predicate():
                    return
                QTest.qWait(5)
            raise AssertionError("Timeout")

        def visual(node, name):
            if node.objectName() == name:
                return node
            for child in node.childItems():
                found = visual(child, name)
                if found:
                    return found
            return None

        def item(name):
            app.processEvents()
            QTest.qWait(20)
            value = visual(window.contentItem(), name) or window.findChild(
                QQuickItem, name
            )
            if value is None:
                print(
                    "MISSING",
                    name,
                    "columns",
                    engine._imports_resources.columns,
                    "source",
                    engine._imports_resources.sourcePath,
                    flush=True,
                )
            assert value is not None, name
            return value

        def focus(name):
            target = item(name)
            assert target.isVisible() and target.isEnabled(), name
            visited = []
            for _ in range(1200):
                current = window.activeFocusItem()
                ancestor = current
                while ancestor and ancestor is not target:
                    ancestor = ancestor.parentItem()
                if ancestor is target:
                    QTest.qWait(10)
                    return target
                visited.append(
                    (current.objectName(), current.metaObject().className())
                    if current
                    else "null"
                )
                QTest.keyClick(window, Qt.Key_Tab)
                app.processEvents()
                QTest.qWait(1)  # Allow popup/focus transitions to finish between keys.
            window.grabWindow().save(
                str(output.with_name(output.stem + "-focus-failure.png"))
            )
            raise AssertionError(f"Tab cannot reach {name}: {visited[-30:]}")

        def click(name):
            focus(name)
            QTest.keyClick(window, Qt.Key_Space)
            app.processEvents()
            actions.append(dict(action="Space", control=name))

        def write(name, text):
            focus(name)
            QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
            app.clipboard().setText(text)
            QTest.keyClick(window, Qt.Key_V, Qt.ControlModifier)
            QTest.keyClick(window, Qt.Key_Tab)
            app.processEvents()
            assert item(name).property("text") == text, name
            actions.append(dict(action="keyboard paste", control=name))

        def choose(name, index):
            target = focus(name)
            # Closed ComboBox arrows activate its real selected-value handler.
            for _ in range(abs(index - target.property("currentIndex"))):
                target = item(name)
                key = (
                    Qt.Key_Down
                    if target.property("currentIndex") < index
                    else Qt.Key_Up
                )
                QTest.keyClick(window, key)
                app.processEvents()
            assert item(name).property("currentIndex") == index, (
                name,
                index,
                item(name).property("currentIndex"),
                window.activeFocusItem().objectName(),
            )
            actions.append(dict(action="arrow selection", control=name, index=index))

        def nav(index):
            QTest.keyClick(window, Qt.Key_1 + index, Qt.ControlModifier)
            spin(lambda: window.property("selectedSection") == index)

        def wait(controller):
            spin(lambda: not controller.busy)
            assert not controller.errorText, controller.errorText

        def snap(name):
            QTest.qWait(100)
            dest = output.with_name(output.stem + "-" + name + ".png")
            assert window.grabWindow().save(str(dest))
            screenshots.append(str(dest))

        try:
            window.setWidth(1366)
            window.setHeight(900)
            spin(lambda: not window.grabWindow().isNull())
            item("beginnerButton").forceActiveFocus()  # Single initial focus setup.
            click("roadmapOpen_0")
            assert window.property("selectedSection") == 1
            click("dataHeading_import")
            assert window.property("dataPane") == "import"
            # Escape help restores origin and advanced retains article+panel.
            QTest.keyClick(window, Qt.Key_F1)
            spin(lambda: window.property("infoOpen"))
            article = engine._learning_resources.article["id"]
            preferences.setView("advanced")
            assert (
                window.property("infoOpen")
                and engine._learning_resources.article["id"] == article
            )
            QTest.keyClick(window, Qt.Key_Escape)
            spin(lambda: not window.property("infoOpen"))
            engine._guide_resources.close()
            if window.property("dataPane") == "import":
                click("dataHeading_import")
            preferences.setView("beginner")
            if walkthrough:
                nav(0)
                # Starting folder is a fixture, same tree chooser and publication path.
                window.findChild(QObject, "projectLocationPicker").setProperty(
                    "currentFolder", QUrl.fromLocalFile(str(root))
                )
                click("newProjectButton")
                click("chooseProjectLocationButton")
                spin(lambda: not engine._folders_resources.busy)
                click("projectLocationPickerChoose")
                click("confirmProjectPathButton")
                wait(engine._projects_resources)
                assert engine._projects_resources.opened
                source = root / "input.csv"
                source.write_text(
                    "x,y,g\n"
                    + "".join(
                        f"{'' if i == 2 else i + 0.5},{2 * i + 3.5},{'A' if i < 60 else 'B'}\n"
                        for i in range(120)
                    )
                )
                source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                nav(1)
                click("dataHeading_import")
                write("importPathInput", str(source))
                click("importPathOpen")
                wait(engine._imports_resources)
                focus("importHeaderRow")
                QTest.keyClick(window, Qt.Key_Up)
                click("previewCsvButton")
                wait(engine._imports_resources)
                choose("importDecimal", 0)
                write("importNullMarkers", "|NA|NULL")
                choose("importType_x", 2)
                choose("importType_y", 2)
                click("previewCsvButton")
                wait(engine._imports_resources)
                click("importCsvButton")
                wait(engine._imports_resources)
                click("dataHeading_rows")
                click("loadDatasetButton")
                wait(engine._dataset_resources)
                # Column selection is a real bounded list button; assign stable object name in QML.
                click("datasetColumn_x")
                choose("profileMethod", 1)
                click("computeColumnProfile")
                wait(engine._dataset_resources)
                assert engine._dataset_resources.profileResult["column_id"]
                click("saveColumnProfile")
                scenarios.append(
                    dict(
                        id="W25-01",
                        result="passed",
                        scope="create project / CSV preview / import / full profile",
                        fixture_setup="initial folder and XDG",
                    )
                )
                original_version = engine._dataset_resources.dataset()["version_id"]
                snap("profile")
                nav(2)
                choose("operationKind", 3)
                choose("cleaningColumn", 0)
                write("cleaningValue", "0")
                click("operationPreview")
                wait(engine._operations_resources)
                click("operationApply")
                wait(engine._operations_resources)
                assert (
                    engine._dataset_resources.dataset()["version_id"]
                    != original_version
                )
                click("operationUndo")
                wait(engine._operations_resources)
                assert (
                    engine._dataset_resources.dataset()["import_metadata"]["row_count"]
                    == 120
                )
                assert (
                    engine._dataset_resources.dataset()["version_id"]
                    == original_version
                )
                scenarios.append(
                    dict(
                        id="W25-02",
                        result="passed",
                        scope="constant missing fill / full preview / publication / undo",
                    )
                )
                nav(3)
                choose("chartX", 0)
                click("chartCreate")
                wait(engine._charts_resources)
                assert not engine._charts_resources.provider.image.isNull()
                snap("chart")
                nav(6)
                write("reportOutputPath", str(root / "report.html"))
                click("reportHTML")
                wait(engine._exports_resources)
                assert (root / "report.html").is_file()
                scenarios.append(
                    dict(
                        id="W25-03",
                        result="passed",
                        scope="histogram / HTML report",
                        sample_label=engine._charts_resources.result["scope"],
                    )
                )
                nav(4)
                choose("statisticsX", 0)
                choose("statisticsGroup", 2)
                write("statisticsQuestion", "Iki subenin ortalama olcumu farkli mi?")
                write("statisticsHypothesis", "Iki grubun ortalamalari esit")
                write("statisticsUnit", "puan")
                write("statisticsObservation", "bagimsiz sentetik kayit")
                for name in ("statisticsMeasurement", "statisticsIndependent"):
                    if not item(name).property("checked"):
                        click(name)
                click("statisticsPreflight")
                wait(engine._statistics_resources)
                click("statisticsAssumptions")
                click("statisticsRun")
                wait(engine._statistics_resources)
                assert engine._statistics_resources.result["primary"]
                scenarios.append(
                    dict(
                        id="W25-04",
                        result="passed",
                        scope="Welch t / explicit assumptions / result",
                    )
                )
                snap("compare")
                nav(5)
                choose("preparationTarget", 1)
                if item("preparationFeature_g").property("checked"):
                    click("preparationFeature_g")
                write("preparationContext", "Olcum alinmadan once x biliniyor")
                click("preparationScan")
                wait(engine._preparation_resources)
                assert not engine._preparation_resources.result["blockers"]
                write("validationNote_x", "Tahmin aninda mevcut olcum")
                click("validationRun")
                wait(engine._validation_resources)
                click("lifecycleOpenSaved")
                wait(engine._lifecycle_resources)
                new = root / "new.csv"
                new.write_text("g,y,x\nA,6.5,1.5\nB,8.5,2.5\n")
                nav(1)
                click("dataHeading_import")
                write("importPathInput", str(new))
                click("importPathOpen")
                wait(engine._imports_resources)
                if item("importHeaderRow").property("value") != 1:
                    focus("importHeaderRow")
                    QTest.keyClick(window, Qt.Key_Up)
                    click("previewCsvButton")
                    wait(engine._imports_resources)
                choose("importDecimal", 0)
                choose("importType_y", 2)
                choose("importType_x", 2)
                click("previewCsvButton")
                wait(engine._imports_resources)
                click("importCsvButton")
                wait(engine._imports_resources)
                nav(5)
                choose("lifecycleDataset", 1)
                click("lifecyclePreview")
                wait(engine._lifecycle_resources)
                write("lifecycleOutputPath", str(root / "prediction.parquet"))
                click("lifecyclePredict")
                wait(engine._lifecycle_resources)
                assert (
                    engine._lifecycle_resources.outputReport["details"]["fit_calls"]
                    == 0
                )
                assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
                scenarios.append(
                    dict(
                        id="W25-05",
                        result="passed",
                        scope="prepare / baseline development / frozen model / new CSV / prediction",
                        fit_calls=0,
                        target_success_metric=None,
                    )
                )
                snap("prediction")
            # Actual Qt interfaces, distinct from AT-SPI/Orca validation.
            names = []
            for index in range(8):
                nav(index)
                for child in window.findChildren(QQuickItem):
                    if not child.isVisible() or not child.isEnabled():
                        continue
                    interface = QAccessible.queryAccessibleInterface(child)
                    if interface and interface.role() in (
                        QAccessible.Button,
                        QAccessible.ComboBox,
                        QAccessible.CheckBox,
                        QAccessible.EditableText,
                        QAccessible.SpinBox,
                    ):
                        name = interface.text(QAccessible.Name)
                        if child.property("focusPolicy") == Qt.NoFocus:
                            continue
                        assert name.strip(), (
                            index,
                            child.objectName(),
                            str(interface.role()),
                            child.metaObject().className(),
                            child.parentItem().objectName()
                            if child.parentItem()
                            else "no parent",
                        )
                        names.append(
                            dict(
                                section=index,
                                object=child.objectName(),
                                name=name,
                                role=str(interface.role()),
                            )
                        )
            for theme in ("dark", "light"):
                preferences.setTheme(theme)
                preferences.setTextScale(2)
                window.setWidth(720)
                window.setHeight(560)
                nav(1)
                for name in ("dataHeading_import", "helpButton", "displayButton"):
                    focus(name)
                    p = item(name).mapToScene(QPointF(0, 0))
                    assert (
                        0 <= p.x() and p.x() + item(name).width() <= window.width() + 1
                    ), (theme, name, "horizontal overflow")
                nav(0)
                focus("newProjectButton")
                snap(theme + "-200-small")
            result = dict(
                date=datetime.now(UTC).isoformat(),
                environment=dict(
                    os=platform.platform(),
                    python=platform.python_version(),
                    qt=qVersion(),
                    backend=os.environ.get("QT_QPA_PLATFORM", "native"),
                    scale_factor=os.environ.get("QT_SCALE_FACTOR", "1"),
                ),
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                actions=actions,
                scenarios=scenarios,
                qt_accessible_names=names,
                screenshots=screenshots,
                assistive_technology_test=False,
                real_user_test=False,
                physical_display_test=False,
            )
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            print(
                "WALKTHROUGH PASS",
                len(scenarios),
                "scenarios",
                len(actions),
                "keyboard actions",
            )
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase25/walkthrough.json")
    )
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--layout-only", action="store_true")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run(args.output, args.package_root, not args.layout_only)
