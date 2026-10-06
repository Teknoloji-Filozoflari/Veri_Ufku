"""Cancelable import process; only the parent can publish a project commit."""

from dataclasses import replace

from veri_ufku.domain.contracts import ComputeBudget, Progress
from veri_ufku.importers.delimited import Control, capture, verify_capture
from veri_ufku.importers.registry import (
    default_settings,
    detect,
    get_adapter,
    settings_from_dict,
    suggest_settings,
)
from veri_ufku.jobs.limits import apply_process_limits
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError


def process_entry(
    action,
    source,
    snapshot,
    settings,
    workspace,
    cancel,
    connection,
    budget=ComputeBudget(),
):
    try:
        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        if action == "capture":
            snapshot = capture(source, workspace, control, any_format=True)
            # Retain capture even when detection/parsing fails: the user can correct format/path.
            snapshot["adapter_id"] = "csv"
            fallback = default_settings("csv")
            connection.send(("captured", (snapshot, dict(fallback.__dict__))))
            adapter_id = detect(snapshot)
            snapshot["adapter_id"] = adapter_id
            settings = default_settings(adapter_id)
            connection.send(("captured", (snapshot, dict(settings.__dict__))))
            settings = suggest_settings(snapshot, adapter_id)
            connection.send(("captured", (snapshot, dict(settings.__dict__))))
        else:
            settings = settings_from_dict(settings)
            adapter_id = snapshot.get("adapter_id", "csv")
            verify_capture(snapshot, control)
        adapter = get_adapter(adapter_id)
        choices = adapter.inspect(snapshot, settings, control)
        connection.send(("inspected", choices))
        if adapter_id == "xlsx" and not settings.sheet:
            settings = replace(settings, sheet=choices["sheets"][0])
            connection.send(("captured", (snapshot, dict(settings.__dict__))))
        result = (
            adapter.import_data(snapshot, settings, workspace, control)
            if action == "import"
            else adapter.preview(snapshot, settings, control)
        )
        verify_capture(snapshot, control)
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
                f"İçe aktarma tamamlanamadı ({type(error).__name__}). Kaynak ve proje korunuyor.",
            )
        )
    finally:
        connection.close()
