"""Real GraphML/GEXF import and graph compute/reopen/export via QML."""

import json
import os

import pytest
from PySide6.QtCore import QObject
from test_graphs import xml
from test_import_gui import setup, spin, teardown

CAPTURE = None
TASKS = ["degree", "centrality", "components", "shortest", "community", "layout"]


def imported(tmp_path, monkeypatch, task="degree", kind="graphml", raw=None):
    source = tmp_path / ("graph." + kind)
    source.write_bytes(raw if raw is not None else xml(kind))
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    controller = engine._graph_resources
    engine._workspace_resources.activate("model.graph." + task)
    window.setProperty("selectedSection", 5)
    window.findChild(QObject, "graphSourceFile").setProperty("text", str(source))
    window.findChild(QObject, "graphChoose").clicked.emit()
    spin(app, lambda: not imports.busy and not projects.busy)
    assert imports.ready, imports.errorText
    assert imports.formatId == kind
    window.findChild(QObject, "graphImport").clicked.emit()
    spin(app, lambda: not imports.busy and not projects.busy)
    assert not imports.errorText, imports.errorText
    spin(app, lambda: not controller.data.busy)
    controller.data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
    spin(app, lambda: not controller.data.busy)
    cols = controller.column_rows()
    for role, name in (
        ("Source", "source"),
        ("Target", "target"),
        ("Node", "node_id"),
        ("RecordType", "record_type"),
        ("EdgeID", "edge_id"),
        ("Weight", "weight"),
        ("Attributes", "attributes"),
    ):
        window.findChild(QObject, "graph" + role).setProperty(
            "currentIndex", next(i for i, c in enumerate(cols) if c["name"] == name)
        )
    for k in ("Unified", "UseEdgeID", "UseWeight", "UseAttributes"):
        window.findChild(QObject, "graph" + k).setProperty("checked", True)
    if task == "shortest":
        window.findChild(QObject, "graphMeaning").setProperty("currentIndex", 1)
        window.findChild(QObject, "graphPathTarget").setProperty("text", '"c"')
    if task == "layout":
        window.findChild(QObject, "graphNodeBudget").setProperty("text", "2")
        window.findChild(QObject, "graphSample").setProperty("checked", True)
        window.findChild(QObject, "graphLayout").setProperty("currentIndex", 1)
    spin(app, lambda: not projects.busy and controller.canGraphRun)
    return app, window, projects, controller, source


@pytest.mark.parametrize("task", TASKS)
def test_real_graph_compute_reopen_export(tmp_path, monkeypatch, task):
    kind = "gexf" if task in ("components", "community", "layout") else "graphml"
    app, window, projects, controller, source = imported(
        tmp_path, monkeypatch, task, kind
    )
    before = source.read_bytes()
    try:
        window.findChild(QObject, "graphHelp").clicked.emit()
        spin(app, lambda: window.property("infoOpen"))
        assert (
            app._veri_ufku_resources[0]._learning_resources.article["id"]
            == "graph-structure"
        )
        window.setProperty("infoOpen", False)
        window.findChild(QObject, "graphRun").clicked.emit()
        spin(app, lambda: not controller.busy, timeout=90000)
        assert not controller.errorText, controller.errorText
        assert (
            controller.active["status"] == "completed"
            and controller.active["worker_pid"] != os.getpid()
        )
        assert len(controller.active["nodes"]) == 4
        if task == "shortest":
            assert controller.active["analysis"]["distance"] == 5
        if task == "layout":
            assert "SAMPLED" in window.findChild(
                QObject, "graphSampleCaption"
            ).property("text")
        saved = next(
            r for r in reversed(controller.saved()) if "completed" in r["label"]
        )
        controller.active = None
        controller.openRun(saved["id"])
        assert controller.active["status"] == "completed"
        dest = tmp_path / "full.json"
        window.findChild(QObject, "graphDestination").setProperty("text", str(dest))
        window.findChild(QObject, "graphExportConsent").setProperty("checked", True)
        window.findChild(QObject, "graphExport").clicked.emit()
        data = json.loads(dest.read_text())
        assert len(data["nodes"]) == 4 and len(data["edges"]) == 3
        assert all(n["source_records"] for n in data["nodes"])
        assert source.read_bytes() == before
        assert (
            "rows" not in controller.historyReport
            and "edges" not in controller.historyReport
        )
        if CAPTURE:
            CAPTURE(app, window, projects, controller, task)
    finally:
        teardown(app, window)


def test_real_graph_cancel_and_view_failure(tmp_path, monkeypatch):
    app, window, projects, controller, _ = imported(tmp_path, monkeypatch)
    try:
        window.findChild(QObject, "graphRun").clicked.emit()
        spin(
            app,
            lambda: (
                (
                    controller.stage == "checkpoint"
                    and controller._incoming["status"] == "running"
                )
                or bool(controller.errorText)
            ),
            timeout=90000,
        )
        assert not controller.errorText, controller.errorText
        window.findChild(QObject, "graphCancel").clicked.emit()
        spin(app, lambda: not controller.busy, timeout=90000)
        assert controller.active["status"] == "canceled", controller.errorText
        if CAPTURE:
            CAPTURE(app, window, projects, controller, "canceled")
        spin(app, lambda: not projects.busy and controller.canGraphRun)
        window.findChild(QObject, "graphNodeBudget").setProperty("text", "1")
        window.findChild(QObject, "graphRun").clicked.emit()
        spin(app, lambda: not controller.busy, timeout=90000)
        assert (
            controller.active["status"] == "failed" and "bütçe" in controller.errorText
        ), (
            controller.active["status"],
            controller.errorText,
            controller.active["warnings"],
        )
        if CAPTURE:
            CAPTURE(app, window, projects, controller, "view-budget-failed")
    finally:
        teardown(app, window)


