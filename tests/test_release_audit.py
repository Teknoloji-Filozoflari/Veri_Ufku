"""Negative release gates: evidence presence is never whole release acceptance."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def audit(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "audit75_test", ROOT / "scripts/audit_phase75.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("missing", ["requirements", "checks", "human", "empty"])
def test_partial_release_never_verified(audit, missing):
    req = [dict(verified=True)]
    checks = [True]
    human = True
    if missing == "requirements":
        req.append(dict(verified=False))
    if missing == "checks":
        checks.append(False)
    if missing == "human":
        human = False
    if missing == "empty":
        req = []
    assert audit.release_gate(req, checks, human) is False
    assert audit.release_gate([dict(verified=True)], [True], True) is True


def test_declaration_cannot_make_stable(audit):
    assert audit.classification("kararlı", True) == "deneysel"
    assert audit.classification("deneysel", False) == "eksik"
    assert audit.classification("mevcut değil", True) == "eksik"


def test_junit_failure_and_skip_preserved(audit, tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    p = tmp_path / "results.xml"
    p.write_text(
        '<testsuite><testcase classname="tests.test_demo" name="ok"/><testcase classname="tests.test_demo" name="fail"><failure/></testcase><testcase classname="tests.test_demo" name="skip"><skipped/></testcase></testsuite>'
    )
    rows = audit.parse_cases([p])
    assert [r["status"] for r in rows] == ["passed", "failure", "skipped"]
    assert len({r["junit_sha256"] for r in rows}) == 1


def test_learning_review_has_hashes_and_no_expert_approval(audit, tmp_path):
    audit.learning_review(tmp_path)
    v = json.loads((tmp_path / "learning-review.json").read_text())
    assert v["expert_approved"] is False
    assert len(v["rows"]) == 424
    assert len({(r["kind"], r["id"]) for r in v["rows"]}) == 424
    for r in v["rows"]:
        assert r["status"] == "pending-independent-expert" and r["reviewer"] is None
        assert r["decision"] is None and len(r["content_sha256"]) == 64


def test_existing_human_review_is_never_overwritten(audit, tmp_path):
    worksheet = tmp_path / "expert-review-worksheet.csv"
    original = (
        "id,reviewer,decision\nexample,independent-local-reviewer,needs-changes\n"
    )
    worksheet.write_text(original)
    with pytest.raises(FileExistsError):
        audit.learning_review(tmp_path)
    assert worksheet.read_text() == original


def test_summary_deduplicates_without_turning_failure_into_pass(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import finalize_phase75 as summary

    monkeypatch.setattr(summary, "ROOT", tmp_path)
    a = tmp_path / "a.xml"
    b = tmp_path / "b.xml"
    a.write_text(
        '<testsuite><testcase classname="test_x" name="one"/><testcase classname="test_x" name="two"><skipped/></testcase></testsuite>'
    )
    b.write_text(
        '<testsuite><testcase classname="test_x" name="one"><failure/></testcase></testsuite>'
    )
    result = summary.counts([a, b])
    assert result["unique_cases"] == 2
    assert result["outcomes"] == dict(passed=0, failure=1, error=0, skipped=1)
