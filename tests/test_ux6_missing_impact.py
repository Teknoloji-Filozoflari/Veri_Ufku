"""UX6: missing-drop impact preview does not mutate data."""

import polars as pl

from veri_ufku.analytics.dataset import missing_drop_impact


def test_missing_drop_impact_counts_and_leaves_file(tmp_path):
    path = tmp_path / "t.parquet"
    frame = pl.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "amount": [10.0, None, 30.0, 40.0],
            "score": [1.0, 2.0, 3.0, 4.0],
        }
    )
    frame.write_parquet(path)
    before = path.read_bytes()
    impact = missing_drop_impact(path, "amount", "score")
    assert impact["total_n"] == 4
    assert impact["missing_n"] == 1
    assert impact["remaining_n"] == 3
    assert abs(impact["lost_ratio"] - 0.25) < 1e-9
    assert impact["applied"] is False
    assert abs(impact["mean_before"] - 2.5) < 1e-9
    assert abs(impact["mean_after"] - (1 + 3 + 4) / 3) < 1e-9
    assert path.read_bytes() == before
