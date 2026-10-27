"""Statistics advice uses preflight counts and does not invent a test."""

from veri_ufku.ui.statistics_advice import statistics_advice


def _blob(text):
    return " ".join(
        text[key]
        for key in ("question", "structure", "suggestion", "assumption", "selection")
    )


def test_two_groups_keep_welch_and_mann_whitney_apart():
    text = statistics_advice(
        {
            "used_rows": 52,
            "n": [40, 12],
            "spec": {
                "path": "independent",
                "method": "welch_t",
                "question": "iki şubenin ortalaması",
                "independent": True,
            },
            "filters": [{"value": "s3cr3t-token"}],
        }
    )
    blob = _blob(text)
    assert text["ready"] is True
    assert "iki şubenin ortalaması" in text["question"]
    assert "52" in text["question"]
    assert "Welch" in text["suggestion"]
    assert "Mann-Whitney" in text["suggestion"]
    assert "12" in text["suggestion"]
    assert "p değeriyle seçilmedi" in text["suggestion"]
    assert "otomatik test edilmedi" in text["assumption"]
    assert "işaretli" in text["selection"]
    assert "s3cr3t-token" not in blob
    assert "neden olur" not in blob


def test_sparse_two_by_two_points_at_fisher_without_a_fake_p():
    text = statistics_advice(
        {
            "used_rows": 14,
            "spec": {"path": "categorical", "method": "chi2", "question": "bağ"},
            "expected": [[6, 1], [1, 6]],
        }
    )
    assert "Fisher" in text["suggestion"]
    assert "1" in text["structure"]
    assert "p=" not in _blob(text)
    assert "Monte Carlo" not in text["suggestion"]


def test_sparse_large_table_does_not_invent_an_exact_test():
    text = statistics_advice(
        {
            "used_rows": 20,
            "spec": {"path": "categorical", "method": "chi2"},
            "expected": [[2, 2, 2], [8, 8, 8]],
        }
    )
    assert "hesaplanmaz" in text["suggestion"]
    assert "3" in text["structure"]


def test_missing_preflight_invents_nothing():
    text = statistics_advice({"spec": {"path": "independent", "method": "welch_t"}})
    assert text["ready"] is False
    assert "uydurulmaz" in text["question"]
    assert text["suggestion"] == ""
