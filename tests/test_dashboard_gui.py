"""Actual desktop QML, spawn worker, saved layout and local exports."""

import copy
import json
import os
from contextlib import closing

import polars as pl
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown

from veri_ufku.analytics.contracts import metadata_version
from veri_ufku.storage.project_store import ProjectStore


def test_dashboard_qml_worker_linkage_save_reopen_export_help(
    tmp_path, monkeypatch, capture=None
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "dashboard.parquet"
    pl.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6],
            "y": [2, 4, 6, 8, 10, 12],
            "group": ["A", "B", "A", "B", "A", "B"],
        }
    ).write_parquet(source)
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        resources = app._veri_ufku_resources[0]
        charts = resources._charts_resources
        data = resources._dataset_resources
        dashboard = resources._dashboard_resources
        cols = {c["name"]: c["id"] for c in data.datasetColumns}
        charts.create(
            json.dumps(
                {
                    "kind": "scatter",
                    "x": cols["x"],
                    "y": cols["y"],
                    "group": cols["group"],
                    "scope": "full",
                    "title": "Reference scatter",
                }
            )
        )
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        charts.save()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        window.setProperty("selectedSection", 3)
        expanded = window.findChild(QObject, "dashboardExpanded")
        assert expanded is not None
        expanded.setProperty("checked", True)

        def field(name, prop, value):
            obj = window.findChild(QObject, name)
            assert obj is not None, name
            obj.setProperty(prop, value)
            return obj

        field("dashboardDataset", "currentIndex", 0)
        field("dashboardColumn", "currentIndex", 0)
        field("dashboardChart", "currentIndex", 0)
        button = window.findChild(QObject, "dashboardAddWidget")
        for index in range(4):
            field("dashboardWidgetKind", "currentIndex", index)
            if index == 3:
                field("dashboardNewNote", "text", "Question and source remain visible")
            button.clicked.emit()
            assert not dashboard.errorText, dashboard.errorText
        assert {w["kind"] for w in dashboard.spec["widgets"]} == {
            "chart",
            "table",
            "kpi",
            "note",
        }
        for i, w in enumerate(copy.deepcopy(dashboard.spec["widgets"])):
            dashboard.updateWidget(
                w["id"], json.dumps({"grid": [i // 2 * 4, i % 2 * 6, 4, 6]})
            )
        dashboard.rename("Which observations are linked?")
        field("dashboardFilterColumn", "currentIndex", 2)
        field("dashboardFilterValue", "text", "A")
        window.findChild(QObject, "dashboardAddFilter").clicked.emit()
        window.findChild(QObject, "dashboardEvaluate").clicked.emit()
        spin(app, lambda: not dashboard.busy, timeout=40000)
        assert not dashboard.errorText, dashboard.errorText
        assert dashboard.result["worker_pid"] != os.getpid()
        assert [w["n"] for w in dashboard.result["widgets"]] == [3, 3, 3, 3]
        table = dashboard.result["widgets"][1]
        dashboard.selectRows(table["id"], json.dumps([table["rows"][0]["row_id"]]))
        spin(app, lambda: not dashboard.busy, timeout=40000)
        assert not dashboard.errorText, dashboard.errorText
        assert all(w["linked_count"] == 1 for w in dashboard.result["widgets"])
        assert dashboard.result["widgets"][0]["chart"]["render"]["highlight"]
        window.findChild(QObject, "dashboardDrillDown").clicked.emit()
        spin(app, lambda: not dashboard.busy, timeout=40000)
        assert all(w["n"] == 1 for w in dashboard.result["widgets"])
        dashboard.clearSelection()
        spin(app, lambda: not dashboard.busy, timeout=40000)
        assert not dashboard.errorText, dashboard.errorText
        dashboard.setFigure(
            json.dumps(
                {
                    "rows": 1,
                    "columns": 1,
                    "font": "DejaVu Serif",
                    "font_size": 12,
                    "caption": "GUI publication caption",
                    "unit": "kg",
                    "source": "Explicit immutable source",
                    "palette": "grayscale",
                    "shared_legend": True,
                    "width": 10,
                    "height": 8,
                }
            )
        )
        dashboard.evaluate()
        spin(app, lambda: not dashboard.busy, timeout=40000)
        assert not dashboard.errorText, dashboard.errorText
        field("figureExpanded", "checked", True)
        exports = []
        for i, fmt in enumerate(("svg", "png", "pdf", "html")):
            path = tmp_path / ("figure." + fmt)
            field("figureFormat", "currentIndex", i)
            field("figureDestination", "text", str(path))
            window.findChild(QObject, "figureExport").clicked.emit()
            spin(app, lambda: not dashboard.busy, timeout=40000)
            assert not dashboard.errorText, (fmt, dashboard.errorText)
            assert path.is_file() and path.stat().st_size > 1000
            exports.append(path)
        assert "<image" not in exports[0].read_text()
        assert "GUI publication caption" in exports[0].read_text()
        assert "<script src" not in exports[3].read_text()
        window.findChild(QObject, "dashboardSave").clicked.emit()
        spin(app, lambda: not projects.busy)
        assert not projects.errorText, projects.errorText
        saved = copy.deepcopy(dashboard.spec)
        ident = dashboard.savedViews[-1]["id"]
        with closing(
            ProjectStore.open(projects.store.root, writable=False)
        ) as reopened:
            assert reopened.state["results"][-1]["dashboard"] == saved
        dashboard.newView()
        dashboard.openSaved(ident)
        spin(app, lambda: not dashboard.busy, timeout=40000)
        assert not dashboard.errorText, dashboard.errorText
        assert dashboard.spec == saved
        assert [w["grid"] for w in dashboard.result["widgets"]] == [
            w["grid"] for w in saved["widgets"]
        ]
        help_button = window.findChild(QObject, "dashboardHelp")
        spin(app, lambda: help_button.property("enabled") and not projects.busy)
        help_button.forceActiveFocus()
        app.processEvents()
        QTest.keyClick(window, Qt.Key_F1)
        app.processEvents()
        assert window.property("infoOpen")
        assert resources._learning_resources.article["id"] == "dashboard-question"
        QTest.keyClick(window, Qt.Key_Escape)
        app.processEvents()
        assert not window.property("infoOpen")
        assert help_button.property("activeFocus")
        before = copy.deepcopy(dashboard.result)
        dashboard.evaluate()
        dashboard.cancel()
        spin(app, lambda: not dashboard.busy, timeout=40000)
        assert dashboard.result == before
        old = projects.draft["datasets"][-1]
        new = metadata_version(old, cols["x"], "measurement", "kg", [], "observation")
        projects.draft["datasets"].append(new)
        projects.changed.emit()
        assert all(w["freshness"] == "stale" for w in dashboard.widgets)
        assert all(
            "güncel veri değildir" in w["status_text"] for w in dashboard.widgets
        )
        if capture:
            capture(app, window, dashboard, exports)
        assert source.read_bytes() == original
    finally:
        teardown(app, window)
