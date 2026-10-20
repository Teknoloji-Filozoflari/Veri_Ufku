"""Spawned dashboard worker; immutable inputs, no Qt or project publication."""

import os
from pathlib import Path

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError


def process_entry(action, request, workspace, cancel, connection, budget):
    try:
        apply_process_limits(budget)
        os.environ["MPLCONFIGDIR"] = str(Path(workspace) / "mpl-config")
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(("progress", phase)),
            budget,
        )
        if action == "evaluate":
            from veri_ufku.charts.dashboard_engine import evaluate

            value = evaluate(request, workspace, control)
        else:
            from veri_ufku.charts.figure import compose, interactive_export

            if request["format"] == "html":
                value = interactive_export(
                    request["result"],
                    request["destination"],
                    request["project_root"],
                    workspace,
                    control,
                )
            else:
                value = compose(
                    request["figure"],
                    request["charts"],
                    request["destination"],
                    request["format"],
                    request["project_root"],
                    workspace,
                    control,
                )
        control.check()
        connection.send(("result", value))
    except Canceled:
        connection.send(("canceled", None))
    except ProjectError as error:
        connection.send(("error", str(error)))
    except Exception as error:
        connection.send(
            (
                "error",
                resource_error_text(
                    error,
                    f"Dashboard işi tamamlanamadı ({type(error).__name__}); proje korundu.",
                ),
            )
        )
    finally:
        connection.close()
