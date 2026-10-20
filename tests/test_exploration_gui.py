"""Real Phase47 QML selection, preflight, spawn, contextual help and hash reopen."""

import os

import numpy as np
import polars as pl
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest
from test_import_gui import setup, spin, teardown
from test_unsupervised_gui import visual_find

from veri_ufku.modeling.unsupervised_contracts import CLUSTER_METHODS

CASES = [(m, "outlier") for m in CLUSTER_METHODS] + [
    (m, mode)
    for m in ("lof", "one_class_svm", "robust_covariance")
    for mode in ("outlier", "novelty")
]
CAPTURE = None


@pytest.mark.parametrize("method,mode", CASES)
def test_real_exploration_controls(tmp_path, monkeypatch, method, mode):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "numeric.parquet"
    rng = np.random.default_rng(7)
    values = np.vstack(
        [rng.normal(-4, 0.3, (30, 2)), rng.normal(4, 0.3, (30, 2)), [[20.0, 20.0]]]
    )
    pl.DataFrame(
        dict(
            x=values[:, 0], y=values[:, 1], note=["preserve"] * 61, label=[0] * 60 + [1]
        )
    ).write_parquet(source)
    before = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        window.setProperty("selectedSection", 5)
        purpose = window.findChild(QObject, "preparationPurpose")
        purpose.setProperty("currentIndex", 2 if method in CLUSTER_METHODS else 3)
        spin(
            app,
            lambda: (
                visual_find(window.contentItem(), "unsupervisedFeature_x") is not None
            ),
        )
        c = app._veri_ufku_resources[0]._unsupervised_resources
        methods = (
            CLUSTER_METHODS
            if method in CLUSTER_METHODS
            else (
                "isolation_forest",
                "iqr",
                "lof",
                "one_class_svm",
                "robust_covariance",
            )
        )
        window.findChild(QObject, "unsupervisedMethod").setProperty(
            "currentIndex", 1 if methods.index(method) == 0 else 0
        )
        expert = app._veri_ufku_resources[0]._workspace_resources
        expert.activate("model." + method.replace("_", "-"))
        spin(
            app,
            lambda: (
                window.findChild(QObject, "unsupervisedMethod").property("currentIndex")
                == methods.index(method)
            ),
        )
        for name in ("x", "y"):
            item = visual_find(window.contentItem(), "unsupervisedFeature_" + name)
            item.setProperty("checked", True)
            item.clicked.emit()
        window.findChild(QObject, "unsupervisedClusters").setProperty("text", "2")
        window.findChild(QObject, "unsupervisedScaling").setProperty("currentIndex", 1)
        window.findChild(QObject, "unsupervisedEps").setProperty("text", "0.8")
        if method in CLUSTER_METHODS:
            window.findChild(QObject, "explorationStability").setProperty("text", "1")
        else:
            window.findChild(QObject, "explorationMode").setProperty(
                "currentIndex", int(mode == "novelty")
            )
        if method == "kmeans":
            checkbox = window.findChild(QObject, "explorationCompare")
            checkbox.setProperty("checked", True)
            checkbox.clicked.emit()
        if method == "lof":
            index = (
                next(
                    i for i, column in enumerate(c.columns) if column["name"] == "label"
                )
                + 1
            )
            window.findChild(QObject, "explorationLabel").setProperty(
                "currentIndex", index
            )
            window.findChild(QObject, "explorationFPCost").setProperty("text", "2")
            window.findChild(QObject, "explorationFNCost").setProperty("text", "3")
        window.findChild(QObject, "explorationPreflight").clicked.emit()
        assert not c.errorText, c.errorText
        assert c.costPreview["rows"] == 61 and c.costPreview["worst_case_bytes"] > 0
        window.findChild(QObject, "explorationHelp").clicked.emit()
        library = app._veri_ufku_resources[0]._learning_resources
        assert library.article["id"] == "exploration"
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(app, lambda: not window.property("infoOpen"))
        window.findChild(QObject, "unsupervisedRun").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.result["worker_pid"] != os.getpid() and c.current
        assert (
            c.report["spec"]["method"] == method
            and c.report["spec"]["anomaly_mode"] == mode
        )
        if method in ("kmeans", "agglomerative", "gmm"):
            assert c.report["spec"]["clusters"] == 2
        if method == "kmeans":
            assert len(c.report["method_state"]["comparison"]) == 6
        if method == "lof":
            assert c.report["evaluation"]["labels_available"]
        if method == "agglomerative":
            assert c.treeImage.startswith("data:image/svg+xml;base64,")
            spin(
                app,
                lambda: (
                    window.findChild(QObject, "explorationDendrogram").property(
                        "imageReady"
                    )
                    is True
                ),
            )
        if CAPTURE:
            CAPTURE(app, window, c, method, mode)
        record = c.record_id
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        c.openSaved(record)
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.report["spec"]["method"] == method
        assert source.read_bytes() == before
    finally:
        teardown(app, window)


@pytest.mark.parametrize("stop", ["cancel", "timeout"])
def test_exploration_process_cancel_timeout_preserves_active(
    tmp_path, monkeypatch, stop
):
    import json
    from dataclasses import replace

    from test_unsupervised_gui import imported

    app, window, projects, c, source = imported(tmp_path, monkeypatch)
    before = source.read_bytes()
    commit = projects.store.commit_id
    try:
        if stop == "timeout":
            c.budget = replace(c.budget, max_wall_seconds=0.05, cancel_grace_ms=100)
        feature = next(col["id"] for col in c.columns if col["name"] == "x")
        c.create(json.dumps(dict(method="optics", features=[feature], min_samples=3)))
        assert c.busy
        if stop == "cancel":
            c.cancel()
        spin(app, lambda: not c.busy)
        assert not projects.draft["results"]
        assert projects.store.commit_id == commit and source.read_bytes() == before
    finally:
        teardown(app, window)
