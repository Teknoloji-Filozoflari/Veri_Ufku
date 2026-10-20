"""Registry contract, immutable runs, persistence, unknown versions and real QML."""

import copy
import json
from dataclasses import replace
from unittest.mock import patch

import polars as pl
import pytest
from PySide6.QtCore import QObject
from test_gui import visual_item
from test_import_gui import setup, spin, teardown

from veri_ufku.domain.capabilities import (
    CAPABILITIES,
    availability,
    result_compatibility,
)
from veri_ufku.domain.contracts import ResultArtifact
from veri_ufku.ui.workspace import describe_result


def test_one_registry_honest_operations_and_missing_dependencies():
    c = CAPABILITIES["statistics.pearson"]
    assert c.contract_version == 2
    assert [r.name for r in c.inputs.roles] == ["x", "y"]
    assert dict((o.name, o.status) for o in c.operations) == dict(
        fit="unsupported",
        predict="unsupported",
        proba="unsupported",
        transform="unsupported",
        interval="unsupported",
        persist="supported",
    )
    assert {p.name for p in c.parameters} >= {"confidence", "alternative", "precision"}
    for capability in CAPABILITIES.values():
        assert capability.inputs and capability.parameters and capability.assumptions
        assert {s.name for s in capability.support_details} >= {
            "missing",
            "weights",
            "group",
            "time",
            "sparse",
        }
        assert {s.name for s in capability.operations} == {
            "fit",
            "predict",
            "proba",
            "transform",
            "interval",
            "persist",
        }
        assert capability.learning and capability.artifact_kinds
    assert result_compatibility("future.unknown")[0] == "readonly"
    assert result_compatibility(c.capability_id, 2, 1)[0] == "readonly"
    assert result_compatibility(c.capability_id, 1, 2)[0] == "readonly"
    with patch("importlib.util.find_spec", return_value=None):
        enabled, reason = availability(c)
    assert not enabled and "scipy" in reason and "komut çalıştırmaz" in reason
    assert availability(replace(c, dependencies=())) == (True, "")
    with pytest.raises(ValueError):
        ResultArtifact("x", "html", "unsafe")


def test_result_contract_model_log_and_unknown_readonly():
    row = describe_result(
        "result:known",
        "model.lifecycle",
        dict(
            spec={"x": "column:x"},
            model_card={"method": "linear"},
            warnings=["Risk"],
            method_version=1,
        ),
    )
    assert {a["kind"] for a in row["artifacts"]} == {"text", "table", "model", "log"}
    assert row["artifacts"][1]["rows"][0]["name"] == "x"
    unknown = describe_result("result:old", "future.method", dict(summary={"value": 7}))
    assert unknown["readonly"] and "7" in unknown["artifacts"][0]["content"]
    assert "Eski kayıtta yok" in unknown["filters"]


@pytest.mark.parametrize("method", ["pearson", "spearman"])
def test_registry_real_gui_run_preset_tabs_compare_reopen(
    tmp_path, monkeypatch, method
):
    app, window, _, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "pairs.parquet"
    pl.DataFrame(dict(x=[-2, -1, 0, 1, 2], y=[-2, 0, -1, 2, 1])).write_parquet(source)
    original = source.read_bytes()
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        imports.importData()
        spin(app, lambda: not imports.busy)
        engine = app._veri_ufku_resources[0]
        registry = engine._workspace_resources
        stats = engine._statistics_resources
        preferences = app._veri_ufku_resources[-2]
        preferences.setView("advanced")
        registry.search(method)
        assert any(m["id"] == "statistics." + method for m in registry.modules)
        app.processEvents()
        button = visual_item(window.contentItem(), "module-statistics." + method)
        assert button and button.property("enabled")
        button.clicked.emit()
        app.processEvents()
        assert window.property("selectedSection") == 4
        assert window.findChild(QObject, "statisticsPath").property("currentIndex") == 4
        columns = {c["name"]: c["id"] for c in stats.columns}
        spec = dict(
            path="numeric",
            method=method,
            x=columns["x"],
            y=columns["y"],
            question="İlişki?",
            hypothesis="İlişki yok",
            unit="puan",
            observation_unit="kişi",
            independent=True,
            measurement_confirmed=True,
        )
        stats.create(json.dumps(spec), True)
        spin(app, lambda: not stats.busy)
        assert stats.preflightCurrent, stats.errorText
        stats.create(json.dumps(dict(spec, assumptions_confirmed=True)), False)
        spin(app, lambda: not stats.busy)
        assert not stats.errorText
        # Independent reference: ranks here have identical Pearson/Spearman dot products.
        assert stats.result["primary"]["effect"]["value"] == pytest.approx(0.8)
        ident = stats.result["result_version"]
        frozen = copy.deepcopy(stats.result)
        assert registry.selected["id"] == ident
        assert window.findChild(QObject, "commonResultId").property("text") == ident
        preferences.setView("beginner")
        app.processEvents()
        assert registry.selected["id"] == ident
        assert window.findChild(QObject, "commonResultId").property("text") == ident
        preferences.setView("advanced")
        stats.save()
        spin(app, lambda: not stats.busy)
        registry.favorite("statistics." + method)
        spin(app, lambda: not projects.busy)
        registry.pin(ident)
        spin(app, lambda: not projects.busy)
        registry.savePreset("İlişki", json.dumps(spec))
        spin(app, lambda: not projects.busy)
        assert registry.presets and registry.tabs[0]["id"] == ident
        registry.applyPreset(0)
        assert stats.result == frozen
        assert not stats.preflightCurrent
        stats.create(json.dumps(dict(spec, confidence=0.9)), True)
        spin(app, lambda: not stats.busy)
        stats.create(
            json.dumps(dict(spec, confidence=0.9, assumptions_confirmed=True)), False
        )
        spin(app, lambda: not stats.busy)
        second = stats.result["result_version"]
        assert second != ident
        registry.compare(ident)
        registry.compare(second)
        assert len(registry.comparison) == 2
        assert (
            registry.results()[ident]["parameters"]
            != registry.results()[second]["parameters"]
        )
        root = str(projects.store.root)
        assert projects.closeProject(True)
        assert projects.open(root)
        assert (
            registry.tabs[0]["id"] == ident and registry.presets[0]["name"] == "İlişki"
        )
        registry.selectResult(ident)
        assert registry.selected["id"] == ident
        assert next(m for m in registry.modules if m["id"] == "statistics." + method)[
            "favorite"
        ]
        engine._learning_resources.openContext("expert-workspace")
        assert engine._learning_resources.article["id"] == "expert-workspace"
        assert source.read_bytes() == original
        # Unknown capability keeps the validated known result artifacts readable.
        record = next(r for r in projects.draft["results"] if "analysis" in r)
        record["capability_id"] = "future.method"
        assert projects.save()
        registry.selectResult(ident)
        assert registry.selected["readonly"]
        assert projects.closeProject(True) and projects.open(root)
        registry.selectResult(ident)
        assert registry.selected["readonly"]
    finally:
        teardown(app, window)
