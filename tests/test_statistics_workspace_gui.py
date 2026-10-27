"""İstatistik yerleşim A: 8 çip, canlı/önizle, varsayım, kaydet, unsupported."""

import copy

import polars as pl
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item


def test_statistics_workspace_shell_preflight_save_unsupported(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "stats-ws.parquet"
    pl.DataFrame(
        dict(x=[1, 2, 3, 4, 3, 4, 5, 7], g=["A"] * 4 + ["B"] * 4)
    ).write_parquet(source)
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
        controller = engine._statistics_resources
        data = engine._dataset_resources
        version_before = data.dataset()["version_id"]
        before = copy.deepcopy(projects.draft)

        window.setProperty("selectedSection", 4)
        window.setProperty("examineTool", 0)
        spin(app, lambda: window.property("istatistikOpen"))
        assert window.property("centerOpen")
        assert item("statisticsWorkspace") is not None
        assert item("statisticsWorkspace").property("visible")
        assert item("statisticsCatalogPanel") is not None
        for index in range(1, 9):
            assert item(f"statisticsCatalogChip_{index}") is not None
        panel = item("statisticsPanel")
        if panel is not None:
            panel.setProperty("liveEnabled", False)
            panel.setProperty("liveArmed", False)

        item("statisticsCatalogChip_3").clicked.emit()
        app.processEvents()
        cols = {c["name"]: i for i, c in enumerate(controller.columns)}

        def field(name, prop, value):
            obj = item("statistics" + name)
            assert obj is not None, name
            assert obj.setProperty(prop, value)

        field("Path", "currentIndex", 0)
        app.processEvents()
        field("Method", "currentIndex", 0)
        field("X", "currentIndex", cols["x"])
        field("Group", "currentIndex", cols["g"])
        field("Question", "text", "Grup ortalamaları farklı mı?")
        field("Hypothesis", "text", "H0: eşit")
        field("Unit", "text", "puan")
        field("Observation", "text", "kişi")
        field("Measurement", "checked", True)
        field("Independent", "checked", True)
        app.processEvents()

        assert item("statisticsPreflight") is not None
        item("statisticsPreflight").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, controller.errorText
        assert controller.preflightCurrent
        assert data.dataset()["version_id"] == version_before
        assert projects.draft["datasets"] == before["datasets"]

        field("Assumptions", "checked", True)
        run = item("statisticsRun")
        assert run is not None
        assert run.property("enabled")
        run.clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, controller.errorText
        assert controller.current
        assert data.dataset()["version_id"] == version_before
        primary = item("statisticsPrimary")
        assert primary is not None
        assert "p=" in (primary.property("text") or "")

        item("statisticsSave").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText
        assert any("analysis" in r for r in projects.draft["results"])
        assert data.dataset()["version_id"] == version_before

        item("statisticsCatalogChip_8").clicked.emit()
        app.processEvents()
        note = item("statisticsUnsupportedNote")
        assert note is not None and note.property("visible")
        assert "desteklenmiyor" in (note.property("text") or "")

        assert source.read_bytes() == original
    finally:
        teardown(app, window)


def test_statistics_block1_no_fake_shapiro(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "stats-b1.parquet"
    pl.DataFrame(dict(x=[1.0, 2.0, 3.0, 4.0], g=["A", "A", "B", "B"])).write_parquet(
        source
    )

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        window.setProperty("selectedSection", 4)
        window.setProperty("examineTool", 0)
        spin(app, lambda: window.property("istatistikOpen"))
        item("statisticsCatalogChip_1").clicked.emit()
        app.processEvents()
        note = item("statisticsBlock1Note")
        assert note is not None and note.property("visible")
        assert "desteklenmiyor" in (note.property("text") or "")
        assert source.is_file()
    finally:
        teardown(app, window)
