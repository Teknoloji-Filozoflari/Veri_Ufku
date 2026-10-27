"""Read-only chart Python text stays tied to the assigned columns."""

from veri_ufku.ui.chart_python import chart_python_snippet

COLUMNS = [
    {"id": "c-age", "name": "Age"},
    {"id": "c-sex", "name": "Sex"},
    {"id": "c-fare", "name": "Fare"},
]


def test_histogram_snippet_names_the_column_and_kind():
    text = chart_python_snippet(
        {
            "kind": "histogram",
            "x": "c-age",
            "bins": 12,
            "used_n": 40,
            "scope": "view",
            "filters": [{"value": "s3cr3t-token"}],
            "title": "s3cr3t-token",
        },
        COLUMNS,
    )
    assert "Age" in text
    assert "kind=histogram" in text
    assert "plot.hist" in text
    assert "s3cr3t-token" not in text
    assert "neden olur" not in text
    assert "nedensel etki vardır" not in text.lower()


def test_scatter_snippet_refuses_a_causal_claim():
    text = chart_python_snippet(
        {"kind": "scatter", "x": "c-age", "y": "c-fare", "purpose": "relationship"},
        COLUMNS,
    )
    assert "Age" in text and "Fare" in text
    assert "kind=scatter" in text
    assert "plot.scatter" in text
    assert "Nedensel etki değildir" in text
    assert "neden olur" not in text


def test_unknown_kind_does_not_invent_a_plot():
    text = chart_python_snippet({"kind": "map-raster", "x": "c-age"}, COLUMNS)
    assert "map-raster" in text
    assert "sahte" in text
    assert "plot." not in text
    assert "Age" not in text
