"""Shared accessibility and help contracts; these are developer tests, not AT."""

import copy
import json
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAccessible
from PySide6.QtQml import QQmlEngine, QQmlExpression
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown

from veri_ufku.learning.audit import audit
from veri_ufku.learning.catalog import Catalog
from veri_ufku.ui.preferences import PresentationPreferences

ROOT = Path(__file__).resolve().parents[1]


def expression(obj, source):
    expr = QQmlExpression(QQmlEngine.contextForObject(obj), obj, source)
    result = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return result


def test_structural_audit_and_missing_help_rejection(tmp_path):
    result = audit(ROOT)
    assert len(result["articles"]) == 414 and result["core_english_messages"] >= 216
    assert {
        "dashboard-question",
        "dashboard-filter-scope",
        "dashboard-kpi",
        "figure-readable",
    } <= {a["id"] for a in result["articles"]}
    assert result["assistive_technology_test"] is False
    data = copy.deepcopy(Catalog().data)
    data["contexts"]["model.new-data"] = "broken-id"
    file = tmp_path / "broken.json"
    file.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Missing help article"):
        Catalog(file)


def test_future_common_component_missing_accessible_name_fails(tmp_path):
    # Audit uses real help/translation fixtures and a newly introduced bad field.
    qml = tmp_path / "src/veri_ufku/ui/qml"
    qml.mkdir(parents=True)
    (qml / "Bad.qml").write_text('UiCombo { model: ["A"]; helpContext: "home" }')
    with pytest.raises(ValueError, match="Missing accessible purpose"):
        audit(tmp_path)


def test_ui_preferences_are_atomic_and_do_not_touch_parsing(tmp_path):
    file = tmp_path / "settings.json"
    file.write_text('{"locale":"tr", "budget":{"cpu_threads":1}}')
    before = file.read_bytes()
    p = PresentationPreferences(tmp_path)
    p.setTheme("light")
    p.setTextScale(2)
    p.setLocale("en")
    p.setView("advanced")
    q = PresentationPreferences(tmp_path)
    assert (q.theme, q.textScale, q.locale, q.view) == ("light", 1.0, "en", "advanced")
    assert file.read_bytes() == before
    original = p.path.read_bytes()
    p.setTextScale(float("inf"))
    p.setLocale("unknown")
    assert p.path.read_bytes() == original
    p.setLocale("kk")
    assert json.loads(p.path.read_text())["locale"] == "kk"
    assert json.loads(p.path.read_text())["text_scale"] == 1.0


def test_qt_names_display_keyboard_locale_and_import_boundary(tmp_path, monkeypatch):
    app, window, _, _, imports = setup(tmp_path, monkeypatch)
    preferences = app._veri_ufku_resources[-2]
    try:
        QAccessible.setActive(True)
        for section, name, expected in (
            (0, "newProjectButton", "Yeni proje"),
            (1, "importPathInput", "Yerel veri dosyası yolu"),
            (4, "statisticsMethod", "Karşılaştırma yöntemi"),
            (5, "preparationPurpose", "Model amacı"),
        ):
            window.setProperty("selectedSection", section)
            app.processEvents()
            obj = window.findChild(QObject, name)
            interface = QAccessible.queryAccessibleInterface(obj)
            assert interface and interface.text(QAccessible.Name) == expected
        imports.setOption("decimal", ",")
        imports.setOption("date_format", "%d.%m.%Y")
        before = copy.deepcopy(imports.settings)
        QTest.keyClick(window, Qt.Key_Comma, Qt.ControlModifier)
        dialog = window.findChild(QObject, "displayDialog")
        spin(app, lambda: dialog.property("visible"))
        assert window.activeFocusItem().objectName() == "displayTheme"
        QTest.keyClick(window, Qt.Key_Down)
        spin(app, lambda: preferences.theme == "light")
        QTest.keyClick(window, Qt.Key_Tab)
        assert window.activeFocusItem().objectName() == "displayLocale"
        QTest.keyClick(window, Qt.Key_Down)
        spin(app, lambda: preferences.locale == "en")
        assert window.isVisible()
        assert (
            window.findChild(QObject, "newProjectButton").property("text")
            == "New project"
        )
        assert imports.settings == before
        assert expression(window, "Qt.locale().name") == "en_GB"
        QTest.keyClick(window, Qt.Key_Escape)
        spin(app, lambda: not dialog.property("visible"))
        assert window.activeFocusItem().objectName() == "displayButton"
    finally:
        # Qt application is reused across tests, so its translators must reset too.
        preferences.setLocale("tr")
        teardown(app, window)


def luminance(color):
    values = [color.redF(), color.greenF(), color.blueF()]
    values = [
        v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values
    ]
    return sum(a * b for a, b in zip(values, (0.2126, 0.7152, 0.0722)))


