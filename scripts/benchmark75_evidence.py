"""Pytest evidence collection for synthetic Phase75 runs; never used on user projects."""

import ast
import hashlib
import json
import os
from pathlib import Path

import pytest

RECORDS = []


def persist(exitstatus=None):
    output = os.environ.get("VU75_EVIDENCE")
    if output:
        Path(output).write_text(
            json.dumps(
                dict(exitstatus=exitstatus, cases=RECORDS), ensure_ascii=False, indent=2
            )
            + "\n"
        )


def pytest_configure(config):
    if os.environ.get("VU75_GUI_CAPTURE") != "1":
        return
    from veri_ufku import app as module

    original = module.create_application

    def create(*args, **kwargs):
        if os.environ.get("VU75_GUI_RAM_GIB") == "4":
            config = Path(os.environ["XDG_CONFIG_HOME"])
            # Only isolated synthetic pytest directories; never user settings.
            if not config.is_relative_to(Path("/tmp")) or "pytest" not in str(config):
                raise RuntimeError("4GiB test profile requires isolated pytest XDG")
            settings = config / "veri_ufku/settings.json"
            settings.parent.mkdir(parents=True, exist_ok=True)
            value = json.loads(settings.read_text()) if settings.exists() else {}
            value.setdefault("budget", {})["ram_bytes"] = 4 * 1024**3
            settings.write_text(json.dumps(value))
        app, window, bridge = original(*args, **kwargs)
        resources = app._veri_ufku_resources
        shutdown = resources[-1]

        def finish():
            folder = Path(os.environ["VU75_EVIDENCE"]).parent
            ident = str(len(list(folder.glob("gui-*.png")))).zfill(3)
            try:
                app.processEvents()
                window.grabWindow().save(str(folder / ("gui-" + ident + ".png")))
                engine = resources[0]
                projects = engine._projects_resources
                supervisor = engine._resource_supervisor
                result = dict(
                    project_commit=projects.store.commit_id if projects.store else None,
                    result_records=len(projects.draft["results"]),
                    scope="offscreen screenshot before test shutdown, including failure paths; assertion outcome in JUnit determines success",
                    sampled_peak_rss_bytes=supervisor.peak_rss_bytes,
                    resource_report=supervisor.report,
                )
                result["budget_profile"] = (
                    os.environ.get("VU75_GUI_RAM_GIB", "2")
                    + "GiB explicit synthetic fixture; default failures separate"
                )
                (folder / ("gui-" + ident + ".json")).write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
                )
            finally:
                shutdown()

        app._veri_ufku_resources = (*resources[:-1], finish)
        return app, window, bridge

    module.create_application = create


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    folder = item.funcargs.get("tmp_path")
    files = []
    if folder:
        for f in sorted(folder.rglob("*")):
            if len(files) >= 1024:
                break
            if f.is_file() and not f.is_symlink() and f.stat().st_size <= 32 * 1024**2:
                files.append(
                    dict(
                        path=str(f.relative_to(folder)),
                        bytes=f.stat().st_size,
                        sha256=sha(f),
                    )
                )
    source = Path(item.path)
    text = source.read_text()
    function = next(
        (
            n
            for n in ast.walk(ast.parse(text))
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name == item.originalname
        ),
        None,
    )
    RECORDS.append(
        dict(
            nodeid=item.nodeid,
            outcome=report.outcome,
            seconds=report.duration,
            test_file_sha256=sha(source),
            reference_assertions=[
                ast.get_source_segment(text, n)
                for n in ast.walk(function)
                if isinstance(n, ast.Assert)
            ]
            if function
            else [],
            fixture_files=files,
            fixture_scope="post-call synthetic fixture/artifact bytes, before teardown; max1024files/32MiB each; absent ephemeral files not invented",
            properties=list(report.user_properties),
            failure=report.longreprtext[-16000:] if report.failed else None,
        )
    )
    persist()


def pytest_sessionfinish(session, exitstatus):
    persist(int(exitstatus))
