"""Disposable CPU worker; parent retains sole project publication authority."""

import os

from veri_ufku.domain.contracts import Progress
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError


def process_entry(action, request, parameters, workspace, cancel, connection, budget):
    try:
        from veri_ufku.jobs.limits import configure_threads

        configure_threads(budget.worker_threads)
        from veri_ufku.statistics.engine import calculate

        if parameters.get("path") == "models":
            # Include native library mappings in the shared RLIMIT_AS baseline;
            # RSS admission and working-memory budget remain enforced.
            from veri_ufku.statistics import models

            del models

        if parameters.get("path") == "dimensions":
            from matplotlib import pyplot

            from veri_ufku.statistics import dimensions

            if parameters.get("method") == "dimension_umap":
                os.environ["NUMBA_CACHE_DIR"] = workspace
                from umap import UMAP

                del UMAP
            del dimensions, pyplot

        if parameters.get("path") == "survival":
            from matplotlib import pyplot

            from veri_ufku.statistics import survival

            del survival, pyplot

        if parameters.get("path") == "causal":
            from veri_ufku.statistics import causal

            del causal

        if parameters.get("path") == "experiments":
            # Prime native statsmodels power mappings before the address-space baseline.
            from veri_ufku.statistics import experiments

            del experiments

        if parameters.get("path") == "bayes":
            os.environ["XDG_CACHE_HOME"] = workspace
            os.environ["MPLCONFIGDIR"] = workspace
            from veri_ufku.statistics.bayes import backend

            backend()

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        result = calculate(
            request, parameters, workspace, control, preflight=action == "preflight"
        )
        result["worker_pid"] = os.getpid()
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
                    f"İstatistik işi tamamlanamadı ({type(error).__name__}); veri korunuyor.",
                ),
            )
        )
    finally:
        connection.close()
