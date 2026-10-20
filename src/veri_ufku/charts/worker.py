"""Disposable spawn process for calculate, render and disk membership selection."""

import copy
import os
import shutil
from pathlib import Path

from veri_ufku.charts.engine import calculate, select
from veri_ufku.domain.contracts import Progress
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError


def process_entry(action, request, parameters, workspace, cancel, connection, budget):
    try:
        apply_process_limits(budget)
        os.environ["MPLCONFIGDIR"] = str(Path(workspace) / "mpl-config")
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        if action == "export":
            from veri_ufku.charts.export import export

            value = export(
                request,
                parameters["destination"],
                parameters["format"],
                parameters["project_root"],
                control,
            )
            connection.send(("result", value))
            return
        if action == "calculate":
            result = calculate(request, parameters, workspace, control)
        else:
            result = copy.deepcopy(request)
            if action == "select":
                value = select(
                    result,
                    parameters["point_ids"],
                    parameters.get("row_ids", ()),
                    page_row_ids=parameters.get("page_row_ids", ()),
                )
                control.check()
                connection.send(("result", value))
                return
            # Copy immutable base artifacts into this render job, never overwrite a saved result.
            for key in ("data", "members"):
                source = Path(result["paths"][key])
                dest = Path(workspace) / source.name
                if source != dest:
                    shutil.copyfile(source, dest)
                result["paths"][key] = str(dest)
        from veri_ufku.charts.plot import render

        result["worker_pid"] = os.getpid()
        result = render(
            result,
            workspace,
            parameters.get("bounds", ()),
            parameters.get("highlight", ()),
            control,
        )
        control.disk(workspace, force=True)
        control.check()
        connection.send(("result", result))
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
                    f"Grafik işi tamamlanamadı ({type(error).__name__}); veri değiştirilmedi.",
                ),
            )
        )
    finally:
        connection.close()
