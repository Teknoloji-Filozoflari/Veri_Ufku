"""Real QML, spawned computation, human approval, undo and portable reopen."""

import json
from contextlib import closing
from pathlib import Path

import polars as pl
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item

from veri_ufku.storage.project_store import ProjectStore


def loaded(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "people.csv"
    source.write_text(
        "name,town,grade,weight\nAda Lee,X,high,1\nAda Lea,X,low,900\nAda Lee,Y,mid,3\nOther,X,low,4\n"
    )
    imports.choose(str(source))
    spin(app, lambda: not imports.busy)
    imports.setType(3, "int64")
    imports.refreshPreview()
    spin(app, lambda: not imports.busy)
    imports.importData()
    spin(app, lambda: not imports.busy)
    assert imports.errorText == ""
    engine = app._veri_ufku_resources[0]
    data, operations = engine._dataset_resources, engine._operations_resources
    spin(app, lambda: not data.busy)
    window.setProperty("selectedSection", 1)
    window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 0)
    window.setProperty("dataPane", "profile")
    window.findChild(QObject, "dataContractToggle").setProperty("checked", True)
    spin(app, lambda: window.findChild(QObject, "contractColumn") is not None)
    return app, window, projects, data, operations, source


def click(window, name):
    obj = window.findChild(QObject, name) or visual_item(window.contentItem(), name)
    assert obj is not None and obj.property("enabled"), name
    obj.clicked.emit()


def finish(app, operations):
    spin(app, lambda: not operations.busy)
    assert operations.errorText == ""


def test_qml_dictionary_quality_policy_export_help_reopen(tmp_path, monkeypatch):
    app, window, projects, data, operations, source = loaded(tmp_path, monkeypatch)
    original = source.read_bytes()
    try:
        ids = {c["name"]: c["id"] for c in data.datasetColumns}
        data.selectColumn(ids["grade"])
        spin(app, lambda: not data.busy)
        window.findChild(QObject, "contractMeaning").setProperty(
            "text", "Ordered grade"
        )
        window.findChild(QObject, "contractMeasurementLevel").setProperty(
            "currentIndex", 2
        )
        window.findChild(QObject, "contractOrder").setProperty("text", "low|mid|high")
        data.changed.emit()
        app.processEvents()
        assert (
            window.findChild(QObject, "contractOrder").property("text")
            == "low|mid|high"
        )
        click(window, "contractPreviewMetadata")
        finish(app, operations)
        assert operations.canApply
        click(window, "contractApply")
        finish(app, operations)
        spin(app, lambda: not data.busy)
        d = data.dataset()
        assert d["semantic_metadata"][ids["grade"]]["measurement_level"] == "ordinal"
        assert d["semantic_metadata"][ids["grade"]]["ordinal_order"] == [
            "low",
            "mid",
            "high",
        ]
        definition = operations.contractRecipe["contract"]
        assert definition["rules"]
        click(window, "contractValidate")
        finish(app, operations)
        assert (
            operations.preview["diagnostics"]["contract_report"]["error_violations"]
            == 0
        )
        data.selectColumn(ids["weight"])
        spin(app, lambda: not data.busy)
        window.findChild(QObject, "contractUnit").setProperty("text", "kg")
        window.findChild(QObject, "contractExpectedUnit").setProperty("text", "kg")
        window.findChild(QObject, "contractMinimum").setProperty("text", "0")
        window.findChild(QObject, "contractMaximum").setProperty("text", "10")
        click(window, "contractPreviewMetadata")
        finish(app, operations)
        click(window, "contractApply")
        finish(app, operations)
        spin(app, lambda: not data.busy)
        click(window, "contractValidate")
        finish(app, operations)
        assert (
            operations.preview["diagnostics"]["contract_report"]["error_violations"]
            == 1
        )
        assert not operations.canApply
        window.findChild(QObject, "contractPolicy").setProperty("currentIndex", 1)
        click(window, "contractValidate")
        finish(app, operations)
        assert operations.preview["diagnostics"]["relation_rows"] == 1
        click(window, "contractApply")
        finish(app, operations)
        spin(app, lambda: not data.busy)
        assert data.dataset()["import_metadata"]["row_count"] == 3
        assert operations.contractReport["saved"]
        assert operations.contractReport["report"]["error_violations"] == 1
        assert operations.contractReport["policy"] == "quarantine"
        assert operations.contractReport["current"]
        path = tmp_path / "portable-contract.json"
        operations.exportContractRecipe(
            str(path), json.dumps(operations.contractRecipe)
        )
        export = json.loads(path.read_text())
        assert export["bound_dataset_version"] == data.dataset()["version_id"]
        assert export["recipe"]["semantic_metadata"][ids["grade"]]["ordinal_order"] == [
            "low",
            "mid",
            "high",
        ]
        learning = app._veri_ufku_resources[0]._learning_resources
        for name, article in [
            ("contractMeasurementLevel", "contract-level"),
            ("contractPolicy", "contract-schema"),
            ("contractForeignKey", "contract-reference"),
            ("entityThreshold", "contract-fuzzy"),
            ("entityFindCandidates", "contract-merge"),
        ]:
            obj = window.findChild(QObject, name) or visual_item(
                window.contentItem(), name
            )
            # Export can trigger a source-directory refresh that disables this grid.
            QTest.qWait(30)
            spin(app, lambda: not projects.busy and obj.property("enabled"))
            obj.forceActiveFocus()
            assert obj.property("activeFocus"), name
            QTest.keyClick(window, Qt.Key_F1)
            spin(app, lambda: window.property("infoOpen"))
            assert learning.article["id"] == article
            QTest.keyClick(window, Qt.Key_Escape)
            spin(app, lambda: not window.property("infoOpen"))
        root = projects.store.root
        copied = tmp_path / "portable-project"
        projects.store.save_as(copied)
        with closing(ProjectStore.open(copied)) as store:
            assert (
                store.state["datasets"][-1]["schema_contract"]["definition"]
                == data.dataset()["schema_contract"]["definition"]
            )
        assert Path(root).exists()
        projects.request("open", str(copied))
        spin(app, lambda: not projects.busy)
        spin(app, lambda: not data.busy)
        assert (
            operations.contractReport["saved"] and operations.contractReport["current"]
        )
        assert operations.contractReport["report"]["error_violations"] == 1
    finally:
        assert source.read_bytes() == original
        teardown(app, window)


