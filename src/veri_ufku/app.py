"""Single application entry point; Qt imports happen only in the GUI process."""

import argparse
import json
import resource
import signal
import sys
import time
from pathlib import Path


def create_application():
    from PySide6.QtCore import QTranslator, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    from veri_ufku.config import AppPaths, Settings, load_settings
    from veri_ufku.domain.contracts import AppError
    from veri_ufku.jobs.manager import JobManager
    from veri_ufku.logging_setup import EventLog
    from veri_ufku.services.demo import DemoSession
    from veri_ufku.ui.controller import ShellController, tr
    from veri_ufku.ui.preferences import PresentationPreferences

    if QGuiApplication.instance() is None:
        QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication(["veri-ufku"])
    app.setApplicationName("Veri_Ufku")
    app.setOrganizationName("Veri_Ufku")
    app.setApplicationVersion("0.1.0")
    root_dir = Path(__file__).parent
    paths, settings, startup_error, log, manager = (
        AppPaths.discover(),
        Settings(),
        "",
        None,
        None,
    )
    try:
        paths.prepare()
        log = EventLog(paths.state)
        settings = load_settings(paths)
    except (OSError, ValueError, TypeError) as exception:
        error = AppError.create("configuration", type(exception).__name__)
        if log:
            log.event("startup_failed", error=error)
        startup_error = "Configuration is invalid. Check local settings."
    translator = QTranslator(app)
    if settings.locale == "tr":
        if not translator.load(str(root_dir / "learning/i18n/tr.qm")):
            raise RuntimeError("Bundled Turkish translation is missing")
        app.installTranslator(translator)
    engine = QQmlApplicationEngine()
    preferences = PresentationPreferences(paths.config)
    engine.rootContext().setContextProperty("preferences", preferences)
    controller = None
    if not startup_error:
        manager = JobManager(paths.cache, settings.budget, log)
        controller = ShellController(DemoSession(manager, settings.budget))
    engine.rootContext().setContextProperty("bridge", controller)
    engine.rootContext().setContextProperty(
        "startupError", tr(startup_error) if startup_error else ""
    )
    engine.load(QUrl.fromLocalFile(str(root_dir / "ui/qml/Main.qml")))
    if not engine.rootObjects():
        if manager:
            manager.shutdown()
        raise RuntimeError("Application UI could not be loaded")
    window = engine.rootObjects()[0]
    if controller:
        controller.shutdownReady.connect(window.close)

    def cleanup():
        if manager:
            manager.shutdown()
        if log:
            log.close()

    app.aboutToQuit.connect(cleanup)
    # Retain Python/Qt objects until the event loop ends.
    app._veri_ufku_resources = (
        engine,
        controller,
        translator,
        manager,
        log,
        preferences,
        cleanup,
    )
    return app, window, controller


def main(argv=None):
    parser = argparse.ArgumentParser(prog="veri-ufku")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Open the GUI, run a CPU task and exit with a verified result",
    )
    parser.add_argument(
        "--startup-probe",
        action="store_true",
        help="Measure the first rendered frame and exit",
    )
    args = parser.parse_args(argv)
    started = time.monotonic()
    from PySide6.QtCore import QTimer

    app, window, controller = create_application()
    if args.startup_probe:

        def first_frame():
            print(
                "STARTUP_READY "
                + json.dumps(
                    {
                        "ms": (time.monotonic() - started) * 1000,
                        "rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                        * 1024,
                    }
                ),
                flush=True,
            )
            app.exit(0)

        window.frameSwapped.connect(first_frame)
        QTimer.singleShot(10000, lambda: app.exit(4))
    if args.smoke_test:
        if not controller:
            return 2
        from veri_ufku.domain.contracts import Binding, DemoParameters, JobSpec

        spec = JobSpec("demo.cpu", Binding("smoke:v1", 0), DemoParameters(3, 10, 0))
        controller.session.binding = spec.binding
        controller.job_id = controller.session.manager.submit(spec)
        controller._active = True
        timer = QTimer(app)

        def check():
            snapshot = controller.session.manager.snapshot(controller.job_id)
            if snapshot.state.terminal:
                result = snapshot.result_for(spec.binding)
                code = (
                    0 if result and result.value == 435 and controller.beats >= 2 else 3
                )
                print("GUI_SMOKE", "PASS" if code == 0 else "FAIL", flush=True)
                app.exit(code)

        timer.timeout.connect(check)
        timer.start(25)
        QTimer.singleShot(10000, lambda: app.exit(4))
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda _signal, _frame: window.close())
    try:
        return app.exec()
    finally:
        app._veri_ufku_resources[-1]()


if __name__ == "__main__":
    sys.exit(main())
