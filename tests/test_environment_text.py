"""Report environment text keeps installed names and drops extra fields."""

import platform

from veri_ufku.exports.environment_text import (
    current_environment_text,
    environment_text,
)


def test_environment_text_lists_packages_and_skips_extra_fields():
    secret = "/home/s3cr3t-user"
    text = environment_text(
        {
            "python": "3.13.15",
            "implementation": "CPython",
            "machine": "x86_64",
            "packages": {"polars": "1.2.3", "veri-ufku": "0.1.0"},
            "engine_hash": "abc123",
            "home": secret,
            "token": "hidden-token",
        }
    )
    assert "Python: 3.13.15" in text
    assert "veri-ufku==0.1.0" in text
    assert "polars==1.2.3" in text
    assert "motor: abc123" in text
    assert secret not in text
    assert "hidden-token" not in text


def test_missing_packages_are_not_invented():
    assert "uydurulmaz" in environment_text({})


def test_current_environment_matches_this_interpreter():
    text = current_environment_text()
    assert platform.python_version() in text
    assert "veri-ufku==" in text
