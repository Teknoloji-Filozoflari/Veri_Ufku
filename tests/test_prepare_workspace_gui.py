"""Hazırla önizleme ekranı: merkez rozet/zincir/önce-sonra; sağ 10 blok; Mod 1/2."""

import copy

from PySide6.QtCore import QObject
from test_dataset_gui import load
from test_import_gui import spin, teardown
from test_learning_gui import visual_item


def test_prepare_workspace_shell_preview_apply_mod2_inspect(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 40)
    before = copy.deepcopy(projects.draft)
    version_before = data.dataset()["version_id"]
    ops = app._veri_ufku_resources[0]._operations_resources

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        window.setProperty("selectedSection", 2)
        window.setProperty("prepareTool", 0)
        spin(app, lambda: window.property("hazirlaOpen"))
        assert window.property("centerOpen")
        assert item("prepareWorkspace") is not None
        assert item("prepareWorkspace").property("visible")
        assert item("prepareCatalogPanel") is not None
        for index in range(1, 11):
            assert item(f"prepareCatalogChip_{index}") is not None
        assert item("prepareImpactBadges") is not None
        assert item("prepareVersionChain") is not None
        assert item("prepareBeforeTable") is not None
        assert item("prepareAfterTable") is not None
        assert item("operationPreview") is not None
        assert item("operationApply") is not None
        assert item("operationCancel") is not None
        assert item("prepareScopeModeCombo") is not None

        # Önizleme sürüm yazmaz
        item("prepareCatalogChip_1").clicked.emit()
        app.processEvents()
        spin(
            app,
            lambda: (
                item("operationPreview") is not None
                and item("operationPreview").property("enabled")
            ),
        )
        item("operationPreview").clicked.emit()
        spin(app, lambda: not ops.busy and not projects.busy)
        assert not ops.errorText, ops.errorText
        assert ops.canApply
        assert data.dataset()["version_id"] == version_before
        assert projects.draft["datasets"] == before["datasets"]

        # Uygula yeni sürüm
        item("operationApply").clicked.emit()
        spin(app, lambda: not ops.busy and not projects.busy)
        assert not ops.errorText, ops.errorText
        version_after = data.dataset()["version_id"]
        assert version_after != version_before

        # Undo geri alır
        item("prepareCatalogChip_10").clicked.emit()
        app.processEvents()
        spin(app, lambda: item("operationUndo") is not None)
        item("operationUndo").clicked.emit()
        spin(app, lambda: not ops.busy and not projects.busy)
        assert data.dataset()["version_id"] == version_before

        # inspectDraft: fill taslağı blok varsayılanı (dedup) yazmadan chip seçer
        fill_col = data.dataset()["import_metadata"]["columns"][0]["id"]
        ops.setInspectDraft(
            {
                "kind": "fill",
                "column_ids": [fill_col],
                "method": "median",
                "parameters": {"method": "median", "missing": "null"},
                "rationale": "test-fill",
                "expected_impact": "eksik",
                "origin": "İncele / Eksik veri / Eksik değer",
                "dataset_version": version_before,
            }
        )
        spin(app, lambda: ops.hasInspectDraft)
        catalog = item("prepareCatalogPanel")
        assert catalog is not None
        spin(app, lambda: catalog.property("selectedBlock") == 3)
        assert catalog.property("selectedBlock") == 3
        cleaning = item("cleaningMethod")
        # Taslağı açmadan form blok varsayılanına (dedup) zorlanmamalı
        if cleaning is not None:
            assert cleaning.property("currentIndex") != 3  # dedup index

        # inspectDraft preselect + Taslağı aç
        ops.setInspectDraft(
            {
                "kind": "outlier",
                "column_ids": [fill_col],
                "method": "mark",
                "parameters": {"action": "mark", "multiplier": "1.5", "flag_name": "Aykırı_adayı"},
                "rationale": "test",
                "expected_impact": "aday",
                "origin": "İncele / Kalite / Aykırı",
                "dataset_version": version_before,
            }
        )
        spin(app, lambda: ops.hasInspectDraft)
        frame = item("inspectDraftFrame")
        assert frame is not None and frame.property("visible")
        spin(app, lambda: catalog.property("selectedBlock") == 2)
        accept = item("inspectDraftAccept")
        if accept is not None:
            accept.clicked.emit()
            app.processEvents()
        assert catalog.property("selectedBlock") == 2
        if cleaning is not None:
            assert cleaning.property("currentIndex") == 8  # outlier

        # Mod 2 uyarı (LEARNED) — train-only motor yok
        item("prepareCatalogChip_7").clicked.emit()
        app.processEvents()
        combo = item("prepareScopeModeCombo")
        combo.setProperty("currentIndex", 1)
        catalog.setProperty("prepareScopeMode", 1)
        app.processEvents()
        warn = item("prepareMod2Warning")
        assert warn is not None
        assert warn.property("visible")
        assert "train-only" in (warn.property("text") or "")

        assert source.is_file()
        assert data.dataset()["version_id"] == version_before
    finally:
        teardown(app, window)


def test_prepare_non_learned_mod_unaffected(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 40)
    version_before = data.dataset()["version_id"]
    ops = app._veri_ufku_resources[0]._operations_resources

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        window.setProperty("selectedSection", 2)
        window.setProperty("prepareTool", 0)
        spin(app, lambda: window.property("hazirlaOpen"))
        item("prepareCatalogChip_1").clicked.emit()
        app.processEvents()
        catalog = item("prepareCatalogPanel")
        catalog.setProperty("prepareScopeMode", 1)
        item("prepareScopeModeCombo").setProperty("currentIndex", 1)
        app.processEvents()
        # trim is not LEARNED — Mod 2 uyarısı yok
        warn = item("prepareMod2Warning")
        assert warn is None or not warn.property("visible")
        spin(
            app,
            lambda: item("operationPreview").property("enabled"),
        )
        item("operationPreview").clicked.emit()
        spin(app, lambda: not ops.busy and not projects.busy)
        assert not ops.errorText
        assert data.dataset()["version_id"] == version_before
        assert source.is_file()
    finally:
        teardown(app, window)
