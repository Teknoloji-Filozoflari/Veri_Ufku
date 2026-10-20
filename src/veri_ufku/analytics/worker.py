"""Bounded dataset work in a disposable process; only the parent owns project writes."""

from veri_ufku.analytics.contracts import ProfileSpec, ViewSpec
from veri_ufku.analytics.dataset import checked, page, profile
from veri_ufku.analytics.quality import scan
from veri_ufku.domain.contracts import Progress
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError


def process_entry(action, request, parameters, workspace, cancel, connection, budget):
    try:
        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        view = ViewSpec.from_dict(parameters["view"])
        if action in {"inventory", "describe"}:
            from veri_ufku.analytics.inspection import inspect

            result = inspect(
                request,
                dict(parameters, describe=action == "describe"),
                workspace,
                control,
            )
            control.disk(workspace, force=True)
            control.check()
            connection.send(("result", result))
            return
        if action == "page" and parameters.get("cached_page") is not None:
            # Cache is supplied by the trusted parent, only after the complete
            # request/view/fingerprint key matches. Rehash source off the GUI thread.
            checked(request, control)
            control.check()
            connection.send(("result", parameters["cached_page"]))
            return
        if action == "quality":
            result = scan(request, parameters, workspace, control)
            control.check()
            connection.send(("result", result))
            return
        result = (
            page(request, view, parameters["offset"], control)
            if action == "page"
            else profile(
                request,
                ProfileSpec(
                    parameters["column_id"],
                    parameters["sample"],
                    parameters["target"],
                    parameters["ddof"],
                    view,
                ),
                workspace,
                control,
                parameters.get("unique_offset", 0),
                parameters.get("unique_query", ""),
            )
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
                    f"Tablo/profil işi tamamlanamadı ({type(error).__name__}); dataset değiştirilmedi.",
                ),
            )
        )
    finally:
        connection.close()
