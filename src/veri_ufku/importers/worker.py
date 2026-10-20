"""Cancelable import process; only the parent can publish a project commit."""

from dataclasses import replace

from veri_ufku.domain.contracts import ComputeBudget, Progress
from veri_ufku.geo import FORMATS as GEO_FORMATS
from veri_ufku.importers.advanced import ADVANCED_FORMATS
from veri_ufku.importers.arrays import ARRAY_FORMATS
from veri_ufku.importers.connector_contracts import CONNECTORS, ConnectorSpec
from veri_ufku.importers.delimited import (
    Control,
    ImportSettings,
    infer_settings,
    verify_capture,
)
from veri_ufku.importers.registry import (
    default_settings,
    detect,
    get_adapter,
    settings_from_dict,
    suggest_settings,
)
from veri_ufku.importers.sources import (
    capture_source,
    input_snapshot,
    unpack,
    verify_sources,
)
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
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
        if action in ("connector", "connector_tables"):
            from veri_ufku.importers import connectors, credentials

            spec = ConnectorSpec.from_dict(source)
            if not spec.terms_acknowledged:
                raise ProjectError("Bağlantı/servis koşullarını açıkça onaylayın.")
            secret = credentials.load(spec.credential_ref)
            if action == "connector_tables":
                connection.send(("tables", connectors.discover(spec, secret, control)))
                return
            snapshot, settings = connectors.capture(spec, secret, workspace, control)
            adapter_id = spec.kind
            connection.send(("captured", (snapshot, dict(settings.__dict__))))
        elif action == "capture":
            snapshot = unpack(
                capture_source(source, workspace, control), workspace, control
            )
            # Retain capture even when detection/parsing fails: the user can correct format/path.
            snapshot["adapter_id"] = "csv"
            fallback = default_settings("csv")
            connection.send(("captured", (snapshot, dict(fallback.__dict__))))
            adapter_id = detect(snapshot)
            if adapter_id in ADVANCED_FORMATS + ARRAY_FORMATS + GEO_FORMATS:
                snapshot["strict_source"] = True
            snapshot["adapter_id"] = adapter_id
            settings = default_settings(adapter_id)
            connection.send(("captured", (snapshot, dict(settings.__dict__))))
            settings = suggest_settings(input_snapshot(snapshot), adapter_id)
            connection.send(("captured", (snapshot, dict(settings.__dict__))))
        else:
            settings = settings_from_dict(settings)
            adapter_id = snapshot.get("adapter_id", "csv")
            verify_capture(snapshot, control)
        if adapter_id not in CONNECTORS:
            verify_sources(snapshot, control)
        adapter = get_adapter(adapter_id)
        effective = (
            snapshot
            if adapter_id in ADVANCED_FORMATS + ARRAY_FORMATS + GEO_FORMATS + CONNECTORS
            else input_snapshot(snapshot)
        )
        choices = adapter.inspect(effective, settings, control)
        connection.send(("inspected", choices))
        if adapter_id in ("xlsx", "ods", "sqlite") and not settings.sheet:
            if not choices["sheets"]:
                raise ProjectError("Okunabilir sayfa/tablo yok.")
            settings = replace(settings, sheet=choices["sheets"][0])
            connection.send(("captured", (snapshot, dict(settings.__dict__))))
        if isinstance(settings, ImportSettings):
            settings = infer_settings(effective, settings, control)
        result = (
            adapter.import_data(effective, settings, workspace, control)
            if action == "import"
            else adapter.preview(effective, settings, control)
        )
        result["capture"] = snapshot
        from veri_ufku.learning.catalog import Catalog

        result["learning_content_version"] = str(Catalog().data["content_version"])
        if action == "import" and result["examined"] > 10000000:
            raise ProjectError("İçe aktarma10000000 satır sınırını aştı; yayın yok.")
        verify_capture(snapshot, control)
        if adapter_id not in CONNECTORS:
            verify_sources(snapshot, control)
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
                    f"İçe aktarma tamamlanamadı ({type(error).__name__}). Kaynak ve proje korunuyor.",
                ),
            )
        )
    finally:
        connection.close()
