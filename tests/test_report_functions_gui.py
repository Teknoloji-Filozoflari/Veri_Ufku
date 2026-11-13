"""Raporla yedi işlevi ve Word (DOCX) dışa aktarımı."""

import io
import zipfile

import polars as pl
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item


def item(window, name):
    found = window.findChild(QObject, name) or visual_item(window.contentItem(), name)
    assert found is not None, name
    return found


def visible(window, name):
    found = item(window, name)
    assert found.property("visible"), name
    return found


def test_report_exposes_the_seven_schema_functions(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "report-functions.parquet"
    pl.DataFrame(dict(x=[1, 2, 3], y=[3, 2, 1])).write_parquet(source)

    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        window.setProperty("selectedSection", 6)
        window.setProperty("reportTool", 0)
        spin(app, lambda: window.property("raporlaOpen"))
        panel = item(window, "reportCatalogPanel")
        assert panel is not None

        titles = {
            1: "Bulgu defteri",
            2: "Rapor yapısı",
            3: "Rapor öncesi kontrol",
            4: "Dışa aktar",
            5: "Yeniden üretim",
            6: "Gizlilik ve paylaşım",
            7: "İleri çıktılar",
        }
        for index, title in titles.items():
            row = item(window, f"reportFunction_{index}")
            assert row is not None
            assert title in (row.property("text") or "") or any(
                title in (child.property("text") or "")
                for child in row.findChildren(QObject)
                if hasattr(child, "property")
            )
            scope = item(window, f"reportFunctionScope_{index}")
            assert scope is not None

        # Her işlev kendi içeriğini gösterir.
        pages = {
            1: "reportNotebookSummary",
            2: "reportLayoutBuild",
            3: "reportLimitationsNote",
            4: "reportExportHtml",
            5: "reportReproOpen",
            6: "reportPrivacyOpen",
            7: "reportAdvancedModuleNote",
        }
        for index, marker in pages.items():
            panel.setProperty("currentFunction", index)
            app.processEvents()
            visible(window, marker)

        # Kaynak-aşamaya göre bölümler ikincil kalır.
        panel.setProperty("currentFunction", 2)
        app.processEvents()
        for index in range(1, 9):
            assert item(window, f"reportBlockChip_{index}") is not None
    finally:
        teardown(app, window)


def test_report_docx_export_writes_a_valid_document(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "report-docx.parquet"
    pl.DataFrame(dict(x=[1, 2, 3], y=[3, 2, 1])).write_parquet(source)
    destination = tmp_path / "rapor.docx"

    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        engine = app._veri_ufku_resources[0]
        builder = engine._report_builder_resources
        window.setProperty("selectedSection", 6)
        window.setProperty("reportTool", 0)
        spin(app, lambda: window.property("raporlaOpen"))

        panel = item(window, "reportCatalogPanel")
        panel.setProperty("currentFunction", 2)
        app.processEvents()
        item(window, "reportLayoutBuild").clicked.emit()
        spin(app, lambda: not builder.busy, timeout=60000)
        assert not builder.errorText, builder.errorText
        assert builder.result and builder.result.get("status") == "completed"

        # Dışa aktarım onay ve gözden geçirme kapısına bağlıdır.
        panel.setProperty("currentFunction", 4)
        app.processEvents()
        assert not item(window, "reportExportDocx").property("enabled")
        panel.setProperty("reviewed", True)
        item(window, "reportLayoutReviewed").setProperty("checked", True)
        app.processEvents()
        assert item(window, "reportExportDocx").property("enabled")

        item(window, "reportLayoutDestination").setProperty("text", str(destination))
        item(window, "reportExportDocx").clicked.emit()
        spin(app, lambda: not builder.busy and destination.exists(), timeout=60000)
        assert destination.is_file()
        with zipfile.ZipFile(io.BytesIO(destination.read_bytes())) as archive:
            assert archive.testzip() is None
            names = archive.namelist()
            assert "word/document.xml" in names
            assert "[Content_Types].xml" in names
            body = archive.read("word/document.xml").decode("utf-8")
        assert "Veri_Ufku" in body
    finally:
        teardown(app, window)
