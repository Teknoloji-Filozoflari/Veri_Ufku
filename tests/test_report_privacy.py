"""Report privacy preview names columns and does not copy cell values."""

from contextlib import closing

import polars as pl
from test_dataset import prepare

from veri_ufku.exports.report_privacy import column_findings, privacy_note
from veri_ufku.exports.reports import ReportSpec, build
from veri_ufku.importers.delimited import Control


def test_preview_names_the_column_and_drops_the_value():
    secret = "secret-user@example.com"
    findings = column_findings(
        ["kod", "eposta"],
        {"kod": ["a", "b"], "eposta": [secret, "ok"]},
    )
    text = privacy_note(findings, False)
    assert findings == [{"name": "eposta", "reason": "sensitive-name"}]
    assert "eposta" in text
    assert secret not in text
    assert "ok" not in text
    assert "Hücre değeri yazılmadı" in text


def test_cell_pattern_is_a_reason_without_the_cell():
    token = "bearer gizli-anahtar-degeri"
    findings = column_findings(["not"], {"not": [token]})
    text = privacy_note(findings, True)
    assert findings[0]["reason"] == "secret-pattern"
    assert "açık seçimle" in text
    assert token not in text


def test_report_omits_personal_cells_until_explicitly_included(tmp_path):
    secret = "kisi@example.com"
    store, request, _work = prepare(
        tmp_path, pl.DataFrame({"kod": [1, 2], "eposta": [secret, "baska@example.com"]})
    )
    with closing(store):
        hidden, _, _ = build(request, ReportSpec("html"), Control())
        shown, _, _ = build(
            request, ReportSpec("html", include_personal=True), Control()
        )
    assert "Kişisel sütunlar rapora alınmadı" in hidden
    assert secret not in hidden
    assert "baska@example.com" not in hidden
    assert ">kod<" in hidden
    assert "Kişisel sütunlar açık seçimle rapora alındı" in shown
    assert secret in shown
