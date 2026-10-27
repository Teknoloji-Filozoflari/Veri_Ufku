"""Chart explanation sentences stay tied to computed numbers."""

from veri_ufku.ui.chart_explain import chart_explanation


def test_histogram_sentences_use_the_computed_counts():
    text = chart_explanation(
        {
            "spec": {"kind": "histogram"},
            "used_n": 40,
            "points": [{"n": 12}, {"n": 28}],
            "summary": [{"column_name": "Age", "numeric": {"mean": 31.2}}],
            "details": {"excluded_rows": 3},
            "filters": [{"value": "s3cr3t-token"}],
        }
    )
    blob = " ".join(text[key] for key in ("see", "read", "caution", "next"))
    assert text["ready"] is True
    assert "40" in text["see"] and "28" in text["see"]
    assert "Age" in text["read"] and "31.2" in text["read"]
    assert "3" in text["caution"]
    assert "s3cr3t-token" not in blob
    assert "neden olur" not in blob


def test_scatter_sentence_denies_causation():
    text = chart_explanation(
        {
            "spec": {"kind": "scatter"},
            "used_n": 8,
            "points": [{"x": 1, "y": 2, "n": 1}] * 8,
        }
    )
    assert "8" in text["see"]
    assert "Nedensellik kanıtlamaz" in text["caution"]
    assert "neden olur" not in text["caution"]


def test_unknown_chart_does_not_invent_a_mean():
    text = chart_explanation(
        {"spec": {"kind": "map-raster"}, "used_n": 4, "points": [{}]}
    )
    blob = text["see"] + text["read"]
    assert text["ready"] is False
    assert "uydurulmaz" in text["see"]
    assert "ortalama" not in blob
    assert text["read"] == ""
