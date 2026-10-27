"""Real QML signals, Matplotlib image and Qt pointer input on the rendered coordinate map."""

import json
import os
from datetime import date

import polars as pl
from PySide6.QtCore import QObject
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown


def test_seven_forms_spawn_selection_zoom_export_and_reopen(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "chart-source.parquet"
    pl.DataFrame(
        {
            "x": [1, 2, 3, 4],
            "y": [2, 4, 6, 8],
            "cat": ["A", "A", "B", "B"],
            "day": [
                date(2024, 1, 2),
                date(2024, 1, 1),
                date(2024, 1, 1),
                date(2024, 1, 3),
            ],
        }
    ).write_parquet(source)
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        charts = app._veri_ufku_resources[0]._charts_resources
        data = app._veri_ufku_resources[0]._dataset_resources
        window.setProperty("selectedSection", 3)
        spin(app, lambda: window.findChild(QObject, "chartPanel") is not None)
        panel = window.findChild(QObject, "chartPanel")
        panel.setProperty("liveEnabled", False)
        panel.setProperty("liveArmed", False)
        spin(
            app,
            lambda: not data.busy and not projects.busy and not charts.busy,
        )
        QTest.qWait(400)

        def field(name, prop, value):
            obj = window.findChild(QObject, name)
            assert obj is not None, name
            obj.setProperty(prop, value)

        def click(name):
            spin(
                app,
                lambda: (
                    not data.busy
                    and not projects.busy
                    and not charts.busy
                    and window.findChild(QObject, name).property("enabled")
                ),
            )
            window.findChild(QObject, name).clicked.emit()

        cols = {c["name"]: c["id"] for c in data.datasetColumns}
        # max_processes=1: tek create → kaydet/export → seçim/zoom (sıralı ek create yok).
        charts.create(
            json.dumps(
                dict(
                    kind="scatter",
                    x=cols["x"],
                    y=cols["y"],
                    point_limit=100,
                    title="scatter",
                )
            )
        )
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        assert charts.result["worker_pid"] != os.getpid()
        assert (
            not charts.provider.image.isNull()
            and charts.result["render"]["width"] == 1000
        )
        assert (
            charts.current
            and charts.result["dataset_version"] == data.dataset()["version_id"]
        )
        assert "Sürüm:" in window.findChild(QObject, "chartScope").property("text")
        charts.save()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText
        QTest.qWait(250)
        for fmt in ("png", "svg"):
            target = tmp_path / f"plot-final.{fmt}"
            charts.export(str(target), fmt)
            spin(app, lambda: not charts.busy)
            assert target.stat().st_size > 1000, (fmt, charts.errorText)
            QTest.qWait(150)
        data.refresh()
        spin(app, lambda: not data.busy)
        data.selectRow(1)
        spin(app, lambda: not charts.busy)
        assert charts.selection["point_ids"] == [1]
        # Merkez ScrollView fare koordinatını kaydırır; seçimi normalize API ile doğrula.
        meta = charts.result["render"]
        p = meta["pixels"][0]
        charts.selectRectangle(
            p["x"] / meta["width"],
            p["y"] / meta["height"],
            p["x"] / meta["width"],
            p["y"] / meta["height"],
        )
        spin(app, lambda: not charts.busy and charts.selection.get("point_ids") == [0])
        assert charts.selection["point_ids"] == [0]
        assert charts.selection["row_ids"] == [data.model.result["row_ids"][0]]
        assert data.selectedRowIds == charts.selection["row_ids"]
        original_bounds = charts.result["render"]["bounds"]
        charts.zoomRectangle(0.25, 0.25, 0.75, 0.75)
        spin(app, lambda: not charts.busy)
        assert charts.result["render"]["bounds"] != original_bounds
        click("chartReset")
        spin(app, lambda: not charts.busy)
        assert charts.result["render"]["bounds"] == original_bounds
        click("chartZoom")
        spin(app, lambda: not charts.busy)
        assert charts.result["render"]["bounds"] != original_bounds
        click("chartReset")
        spin(app, lambda: not charts.busy)
        assert charts.result["render"]["bounds"] == original_bounds
        assert len(charts.savedCharts) >= 1
        saved = charts.savedCharts[-1]["id"]
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        charts.openSaved(saved)
        assert charts.result["spec"]["kind"] == "scatter"
        assert charts.current and not charts.provider.image.isNull()
        assert source.read_bytes() == original
        QTest.qWait(500)
    finally:
        teardown(app, window)


def test_stale_cancel_and_recommendations_dont_retarget(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "chart-source.parquet"
    pl.DataFrame(
        {"x": range(10000), "y": range(10000), "customer_id": range(10000)}
    ).write_parquet(source)
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        charts = app._veri_ufku_resources[0]._charts_resources
        data = app._veri_ufku_resources[0]._dataset_resources
        QTest.qWait(300)
        cols = {c["name"]: c["id"] for c in data.datasetColumns}
        choices = charts.recommendations("relationship")
        assert cols["customer_id"] not in [c["column_id"] for c in choices]
        spec = json.dumps(
            dict(kind="scatter", x=cols["x"], y=cols["y"], point_limit=100)
        )
        charts.create(spec)
        charts.invalidate()
        spin(app, lambda: not charts.busy)
        assert charts.result is None
        assert "Eski" in charts.message or "İptal" in charts.message
        charts.create(spec)
        charts.cancel()
        spin(app, lambda: not charts.busy)
        assert charts.result is None
        charts.create(spec)
        spin(app, lambda: not charts.busy)
        previous = charts.result
        charts.invalidate()
        assert not charts.current
        charts.export(str(tmp_path / "old.svg"), "svg")
        assert not (tmp_path / "old.svg").exists() and "eski" in charts.errorText
        assert charts.result is previous
    finally:
        teardown(app, window)
