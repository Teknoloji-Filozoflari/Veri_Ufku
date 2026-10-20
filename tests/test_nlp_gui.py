"""Real NLP QML paths with local safe weights, human review/export and cache-free reopen."""

import json
import os

import polars as pl
import pytest
from PySide6.QtCore import QMetaObject, QObject
from test_import_gui import setup, spin, teardown
from test_nlp import bundle

from veri_ufku.analytics.nlp_contracts import METHODS

CAPTURE = None


@pytest.mark.parametrize("method", METHODS)
def test_real_nlp_gui(tmp_path, monkeypatch, method):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._text_resources
    texts = [
        "güzel iyi elma",
        "mükemmel güzel armut",
        "kötü berbat bozuk",
        "berbat kötü çürük",
        "güzel ürün farklı",
        "kötü ürün başka",
        "iyi yeni başka",
        "TESTLABEL_GİZLİ geleceği görme",
        "İstanbul 👩‍💻 Şule ve I\u0307pek geldi",
    ]
    source = tmp_path / "nlp.parquet"
    pl.DataFrame(dict(text=texts)).write_parquet(source)
    before = source.read_bytes()
    folder = tmp_path / "local"
    bundle(folder)
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        assert not imports.errorText, imports.errorText
        data = engine._dataset_resources
        data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
        spin(app, lambda: not data.busy)
        dataset = data.dataset()
        frame = pl.read_parquet(projects.store.path(dataset["snapshot_uri"]))
        ids = frame["__vu_row_id"].to_list()
        parts = {
            i: "test" if j == 7 else "validation" if j in (4, 5) else "train"
            for j, i in enumerate(ids)
        }
        anns = [
            dict(
                row_id=ids[j],
                label="positive" if j in (0, 1, 4) else "negative",
                spans=[],
                reviewer="human-fixture",
                decision="approved",
            )
            for j in (0, 1, 2, 3, 4, 5)
        ]
        engine._workspace_resources.activate("text.nlp." + method)
        app.processEvents()
        assert window.findChild(QObject, "nlpEnabled").property("checked")
        for field, value in [
            ("nlpFolder", str(folder)),
            ("nlpQuery", "mükemmel"),
            ("nlpPartitions", json.dumps(parts)),
            ("nlpAnnotations", json.dumps(anns)),
        ]:
            window.findChild(QObject, field).setProperty("text", value)
        if method == "retrieval":
            window.findChild(QObject, "nlpRelevance").setProperty(
                "text",
                json.dumps(
                    {ids[j]: int(j in (0, 1, 4, 6)) for j in range(9) if j != 7}
                ),
            )
        window.findChild(QObject, "nlpInspectModel").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.modelInfo["languages"] == ["tr"] and c.modelInfo["bytes"] > 0
        button = window.findChild(QObject, "nlpRun")
        assert button.property("enabled")
        button.clicked.emit()
        spin(app, lambda: not c.busy, timeout=90000)
        assert not c.errorText, c.errorText
        assert c.result and c.result["worker_pid"] != os.getpid()
        a = c.result["advanced"]
        assert (
            a["schema"] == "NLPRun/v1"
            and a["status"] == "completed"
            and a["operation"] == method
        )
        assert source.read_bytes() == before and a["test_withheld"] == 1
        window.findChild(QObject, "nlpHelp").clicked.emit()
        app.processEvents()
        assert engine._learning_resources.article["id"] == "nlp-model-language"
        assert QMetaObject.invokeMethod(window, "closeInformation")
        app.processEvents()
        if method == "annotation":
            ann = dict(
                row_id=ids[8],
                label=None,
                spans=[dict(start=0, end=8, label="LOC")],
                reviewer="gui-human",
                decision="approved",
            )
            window.findChild(QObject, "nlpReviewPatch").setProperty(
                "text", json.dumps(dict(annotations=anns + [ann]))
            )
            window.findChild(QObject, "nlpReviewer").setProperty("text", "gui-human")
            old = c.record_id
            window.findChild(QObject, "nlpReview").clicked.emit()
            spin(app, lambda: not c.busy)
            assert not c.errorText, c.errorText
            assert (
                c.record_id != old
                and c.result["advanced"]["annotations"][-1] == ann
                and c.current
            )
            destination = tmp_path / "annotations.json"
            window.findChild(QObject, "nlpExportPath").setProperty(
                "text", str(destination)
            )
            window.findChild(QObject, "nlpExport").clicked.emit()
            spin(app, lambda: not c.busy)
            assert not c.errorText, c.errorText
            exported = json.loads(destination.read_text())
            assert (
                not exported["raw_text_included"]
                and "TESTLABEL_GİZLİ" not in destination.read_text()
            )
        if method == "nmf":
            window.findChild(QObject, "nlpReviewPatch").setProperty(
                "text", json.dumps(dict(topic_names={"0": "İnsan konu adı"}))
            )
            window.findChild(QObject, "nlpReviewer").setProperty("text", "gui-human")
            window.findChild(QObject, "nlpReview").clicked.emit()
            spin(app, lambda: not c.busy)
            assert not c.errorText, c.errorText
            assert c.result["advanced"]["topics"][0]["name"] == "İnsan konu adı"
        if CAPTURE:
            CAPTURE(app, window, projects, c, method)
        saved = c.record_id
        root = str(projects.store.root)
        (folder / "model.json").unlink()
        assert projects.closeProject(True) and projects.open(root)
        data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
        spin(app, lambda: not data.busy)
        c.openSaved(saved)
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.result["advanced"]["operation"] == method and c.current
        if method == "model":
            window.findChild(QObject, "nlpFolder").setProperty("text", "")
            button.clicked.emit()
            spin(app, lambda: not c.busy)
            assert not c.errorText, c.errorText
            assert c.result["status"] == "unavailable" and c.result["advanced"]["notes"]
        if method == "ner":
            other = tmp_path / "wrong-language"
            bundle(other, "en")
            window.findChild(QObject, "nlpFolder").setProperty("text", str(other))
            button.clicked.emit()
            spin(app, lambda: not c.busy)
            assert "model dili" in c.errorText
        if method == "active-learning":
            saved_ids = [r["id"] for r in projects.draft["results"]]
            button.clicked.emit()
            assert c.busy and c.process.pid
            window.findChild(QObject, "textCancel").clicked.emit()
            spin(app, lambda: not c.busy)
            assert [r["id"] for r in projects.draft["results"]] == saved_ids
    finally:
        teardown(app, window)
