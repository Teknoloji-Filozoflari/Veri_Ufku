import json

from PySide6.QtCore import QSaveFile

from veri_ufku.config import AppPaths, load_settings
from veri_ufku.ui.preferences import PresentationPreferences


def test_preferences_reload_without_changing_runtime_settings(tmp_path):
    runtime = tmp_path / "settings.json"
    runtime.write_text('{"locale":"en","budget":{"cpu_threads":1}}')
    before = runtime.read_bytes()
    preferences = PresentationPreferences(tmp_path)
    preferences.setTheme("dark")
    preferences.setView("advanced")
    preferences.setTextScale(1.5)
    reloaded = PresentationPreferences(tmp_path)
    assert (reloaded.theme, reloaded.view, reloaded.textScale) == (
        "dark",
        "advanced",
        1.5,
    )
    assert runtime.read_bytes() == before
    paths = AppPaths(tmp_path, tmp_path / "state", tmp_path / "cache")
    assert load_settings(paths).budget.cpu_threads == 1
    assert json.loads(preferences.path.read_text())["schema_version"] == 1
    assert preferences.path.stat().st_mode & 0o777 == 0o600


def test_invalid_preferences_are_preserved_and_not_overwritten(tmp_path):
    file = tmp_path / "ui-preferences.json"
    original = b'{"schema_version":999,"private-field":"fixture"}'
    file.write_bytes(original)
    preferences = PresentationPreferences(tmp_path)
    assert preferences.errorText
    preferences.setTheme("dark")
    assert file.read_bytes() == original
    assert preferences.theme == "system"
    assert "fixture" not in preferences.errorText


def test_failed_atomic_commit_retains_file_and_selected_preferences(
    tmp_path, monkeypatch
):
    preferences = PresentationPreferences(tmp_path)
    preferences.setTheme("light")
    original = preferences.path.read_bytes()

    class FailedPublication(QSaveFile):
        def commit(self):
            self.cancelWriting()
            return False

    monkeypatch.setattr("veri_ufku.ui.preferences.QSaveFile", FailedPublication)
    preferences.setTheme("dark")
    assert preferences.theme == "light"
    assert preferences.path.read_bytes() == original
    assert preferences.errorText
