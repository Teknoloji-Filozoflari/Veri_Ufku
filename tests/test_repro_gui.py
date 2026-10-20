"""Real QML report->source graph, bundle opt-in and explicit bounded re-run."""

import json

import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown

CAPTURE = None


def imported(tmp_path, monkeypatch, budget_bytes=None):
    if budget_bytes is not None:
        config = tmp_path / "config" / "veri_ufku"
        config.mkdir(parents=True, exist_ok=True)
        (config / "settings.json").write_text(
            json.dumps(dict(budget=dict(ram_bytes=budget_bytes)))
        )
    source = tmp_path / "input.parquet"
    pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.0, 6.0, 8.0]}).write_parquet(
        source
    )
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._repro_resources
    data = engine._dataset_resources
    imports.choose(str(source))
    spin(app, lambda: not imports.busy and not projects.busy)
    imports.importData(True)
    spin(app, lambda: not imports.busy and not projects.busy)
    assert not imports.errorText, imports.errorText
    data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
    spin(app, lambda: not data.busy)
    data.column_id = data.dataset()["import_metadata"]["columns"][0]["id"]
    data.computeProfile(False, "dataset", 1)
    spin(app, lambda: not data.busy and not projects.busy, timeout=60000)
    assert data.profile_result and data.profile_result["numeric"]["mean"] == "2.5"
    data.saveProfile()
    projects.save()
    spin(app, lambda: not projects.busy)
    ident = projects.draft["results"][-1]["id"]
    window.setProperty("selectedSection", 6)
    window.findChild(QObject, "reproExpanded").setProperty("checked", True)
    spin(app, lambda: c.canAct)
    return app, window, projects, c, ident, source


def focus(window, c, ident):
    index = next(i for i, v in enumerate(c.targets) if v["id"] == ident)
    window.findChild(QObject, "reproFocus").setProperty("currentIndex", index)


def test_gui_report_lineage_reference_bundle_rerun(tmp_path, monkeypatch):
    app, window, projects, c, ident, source = imported(tmp_path, monkeypatch)
    before = source.read_bytes()
    try:
        exports = app._veri_ufku_resources[0]._exports_resources
        report = tmp_path / "report.html"
        exports.create(
            "report",
            json.dumps(
                dict(
                    format="html",
                    scope="full",
                    title="Reference report",
                    purpose="fixture",
                )
            ),
            str(report),
        )
        spin(app, lambda: not exports.busy and not projects.busy, timeout=60000)
        assert not exports.errorText, exports.errorText
        assert report.exists()
        report_id = projects.draft["results"][-1]["id"]
        projects.save()
        spin(app, lambda: not projects.busy)
        focus(window, c, report_id)
        window.findChild(QObject, "reproInspect").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.preview_result["rerun_supported"]
        assert {n["kind"] for n in c.graph_result["nodes"]} == {
            "source",
            "dataset",
            "analysis",
            "report",
        }
        assert any(
            e["source"] == ident and e["target"] == report_id
            for e in c.graph_result["edges"]
        )
        window.findChild(QObject, "reproSelectNode").clicked.emit()
        assert c.result["selected_node"]
        window.findChild(QObject, "reproHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert (
            app._veri_ufku_resources[0]._learning_resources.article["id"]
            == "repro-lineage"
        )
        window.setProperty("infoOpen", False)
        bundle = tmp_path / "report.vurepro"
        window.findChild(QObject, "reproDestination").setProperty("text", str(bundle))
        window.findChild(QObject, "reproExport").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert bundle.exists()
        window.findChild(QObject, "reproArchive").setProperty("text", str(bundle))
        window.findChild(QObject, "reproOpen").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.opened["status"] == "integrity_verified; no execution"
        assert c.result.get("comparison") is None
        window.findChild(QObject, "reproProjectAccess").setProperty("checked", True)
        out = tmp_path / "compare.vureprotest"
        window.findChild(QObject, "reproTestDestination").setProperty("text", str(out))
        window.findChild(QObject, "reproRerun").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.result["comparison"]["status"] == "matched" and out.exists()
        assert source.read_bytes() == before
        if CAPTURE:
            CAPTURE(app, window, projects, c, "report-reference")
    finally:
        teardown(app, window)


