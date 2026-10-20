import json

from PySide6.QtCore import QSaveFile

from veri_ufku.config import AppPaths, load_settings
from veri_ufku.ui.preferences import PresentationPreferences


def test_preferences_reload_without_changing_runtime_settings(tmp_path):
    runtime = tmp_path / "settings.json"
    runtime.write_text('{"locale":"en","budget":{"cpu_threads":1}}')
    before = runtime.read_bytes()
    preferences = PresentationPreferences(tmp_path)
    preferences.setView("advanced")
    reloaded = PresentationPreferences(tmp_path)
    assert reloaded.view == "advanced"
    assert runtime.read_bytes() == before
    paths = AppPaths(tmp_path, tmp_path / "state", tmp_path / "cache")
    assert load_settings(paths).budget.cpu_threads == 1
    assert json.loads(preferences.path.read_text())["schema_version"] == 4
    assert preferences.path.stat().st_mode & 0o777 == 0o600


def test_invalid_preferences_are_preserved_and_not_overwritten(tmp_path):
    file = tmp_path / "ui-preferences.json"
    original = b'{"schema_version":999,"private-field":"fixture"}'
    file.write_bytes(original)
    preferences = PresentationPreferences(tmp_path)
    assert preferences.errorText
    preferences.setView("advanced")
    assert file.read_bytes() == original
    assert preferences.view == "beginner"
    assert "fixture" not in preferences.errorText


def test_failed_atomic_commit_retains_file_and_selected_preferences(
    tmp_path, monkeypatch
):
    preferences = PresentationPreferences(tmp_path)
    preferences.setView("beginner")
    original = preferences.path.read_bytes()

    class FailedPublication(QSaveFile):
        def commit(self):
            self.cancelWriting()
            return False

    monkeypatch.setattr("veri_ufku.ui.preferences.QSaveFile", FailedPublication)
    preferences.setView("advanced")
    assert preferences.view == "beginner"
    assert preferences.path.read_bytes() == original
    assert preferences.errorText


def test_legacy_theme_and_size_removed_on_explicit_level_change(tmp_path):
    file = tmp_path / "ui-preferences.json"
    for version in (1, 2):
        for theme in ("light", "dark", "system"):
            data = {"schema_version": version, "theme": theme, "view": "advanced"}
            if version == 1:
                data["text_scale"] = 2.0
            original = json.dumps(data).encode()
            file.write_bytes(original)
            preferences = PresentationPreferences(tmp_path)
            assert preferences.view == "advanced"
            assert not preferences.errorText
            assert file.read_bytes() == original
            preferences.setView("beginner")
            assert json.loads(file.read_text()) == {
                "schema_version": 4,
                "theme": "dark",
                "locale": "tr",
                "text_scale": 1.0,
                "view": "beginner",
            }
            assert PresentationPreferences(tmp_path).view == "beginner"
