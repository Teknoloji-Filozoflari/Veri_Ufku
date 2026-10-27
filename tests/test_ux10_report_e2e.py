"""UX10: rapor bağlamı + uçtan uca senaryo parçaları (otomatik)."""

import json
from pathlib import Path

import polars as pl

from veri_ufku.analytics.dataset import missing_drop_impact
from veri_ufku.analytics.outliers import candidate_methods
from veri_ufku.domain.json import parse
from veri_ufku.exports.report_contracts import LIMITATIONS, recipe, template
from veri_ufku.exports.ux_report_context import build_context, context_note_text
from veri_ufku.modeling.candidates import suggest_candidates
from veri_ufku.storage import user_library as library
from veri_ufku.ui.report_builder import dump


def test_ux_report_context_binds_version_notes_limits():
    context = build_context(
        dataset_version="ds:abc",
        row_count=10,
        column_count=3,
        chart_notes={"ds:abc:hist": "Dağılım sağa çarpık"},
        outlier_candidates={"applied": False, "union_row_ids": ["r1", "r2"]},
        model_candidates=suggest_candidates("regression", has_time=True),
        scope_note="filtre yok",
    )
    assert context["dataset_version"] == "ds:abc"
    assert context["chart_note_count"] == 1
    assert context["outlier_candidates_applied"] is False
    assert context["outlier_union_n"] == 2
    assert context["model_status"] == "aday"
    assert context["model_auto_fit"] is False
    assert context["reopenable"] is True
    assert context["limitations"] == LIMITATIONS
    text = context_note_text(context)
    assert "ds:abc" in text
    assert "Dağılım sağa çarpık" in text
    assert "Sınırlamalar" in text


def test_append_ux_context_into_recipe_preserves_bindings():
    raw = template("brief")
    context = build_context(
        dataset_version="ds:v1",
        row_count=5,
        column_count=2,
        chart_notes={"k": "not"},
        outlier_candidates={"applied": False, "union_row_ids": ["a"]},
        model_candidates={"status": "aday", "auto_fit": False},
    )
    body = context_note_text(context)
    if len(body) > 2000:
        body = body[:1997] + "..."
    raw["blocks"].append(
        dict(kind="note", title="UX bağlam · sürüm ve sınırlamalar", text=body)
    )
    validated = recipe(raw)
    assert any(
        b["kind"] == "note" and "ds:v1" in b["text"] for b in validated["blocks"]
    )
    again = recipe(parse(dump(validated)))
    assert again["title"] == validated["title"]


def test_e2e_scenario_pieces_chain(tmp_path):
    """Bölüm 11 senaryosunun otomatikleştirilebilir parçaları."""
    data_home = tmp_path / "xdg-data"
    src = tmp_path / "sample.csv"
    src.write_text("x,y\n1,0\n2,1\n3,0\n4,1\n5,0\n", encoding="utf-8")
    entry = library.add_file_entry(data_home, src, name="örnek", tags=["ux10"])
    assert entry["id"].startswith("lib:")
    assert Path(entry["stored_path"]).is_file()

    frame = pl.DataFrame(
        {
            "__vu_row_id": [f"r{i}" for i in range(5)],
            "x": [1.0, 2.0, None, 4.0, 5.0],
            "y": [0, 1, 0, 1, 0],
        }
    )
    path = tmp_path / "data.parquet"
    frame.write_parquet(path)
    before = path.read_bytes()
    impact = missing_drop_impact(str(path), "x")
    assert impact["applied"] is False
    assert impact["missing_n"] == 1
    assert path.read_bytes() == before

    outliers = candidate_methods(str(path), "x")
    assert outliers["applied"] is False
    models = suggest_candidates("classification", has_group=True)
    assert models["auto_fit"] is False
    context = build_context(
        dataset_version="ds:e2e",
        row_count=5,
        column_count=2,
        chart_notes={"hist": "işaretli uçlar"},
        outlier_candidates=outliers,
        model_candidates=models,
    )
    assert context["reopenable"] and "ds:e2e" in context_note_text(context)

    raw = template("scientific")
    note = context_note_text(context)
    raw["blocks"].append(dict(kind="note", title="UX bağlam", text=note[:2000]))
    saved = recipe(raw)
    reopened = recipe(json.loads(json.dumps(saved)))
    assert reopened["blocks"][-1]["text"].startswith("UX bağlam")
    assert any("yeniden hesaplamaz" in lim.lower() for lim in LIMITATIONS)

    # Verilerim silinince kopya gider; kaynak CSV korunur
    source_bytes = src.read_bytes()
    assert library.remove_entry(data_home, entry["id"]) is True
    assert src.read_bytes() == source_bytes
