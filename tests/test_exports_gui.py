"""Developer walkthrough: real QML navigation, selected cleaning and process exports."""

import os
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest
from PySide6.QtCore import QMetaObject, QObject, QTimer, QUrl
from test_import_gui import setup, spin, teardown

from veri_ufku.exports.reports import ASSETS


@pytest.mark.parametrize("example,count", [("sales", 6), ("problem", 7)])
def test_example_to_report_process_exports_history_reopen(
    tmp_path, monkeypatch, example, count
):
    app, window, _, projects, _ = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    guide, exports, data, charts, ops = (
        engine._guide_resources,
        engine._exports_resources,
        engine._dataset_resources,
        engine._charts_resources,
        engine._operations_resources,
    )
    ticks = [0]
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.__setitem__(0, ticks[0] + 1))
    timer.start()
    try:
        assert projects.closeProject()
        guide.createExample(example, str(tmp_path))
        spin(app, lambda: not guide.busy, 30000)
        assert data.datasets, guide.message
        root = projects.store.root
        original = pl.read_parquet(projects.store.path(data.dataset()["snapshot_uri"]))
        assert original.height == count
        assert guide.step == 1 and window.property("selectedSection") == 1
        version = data.dataset()["version_id"]
        guide.go(5)
        assert window.property("selectedSection") == 6
        assert (
            data.dataset()["version_id"] == version
        )  # Skip doesn't clean or change data.
        guide.go(1)
        data.selectColumn(data.datasetColumns[5]["id"])
        data.computeProfile(False, "dataset", 1)
        spin(app, lambda: not data.busy)
        assert data.profile_result, data.errorText
        data.saveProfile()
        guide.go(2)
        data.computeQuality(False, "dataset", "inspect", "[]", "[]")
        spin(app, lambda: not data.busy)
        assert data.quality_result, data.errorText
        data.saveQuality()
        guide.go(3)
        window.findChild(QObject, "operationKind").setProperty("currentIndex", 3)
        window.findChild(QObject, "cleaningMethod").setProperty("currentIndex", 4)
        window.findChild(QObject, "cleaningColumn").setProperty("currentIndex", 2)
        window.findChild(QObject, "operationPreview").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert ops.canApply, ops.errorText
        window.findChild(QObject, "operationApply").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        cleaned = pl.read_parquet(projects.store.path(data.dataset()["snapshot_uri"]))
        assert cleaned["bolge"].to_list() == [
            v.strip() if v else v for v in original["bolge"]
        ]
        assert data.dataset()["version_id"] != version
        guide.go(4)
        window.findChild(QObject, "chartKind").setProperty("currentIndex", 0)
        window.findChild(QObject, "chartX").setProperty("currentIndex", 5)
        window.findChild(QObject, "chartCreate").clicked.emit()
        spin(app, lambda: not charts.busy)
        assert charts.current, charts.errorText
        charts.save()
        spin(app, lambda: not charts.busy)
        guide.go(5)
        for fmt in ("csv", "json", "jsonl", "parquet", "xlsx", "html", "pdf"):
            target = tmp_path / (example + "." + fmt)
            before = ticks[0]
            if fmt in ("html", "pdf"):
                window.findChild(QObject, "reportTitle").setProperty(
                    "text", "Çağrı İıŞşÇçĞğÖöÜü"
                )
                window.findChild(QObject, "reportPurpose").setProperty(
                    "text", "Örnekten rapora"
                )
                window.findChild(QObject, "report" + fmt.upper()).clicked.emit()
            else:
                window.findChild(QObject, "exportFormat").setProperty(
                    "currentIndex",
                    ("csv", "json", "jsonl", "parquet", "xlsx").index(fmt),
                )
                window.findChild(QObject, "exportDescribe").clicked.emit()
                window.findChild(QObject, "exportAcceptLoss").setProperty(
                    "checked", True
                )
                window.findChild(QObject, "exportData").clicked.emit()
            dialog = window.findChild(QObject, "exportTarget")
            assert dialog and dialog.setProperty(
                "selectedFile", QUrl.fromLocalFile(str(target))
            )
            assert QMetaObject.invokeMethod(dialog, "accepted")
            assert QMetaObject.invokeMethod(dialog, "reject")
            spin(app, lambda: not exports.busy, 30000)
            assert not exports.errorText, (fmt, exports.errorText)
            assert target.exists() and target.stat().st_size > 20
            assert exports.result["worker_pid"] != os.getpid()
            assert ticks[0] > before
            assert exports.result["rows"] == count
            if fmt in ("html", "pdf"):
                assert exports.result["charts_shown"] == 1
            else:
                assert exports.result["verified_rows"] == count
            if fmt == "parquet":
                assert pl.read_parquet(target).equals(
                    cleaned.select([c["name"] for c in data.datasetColumns])
                )
        window.findChild(QObject, "exportSaveProject").clicked.emit()
        spin(app, lambda: not projects.busy)
        assert not projects.errorText
        assert projects.closeProject() and projects.open(str(root))
        assert any(
            op.get("kind") == "trim" or op.get("capability_id") == "operation.trim"
            for op in projects.draft["operations"]
        )
        receipts = [r["export"] for r in projects.draft["results"] if "export" in r]
        assert len(receipts) == 7 and receipts[-1]["format"] == "pdf"
        assert {
            r["capability_id"] for r in projects.draft["results"] if "export" in r
        } == {
            "export." + fmt
            for fmt in ("csv", "json", "jsonl", "parquet", "xlsx", "html", "pdf")
        }
        assert any("quality" in r for r in projects.draft["results"])
        assert any("profile" in r for r in projects.draft["results"])
    finally:
        timer.stop()
        teardown(app, window)


