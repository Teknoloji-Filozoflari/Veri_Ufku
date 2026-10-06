import copy

from PySide6.QtCore import QObject
from test_gui import spin

from veri_ufku.app import create_application


def test_project_qml_actions_dirty_close_and_reopen(tmp_path, monkeypatch):
    for var, folder in [
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_STATE_HOME", "state"),
        ("XDG_CACHE_HOME", "cache"),
    ]:
        monkeypatch.setenv(var, str(tmp_path / folder))
    app, window, bridge = create_application()
    projects = app._veri_ufku_resources[0]._projects_resources
    try:
        assert window.findChild(QObject, "projectPanel") is not None
        path = str(tmp_path / "project")
        window.findChild(QObject, "newProjectButton").clicked.emit()
        app.processEvents()
        assert window.findChild(QObject, "projectPathDialog").property("visible")
        window.findChild(QObject, "projectPathField").setProperty("text", path)
        window.findChild(QObject, "confirmProjectPathButton").clicked.emit()
        spin(app, lambda: not projects.busy)
        assert projects.opened
        assert window.findChild(QObject, "projectPanel").property("height") > 400
        projects.setName("GUI Projesi")
        projects.setSeed("123")
        projects.learning.setDepth(2)
        projects.draft["help_preferences"]["context_hint"] = False
        assert projects.dirty
        window.findChild(QObject, "saveProjectButton").clicked.emit()
        spin(app, lambda: not projects.busy)
        assert not projects.dirty
        snapshot = copy.deepcopy(projects.draft)
        assert projects.closeProject(False)
        assert projects.open(path)
        assert projects.draft == snapshot
        assert projects.learning.depth == 2
        assert projects.recent == [path]
        projects.setName("Kurtarma")
        projects.autosave()
        window.close()
        app.processEvents()
        assert window.isVisible()
        assert window.findChild(QObject, "unsavedProjectDialog").property("visible")
        assert projects.closeProject(True)
        assert projects.open(path)
        assert projects.name == "GUI Projesi"
        assert projects.restoreAutosave()
        assert projects.name == "Kurtarma" and projects.dirty
        assert projects.save()
        assert projects.saveAs(str(tmp_path / "fork"))
        assert projects.recent[0] == str(tmp_path / "fork")
        assert not projects.saveAs(str(tmp_path / "fork"))
        assert projects.errorText
        assert projects.closeProject(True)
    finally:
        app._veri_ufku_resources[-1]()
        window.deleteLater()
        app.processEvents()


def test_project_io_thread_responsiveness_and_source_watcher(tmp_path, monkeypatch):
    import threading

    from PySide6.QtCore import QTimer

    from veri_ufku.storage import project_store

    for var, folder in [
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_STATE_HOME", "state"),
        ("XDG_CACHE_HOME", "cache"),
    ]:
        monkeypatch.setenv(var, str(tmp_path / folder))
    app, window, bridge = create_application()
    projects = app._veri_ufku_resources[0]._projects_resources
    original = project_store.source_fingerprint
    entered, release = threading.Event(), threading.Event()

    def delayed(path):
        entered.set()
        assert release.wait(5)
        assert threading.current_thread() is not threading.main_thread()
        return original(path)

    timer = QTimer()
    ticks = []
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(10)
    try:
        projects.request("create", str(tmp_path / "project"))
        spin(app, lambda: not projects.busy)
        assert projects.opened
        source = tmp_path / "source.csv"
        source.write_bytes(b"unaltered")
        monkeypatch.setattr(project_store, "source_fingerprint", delayed)
        projects.request("addSource", str(source), "", True)
        spin(app, lambda: entered.is_set())
        spin(app, lambda: len(ticks) >= 10)
        window.close()
        assert window.isVisible() and projects.busy
        release.set()
        spin(app, lambda: not projects.busy)
        assert "aynı veri" in projects.sourceSummary
        assert projects.dirty
        projects.request("save")
        spin(app, lambda: not projects.busy)
        assert not projects.dirty
        source.write_bytes(b"new data version")
        spin(app, lambda: "değişmiş" in projects.sourceSummary)
        assert source.read_bytes() == b"new data version"
    finally:
        release.set()
        timer.stop()
        app._veri_ufku_resources[-1]()
        window.deleteLater()
        app.processEvents()