def test_qml_no_automatic_merge_human_decision_journal_undo(tmp_path, monkeypatch):
    app, window, projects, data, operations, source = loaded(tmp_path, monkeypatch)
    original = source.read_bytes()
    try:
        original_version = data.dataset()["version_id"]
        frame = pl.read_parquet(projects.store.path(data.dataset()["snapshot_uri"]))
        window.findChild(QObject, "entityNameColumn").setProperty("currentIndex", 0)
        window.findChild(QObject, "entityBlockColumn").setProperty("currentIndex", 1)
        click(window, "entityFindCandidates")
        finish(app, operations)
        assert not operations.canApply
        assert data.dataset()["version_id"] == original_version
        assert len(operations.preview["diagnostics"]["candidates"]) == 1
        button = visual_item(window.contentItem(), "entityApprovePair")
        assert not button.property("enabled")
        window.findChild(QObject, "entityReviewer").setProperty(
            "text", "Fixture reviewer"
        )
        window.findChild(QObject, "entityReason").setProperty(
            "text", "Independent synthetic customer identity verified"
        )
        click(window, "entityApprovePair")
        finish(app, operations)
        assert data.dataset()["version_id"] == original_version
        assert operations.canApply
        click(window, "contractApply")
        finish(app, operations)
        spin(app, lambda: not data.busy)
        merged = data.dataset()
        assert merged["entity_resolution"]
        result = pl.read_parquet(projects.store.path(merged["snapshot_uri"]))
        assert result["__vu_source_record_id"].equals(frame["__vu_source_record_id"])
        assert result["canonical_id"][0] == result["canonical_id"][1]
        assert (
            operations.identityJournal[0]["approval"]["reviewer"] == "Fixture reviewer"
        )
        assert merged["version_id"] in operations.identityJournal[0]["related_versions"]
        click(window, "contractUndo")
        finish(app, operations)
        spin(app, lambda: not data.busy)
        assert data.dataset()["version_id"] == original_version
        assert pl.read_parquet(
            projects.store.path(data.dataset()["snapshot_uri"])
        ).equals(frame)
        assert len(operations.identityJournal) == 1
        click(window, "contractRedo")
        finish(app, operations)
        spin(app, lambda: not data.busy)
        assert data.dataset()["version_id"] == merged["version_id"]
        projects.request("close")
        spin(app, lambda: not projects.busy)
        assert not operations.canApply
    finally:
        assert source.read_bytes() == original
        teardown(app, window)


def test_qml_categories_manual_approval_and_real_worker_cancel(tmp_path, monkeypatch):
    app, window, projects, data, operations, source = loaded(tmp_path, monkeypatch)
    try:
        original = data.dataset()["version_id"]
        window.findChild(QObject, "entityNameColumn").setProperty("currentIndex", 0)
        click(window, "categoryFindCandidates")
        finish(app, operations)
        assert not operations.canApply
        window.findChild(QObject, "entityReviewer").setProperty(
            "text", "Category reviewer"
        )
        window.findChild(QObject, "entityReason").setProperty(
            "text", "Fixture category spelling normalization, not a person merge"
        )
        click(window, "categoryApprovePair")
        finish(app, operations)
        assert data.dataset()["version_id"] == original
        click(window, "contractApply")
        finish(app, operations)
        spin(app, lambda: not data.busy)
        assert data.dataset()["version_id"] != original
        assert operations.identityJournal[0]["mapping"]
        current = data.dataset()["version_id"]
        operations.previewCategoryCandidates(data.datasetColumns[0]["id"], 0.5)
        assert operations.busy
        click(window, "contractCancel")
        spin(app, lambda: not operations.busy)
        assert operations.state == "canceled"
        assert data.dataset()["version_id"] == current
        assert not operations.canApply
    finally:
        teardown(app, window)


