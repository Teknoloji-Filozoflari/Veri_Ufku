"""Source notes keep the id and hash, and do not invent a license."""

from veri_ufku.exports.source_note import source_license_text


def test_source_note_keeps_the_hash_and_drops_the_path():
    secret = "/home/s3cr3t-user/hasta.csv"
    text = source_license_text(
        [
            {
                "id": "source:11111111-1111-1111-1111-111111111111",
                "path": secret,
                "fingerprint": {"size": 10, "sha256": "a" * 64},
                "copy_uri": "artifacts/secret-copy",
            }
        ],
        "Sentetik veri, CC BY 4.0",
    )
    assert "source:11111111-1111-1111-1111-111111111111" in text
    assert "a" * 64 in text
    assert "Lisans notu: Sentetik veri, CC BY 4.0" in text
    assert secret not in text
    assert "secret-copy" not in text


def test_missing_license_is_not_invented():
    text = source_license_text([], "")
    assert "Kaynak uydurulmaz" in text
    assert "Lisans uydurulmaz" in text


def test_secret_license_note_is_not_copied():
    text = source_license_text([], "bearer gizli-lisans")
    assert "geçersiz" in text
    assert "gizli-lisans" not in text