def test_two_application_instances_keep_second_readonly(tmp_path, monkeypatch):
    from veri_ufku.storage.project_store import ProjectStore

    for var, folder in [
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_STATE_HOME", "state"),
        ("XDG_CACHE_HOME", "cache"),
    ]:
        monkeypatch.setenv(var, str(tmp_path / folder))
    path = tmp_path / "project"
    store = ProjectStore.create(path)
    store.close()
    app, first, bridge1 = create_application()
    first_resources = app._veri_ufku_resources
    owner = first_resources[0]._projects_resources
    owner.request("open", str(path))
    spin(app, lambda: not owner.busy)
    _, second, bridge2 = create_application()
    second_resources = app._veri_ufku_resources
    reader = second_resources[0]._projects_resources
    try:
        reader.request("open", str(path))
        spin(app, lambda: not reader.busy)
        assert reader.readOnly
        assert not second.findChild(QObject, "saveProjectButton").property("enabled")
        reader.request("recover")
        spin(app, lambda: not reader.busy)
        assert reader.readOnly
        owner.setName("Yazıcı kaydı")
        owner.request("save")
        spin(app, lambda: not owner.busy)
        assert not owner.dirty
        assert reader.name != owner.name  # pinned committed state
    finally:
        first_resources[-1]()
        second_resources[-1]()
        first.deleteLater()
        second.deleteLater()
        app.processEvents()


def test_new_project_path_error_stays_visible_and_can_be_corrected(
    tmp_path, monkeypatch
):
    for var, folder in [
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_STATE_HOME", "state"),
        ("XDG_CACHE_HOME", "cache"),
    ]:
        monkeypatch.setenv(var, str(tmp_path / folder))
    app, window, bridge = create_application()
    projects = app._veri_ufku_resources[0]._projects_resources
    try:
        window.findChild(QObject, "newProjectButton").clicked.emit()
        dialog = window.findChild(QObject, "projectPathDialog")
        field = window.findChild(QObject, "projectPathField")
        submit = window.findChild(QObject, "confirmProjectPathButton")
        field.setProperty("text", str(tmp_path / "missing-parent" / "project"))
        submit.clicked.emit()
        spin(app, lambda: not projects.busy)
        assert "üst klasörü mevcut değil" in projects.errorText
        assert dialog.property("visible")
        assert not (tmp_path / "missing-parent").exists()
        assert window.findChild(QObject, "chooseProjectLocationButton") is not None
        suggested = projects.newProjectPath(tmp_path.as_uri())
        assert suggested == str(tmp_path / "Yeni_Proje")
        field.setProperty("text", suggested)
        submit.clicked.emit()
        spin(app, lambda: not projects.busy)
        assert projects.opened and not projects.errorText
        assert not dialog.property("visible")
        assert projects.closeProject(False)
    finally:
        app._veri_ufku_resources[-1]()
        window.deleteLater()
        app.processEvents()


def test_project_error_messages_distinguish_path_permissions_and_disk():
    import errno
    import sqlite3

    from veri_ufku.ui.projects import project_error_text

    cases = [
        (FileNotFoundError(errno.ENOENT, "private sample"), "bulunamadı"),
        (PermissionError(errno.EACCES, "private sample"), "yazma izni yok"),
        (OSError(errno.ENOSPC, "private sample"), "boş alan yok"),
        (OSError(errno.EROFS, "private sample"), "salt okunur"),
        (sqlite3.OperationalError("private sample"), "OperationalError"),
    ]
    for error, expected in cases:
        message = project_error_text(error)
        assert expected in message
        assert "private sample" not in message
