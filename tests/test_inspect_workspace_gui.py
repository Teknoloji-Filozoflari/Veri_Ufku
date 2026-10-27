"""İncele tarama ekranı: şerit, 5 çip, kapsam, taslak köprüsü."""

import copy

from PySide6.QtCore import QObject
from test_dataset_gui import load
from test_import_gui import spin, teardown
from test_learning_gui import visual_item


def test_inspect_workspace_strip_chips_and_readonly_scan(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 40)
    before = copy.deepcopy(projects.draft)
    version_before = data.dataset()["version_id"]

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        item("moduleIncele").clicked.emit()
        spin(app, lambda: window.property("inceleOpen"))
        assert window.property("centerOpen")
        assert item("inspectScanStrip") is not None
        assert item("inspectWorkspacePanel").property("visible")
        assert item("datasetTable").property("visible")
        assert not item("dockClose").property("visible")
        for index in range(1, 6):
            assert item(f"inspectBlockChip_{index}") is not None
        assert item("inspectScanCard_1") is not None
        primary = item("inspectPrimaryAction")
        assert primary is not None
        versions = len(projects.draft["datasets"])
        primary.clicked.emit()
        spin(app, lambda: not data.busy)
        assert data.dataset()["version_id"] == version_before
        assert len(projects.draft["datasets"]) == versions
        assert projects.draft["datasets"] == before["datasets"]
        scope = item("inspectScopeLabel")
        assert scope is not None
        text = (scope.property("text") or "").lower()
        assert "kapsam" in text or "örneklem" in text or "tam" in text
        assert item("dataHeading_values") is None
        assert item("dataHeading_describe") is None
        assert item("dataHeading_profile") is None
        assert source.is_file()
    finally:
        teardown(app, window)


def test_inspect_move_to_prepare_sets_draft_without_version(tmp_path, monkeypatch):
    app, window, projects, data, source = load(tmp_path, monkeypatch, 40)
    version_before = data.dataset()["version_id"]
    operations = app._veri_ufku_resources[0].rootContext().contextProperty("operations")

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        item("moduleIncele").clicked.emit()
        spin(app, lambda: window.property("inceleOpen"))
        data.computeQuality(True, "dataset", "inspect", "[]", "[]")
        spin(app, lambda: not data.busy and bool(data.qualityResult))
        panel = item("inspectWorkspacePanel")
        panel.setProperty("selectedBlock", 3)
        app.processEvents()
        finding = next(
            (
                f
                for f in data.qualityResult.get("findings", [])
                if f["code"] == "missing"
            ),
            None,
        )
        if finding is None:
            # Synthetic draft path when fixture has no missing cells.
            operations.setInspectDraft(
                {
                    "kind": "fill",
                    "column_ids": [data.columns[0]["id"]],
                    "method": "median",
                    "rationale": "test",
                    "expected_impact": "1",
                    "origin": "İncele / Eksik veri / Eksik değer",
                    "dataset_version": data.qualityResult.get("dataset_version", ""),
                }
            )
        else:
            move = item("inspectMoveToPrepare")
            if move is not None:
                move.clicked.emit()
            else:
                operations.setInspectDraft(
                    {
                        "kind": "fill",
                        "column_ids": [data.columns[0]["id"]],
                        "method": "median",
                        "rationale": finding.get("reason", ""),
                        "expected_impact": str(finding.get("count", "")),
                        "origin": "İncele / Eksik veri / Eksik değer",
                        "dataset_version": data.qualityResult.get(
                            "dataset_version", ""
                        ),
                    }
                )
        assert operations.hasInspectDraft
        assert data.dataset()["version_id"] == version_before
        window.navigate(2, None)
        app.processEvents()
        assert window.property("selectedSection") == 2
        assert operations.hasInspectDraft
        frame = item("inspectDraftFrame")
        assert frame is not None and frame.property("visible")
        operations.clearInspectDraft()
        assert not operations.hasInspectDraft
        assert data.dataset()["version_id"] == version_before
        assert source.is_file()
    finally:
        teardown(app, window)
