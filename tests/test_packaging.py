import hashlib

import pytest
from test_gui import spin

from veri_ufku.app import create_application, main
from veri_ufku.config import AppPaths


def test_desktop_file_request_waits_for_project_and_only_previews(
    tmp_path, monkeypatch
):
    for key in ("CONFIG", "STATE", "CACHE", "DATA"):
        monkeypatch.setenv("XDG_" + key + "_HOME", str(tmp_path / key))
    source = tmp_path / "synthetic.csv"
    source.write_text("x,y\n1,2\n3,4\n")
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    app, window, _ = create_application()
    engine = app._veri_ufku_resources[0]
    launch, projects, imports = (
        engine._launch_resources,
        engine._projects_resources,
        engine._imports_resources,
    )
    try:
        with pytest.raises(ValueError):
            launch.queue("https://example.invalid/data.csv")
        launch.queue(source.as_uri())
        assert launch.pending == str(source) and not imports.busy
        assert projects.create(str(tmp_path / "project"))
        spin(app, lambda: launch.pending is None and not imports.busy)
        assert imports.valid and imports.result
        assert not projects.draft["datasets"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == original
        assert AppPaths.discover().data == tmp_path / "DATA/veri_ufku"
    finally:
        app._veri_ufku_resources[-1]()
        window.deleteLater()
        app.processEvents()


def test_version_is_available_without_gui(capsys):
    with pytest.raises(SystemExit) as result:
        main(["--version"])
    assert result.value.code == 0
    assert capsys.readouterr().out.strip() == "Veri_Ufku 0.1.0"
