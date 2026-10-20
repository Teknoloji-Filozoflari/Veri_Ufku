"""Small Phase75 table/clean/chart/export path; long multi-method failures stay separate."""

import hashlib
import os

import polars as pl
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown
from test_ui_renewal import evaluate, screenshot


def test_small_table_clean_histogram_export(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    data, ops, charts = (
        engine._dataset_resources,
        engine._operations_resources,
        engine._charts_resources,
    )
    source = tmp_path / "source.parquet"
    pl.DataFrame(dict(value=[1.0, None, 3.0, 4.0])).write_parquet(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()

    def field(name, prop, value):
        item = window.findChild(QObject, name)
        assert item is not None, name
        assert item.setProperty(prop, value)

    def ready():
        spin(
            app,
            lambda: (
                not imports.busy
                and not ops.busy
                and not charts.busy
                and not data.busy
                and not projects.busy
            ),
            timeout=90000,
        )

    def click(name):
        ready()
        item = window.findChild(QObject, name)
        assert item is not None and item.property("enabled"), name
        item.clicked.emit()

    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        ready()
        assert not imports.errorText
        window.setProperty("selectedSection", 2)
        field("operationKind", "currentIndex", 3)
        field("cleaningMethod", "currentIndex", 0)
        field("cleaningColumn", "currentIndex", 0)
        field("cleaningFillMethod", "currentIndex", 0)
        field("cleaningValue", "text", "2")
        click("operationPreview")
        ready()
        assert ops.canApply, ops.errorText
        click("operationApply")
        ready()
        path = projects.store.path(data.dataset()["snapshot_uri"])
        assert pl.read_parquet(path)["value"].to_list() == [1.0, 2.0, 3.0, 4.0]
        window.setProperty("selectedSection", 3)
        field("chartKind", "currentIndex", 0)
        field("chartX", "currentIndex", 0)
        field("chartBins", "value", 2)
        click("chartCreate")
        ready()
        assert charts.current and not charts.errorText, charts.errorText
        assert charts.result["worker_pid"] != os.getpid()
        assert not charts.provider.image.isNull()
        field("chartSettings", "checked", False)
        QTest.qWait(150)
        mouse = window.findChild(QObject, "chartMouse")
        assert evaluate(mouse, "insideImage(width / 2, height / 2)")
        assert not evaluate(mouse, "insideImage(-1, height / 2)")
        evaluate(
            mouse,
            """(function() {
                let p = parent;
                while (p && p.contentY === undefined) p = p.parent;
                if (p) p.contentY = Math.max(0, mapToItem(p.contentItem, 0, 0).y - 60);
                return true;
            })()""",
        )
        screenshot(window, "computed-histogram")
        for fmt in ("png", "svg"):
            charts.export(str(tmp_path / ("histogram." + fmt)), fmt)
            ready()
            assert (tmp_path / ("histogram." + fmt)).stat().st_size > 1000
        charts.save()
        ready()
        window.findChild(QObject, "chartCreate").forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_F1)
        spin(app, lambda: window.property("infoOpen"))
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        assert hashlib.sha256(source.read_bytes()).hexdigest() == before
        projects.save()
        ready()
        saved = projects.store.root
        assert projects.closeProject() and projects.open(str(saved))
        ready()
        assert pl.read_parquet(projects.store.path(data.dataset()["snapshot_uri"]))[
            "value"
        ].to_list() == [1.0, 2.0, 3.0, 4.0]
    finally:
        teardown(app, window)
