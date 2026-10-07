"""Disposable compute process; project publication remains in the parent."""

from veri_ufku.domain.contracts import Progress
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits
from veri_ufku.jobs.workers import Canceled
from veri_ufku.operations.engine import calculate
from veri_ufku.storage.project_model import ProjectError


def process_entry(request, spec, workspace, cancel, connection, budget):
    try:
        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        result = calculate(request, spec, workspace, control)
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
                f"İşlem tamamlanamadı ({type(error).__name__}); eski dataset korundu.",
            )
        )
    finally:
        connection.close()
