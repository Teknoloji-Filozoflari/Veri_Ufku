"""Disposable CPU lab process with no Qt or project writer."""

from veri_ufku.domain.json import sha
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.learning.curriculum import CONTENT


def worker(request, spec, workspace, cancel, sender, budget):
    try:
        apply_process_limits(budget)
        if sha(CONTENT.read_bytes()) != request["curriculum_hash"]:
            raise ValueError("Lesson content changed")
        from veri_ufku.learning.lab_engine import calculate

        sender.send(
            (
                "result",
                calculate(request, spec, workspace, Control(cancel, budget=budget)),
            )
        )
    except Canceled:
        sender.send(("canceled", None))
    except (ValueError, TypeError, KeyError) as e:
        sender.send(
            (
                "error",
                "Laboratuvar tarifi/hesabı geçersiz ("
                + type(e).__name__
                + "). Önceki sonuç korundu.",
            )
        )
    except Exception as e:
        sender.send(
            (
                "error",
                resource_error_text(
                    e, "Laboratuvar tamamlanamadı (" + type(e).__name__ + ")."
                ),
            )
        )
    finally:
        sender.close()
