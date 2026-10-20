"""Actual QML native temporal paths, spawned compute, immutable source/reopen/help."""

import json
import os

import numpy as np
import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_time_series import example

CAPTURE = None
CASES = [
    "decomposition",
    "stl",
    "acf",
    "pacf",
    "stationarity",
    "change-point",
    "arima",
    "sarima",
    "sarimax",
    "var",
    "global-ridge",
    "croston",
    "reconciliation",
    "classification",
    "clustering",
    "local",
    "rolling-origin",
    "mase",
    "probabilistic",
]


@pytest.mark.parametrize("method", CASES)
def test_real_temporal_gui(tmp_path, monkeypatch, method):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._time_series_resources
    n = 80
    rng = np.random.default_rng(53)
    count = 6 if method in ("classification", "clustering") else 2
    frame = example(n, groups=False)
    frames = []
    for g in range(count):
        x = rng.normal(size=n)
        z = rng.normal(size=n)
        y = np.zeros(n)
        for t in range(1, n):
            y[t] = 0.4 * y[t - 1] + 0.7 * x[t] + rng.normal(scale=0.5)
        if method == "croston":
            y = abs(y)
        frames.append(
            frame.with_columns(
                pl.Series("value", y + g * 0.2),
                pl.Series("x", x),
                pl.Series("z", z),
                pl.lit(f"g{g}").alias("group"),
                pl.lit("A" if g % 2 == 0 else "B").alias("label"),
            )
        )
    source = tmp_path / "temporal.parquet"
    pl.concat(frames).write_parquet(source)
    before = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        data = engine._dataset_resources
        data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
        spin(app, lambda: not data.busy)
        columns = data.dataset()["import_metadata"]["columns"]
        ids = {c["name"]: c["id"] for c in columns}
        for name, field in [
            ("timeSeriesDate", "day"),
            ("timeSeriesMeasurement", "value"),
            ("timeSeriesGroup", "group"),
        ]:
            item = window.findChild(QObject, name)
            item.setProperty(
                "currentIndex",
                next(i for i, col in enumerate(columns) if col["name"] == field)
                + (1 if name == "timeSeriesGroup" else 0),
            )
        engine._workspace_resources.activate("model.temporal." + method)
        assert window.findChild(QObject, "modelPath").property("currentIndex") == 1
        assert window.findChild(QObject, "temporalExpanded").property("checked")
        window.findChild(QObject, "timeSeriesSeason").setProperty("text", "4")
        window.findChild(QObject, "timeSeriesFolds").setProperty("text", "2")
        if method == "rolling-origin":
            window.findChild(QObject, "temporalGap").setProperty("text", "2")
            window.findChild(QObject, "temporalEmbargo").setProperty("text", "1")
        if method == "sarimax":
            window.findChild(QObject, "temporalKnown").setProperty(
                "text", json.dumps([ids["x"]])
            )
            window.findChild(QObject, "temporalAvailability").setProperty(
                "text",
                json.dumps(
                    {ids["x"]: "Known scheduled historical fixture scenario at origin"}
                ),
            )
        if method == "var":
            window.findChild(QObject, "temporalVar").setProperty(
                "text", json.dumps([ids["z"]])
            )
            window.findChild(QObject, "temporalVarReason").setProperty(
                "text",
                "Generated stable stationary process; not established by p-value alone",
            )
        if method == "reconciliation":
            window.findChild(QObject, "temporalHierarchy").setProperty(
                "text",
                json.dumps([["total", '["str", "g0"]'], ["total", '["str", "g1"]']]),
            )
        if method == "classification":
            label = window.findChild(QObject, "temporalLabel")
            label.setProperty(
                "currentIndex",
                next(i for i, col in enumerate(columns) if col["name"] == "label") + 1,
            )
            window.findChild(QObject, "temporalTrainSeries").setProperty(
                "text", json.dumps([f'["str", "g{i}"]' for i in range(4)])
            )
            window.findChild(QObject, "temporalValSeries").setProperty(
                "text", json.dumps([f'["str", "g{i}"]' for i in (4, 5)])
            )
        button = window.findChild(QObject, "temporalRun")
        assert button.property("enabled")
        button.clicked.emit()
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        assert c.result and c.result["worker_pid"] != os.getpid()
        assert c.result["advanced"]["schema"] == "TemporalRun/v1"
        if method in ("arima", "sarima", "sarimax", "var", "global-ridge", "croston"):
            assert method in {
                x["method"] for x in c.result["groups"][0]["comparisons"]
            }, c.result["groups"][0]["invalid_models"]
        if method in ("classification", "clustering"):
            assert c.result["advanced"]["series_task"]["task"] == method
        assert source.read_bytes() == before
        engine._learning_resources.openContext("temporal.advanced")
        assert engine._learning_resources.article["id"] == "temporal-advanced"
        if method == "arima":
            window.findChild(QObject, "timeSeriesFinal").clicked.emit()
            spin(app, lambda: not c.busy, timeout=90000)
            assert not c.errorText, c.errorText
            assert (
                c.result["mode"] == "final" and c.result["groups"][0]["final_metrics"]
            )
            assert any("time_series_test_use" in r for r in projects.draft["results"])
        if CAPTURE:
            CAPTURE(app, window, projects, c, method)
        record = c.record_id
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        c.openSaved(record)
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        assert c.result["advanced"]["schema"] == "TemporalRun/v1"
    finally:
        teardown(app, window)
