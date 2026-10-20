"""Real QML start/spawn/atomic publish/reopen/rollback with no network startup."""

import json

from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_monitoring import trained_fixture

from veri_ufku.modeling.monitor_contracts import MonitorSpec
from veri_ufku.storage import monitor_store as storage

CAPTURE = None


def test_real_monitoring_gui_run_reopen_cancel(tmp_path, monkeypatch):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    controller = engine._monitoring_resources
    try:
        requests = []
        for i in range(2):
            path = tmp_path / f"data{i}.csv"
            path.write_text(
                "x\n" + "\n".join(str(float(j) + 10 * i) for j in range(60))
            )
            imports.choose(str(path))
            spin(app, lambda: not imports.busy)
            imports.importData()
            spin(app, lambda: not imports.busy)
            assert not imports.errorText, imports.errorText
            d = projects.draft["datasets"][-1]
            requests.append(
                dict(
                    version=d["version_id"],
                    column=d["import_metadata"]["columns"][0]["id"],
                )
            )
        s = MonitorSpec(
            reference=requests[0]["version"],
            window=requests[1]["version"],
            features=[
                dict(
                    reference=requests[0]["column"],
                    window=requests[1]["column"],
                    kind="numeric",
                    continuous=True,
                )
            ],
            window_start="2026-01-01T00:00:00Z",
            window_end="2026-02-01T00:00:00Z",
            as_of="2026-02-02T00:00:00Z",
        )
        engine._workspace_resources.activate("model.monitor.batch")
        spin(
            app,
            lambda: window.findChild(QObject, "monitoringExpanded").property("checked"),
        )
        window.findChild(QObject, "monitoringRecipe").setProperty(
            "text", json.dumps(s.data())
        )
        window.findChild(QObject, "monitoringRun").clicked.emit()
        spin(app, lambda: not controller.busy, timeout=60000)
        assert not controller.errorText, controller.errorText
        assert (
            controller.result["status"] == "completed"
            and controller.result["models"] == []
        )
        assert projects.draft == projects.store.state
        assert "Başarı ve kalibrasyon ölçülmedi" in window.findChild(
            QObject, "monitoringReport"
        ).property("text")
        saved = controller.saved[-1]["id"]
        if CAPTURE:
            CAPTURE(app, window, projects, controller, "drift")
        before = projects.store.commit_id
        controller.run(json.dumps(s.data()))
        controller.cancel()
        spin(app, lambda: not controller.busy, timeout=60000)
        assert projects.store.commit_id == before
        assert (
            controller.result["status"] == "completed"
            and "iptal" in controller.errorText.lower()
        )
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        controller.openReport(saved)
        assert (
            not controller.errorText
            and controller.result["features"][0]["distribution"]["alarm"]
        )
    finally:
        teardown(app, window)


def test_real_model_monitoring_and_champion_route_gui(tmp_path, monkeypatch):
    build = tmp_path / "build"
    build.mkdir()
    store, r, w, work, s = trained_fixture(build)
    target = str(store.root)
    model = s.champion
    # Persist a second actual model to exercise local rollback from GUI actions.
    from veri_ufku.modeling.baseline import calculate as train
    from veri_ufku.modeling.validation import ValidationSpec
    from veri_ufku.storage.project_model import uid
    from veri_ufku.storage.validation_store import choice, complete

    rid = "run:" + uid()
    r["run_id"] = rid
    protocol = ValidationSpec(
        prediction_moment="second explicit run",
        availability={
            f: dict(offset_seconds=0, note="known")
            for f in r["preparation"]["spec"]["features"]
        },
    )
    choice(
        store,
        store.state,
        r["version_id"],
        protocol.data(),
        r["preparation"]["plan"]["version_id"],
        rid,
    )
    second = work / "second"
    second.mkdir()
    complete(store, store.state, result=train(r, protocol.data(), second), run_id=rid)
    other = next(k for k in storage.models(store.state) if k != model)
    from dataclasses import replace

    s = replace(s, challenger=other)
    store.close()
    config = tmp_path / "config/veri_ufku"
    config.mkdir(parents=True, exist_ok=True)
    (config / "settings.json").write_text(
        json.dumps({"budget": {"ram_bytes": 4 * 1024**3}})
    )
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    try:
        assert projects.closeProject(True) and projects.open(target)
        c = app._veri_ufku_resources[0]._monitoring_resources
        c.run(json.dumps(s.data()))
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert (
            c.result["shadow"]["status"] == "same_batch_no_deploy"
            and not c.result["shadow"]["performance_available"]
        )
        window.setProperty("selectedSection", 5)
        window.findChild(QObject, "monitoringExpanded").setProperty("checked", True)
        combo = window.findChild(QObject, "monitoringChampion")
        for ident in (model, other):
            combo.setProperty(
                "currentIndex",
                next(i for i, v in enumerate(c.models) if v["id"] == ident),
            )
            window.findChild(QObject, "monitoringActivate").clicked.emit()
            spin(app, lambda: not c.busy)
            assert not c.errorText, c.errorText
        window.findChild(QObject, "monitoringRollback").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText and c.currentRoute["value"]["record_id"] == model
        assert c.currentRoute["value"]["rollback"]
        assert "SUNULMUYOR" in window.findChild(QObject, "monitoringReport").property(
            "text"
        )
        if CAPTURE:
            CAPTURE(app, window, projects, c, "shadow-rollback")
    finally:
        teardown(app, window)
