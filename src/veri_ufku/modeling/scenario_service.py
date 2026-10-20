"""Scenario worker receives an immutable request and never owns ProjectStore."""

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError


def worker(request, spec, workspace, cancel, sender, budget):
    try:
        apply_process_limits(budget)
        from veri_ufku.modeling.scenarios import calculate

        result = calculate(request, spec, workspace, Control(cancel, budget=budget))
        sender.send(("result", result))
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
                    "Senaryo tamamlanamadı ("
                    + type(e).__name__
                    + "); önceki kayıt korundu.",
                ),
            )
        )
    finally:
        sender.close()
