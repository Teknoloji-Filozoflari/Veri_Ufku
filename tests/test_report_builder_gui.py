"""Actual desktop actions, isolated PDF process and explicit reviewed export."""

import json

from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_report_builder import fixture

CAPTURE = None


def test_real_report_builder_gui(tmp_path, monkeypatch):
    build = tmp_path / "build"
    build.mkdir()
    store, spec, work = fixture(build)
    target = str(store.root)
    store.close()
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._report_builder_resources
    try:
        assert projects.closeProject(True) and projects.open(target)
        before = projects.store.commit_id
        engine._workspace_resources.activate("report.builder")
        spin(
            app,
            lambda: window.findChild(QObject, "reportBuilderExpanded").property(
                "checked"
            ),
        )
        assert projects.store.commit_id == before and not c.busy
        editor = window.findChild(QObject, "reportBuilderRecipe")
        editor.setProperty("text", json.dumps(spec, ensure_ascii=False, indent=2))
        window.findChild(QObject, "reportBuilderRun").clicked.emit()
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert c.result["status"] == "completed" and c.result["pdf_pages"] >= 1
        assert "Çağrı" in c.preview and "[redacted]" in c.preview
        assert "not_recorded" in c.preview
        ident = c.saved[-1]["id"]
        c.openReport(ident)
        assert not c.errorText
        if CAPTURE:
            CAPTURE(app, window, projects, c)
        path = tmp_path / "report.zip"
        c.exportReport(ident, "zip", str(path), False)
        assert not path.exists() and "onay" in c.errorText
        window.findChild(QObject, "reportBuilderReviewed").setProperty("checked", True)
        window.findChild(QObject, "reportBuilderDestination").setProperty(
            "text", str(path)
        )
        window.findChild(QObject, "reportBuilderExport").clicked.emit()
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, c.errorText
        assert path.read_bytes().startswith(b"PK")
        assert projects.draft == projects.store.state
        before = projects.store.commit_id
        prior = c.result.copy()
        window.findChild(QObject, "reportBuilderRun").clicked.emit()
        window.findChild(QObject, "reportBuilderCancel").clicked.emit()
        spin(app, lambda: not c.busy, timeout=60000)
        assert (
            projects.store.commit_id == before
            and c.result == prior
            and "iptal" in c.errorText
        )
        assert projects.closeProject(True) and projects.open(target)
        c.openReport(ident)
        assert not c.errorText and c.result["spec"] == spec
        # Actual information panel and focus origin; reading is never prerequisite.
        window.findChild(QObject, "reportBuilderHelp").clicked.emit()
        spin(
            app,
            lambda: engine._learning_resources.article.get("id") == "scientific-report",
        )
    finally:
        teardown(app, window)


def test_real_model_and_graph_report_gui(tmp_path, monkeypatch):
    from test_dataset import column
    from test_monitoring import trained_fixture

    from veri_ufku.charts.contracts import ChartSpec
    from veri_ufku.charts.engine import calculate
    from veri_ufku.charts.plot import render
    from veri_ufku.exports.report_contracts import template
    from veri_ufku.storage.chart_store import publish

    build = tmp_path / "build"
    build.mkdir()
    store, r, w, work, monitor = trained_fixture(build)
    model = next(x for x in store.state["results"] if "baseline" in x)
    result = calculate(r, ChartSpec("histogram", x=column(r, "x"), bins=3), work)
    result.update(render(result, work))
    state = publish(store, store.state, result)
    chart = state["results"][-1]
    spec = template()
    spec["allow_graphics"] = True
    spec["blocks"] += [
        dict(kind=k, title=k, record=model["id"])
        for k in ("method", "model-card", "result", "uncertainty", "diagnostic")
    ]
    spec["blocks"] += [
        dict(
            kind="assumption",
            title="Varsayım",
            text="Model fit ve seçim kapsamı ile sınırlı değerlendirme.",
        ),
        dict(
            kind="chart",
            title="Eğitim kaynağı dağılımı",
            record=chart["id"],
            caption="Üç bin; n/filtre bilgisi native kayıtla bağlı.",
        ),
    ]
    target = str(store.root)
    store.close()
    config = tmp_path / "config/veri_ufku"
    config.mkdir(parents=True)
    (config / "settings.json").write_text(
        json.dumps(dict(budget=dict(ram_bytes=4 * 1024**3)))
    )
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    engine = app._veri_ufku_resources[0]
    c = engine._report_builder_resources
    try:
        assert projects.closeProject(True) and projects.open(target)
        engine._workspace_resources.activate("report.builder")
        spin(
            app,
            lambda: window.findChild(QObject, "reportBuilderExpanded").property(
                "checked"
            ),
        )
        window.findChild(QObject, "reportBuilderRecipe").setProperty(
            "text", json.dumps(spec, ensure_ascii=False, indent=2)
        )
        window.findChild(QObject, "reportBuilderRun").clicked.emit()
        spin(app, lambda: not c.busy, timeout=60000)
        assert not c.errorText, c.errorText
        block = next(b for b in c.result["blocks"] if b["kind"] == "result")
        assert block["data"]["cv_summary"] == model["baseline"]["cv_summary"]
        assert block["record_id"] == model["id"]
        assert any(b.get("image") for b in c.result["blocks"])
        if CAPTURE:
            CAPTURE(app, window, projects, c)
        assert projects.draft == projects.store.state
    finally:
        teardown(app, window)