def test_guide_recovers_previous_import_error(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    guide = app._veri_ufku_resources[0]._guide_resources
    data = app._veri_ufku_resources[0]._dataset_resources
    try:
        imports.choose(str(tmp_path / "missing.csv"))
        spin(app, lambda: not imports.busy)
        assert imports.errorText
        assert projects.closeProject()
        guide.createExample("sales", str(tmp_path))
        spin(app, lambda: not guide.busy, 30000)
        assert data.datasets, guide.message
        assert data.dataset()["import_metadata"]["row_count"] == 6
        assert guide.step == 1 and not imports.errorText
    finally:
        teardown(app, window)


def test_documented_shop_reference_import_profile_chart_export(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    data, charts, exports = (
        engine._dataset_resources,
        engine._charts_resources,
        engine._exports_resources,
    )
    source = ASSETS / "examples/magaza.csv"
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.setType(0, "text")
        imports.setType(1, "date")
        imports.setType(3, "decimal")
        imports.setOption("null_markers", "\\N")
        imports.refreshPreview()
        spin(app, lambda: not imports.busy)
        assert imports.ready, imports.errorText
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText
        d = data.dataset()
        frame = pl.read_parquet(projects.store.path(d["snapshot_uri"]))
        assert frame.height == 12
        assert frame["kimlik"].to_list() == [f"{i:04d}" for i in range(1, 13)]
        assert frame["tutar"].null_count() == 2
        assert frame["tutar"].sum() == Decimal(480)
        cols = {c["name"]: c["id"] for c in data.datasetColumns}
        data.selectColumn(cols["tutar"])
        data.computeProfile(False, "dataset", 1)
        spin(app, lambda: not data.busy)
        p = data.profile_result
        assert p, data.errorText
        assert p["counts"]["valid"] == 10 and p["counts"]["null"] == 2
        assert Decimal(p["numeric"]["mean"]) == Decimal(48)
        assert Decimal(p["numeric"]["median"]) == Decimal(45)
        assert cols["kimlik"] not in [
            c["column_id"] for c in charts.recommendations("distribution")
        ]
        window.setProperty("selectedSection", 3)
        window.findChild(QObject, "chartX").setProperty("currentIndex", 3)
        window.findChild(QObject, "chartBins").setProperty("value", 3)
        window.findChild(QObject, "chartCreate").clicked.emit()
        spin(app, lambda: not charts.busy)
        assert charts.current, charts.errorText
        assert [p["n"] for p in charts.result["points"]] == [4, 3, 3]
        assert charts.result["details"]["excluded_rows"] == 2
        charts.save()
        spin(app, lambda: not charts.busy)
        exports.create("data", '{"format":"parquet"}', str(tmp_path / "shop.parquet"))
        spin(app, lambda: not exports.busy)
        assert exports.result["verified_rows"] == 12, exports.errorText
        assert pl.read_parquet(tmp_path / "shop.parquet").equals(
            frame.select("kimlik", "gun", "sube", "tutar")
        )
        projects.save()
        root = Path(projects.store.root)
        assert projects.closeProject() and projects.open(str(root))
        assert any("chart" in r for r in projects.draft["results"])
        assert any("export" in r for r in projects.draft["results"])
        assert source.read_bytes() == original
    finally:
        teardown(app, window)


def test_documented_branches_trim_preserves_legitimate_duplicates(
    tmp_path, monkeypatch
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    data, ops = engine._dataset_resources, engine._operations_resources
    source = ASSETS / "examples/subeler.csv"
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText

        def frame():
            return pl.read_parquet(projects.store.path(data.dataset()["snapshot_uri"]))

        initial = frame()
        assert initial.height == 6
        assert initial["__vu_source_record_id"].n_unique() == 6
        window.setProperty("selectedSection", 2)
        window.findChild(QObject, "operationKind").setProperty("currentIndex", 3)
        window.findChild(QObject, "cleaningMethod").setProperty("currentIndex", 4)
        window.findChild(QObject, "cleaningColumn").setProperty("currentIndex", 1)
        window.findChild(QObject, "operationPreview").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert ops.canApply, ops.errorText
        assert ops.previewResult["impact"]["changed_cells"] == 2
        window.findChild(QObject, "operationApply").clicked.emit()
        spin(app, lambda: not ops.busy)
        cleaned = frame()
        assert cleaned["sube"].to_list() == [
            "Ankara",
            "Ankara",
            "İzmir",
            "İzmir",
            "Bursa",
            "Bursa",
        ]
        assert cleaned["__vu_row_id"].equals(initial["__vu_row_id"])
        assert cleaned["__vu_source_record_id"].equals(initial["__vu_source_record_id"])
        ops.historyAction("undo")
        spin(app, lambda: not ops.busy)
        assert frame().equals(initial)
        ops.historyAction("redo")
        spin(app, lambda: not ops.busy)
        assert frame().equals(cleaned)
        root = projects.store.root
        assert projects.closeProject() and projects.open(str(root))
        assert frame().equals(cleaned)
        assert source.read_bytes() == original
    finally:
        teardown(app, window)