def test_gui_opt_in_data_and_changed_source(tmp_path, monkeypatch):
    app, window, projects, c, ident, source = imported(tmp_path, monkeypatch)
    try:
        focus(window, c, ident)
        window.findChild(QObject, "reproIncludeData").setProperty("checked", True)
        window.findChild(QObject, "reproInspect").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.preview_result["include_data"]
        dest = tmp_path / "included.vurepro"
        window.findChild(QObject, "reproDestination").setProperty("text", str(dest))
        window.findChild(QObject, "reproExport").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        window.findChild(QObject, "reproArchive").setProperty("text", str(dest))
        window.findChild(QObject, "reproOpen").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        out = tmp_path / "standalone.vureprotest"
        window.findChild(QObject, "reproTestDestination").setProperty("text", str(out))
        window.findChild(QObject, "reproRerun").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.result["comparison"]["status"] == "matched"
        # Project input is explicit; changing bytes is never masked by numeric tolerance.
        d = projects.draft["datasets"][-1]
        p = projects.store.path(d["snapshot_uri"])
        old = p.read_bytes()
        try:
            p.write_bytes(old + b"changed")
            window.findChild(QObject, "reproProjectAccess").setProperty("checked", True)
            window.findChild(QObject, "reproTestDestination").setProperty(
                "text", str(tmp_path / "changed.vureprotest")
            )
            window.findChild(QObject, "reproRerun").clicked.emit()
            spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
            assert c.errorText
            assert not (tmp_path / "changed.vureprotest").exists()
            if CAPTURE:
                CAPTURE(app, window, projects, c, "changed-data")
        finally:
            p.write_bytes(old)
    finally:
        teardown(app, window)


@pytest.mark.parametrize("action", ["cancel", "corrupt"])
def test_gui_cancel_or_corrupt_never_success(tmp_path, monkeypatch, action):
    app, window, projects, c, ident, _ = imported(tmp_path, monkeypatch)
    try:
        before = len(projects.draft["results"])
        if action == "cancel":
            focus(window, c, ident)
            window.findChild(QObject, "reproInspect").clicked.emit()
            window.findChild(QObject, "reproCancel").clicked.emit()
        else:
            file = tmp_path / "corrupt.vurepro"
            file.write_bytes(b"not a bundle")
            window.findChild(QObject, "reproArchive").setProperty("text", str(file))
            window.findChild(QObject, "reproOpen").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert c.errorText and not c.opened and len(projects.draft["results"]) == before
        if CAPTURE:
            CAPTURE(app, window, projects, c, action)
    finally:
        teardown(app, window)


def test_gui_workflow_model_numeric_replay_4gib(tmp_path, monkeypatch):
    from test_workflow import recipe

    app, window, projects, c, _, source = imported(
        tmp_path, monkeypatch, budget_bytes=4 * 1024**3
    )
    try:
        engine = app._veri_ufku_resources[0]
        workflow = engine._workflow_resources
        # Explicit4GiB functional fixture; default2GiB model setup failed separately.
        spec = recipe(
            dict(
                version_id=workflow.data.dataset()["version_id"],
                columns=workflow.data.dataset()["import_metadata"]["columns"],
            )
        )
        # Add only train/predict; the workflow native engine checks rank and fit rows.
        from test_workflow import node

        from veri_ufku.storage.project_model import uid

        cols = workflow.data.dataset()["import_metadata"]["columns"]
        spec["nodes"] += [
            node(
                "fit",
                "train",
                dict(feature=cols[0]["id"], target=cols[1]["id"], confirmed=True),
                "source",
            ),
            node(
                "predict",
                "predict",
                dict(prediction_column="col:" + uid()),
                "source",
                "fit",
            ),
        ]
        workflow.setGraph(json.dumps(spec))
        workflow.start(False, False, "", "")
        spin(app, lambda: not workflow.busy and not projects.busy, timeout=60000)
        assert not workflow.errorText, workflow.errorText
        assert workflow.active["status"] == "completed", workflow.active["nodes"]
        ident = projects.draft["results"][-1]["id"]
        focus(window, c, ident)
        window.findChild(QObject, "reproInspect").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.preview_result["rerun_supported"]
        assert any(n["kind"] == "model" for n in c.graph_result["nodes"])
        dest = tmp_path / "model.vurepro"
        window.findChild(QObject, "reproDestination").setProperty("text", str(dest))
        window.findChild(QObject, "reproExport").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        window.findChild(QObject, "reproArchive").setProperty("text", str(dest))
        window.findChild(QObject, "reproOpen").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        window.findChild(QObject, "reproProjectAccess").setProperty("checked", True)
        window.findChild(QObject, "reproMode").setProperty("currentIndex", 1)
        window.findChild(QObject, "reproTestDestination").setProperty(
            "text", str(tmp_path / "model.vureprotest")
        )
        window.findChild(QObject, "reproRerun").clicked.emit()
        spin(app, lambda: not c.busy and not projects.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.result["comparison"]["status"] == "matched"
        assert c.result["comparison"]["policy"]["mode"] == "numeric"
        if CAPTURE:
            CAPTURE(app, window, projects, c, "model-numeric")
    finally:
        teardown(app, window)
