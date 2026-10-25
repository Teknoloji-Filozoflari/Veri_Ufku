"""UX7/UX8: chart notes leave version; three outlier methods share RowId space."""

import polars as pl

from veri_ufku.analytics.outliers import candidate_methods


def test_outlier_three_methods_share_row_id_space(tmp_path):
    path = tmp_path / "o.parquet"
    values = [1.0, 1.1, 1.0, 1.05, 1.02, 1.08, 50.0, 0.01]
    frame = pl.DataFrame(
        {"__vu_row_id": [f"r{i}" for i in range(len(values))], "x": values}
    )
    frame.write_parquet(path)
    before = path.read_bytes()
    result = candidate_methods(str(path), "x")
    assert result["applied"] is False
    assert {m["method"] for m in result["methods"]} == {
        "iqr",
        "robust_z",
        "classic_z",
    }
    for method in result["methods"]:
        assert set(method["row_ids"]).issubset(set(result["union_row_ids"]))
    assert "r6" in result["union_row_ids"] or result["methods"][0]["count"] >= 1
    assert path.read_bytes() == before
