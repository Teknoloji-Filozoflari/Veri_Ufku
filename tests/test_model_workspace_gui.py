"""Model yerleşim A: merkez+10 çip, OLS fit/kaydet, sürüm değişmez, unsupported notu."""

import copy

import polars as pl
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item


def test_model_workspace_shell_fit_save_unsupported(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "model-ws.parquet"
    pl.DataFrame(
        dict(
            y=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            x=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
        )
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

        assert window.property("modelInstalled")
        window.setProperty("selectedSection", 5)
        spin(app, lambda: window.property("modelOpen"))
        assert window.property("centerOpen")
        assert item("modelWorkspace") is not None
        assert item("modelWorkspace").property("visible")
        panel = item("modelCatalogPanel")
        assert panel is not None and panel.property("visible")
        assert item("modelCatalogTitle").property("text") == "Model"
        for index in range(1, 11):
            assert item(f"modelBlockChip_{index}") is not None
        assert item("modelPrimaryAction") is not None
        assert item("modelPrimaryCancel") is not None
        assert item("modelPath") is None or not item("modelPath").property("visible")

        item("modelBlockChip_1").clicked.emit()
        app.processEvents()
        assert panel.property("selectedBlock") == 1

        cols = {c["name"]: i for i, c in enumerate(controller.columns)}

        def field(name, prop, value):
            obj = item("model" + name)
            assert obj is not None, name
            assert obj.setProperty(prop, value)

        field("Response", "currentIndex", cols["y"])
        x_id = next(c["id"] for c in controller.columns if c["name"] == "x")
        from PySide6.QtCore import Q_ARG, QMetaObject, Qt

        assert QMetaObject.invokeMethod(
            panel,
            "updateFeature",
            Qt.ConnectionType.DirectConnection,
            Q_ARG("QVariant", x_id),
            Q_ARG("QVariant", "selected"),
            Q_ARG("QVariant", True),
        )
        app.processEvents()
        field("Question", "text", "y ~ x")
        field("Hypothesis", "text", "β≠0")
        field("Unit", "text", "birim")
        field("Observation", "text", "satır")
        field("Measurement", "checked", True)
        field("Independent", "checked", True)
        app.processEvents()

        item("modelPreflight").clicked.emit()
        spin(app, lambda: not controller.busy)
        assert not controller.errorText, controller.errorText
        assert controller.preflightCurrent
        assert data.dataset()["version_id"] == version_before

        field("Assumptions", "checked", True)
        app.processEvents()
        action = item("modelPrimaryAction")
        assert action.property("enabled")
        action.clicked.emit()
        spin(app, lambda: not controller.busy and controller.current)
        assert not controller.errorText, controller.errorText
        spin(
            app,
            lambda: any(
                "analysis" in r or (isinstance(r, dict) and "models" in str(r))
                for r in projects.draft.get("results", [])
            )
            or controller.current,
        )
        assert data.dataset()["version_id"] == version_before
        assert projects.draft["datasets"] == before["datasets"]
        assert item("modelLayerStrip") is not None
        assert "held-out" in (item("modelTestN").property("text") or "").lower() or "yok" in (
            item("modelTestN").property("text") or ""
        ).lower()

        item("modelBlockChip_7").clicked.emit()
        app.processEvents()
        note = item("modelBlock7Note")
        assert note is not None and note.property("visible")
        assert "desteklenmiyor" in (note.property("text") or "").lower()

        assert source.read_bytes() == original
    finally:
        teardown(app, window)


def test_model_block7_no_fake_formula(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "model-b7.parquet"
    pl.DataFrame(dict(y=[1.0, 2.0, 3.0, 4.0], x=[1.0, 2.0, 3.0, 4.0])).write_parquet(
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
        window.setProperty("selectedSection", 5)
        spin(app, lambda: window.property("modelOpen"))
        item("modelBlockChip_7").clicked.emit()
        app.processEvents()
        assert not item("modelPrimaryAction").property("enabled")
        assert "desteklenmiyor" in (item("modelBlock7Note").property("text") or "").lower()
    finally:
        teardown(app, window)
