"""Report statistics stay numeric findings and do not quote model metrics."""

from veri_ufku.exports.report_statistics import statistics_report_text


def test_core_finding_keeps_the_question_and_interval_limit():
    text = statistics_report_text(
        [
            {
                "dataset_version": "dv-1",
                "spec": {
                    "path": "independent",
                    "method": "welch_t",
                    "question": "iki şube",
                },
                "method_label": "Welch t — bağımsız grup ortalamaları",
                "n": [20, 18],
                "excluded_rows": 2,
                "primary": {
                    "statistic": 1.5,
                    "p_value": 0.12,
                    "effect": {
                        "name": "Ortalama farkı",
                        "value": 3,
                        "ci_limitation": "güven aralığı sunulmuyor",
                    },
                },
                "artifact_uris": {"png": "secret-uri"},
                "accuracy": 0.99,
            }
        ]
    )
    assert "iki şube" in text
    assert "ci_limitation: güven aralığı sunulmuyor" in text
    assert "[20, 18]" in text
    assert "secret-uri" not in text
    assert "0.99" not in text
    assert "accuracy" not in text


def test_model_record_is_counted_and_not_quoted():
    text = statistics_report_text(
        [
            {
                "spec": {"path": "models", "question": "tahmin"},
                "metrics": {"rmse": 4.25, "token": "s3cr3t-token"},
            }
        ]
    )
    assert "Kaydedilmiş istatistiksel analiz yok" in text
    assert "Model kaydı 1" in text
    assert "uydurulmaz" in text
    assert "4.25" not in text
    assert "s3cr3t-token" not in text
    assert "tahmin" not in text
