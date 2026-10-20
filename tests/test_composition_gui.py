"""Every Phase37 graphic through real QML/spawn/help/export/save/reopen."""

import copy
import json
import os
from pathlib import Path

import polars as pl
import pytest
from phase37_fixtures import frame, options
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown

from veri_ufku.charts.contracts import COMPOSITION_KINDS

CASES = COMPOSITION_KINDS


@pytest.mark.parametrize("kind", CASES)
def test_qml_composition_help_worker_exports_and_reopen(
    tmp_path, monkeypatch, kind, render=None
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "distribution.parquet"
    frame(kind).write_parquet(source)
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
        learning = resources._learning_resources
        window.setProperty("selectedSection", 3)

        def field(name, prop, value):
            obj = window.findChild(QObject, name)
            assert obj is not None, name
            obj.setProperty(prop, value)
            return obj

        panel = window.findChild(QObject, "chartPanel")
        kinds = list(panel.property("kindValues").toVariant())
        field("chartKind", "currentIndex", kinds.index(kind))
        field("chartX", "currentIndex", 0)
        field("chartY", "currentIndex", 1)
        field("chartBins", "value", 2)
        field("chartAnnotation", "text", "Kaynak korunur · gerçek GUI")
        specification = options(kind, data.datasetColumns)
        for name, key in (
            ("chartX", "x"),
            ("chartY", "y"),
            ("chartParent", "parent"),
            ("chartTarget", "target"),
            ("chartWaterfallRole", "waterfall_role"),
            ("chartEntity", "entity"),
        ):
            if specification.get(key):
                field(
                    name,
                    "currentIndex",
                    next(
                        i
                        for i, c in enumerate(data.datasetColumns)
                        if c["id"] == specification[key]
                    ),
                )
        if specification.get("group"):
            field(
                "chartGroup",
                "currentIndex",
                1
                + next(
                    i
                    for i, c in enumerate(data.datasetColumns)
                    if c["id"] == specification["group"]
                ),
            )
        field("chartPanel", "selected", specification.get("columns", []))
        field(
            "chartAggregation",
            "currentIndex",
            0 if kind == "funnel" else 2 if kind == "radar" else 1,
        )
        field(
            "chartCompositionOrder",
            "text",
            "|".join(specification.get("category_order", [])),
        )
        field("chartCompositionAdvanced", "checked", kind == "radar")
        field("chartScopeChoice", "currentIndex", 2)
        field("chartSample", "value", frame(kind).height)
        field("chartGalleryQuery", "text", "nereden nereye")
        window.findChild(QObject, "chartGallerySearch").clicked.emit()
        gallery_rows = panel.property("galleryRows")
        if not isinstance(gallery_rows, list):
            gallery_rows = gallery_rows.toVariant()
        assert {v["kind"] for v in gallery_rows} == {"sankey", "alluvial"}
        assert all(v["ready"] and v["schema"] for v in gallery_rows)
        assert charts.gallery("nereden nereye", False) and all(
            v["ready"] for v in charts.gallery("nereden nereye", False)
        )
        assert not any(v["kind"] == "radar" for v in charts.gallery("", False))
        assert any(v["kind"] == "radar" for v in charts.gallery("", True))
        before = projects.store.commit_id
        control = window.findChild(QObject, "chartKind")
        control.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_F1)
        spin(app, lambda: window.property("infoOpen"))
        assert learning.article["id"] == "chart-" + kind
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        assert control.hasActiveFocus()
        assert projects.store.commit_id == before
        if kind == "error-bar":
            field("chartYScale", "currentIndex", 1)
            window.findChild(QObject, "chartCreate").clicked.emit()
            spin(app, lambda: not charts.busy)
            assert "Log" in charts.errorText
            field("chartYScale", "currentIndex", 2)
        window.findChild(QObject, "chartCreate").clicked.emit()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, (kind, charts.errorText)
        assert charts.result["worker_pid"] != os.getpid() and charts.current
        assert not charts.provider.image.isNull()
        assert charts.result["details"]["included_n"] == frame(kind).height
        assert "Normalizasyon" in window.findChild(
            QObject, "chartMethodDetails"
        ).property("text")
        original_version = data.dataset()["version_id"]
        before_selection = projects.store.commit_id
        point = charts.result["render"]["pixels"][0]
        w, h = charts.result["render"]["width"], charts.result["render"]["height"]
        charts.selectRectangle(
            point["x"] / w, point["y"] / h, point["x"] / w, point["y"] / h
        )
        spin(app, lambda: not charts.busy)
        assert charts.selection["count"] >= 1
        source_ids = set(
            pl.read_parquet(charts.result["paths"]["members"]).filter(
                pl.col("point_id").is_in(charts.selection["point_ids"])
            )["row_id"]
        )
        assert set(charts.selection["dataset_row_ids"]) == source_ids
        assert set(data._selected_ids) <= source_ids
        assert (
            projects.store.commit_id == before_selection
            and data.dataset()["version_id"] == original_version
        )
        window.findChild(QObject, "chartSelectionExportContext").clicked.emit()
        spin(app, lambda: not charts.busy)
        assert charts.result["render"]["selection_context"]["count"] == len(source_ids)
        if render:
            render(app, window, kind, "chartImage", charts.result)
        for fmt in ("png", "svg", "pdf"):
            target = tmp_path / f"{kind}.{fmt}"
            charts.export(str(target), fmt)
            spin(app, lambda: not charts.busy)
            assert not charts.errorText, charts.errorText
            assert target.stat().st_size > 1000
        charts.save()
        spin(app, lambda: not charts.busy)
        assert not charts.errorText, charts.errorText
        saved = copy.deepcopy(charts.result["details"])
        record = projects.draft["results"][-1]["id"]
        points = copy.deepcopy(charts.result["points"])
        charts.openSaved(record)
        assert charts.result["details"] == saved and charts.result["points"] == points
        assert Path(charts.result["paths"]["pdf"]).read_bytes().startswith(b"%PDF")
        assert source.read_bytes() == original
        assert charts.result["provenance"]["dataset_versions"] == [
            data.dataset()["version_id"]
        ]
        # Explicit preview changes neither ACTIVE nor the source. Apply creates a copy dataset.
        ops = resources._operations_resources
        chart_rows = charts.result["render"]["selection_context"]["dataset_row_ids"]
        selection = dict(charts.result["render"]["selection_context"])
        selection["dataset_version"] = original_version
        charts.selection = selection
        before_preview = projects.store.commit_id
        window.findChild(QObject, "chartSelectionDataset").clicked.emit()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        assert ops.canApply and projects.store.commit_id == before_preview
        assert ops.preview["spec"]["destination"] == "copy"
        assert ops.preview["spec"]["parameters"]["row_ids"] == chart_rows
        ops.apply()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        assert any(
            d["version_id"] == original_version for d in projects.draft["datasets"]
        )
        assert source.read_bytes() == original
        if kind == "ecdf":
            field("chartSettings", "checked", True)
            field("chartTitle", "text", "Sadece başlık değişti")
            field("chartX", "currentIndex", 0)
            field("chartXScale", "currentIndex", 2)
            window.findChild(QObject, "chartCreate").clicked.emit()
            spin(app, lambda: not charts.busy)
            assert not charts.errorText and charts.result["points"] == points
            charts.create(json.dumps(charts.result["spec"]))
            charts.cancel()
            spin(app, lambda: not charts.busy)
            assert source.read_bytes() == original
    finally:
        teardown(app, window)
