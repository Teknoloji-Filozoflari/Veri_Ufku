"""Actual QML/spawn, explicit private preview, offline help and labeled text pipeline."""

import os

import polars as pl
from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown


def imported(tmp_path, monkeypatch):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    source = tmp_path / "text.parquet"
    pl.DataFrame(
        dict(
            text=[
                ("IŞIK sıcak GİZLİ987" if i % 2 else "yağmur soğuk") for i in range(120)
            ],
            label=["sıcak" if i % 2 else "soğuk" for i in range(120)],
        )
    ).write_parquet(source)
    imports.choose(str(source))
    spin(app, lambda: not imports.busy)
    imports.importData()
    spin(app, lambda: not imports.busy)
    data = engine._dataset_resources
    data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
    spin(app, lambda: not data.busy)
    window.setProperty("selectedSection", 5)
    return app, window, projects, engine, source


def test_text_qml_private_preview_save_reopen_cancel_help(
    tmp_path, monkeypatch, caplog
):
    app, window, projects, engine, source = imported(tmp_path, monkeypatch)
    c = engine._text_resources
    before = source.read_bytes()
    try:
        window.findChild(QObject, "modelPath").setProperty("currentIndex", 2)
        assert window.findChild(QObject, "textPanel").property("visible")
        window.findChild(QObject, "textRun").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.current and c.result["worker_pid"] != os.getpid()
        assert c.result["retained_vocab"] and not c.report["previews"]
        window.findChild(QObject, "textPreviewConsent").setProperty("checked", True)
        window.findChild(QObject, "textRun").clicked.emit()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert "GİZLİ987" in c.result["previews"][1]["before"]
        assert all(
            not r["text_analysis"]["previews"]
            for r in projects.draft["results"]
            if "text_analysis" in r
        )
        assert "GİZLİ987" not in caplog.text
        for context in (
            "text.tokens",
            "text.language",
            "text.tfidf",
            "text.similarity",
        ):
            engine._learning_resources.openContext(context)
            assert engine._learning_resources.article["id"].startswith("text-")
        saved = c.record_id
        root = str(projects.store.root)
        assert projects.closeProject(True) and projects.open(root)
        data = engine._dataset_resources
        data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
        spin(app, lambda: not data.busy)
        c.openSaved(saved)
        spin(app, lambda: not c.busy)
        assert c.current and not c.errorText and not c.report["previews"]
        window.findChild(QObject, "textRun").clicked.emit()
        c.cancel()
        spin(app, lambda: not c.busy)
        assert source.read_bytes() == before
    finally:
        teardown(app, window)


def test_labeled_text_qml_uses_existing_classification_and_final_defter(
    tmp_path, monkeypatch
):
    app, window, projects, engine, source = imported(tmp_path, monkeypatch)
    prep = engine._preparation_resources
    c = engine._validation_resources
    try:
        window.findChild(QObject, "preparationPurpose").setProperty("currentIndex", 1)
        window.findChild(QObject, "preparationTarget").setProperty("currentIndex", 1)
        window.findChild(QObject, "preparationTextEnabled").setProperty("checked", True)
        window.findChild(QObject, "preparationScan").clicked.emit()
        spin(app, lambda: not prep.busy)
        assert not prep.errorText and not prep.report["blockers"], prep.errorText
        assert prep.result["spec"]["text"]
        panel = window.findChild(QObject, "validationPanel")
        feature = prep.result["spec"]["features"][0]
        panel.setProperty(
            "availability", {feature: dict(offset_seconds=0, note="Metin bilinir")}
        )
        # The classification panel uses existing positive-class controls.
        positive = window.findChild(QObject, "classificationPositive")
        if positive:
            for i in range(positive.property("count")):
                if positive.valueAt(i) == "sıcak":
                    positive.setProperty("currentIndex", i)
        import json

        from veri_ufku.modeling.classification import settings
        from veri_ufku.modeling.validation import ValidationSpec

        protocol = ValidationSpec(
            prediction_moment="Metin bilinir",
            availability={feature: dict(offset_seconds=0, note="Önceden bilinir")},
        )
        c.createClassification(
            json.dumps(protocol.data()),
            json.dumps(
                settings(
                    dict(candidates=["baseline", "logistic"], positive_class="sıcak")
                )
            ),
        )
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.result["selected_model"] == "logistic"
        assert c.result["preparation_spec"]["text"]
        c.evaluateTest()
        spin(app, lambda: not c.busy)
        assert not c.errorText, c.errorText
        assert c.result["mode"] == "final"
        assert any(
            r.get("test_use", {}).get("status") == "completed"
            for r in projects.draft["results"]
        )
    finally:
        teardown(app, window)