def test_empty_tables_do_not_trap_keyboard_focus(tmp_path, monkeypatch):
    app, window, *_ = setup(tmp_path, monkeypatch)
    try:
        window.setProperty("selectedSection", 1)
        tabs = window.findChild(QObject, "datasetTabs")
        for index, name in ((0, "datasetTable"), (1, "csvPreviewTable")):
            tabs.setProperty("currentIndex", index)
            app.processEvents()
            if index == 0:
                window.setProperty("dataPane", "rows")
                app.processEvents()
            table = window.findChild(QObject, name)
            if index == 1:
                # Empty import previews are hidden in the beginner flow.
                assert not table.isVisible()
                origin = window.findChild(QObject, "importAdvancedButton")
                origin.forceActiveFocus()
                QTest.keyClick(window, Qt.Key_Tab)
                assert window.activeFocusItem() is not table
                QTest.keyClick(window, Qt.Key_Tab, Qt.ShiftModifier)
                assert origin.hasActiveFocus()
                continue
            table.forceActiveFocus()
            QTest.keyClick(window, Qt.Key_Tab)
            assert window.activeFocusItem() is not table
            QTest.keyClick(window, Qt.Key_Tab, Qt.ShiftModifier)
            assert window.activeFocusItem() is table
    finally:
        teardown(app, window)


def test_closed_shell_releases_engine_before_reopening(tmp_path, monkeypatch):
    app, window, bridge, *_ = setup(tmp_path / "first", monkeypatch)
    engine = app._veri_ufku_resources[0]
    released = []
    engine.destroyed.connect(lambda: released.append(True))
    cleanup = app._veri_ufku_resources[-1]
    cleanup()
    assert not bridge._timer.isActive()
    cleanup()  # Shutdown is safe when called again by the caller.
    window.deleteLater()
    app, next_window, *_ = setup(tmp_path / "second", monkeypatch)
    try:
        assert released == [True]
        assert next_window.isVisible()
    finally:
        teardown(app, next_window)


def test_both_theme_contrast_shared_states(tmp_path, monkeypatch):
    app, window, *_ = setup(tmp_path, monkeypatch)
    preferences = app._veri_ufku_resources[-2]
    try:
        for theme in ("dark", "light"):
            preferences.setTheme(theme)
            app.processEvents()
            for fg, bg in (
                ("text", "surface"),
                ("secondary", "raised"),
                ("text", "field"),
                ("warning", "warningSurface"),
                ("error", "errorSurface"),
                ("accentText", "accent"),
                ("accentText", "violetPressed"),
                ("accentText", "mintPressed"),
                ("accentText", "cyanPressed"),
            ):
                a, b = (luminance(expression(window, "Theme." + v)) for v in (fg, bg))
                contrast = (max(a, b) + 0.05) / (min(a, b) + 0.05)
                assert contrast >= 4.5, (theme, fg, bg, contrast)
    finally:
        teardown(app, window)


def test_textarea_tab_exits_and_picker_survives_type_update(tmp_path, monkeypatch):
    from PySide6.QtQuick import QQuickItem
    from test_gui import visual_item

    app, window, _, _, imports = setup(tmp_path, monkeypatch)
    try:
        window.setProperty("selectedSection", 1)
        source = tmp_path / "keyboard.csv"
        source.write_text("x,y\n1.5,2.5\n3.5,4.5\n")
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.setOption("header_row", 1)
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        engine = app._veri_ufku_resources[0]
        data = engine._dataset_resources
        data.selectColumn(data.datasetColumns[0]["id"])
        window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 0)
        window.setProperty("dataPane", "rows")
        field = window.findChild(QQuickItem, "columnDescription")
        window.findChild(QObject, "columnNotesToggle").setProperty("checked", True)
        app.processEvents()
        spin(app, lambda: field.isEnabled())
        field.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Tab)
        assert not field.hasActiveFocus()
        original = field.property("text")
        QTest.keyClick(window, Qt.Key_Tab, Qt.ShiftModifier)
        assert field.hasActiveFocus() and field.property("text") == original
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 1)
        window.findChild(QObject, "importAdvancedButton").clicked.emit()
        QTest.qWait(50)
        picker = visual_item(window.contentItem(), "importType_x")
        assert picker
        picker.forceActiveFocus()
        initial = picker.property("currentIndex")
        for expected in (initial + 1, initial + 2):
            QTest.keyClick(window, Qt.Key_Down)
            QTest.qWait(30)
            replacement = visual_item(window.contentItem(), "importType_x")
            assert replacement.property("currentIndex") == expected
            assert replacement.hasActiveFocus()
    finally:
        teardown(app, window)