def test_real_separate_node_edge_tables(tmp_path, monkeypatch):
    import polars as pl

    config = tmp_path / "config" / "veri_ufku"
    config.mkdir(parents=True)
    (config / "settings.json").write_text(
        json.dumps({"budget": {"ram_bytes": 4 * 1024**3}})
    )

    app, window, projects, controller, _ = imported(tmp_path, monkeypatch)
    try:
        imports = app._veri_ufku_resources[0]._imports_resources
        for name, frame in (
            ("nodes", pl.DataFrame(dict(node=["a", "b", "c", "isolated"]))),
            (
                "edges",
                pl.DataFrame(
                    dict(source=["a", "b"], target=["b", "c"], edge_id=["one", "two"])
                ),
            ),
        ):
            p = tmp_path / (name + ".parquet")
            frame.write_parquet(p)
            spin(app, lambda: not imports.busy and not projects.busy)
            imports.choose(str(p))
            spin(app, lambda: not imports.busy and not projects.busy)
            assert imports.ready, imports.errorText
            imports.importData(True)
            spin(app, lambda: not imports.busy and not projects.busy)
            assert not imports.errorText, (name, imports.errorText, imports.message)
            assert len(projects.draft["datasets"]) == (2 if name == "nodes" else 3)
            spin(app, lambda: not controller.data.busy)
            if name == "nodes":
                node_dataset = projects.draft["datasets"][-1]
        spin(app, lambda: not controller.data.busy)
        controller.data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
        spin(app, lambda: not controller.data.busy)
        cols = controller.column_rows()
        for role, name in (
            ("Source", "source"),
            ("Target", "target"),
            ("EdgeID", "edge_id"),
        ):
            window.findChild(QObject, "graph" + role).setProperty(
                "currentIndex", next(i for i, c in enumerate(cols) if c["name"] == name)
            )
        for key in ("Unified", "UseWeight", "UseAttributes"):
            window.findChild(QObject, "graph" + key).setProperty("checked", False)
        combo = window.findChild(QObject, "graphNodeSource")
        index = next(
            i
            for i, v in enumerate(controller.nodeSources)
            if v["id"] == node_dataset["version_id"]
        )
        combo.setProperty("currentIndex", index)
        combo.activated.emit(index)
        spin(app, lambda: bool(controller.nodeColumns))
        window.findChild(QObject, "graphNodeColumn").setProperty("currentIndex", 0)
        window.findChild(QObject, "graphRun").clicked.emit()
        spin(app, lambda: not controller.busy, timeout=90000)
        assert not controller.errorText, controller.errorText
        out = controller.active
        assert out["status"] == "completed" and len(out["nodes"]) == 4
        assert out["origin_version"] == node_dataset["version_id"]
        record = next(
            r
            for r in reversed(projects.draft["results"])
            if r.get("neural", {}).get("status") == "completed"
        )
        assert len(record["dataset_version_ids"]) == 2
        controller.openRun(record["id"])
        original = controller.node_version
        controller.node_version = "version:unavailable-in-current-project"
        spec = out["graph_spec"]
        controller.startGraph(json.dumps(spec))
        assert "bu projede yok" in controller.errorText and not controller.busy
        controller.node_version = original
        controller._error = ""
        if CAPTURE:
            CAPTURE(app, window, projects, controller, "separate-tables")
    finally:
        teardown(app, window)


def test_real_multigraph_projection_export(tmp_path, monkeypatch):
    from veri_ufku.importers.graphs import read

    raw = xml().replace(
        b"</graph>",
        b'<edge id="parallel" source="a" target="b"/><edge id="loop" source="a" target="a"/></graph>',
    )
    app, window, projects, controller, _ = imported(
        tmp_path, monkeypatch, "community", raw=raw
    )
    try:
        for role in ("Multi", "Loops"):
            window.findChild(QObject, "graph" + role).setProperty("checked", True)
        window.findChild(QObject, "graphProjection").setProperty("currentIndex", 1)
        window.findChild(QObject, "graphRun").clicked.emit()
        spin(app, lambda: not controller.busy, timeout=90000)
        assert controller.active["status"] == "completed", controller.errorText
        assert (
            len(controller.active["edges"]) == 5
            and controller.active["analysis"]["projection_edge_count"] == 4
        )
        dest = tmp_path / "preserved.graphml"
        window.findChild(QObject, "graphDestination").setProperty("text", str(dest))
        window.findChild(QObject, "graphExportFormat").setProperty("currentIndex", 1)
        window.findChild(QObject, "graphExportConsent").setProperty("checked", True)
        window.findChild(QObject, "graphExport").clicked.emit()
        frame, _ = read(dest.read_bytes(), "graphml")
        assert set(frame["edge_id"].drop_nulls()) == {
            "e1",
            "e2",
            "e3",
            "parallel",
            "loop",
        }
        if CAPTURE:
            CAPTURE(app, window, projects, controller, "multigraph")
    finally:
        teardown(app, window)
