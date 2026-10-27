"""Raporla yerleşim A: merkez+8 çip, bölüm seçimi, freshness, export kapısı."""

import copy

import polars as pl
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item


def test_report_workspace_shell_sections_and_build(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "report-ws.parquet"
    pl.DataFrame(dict(x=[1, 2, 3, 4], y=[4, 3, 2, 1])).write_parquet(source)
    original = source.read_bytes()

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        engine = app._veri_ufku_resources[0]
        data = engine._dataset_resources
        version_before = data.dataset()["version_id"]
        before = copy.deepcopy(projects.draft)

        window.setProperty("selectedSection", 6)
        window.setProperty("reportTool", 0)
        spin(app, lambda: window.property("raporlaOpen"))
        assert window.property("centerOpen")
        assert item("reportWorkspace") is not None
        assert item("reportWorkspace").property("visible")
        panel = item("reportCatalogPanel")
        assert panel is not None and panel.property("visible")
        assert item("reportCatalogTitle").property("text") == "Raporla"
        for index in range(1, 9):
            assert item(f"reportBlockChip_{index}") is not None
        assert item("reportExportHtml") is not None
        assert item("reportExportPdf") is not None
        assert item("reportFreshness") is not None
        assert item("reportLimitationsBanner") is not None
        assert "yeniden hesaplamaz" in (
            item("reportLimitationsBanner").property("text") or ""
        )

        # Toggle section 2 on (may already be off); chip click toggles
        item("reportBlockChip_2").clicked.emit()
        app.processEvents()
        count = panel.property("selectedCount")
        assert count >= 1

        item("reportLayoutBuild").clicked.emit()
        builder = engine._report_builder_resources
        spin(app, lambda: not builder.busy, timeout=60000)
        assert not builder.errorText, builder.errorText
        assert builder.result and builder.result.get("status") == "completed"
        assert data.dataset()["version_id"] == version_before
        assert projects.draft["datasets"] == before["datasets"]
        assert any("scientific_report" in r for r in projects.draft["results"])
        assert source.read_bytes() == original

        # Export gated until reviewed
        assert not item("reportExportHtml").property("enabled")
        panel.setProperty("reviewed", True)
        item("reportLayoutReviewed").setProperty("checked", True)
        app.processEvents()
        assert panel.property("reviewed")
        assert item("reportExportHtml").property("enabled")
        assert builder.saved
    finally:
        teardown(app, window)


def test_report_block8_limitations_visible(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "report-b8.parquet"
    pl.DataFrame(dict(a=[1.0, 2.0])).write_parquet(source)

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        window.setProperty("selectedSection", 6)
        window.setProperty("reportTool", 0)
        spin(app, lambda: window.property("raporlaOpen"))
        note = item("reportLimitationsNote")
        assert note is not None
        assert "yeniden hesaplamaz" in (note.property("text") or "")
    finally:
        teardown(app, window)