def test_qml_foreign_key_unique_wrong_unit_type_actual_second_dataset(
    tmp_path, monkeypatch
):
    app, window, projects, data, operations, source = loaded(tmp_path, monkeypatch)
    try:
        first_id = data.selectedDataset
        first_version = data.dataset()["version_id"]
        imports = app._veri_ufku_resources[0]._imports_resources
        reference = tmp_path / "reference.csv"
        reference.write_text("pk\nX\n")
        imports.choose(str(reference))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert imports.errorText == ""
        spin(app, lambda: not data.busy)
        others = [
            d for d in projects.draft["datasets"] if d["version_id"] != first_version
        ]
        ref = others[-1]
        data.selectDataset(first_id)
        spin(app, lambda: not data.busy)
        town = next(c["id"] for c in data.datasetColumns if c["name"] == "town")
        data.selectColumn(town)
        spin(app, lambda: not data.busy)
        window.findChild(QObject, "contractUnique").setProperty("checked", True)
        window.findChild(QObject, "contractUnit").setProperty("text", "g")
        window.findChild(QObject, "contractExpectedUnit").setProperty("text", "kg")
        window.findChild(QObject, "contractExpectedType").setProperty("text", "Int64")
        window.findChild(QObject, "contractForeignKey").setProperty("checked", True)
        picker = window.findChild(QObject, "contractReference")
        picker.setProperty(
            "currentIndex",
            next(
                i
                for i, d in enumerate(operations.secondaryDatasets)
                if d["version_id"] == ref["version_id"]
            ),
        )
        window.findChild(QObject, "contractReferenceColumn").setProperty(
            "currentIndex", 0
        )
        click(window, "contractPreviewMetadata")
        finish(app, operations)
        click(window, "contractApply")
        finish(app, operations)
        spin(app, lambda: not data.busy)
        click(window, "contractValidate")
        finish(app, operations)
        report = operations.preview["diagnostics"]["contract_report"]
        bykind = {r["kind"]: r for r in report["rules"]}
        assert bykind["unique"]["violations"] == 3
        assert bykind["foreign_key"]["violations"] == 1
        assert bykind["unit"]["violations"] == 4
        assert bykind["type"]["violations"] == 4
        assert not operations.canApply
        window.findChild(QObject, "contractPolicy").setProperty("currentIndex", 2)
        click(window, "contractValidate")
        finish(app, operations)
        click(window, "contractApply")
        finish(app, operations)
        spin(app, lambda: not data.busy)
        assert len(data.dataset()["input_version_ids"]) == 2
        assert data.dataset()["import_metadata"]["row_count"] == 4
    finally:
        teardown(app, window)


def test_export_directory_watch_event_after_shutdown_does_not_start_io(
    tmp_path, monkeypatch
):
    app, window, projects, data, operations, source = loaded(tmp_path, monkeypatch)
    try:
        spin(app, lambda: not projects.busy)
        projects.shutdown()
        submitted = projects.future
        projects._source_changed(str(source.parent))
        projects._scheduled()
        projects.request("refresh")
        assert projects.future is submitted and projects._closing
        assert not projects.watcher.files() and not projects.watcher.directories()
    finally:
        teardown(app, window)


def test_phase07_ordinal_dictionary_extension_preserves_existing_order(
    tmp_path, monkeypatch
):
    app, window, projects, data, operations, source = loaded(tmp_path, monkeypatch)
    try:
        grade = next(c["id"] for c in data.datasetColumns if c["name"] == "grade")
        data.selectColumn(grade)
        spin(app, lambda: not data.busy)
        data.applyRole(
            "ordinal", "", "low|mid|high", "person", "Phase07 existing order"
        )
        spin(app, lambda: not data.busy)
        previous = data.dataset()["semantic_metadata"][grade]
        assert "measurement_level" not in previous
        assert previous["ordinal_order"] == ["low", "mid", "high"]
        assert (
            window.findChild(QObject, "contractMeasurementLevel").property(
                "currentIndex"
            )
            == 2
        )
        window.findChild(QObject, "contractMeaning").setProperty(
            "text", "Extended meaning"
        )
        click(window, "contractPreviewMetadata")
        finish(app, operations)
        actual = operations.preview["spec"]["parameters"]["semantic_metadata"][grade]
        assert actual["ordinal_order"] == previous["ordinal_order"]
        assert actual["role"] == previous["role"]
        assert actual["confirmed"] == previous["confirmed"]
        assert actual["measurement_level"] == "ordinal"
        click(window, "contractApply")
        finish(app, operations)
        spin(app, lambda: not data.busy)
        assert data.dataset()["semantic_metadata"][grade]["ordinal_order"] == [
            "low",
            "mid",
            "high",
        ]
    finally:
        teardown(app, window)
