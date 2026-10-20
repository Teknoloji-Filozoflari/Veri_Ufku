"""Real QML signals, Matplotlib image and Qt pointer input on the rendered coordinate map."""

import json
import os
from datetime import date

import polars as pl
from PySide6.QtCore import QObject, QPoint, Qt
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
                    and window.findChild(QObject, name).property("enabled")
                ),
            )
            window.findChild(QObject, name).clicked.emit()

        cols = {c["name"]: c["id"] for c in data.datasetColumns}
        for method in range(7):
            field("chartKind", "currentIndex", method)
            field(
                "chartX", "currentIndex", 2 if method == 2 else 3 if method == 3 else 0
            )
            field("chartY", "currentIndex", 1)
            field("chartAggregation", "currentIndex", 1)
            field("chartPanel", "selected", [cols["x"], cols["y"]])
            field("chartTitle", "text", "Gerçek Qt grafik " + str(method))
            click("chartCreate")
            spin(app, lambda: not charts.busy)
            assert not charts.errorText, (method, charts.errorText)
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
            for fmt in ("png", "svg"):
                target = tmp_path / f"plot-{method}.{fmt}"
                charts.export(str(target), fmt)
                spin(app, lambda: not charts.busy)
                assert target.stat().st_size > 1000, (method, fmt, charts.errorText)
            charts.save()
            spin(app, lambda: not charts.busy)
            assert not charts.errorText
        # Table row => a real scatter point using stable RowId, independent of display index.
        field("chartKind", "currentIndex", 4)
        field("chartX", "currentIndex", 0)
        field("chartY", "currentIndex", 1)
        click("chartCreate")
        spin(app, lambda: not charts.busy)
        data.refresh()
        spin(app, lambda: not data.busy)
        data.selectRow(1)
        spin(app, lambda: not charts.busy)
        assert charts.selection["point_ids"] == [1]
        # Scroll graph into view and use QTest pointer on the actual QML MouseArea.
        workspace = window.findChild(QObject, "workspace")
        flick = workspace.property("contentItem")
        image = window.findChild(QObject, "chartImage")
        mouse = window.findChild(QObject, "chartMouse")
        from PySide6.QtCore import QPointF

        location = image.mapToItem(flick.property("contentItem"), QPointF(0, 0))
        flick.setProperty("contentY", max(0, location.y() - 30))
        app.processEvents()
        QTest.qWait(50)
        meta = charts.result["render"]
        p = meta["pixels"][0]
        width, height = float(image.property("width")), float(image.property("height"))
        pw, ph = (
            float(image.property("paintedWidth")),
            float(image.property("paintedHeight")),
        )
        pos = mouse.mapToScene(
            QPointF(
                (width - pw) / 2 + p["x"] / meta["width"] * pw,
                (height - ph) / 2 + p["y"] / meta["height"] * ph,
            )
        )
        QTest.mouseClick(
            window, Qt.LeftButton, Qt.NoModifier, QPoint(round(pos.x()), round(pos.y()))
        )
        spin(app, lambda: not charts.busy)
        assert charts.selection["point_ids"] == [0]
        assert charts.selection["row_ids"] == [data.model.result["row_ids"][0]]
        assert data.selectedRowIds == charts.selection["row_ids"]
        original_bounds = charts.result["render"]["bounds"]
        field("chartMode", "currentIndex", 1)

        def position(fx, fy):
            return mouse.mapToScene(
                QPointF((width - pw) / 2 + fx * pw, (height - ph) / 2 + fy * ph)
            ).toPoint()

        QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, position(0.35, 0.30))
        QTest.mouseMove(window, position(0.65, 0.45))
        QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, position(0.65, 0.45))
        spin(app, lambda: not charts.busy)
        assert charts.result["render"]["bounds"] != original_bounds
        click("chartReset")
        spin(app, lambda: not charts.busy)
        assert charts.result["render"]["bounds"] == original_bounds
        field("chartMode", "currentIndex", 0)
        click("chartZoom")
        spin(app, lambda: not charts.busy)
        assert charts.result["render"]["bounds"] != original_bounds
        click("chartReset")
        spin(app, lambda: not charts.busy)
        assert charts.result["render"]["bounds"] == original_bounds
        assert len(charts.savedCharts) == 7
        saved = charts.savedCharts[-1]["id"]
        assert projects.closeProject() and projects.open(str(tmp_path / "project"))
        charts.openSaved(saved)
        assert charts.result["spec"]["kind"] == "missing"
        assert charts.current and not charts.provider.image.isNull()
        assert source.read_bytes() == original
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
        cols = {c["name"]: c["id"] for c in data.datasetColumns}
        choices = charts.recommendations("relationship")
        assert cols["customer_id"] not in [c["column_id"] for c in choices]
        spec = json.dumps(
            dict(kind="scatter", x=cols["x"], y=cols["y"], point_limit=100)
        )
        charts.create(spec)
        charts.invalidate()
        spin(app, lambda: not charts.busy)
        assert charts.result is None and "Eski" in charts.message
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
