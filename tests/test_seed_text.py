"""Seed report prints recorded integers and hides other values."""

from veri_ufku.exports.seed_text import seed_text


def test_recorded_seed_is_shown_and_secret_parameter_is_not():
    secret = "s3cr3t-tohum"
    text = seed_text(
        17,
        [
            {
                "id": "op:1",
                "seed": 17,
                "spec": {
                    "kind": "sample",
                    "parameters": {"token": secret},
                },
            }
        ],
        [{"id": "result:1", "seed": None}],
    )
    assert "Proje tohumu: 17" in text
    assert "sample · tohum 17" in text
    assert "tohum kayıtlı değil" in text
    assert secret not in text
    assert "uydurulmaz" not in text


def test_missing_seed_is_not_replaced():
    text = seed_text(None, [{"seed": None, "spec": {"kind": "trim"}}], [])
    assert "Proje tohumu: kayıtlı değil" in text
    assert "trim · tohum kayıtlı değil" in text
    assert "Tohum uydurulmaz" in text
    assert "42" not in text


def test_non_integer_seed_is_not_copied():
    text = seed_text("bearer gizli-deger", [], [])
    assert "geçersiz" in text
    assert "gizli-deger" not in text
    assert "Tohum uydurulmaz" in text
