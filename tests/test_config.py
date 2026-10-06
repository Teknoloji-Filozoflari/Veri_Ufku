import json

import pytest

from veri_ufku.config import AppPaths, load_settings


def test_defaults_and_explicit_local_configuration(tmp_path):
    paths = AppPaths(tmp_path / "config", tmp_path / "state", tmp_path / "cache")
    paths.prepare()
    assert load_settings(paths).locale == "tr"
    file = paths.config / "settings.json"
    file.write_text(json.dumps({"locale": "en", "budget": {"cpu_threads": 1}}))
    settings = load_settings(paths)
    assert settings.locale == "en"
    assert settings.budget.cpu_threads == 1
    file.write_text('{"download_remote": true}')
    with pytest.raises(ValueError):
        load_settings(paths)
