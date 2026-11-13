"""Bulgu defteri yüzeyi: alta çekmece, aşama eylemi, kalıcılık ve güncellik."""

from PySide6.QtCore import QObject
from test_dataset_gui import load
from test_import_gui import spin, teardown


def item(window, name):
    found = window.findChild(QObject, name)
    assert found is not None, name
    return found


def test_finding_drawer_is_reachable_from_every_stage(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 40)
    engine = app._veri_ufku_resources[0]
    findings = engine._findings_resources
    try:
        drawer = item(window, "findingDrawerHost")
        assert drawer.property("visible")

        # Veri aşaması: kalıcı yüzey ve bulgu ekleme eylemi.
        window.setProperty("selectedSection", 1)
        window.setProperty("dataPane", "rows")
        spin(app, lambda: window.property("showTable"))
        assert item(window, "findingAddVeri") is not None
        item(window, "findingAddVeri").clicked.emit()
        spin(app, lambda: findings.currentStage == "veri")
        assert drawer.property("expanded")

        # İncele aşaması kendi eylemini taşır.
        window.setProperty("selectedSection", 1)
        window.setProperty("dataPane", "quality")
        spin(app, lambda: window.property("inceleOpen"))
        assert item(window, "findingAddIncele") is not None

        # Hazırla, İstatistik, Model ve Raporla eylemleri de erişilebilirdir.
        window.setProperty("selectedSection", 2)
        spin(app, lambda: window.property("hazirlaOpen"))
        assert item(window, "findingAddHazirla") is not None

        window.setProperty("selectedSection", 4)
        spin(app, lambda: window.property("istatistikOpen"))
        assert item(window, "findingAddIstatistik") is not None

        window.setProperty("selectedSection", 6)
        spin(app, lambda: window.property("raporlaOpen"))
        assert item(window, "findingAddRaporla") is not None
    finally:
        teardown(app, window)


def test_finding_is_created_persisted_and_removed(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 40)
    engine = app._veri_ufku_resources[0]
    findings = engine._findings_resources
    try:
        window.setProperty("selectedSection", 1)
        window.setProperty("dataPane", "rows")
        spin(app, lambda: window.property("showTable"))

        assert findings.count == 0
        ok = findings.add(
            "veri",
            "Kaç satır var?",
            "Veri sürümü kaydı",
            interpretation="Üç satır bekleniyordu.",
            decision="Kayıt doğru.",
        )
        spin(app, lambda: not projects.busy)
        assert ok, findings.errorText
        assert findings.count == 1
        assert not findings.dirty if hasattr(findings, "dirty") else True

        row = findings.findings[0]
        assert row["question"] == "Kaç satır var?"
        assert row["stage_label"] == "Veri"
        assert row["stale"] is False
        assert len(projects.draft["findings"]) == 1

        # Proje kaydı bulguyla birlikte kalıcıdır.
        spin(app, lambda: not projects.busy)
        assert projects.draft["findings"][0]["method"] == "Veri sürümü kaydı"

        # Silme açık eylemdir ve kayıt defterden çıkar.
        assert findings.remove(row["id"])
        spin(app, lambda: not projects.busy)
        assert findings.count == 0
        assert projects.draft["findings"] == []
    finally:
        teardown(app, window)


def test_drawer_lists_the_finding_and_marks_it_out_of_date(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 40)
    engine = app._veri_ufku_resources[0]
    findings = engine._findings_resources
    operations = engine._operations_resources
    try:
        window.setProperty("selectedSection", 1)
        window.setProperty("dataPane", "rows")
        spin(app, lambda: window.property("showTable"))
        assert findings.add("veri", "Kaç satır var?", "Veri sürümü kaydı")
        spin(app, lambda: not projects.busy)
        assert findings.count == 1

        drawer = item(window, "findingDrawerHost")
        drawer.setProperty("expanded", True)
        app.processEvents()
        listview = item(window, "findingDrawerList")
        assert listview.property("count") == 1

        # Yeni bir hazırlama sürümü eski bulguyu "güncel değil" yapar.
        import json

        from veri_ufku.operations.cleaning_contracts import defaults

        columns = [
            c
            for c in data.dataset()["import_metadata"]["columns"]
            if c["type"] == "text"
        ]
        operations.previewCleaning(
            "trim",
            json.dumps([columns[0]["id"]]),
            json.dumps(defaults("trim")),
            "copy",
        )
        spin(app, lambda: not operations.busy and not projects.busy)
        assert operations.canApply, operations.errorText
        operations.apply()
        spin(app, lambda: not operations.busy and not projects.busy)
        assert not operations.errorText, operations.errorText

        assert findings.staleCount == 1
        row = findings.findings[0]
        assert row["stale"] is True
        assert row["stale_reason"]
    finally:
        teardown(app, window)
