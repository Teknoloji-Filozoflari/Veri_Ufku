"""Single application entry point; Qt imports happen only in the GUI process."""

import argparse
import json
import resource
import signal
import sys
import time
from pathlib import Path


def create_application():
    from veri_ufku.config import AppPaths, load_settings
    from veri_ufku.jobs.limits import configure_threads

    try:
        configure_threads(load_settings(AppPaths.discover()).budget.worker_threads)
    except (OSError, ValueError, TypeError):
        configure_threads(2)
    from PySide6.QtCore import QCoreApplication, QEvent, QLocale, QTranslator, QUrl
    from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    from veri_ufku.config import AppPaths, Settings, load_settings
    from veri_ufku.domain.contracts import AppError
    from veri_ufku.jobs.manager import JobManager
    from veri_ufku.logging_setup import EventLog
    from veri_ufku.services.demo import DemoSession
    from veri_ufku.ui.charts import ChartController, ChartImages
    from veri_ufku.ui.controller import ShellController, tr
    from veri_ufku.ui.dashboard import DashboardController
    from veri_ufku.ui.dataset import DatasetController
    from veri_ufku.ui.exports import ExportController
    from veri_ufku.ui.folders import FolderController
    from veri_ufku.ui.guide import GuideController
    from veri_ufku.ui.imports import ImportController
    from veri_ufku.ui.learning import LearningController
    from veri_ufku.ui.lifecycle import LifecycleController
    from veri_ufku.ui.operations import OperationsController
    from veri_ufku.ui.preferences import PresentationPreferences
    from veri_ufku.ui.preparation import PreparationController
    from veri_ufku.ui.projects import ProjectController
    from veri_ufku.ui.recipes import RecipeController
    from veri_ufku.ui.statistics import StatisticsController
    from veri_ufku.ui.text import TextController
    from veri_ufku.ui.time_series import TimeSeriesController
    from veri_ufku.ui.unsupervised import UnsupervisedController
    from veri_ufku.ui.validation import ValidationController

    if QGuiApplication.instance() is None:
        QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication(["veri-ufku"])
    # Finish disposal of a previous shell before reusing the Qt application.
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    # Destroying its window schedules the engine for a separate deferred pass.
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.setApplicationName("Veri_Ufku")
    app.setOrganizationName("Veri_Ufku")
    app.setApplicationVersion("0.1.0")
    root_dir = Path(__file__).parent
    app.setDesktopFileName("org.veriufku.Veri_Ufku")
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256, 512):
        icon.addFile(str(root_dir / f"assets/branding/icon-{size}.png"))
    if icon.isNull():
        raise RuntimeError("Bundled application logo is missing")
    app.setWindowIcon(icon)
    if (
        QFontDatabase.addApplicationFont(str(root_dir / "assets/fonts/DejaVuSans.ttf"))
        < 0
    ):
        raise RuntimeError("Bundled font is missing")
    app.setFont(QFont("DejaVu Sans", 11))
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
    preferences = PresentationPreferences(paths.config, locale=settings.locale)
    translator = QTranslator(app)
    if not translator.load(str(root_dir / "learning/i18n/tr.qm")):
        raise RuntimeError("Bundled Turkish translation is missing")
    if preferences.locale == "tr":
        app.installTranslator(translator)
    english = QTranslator(app)
    if not english.load(str(root_dir / "learning/i18n/en.qm")):
        raise RuntimeError("Bundled core English translation is missing")
    if preferences.locale == "en":
        app.installTranslator(english)
    QLocale.setDefault(QLocale("tr_TR" if preferences.locale == "tr" else "en_GB"))
    engine = QQmlApplicationEngine()
    current_locale = preferences.locale

    def update_locale():
        nonlocal current_locale
        if preferences.locale == current_locale:
            return
        current_locale = preferences.locale
        app.removeTranslator(translator)
        app.removeTranslator(english)
        app.installTranslator(translator if preferences.locale == "tr" else english)
        QLocale.setDefault(QLocale("tr_TR" if preferences.locale == "tr" else "en_GB"))
        engine.retranslate()

    preferences.changed.connect(update_locale)
    engine._english_translation = english
    folders = FolderController(engine)
    engine._folders_resources = folders
    engine.rootContext().setContextProperty("folders", folders)
    learning = LearningController(paths.config, engine)
    projects = ProjectController(paths.config, learning, engine)
    imports = ImportController(
        projects, paths.cache / "imports", settings.budget, engine
    )
    data_view = DatasetController(
        projects, paths.cache / "dataset", settings.budget, engine
    )
    operations = OperationsController(
        data_view, projects, paths.cache / "operations", settings.budget, engine
    )
    image_provider = ChartImages()
    engine.addImageProvider("charts", image_provider)
    charts = ChartController(
        data_view,
        projects,
        paths.cache / "charts",
        settings.budget,
        image_provider,
        engine,
    )
    dashboard = DashboardController(
        projects, paths.cache / "dashboard", settings.budget, engine
    )
    engine._dashboard_resources = dashboard
    engine.rootContext().setContextProperty("dashboard", dashboard)
    exports = ExportController(
        data_view, projects, charts, paths.cache / "exports", settings.budget, engine
    )
    from veri_ufku.ui.code_bridge import CodeController

    code_bridge = CodeController(
        data_view,
        projects,
        exports,
        paths.cache / "code-bridge",
        settings.budget,
        engine,
    )
    engine._code_resources = code_bridge
    engine.rootContext().setContextProperty("codeBridge", code_bridge)
    from veri_ufku.ui.workflow import WorkflowController

    workflow_runner = WorkflowController(
        data_view, projects, paths.cache / "workflow", settings.budget, engine
    )
    engine._workflow_resources = workflow_runner
    engine.rootContext().setContextProperty("workflowRunner", workflow_runner)
    from veri_ufku.ui.repro import ReproController

    reproducibility = ReproController(
        projects, paths.cache / "repro", settings.budget, engine
    )
    engine._repro_resources = reproducibility
    engine.rootContext().setContextProperty("reproducibility", reproducibility)
    guide = GuideController(projects, imports, data_view, engine)
    statistics = StatisticsController(
        data_view, projects, charts, paths.cache / "statistics", settings.budget, engine
    )
    preparation = PreparationController(
        data_view, projects, paths.cache / "preparation", settings.budget, engine
    )
    validation = ValidationController(
        data_view,
        projects,
        preparation,
        paths.cache / "validation",
        settings.budget,
        engine,
    )
    engine._validation_resources = validation
    engine.rootContext().setContextProperty("validation", validation)
    from veri_ufku.ui.search import SearchController

    model_search = SearchController(
        data_view,
        projects,
        preparation,
        validation,
        paths.cache / "search",
        settings.budget,
        engine,
    )
    engine._search_resources = model_search
    engine.rootContext().setContextProperty("modelSearch", model_search)
    from veri_ufku.ui.neural import NeuralController

    neural = NeuralController(
        data_view,
        projects,
        preparation,
        paths.cache / "neural",
        settings.budget,
        engine,
    )
    from veri_ufku.ui.vision import VisionController

    vision = VisionController(
        data_view,
        projects,
        preparation,
        paths.cache / "vision",
        settings.budget,
        engine,
    )
    from veri_ufku.ui.audio import AudioController

    audio = AudioController(
        data_view, projects, preparation, paths.cache / "audio", settings.budget, engine
    )
    from veri_ufku.ui.recommendation import RecommendationController

    recommendation = RecommendationController(
        data_view,
        projects,
        preparation,
        paths.cache / "recommendation",
        settings.budget,
        engine,
    )
    from veri_ufku.ui.patterns import PatternController

    patterns = PatternController(
        data_view,
        projects,
        preparation,
        paths.cache / "patterns",
        settings.budget,
        engine,
    )
    from veri_ufku.ui.graphs import GraphController

    graphs = GraphController(
        data_view,
        projects,
        preparation,
        paths.cache / "graphs",
        settings.budget,
        engine,
    )
    engine._graph_resources = graphs
    engine.rootContext().setContextProperty("graphs", graphs)
    from veri_ufku.ui.streams import StreamController

    streams = StreamController(
        data_view,
        projects,
        preparation,
        paths.cache / "streams",
        settings.budget,
        engine,
    )
    engine._stream_resources = streams
    engine.rootContext().setContextProperty("streams", streams)
    engine._pattern_resources = patterns
    engine.rootContext().setContextProperty("patterns", patterns)
    engine._recommendation_resources = recommendation
    engine.rootContext().setContextProperty("recommendationAnalysis", recommendation)
    engine._audio_resources = audio
    engine.rootContext().setContextProperty("audioAnalysis", audio)
    engine._vision_resources = vision
    engine.rootContext().setContextProperty("visionAnalysis", vision)
    engine._neural_resources = neural
    engine.rootContext().setContextProperty("neuralTraining", neural)
    engine._preparation_resources = preparation
    engine.rootContext().setContextProperty("preparation", preparation)
    unsupervised = UnsupervisedController(
        data_view, projects, paths.cache / "unsupervised", settings.budget, engine
    )
    text_analysis = TextController(
        data_view, projects, paths.cache / "text", settings.budget, engine
    )
    engine._text_resources = text_analysis
    engine.rootContext().setContextProperty("textAnalysis", text_analysis)
    time_series = TimeSeriesController(
        data_view, projects, paths.cache / "time-series", settings.budget, engine
    )
    engine._time_series_resources = time_series
    engine.rootContext().setContextProperty("timeSeries", time_series)
    lifecycle = LifecycleController(
        data_view, projects, paths.cache / "lifecycle", settings.budget, engine
    )
    recipes = RecipeController(
        data_view, projects, paths.cache / "recipes", settings.budget, engine
    )
    engine._recipe_resources = recipes
    engine.rootContext().setContextProperty("recipes", recipes)
    engine._lifecycle_resources = lifecycle
    engine.rootContext().setContextProperty("lifecycle", lifecycle)
    engine._unsupervised_resources = unsupervised
    engine.rootContext().setContextProperty("unsupervised", unsupervised)
    from veri_ufku.ui.workspace import WorkspaceController

    workspace = WorkspaceController(
        projects,
        statistics,
        charts,
        (
            preparation,
            validation,
            unsupervised,
            text_analysis,
            time_series,
            lifecycle,
            model_search,
            neural,
            vision,
            audio,
            recommendation,
            patterns,
            graphs,
            streams,
            code_bridge,
            workflow_runner,
            reproducibility,
        ),
        engine,
    )
    engine._workspace_resources = workspace
    engine.rootContext().setContextProperty("expertWorkspace", workspace)
    engine._statistics_resources = statistics
    engine.rootContext().setContextProperty("statistics", statistics)
    engine._exports_resources = exports
    engine._guide_resources = guide
    engine.rootContext().setContextProperty("exports", exports)
    engine.rootContext().setContextProperty("guide", guide)
    engine._charts_resources = charts
    engine.rootContext().setContextProperty("charts", charts)
    engine._operations_resources = operations
    engine.rootContext().setContextProperty("operations", operations)
    engine._dataset_resources = data_view
    engine.rootContext().setContextProperty("dataView", data_view)
    engine._imports_resources = imports
    engine.rootContext().setContextProperty("imports", imports)
    from veri_ufku.ui.launch import LaunchRequests

    launch = LaunchRequests(projects, imports, engine)
    engine._launch_resources = launch
    engine.rootContext().setContextProperty("launchRequests", launch)
    engine._projects_resources = projects
    engine.rootContext().setContextProperty("projects", projects)
    engine._learning_resources = learning
    engine.rootContext().setContextProperty("learning", learning)
    engine.rootContext().setContextProperty("preferences", preferences)
    controller = None
    if not startup_error:
        manager = JobManager(paths.cache, settings.budget, log)
        controller = ShellController(DemoSession(manager, settings.budget), engine)
        controller.admission = lambda: not projects.busy
        projects.external_busy = lambda: controller._active
        controller.changed.connect(projects.changed.emit)
    from veri_ufku.ui.learning_lab import LearningLabController

    learning_lab = LearningLabController(
        learning, paths.cache / "learning-lab", settings.budget, engine
    )
    engine._learning_lab_resources = learning_lab
    engine.rootContext().setContextProperty("learningLab", learning_lab)
    from veri_ufku.ui.scenarios import ScenarioController

    scenarios = ScenarioController(
        projects, paths.cache / "scenarios", settings.budget, engine
    )
    engine._scenario_resources = scenarios
    engine.rootContext().setContextProperty("scenarios", scenarios)
    from veri_ufku.ui.environment import EnvironmentController

    environment = EnvironmentController(
        projects, paths.cache / "environment", settings.budget, engine
    )
    engine._environment_resources = environment
    engine.rootContext().setContextProperty("environment", environment)
    from veri_ufku.ui.plugins import PluginController

    plugins = PluginController(
        projects, paths.cache / "plugins", settings.budget, engine
    )
    engine._plugin_resources = plugins
    engine.rootContext().setContextProperty("plugins", plugins)
    from veri_ufku.ui.privacy import PrivacyController

    privacy = PrivacyController(
        projects, paths.cache / "privacy", settings.budget, engine
    )
    engine._privacy_resources = privacy
    engine.rootContext().setContextProperty("privacy", privacy)
    from veri_ufku.ui.sharing import SharingController

    sharing = SharingController(
        projects, paths.cache / "sharing", settings.budget, engine
    )
    engine._sharing_resources = sharing
    engine.rootContext().setContextProperty("sharing", sharing)
    from veri_ufku.ui.report_builder import ReportBuilderController

    report_builder = ReportBuilderController(
        projects, paths.cache / "reports", settings.budget, engine
    )
    engine._report_builder_resources = report_builder
    engine.rootContext().setContextProperty("reportBuilder", report_builder)
    from veri_ufku.ui.monitoring import MonitoringController

    monitoring = MonitoringController(
        projects, paths.cache / "monitoring", settings.budget, engine
    )
    engine._monitoring_resources = monitoring
    engine.rootContext().setContextProperty("monitoring", monitoring)
    from veri_ufku.jobs.supervision import ResourceSupervisor

    supervisor = ResourceSupervisor(
        (
            environment,
            plugins,
            privacy,
            sharing,
            report_builder,
            learning_lab,
            scenarios,
            monitoring,
            imports,
            data_view,
            operations,
            charts,
            exports,
            code_bridge,
            workflow_runner,
            reproducibility,
            dashboard,
            statistics,
            preparation,
            validation,
            model_search,
            neural,
            vision,
            audio,
            recommendation,
            patterns,
            graphs,
            streams,
            unsupervised,
            text_analysis,
            time_series,
            lifecycle,
            recipes,
        ),
        settings.budget,
        engine,
    )
    engine._resource_supervisor = supervisor
    engine.rootContext().setContextProperty("computeResources", supervisor)
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
    window.destroyed.connect(engine.deleteLater)
    if controller:
        controller.shutdownReady.connect(window.close)

    cleaned = False

    def cleanup():
        nonlocal cleaned
        if cleaned:
            return
        cleaned = True
        app.aboutToQuit.disconnect(cleanup)
        preferences.changed.disconnect(update_locale)
        app.removeTranslator(translator)
        app.removeTranslator(english)
        window.hide()
        supervisor.shutdown()
        if controller:
            controller.dispose()
        environment.shutdown()
        plugins.shutdown()
        privacy.shutdown()
        sharing.shutdown()
        report_builder.shutdown()
        learning_lab.shutdown()
        scenarios.shutdown()
        monitoring.shutdown()
        folders.shutdown()
        text_analysis.shutdown()
        time_series.shutdown()
        recipes.shutdown()
        lifecycle.shutdown()
        unsupervised.shutdown()
        validation.shutdown()
        model_search.shutdown()
        neural.shutdown()
        vision.shutdown()
        audio.shutdown()
        recommendation.shutdown()
        patterns.shutdown()
        graphs.shutdown()
        streams.shutdown()
        preparation.shutdown()
        statistics.shutdown()
        guide.shutdown()
        reproducibility.shutdown()
        workflow_runner.shutdown()
        code_bridge.shutdown()
        exports.shutdown()
        charts.shutdown()
        dashboard.shutdown()
        operations.shutdown()
        data_view.shutdown()
        imports.shutdown()
        projects.shutdown()
        if manager:
            manager.shutdown()
        if log:
            log.close()
        translator.deleteLater()
        english.deleteLater()

    app.aboutToQuit.connect(cleanup)
    # Retain Python/Qt objects until the event loop ends.
    app._veri_ufku_resources = (
        engine,
        controller,
        translator,
        manager,
        log,
        learning,
        preferences,
        cleanup,
    )
    return app, window, controller


def main(argv=None):
    parser = argparse.ArgumentParser(prog="veri-ufku")
    parser.add_argument("--version", action="version", version="Veri_Ufku 0.1.0")
    parser.add_argument(
        "file",
        nargs="?",
        help="Local data file; opens an import preview after project selection",
    )
    parser.add_argument(
        "--install-desktop",
        action="store_true",
        help="Install the application menu launcher and logo for the current user",
    )
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
    if args.install_desktop:
        from veri_ufku.desktop import install

        for path in install():
            print(path)
        return 0
    started = time.monotonic()
    from PySide6.QtCore import QTimer

    app, window, controller = create_application()
    if args.file:
        try:
            app._veri_ufku_resources[0]._launch_resources.queue(args.file)
        except (ValueError, OSError) as error:
            print(str(error), file=sys.stderr)
            app._veri_ufku_resources[-1]()
            return 2
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
            if snapshot.state.terminal and controller.beats >= 2:
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
