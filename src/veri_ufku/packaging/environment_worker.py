"""Explicit local metadata/import/export/update planning, no automatic installers."""

from pathlib import Path

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.packaging.environment import (
    export_profile,
    import_profile,
    inspect_cache,
    scan,
    update_plan,
)
from veri_ufku.storage.project_model import ProjectError


def calculate(request, workspace, control):
    action = request["action"]
    if action == "scan":
        return dict(action=action, report=scan(request["artifacts"], control))
    if action == "export":
        return export_profile(
            request["report"],
            request["destination"],
            request["project_root"],
            workspace,
            control,
        )
    if action == "import":
        return import_profile(request["path"], request["approved"], control)
    if action == "update-plan":
        return update_plan(
            request["path"],
            request["expected_sha256"],
            request["current_commit"],
            request["approved"],
            control,
        )
    if action == "cache":
        return inspect_cache(request["path"], request["approved"], control)
    raise ProjectError("Environment action unsupported.")


def worker(request, workspace, cancel, sender, budget):
    try:
        apply_process_limits(budget)
        sender.send(
            (
                "result",
                calculate(request, Path(workspace), Control(cancel, budget=budget)),
            )
        )
    except Canceled:
        sender.send(("canceled", None))
    except ProjectError as e:
        sender.send(("error", str(e)))
    except Exception as e:
        sender.send(
            (
                "error",
                resource_error_text(
                    e,
                    "Environment işlemi tamamlanamadı ("
                    + type(e).__name__
                    + "); kurulum/proje değişmedi.",
                ),
            )
        )
    finally:
        sender.close()
