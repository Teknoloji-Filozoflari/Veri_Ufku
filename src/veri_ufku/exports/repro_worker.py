"""Explicit Qt-free worker: read-only project, bounded archive work, never ACTIVE."""

import zipfile
from contextlib import closing, nullcontext
from pathlib import Path

from veri_ufku.exports.files import publish
from veri_ufku.exports.repro import build, open_bundle, preview
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.repro_verify import rerun
from veri_ufku.storage.project_model import ProjectError, relative
from veri_ufku.storage.project_store import ProjectStore


class RecordedProject:
    """Parent-validated immutable envelope, pinned read-only artifact paths only.

    No SQLite/open/ACTIVE validation pass or mutable ProjectStore reaches a worker.
    """

    def __init__(self, envelope):
        self.state = envelope["state"]
        self.manifest = envelope["manifest"]
        self.commit_id = envelope["commit_id"]
        self.root = Path(envelope["root"])
        self.paths = envelope["paths"]

    def path(self, uri):
        if uri not in ("sources", "snapshots"):
            relative(uri)
        if uri not in self.paths:
            raise ProjectError("Repro read-only artifact reference izinli değil.")
        return Path(self.paths[uri])


def calculate(action, request, work, control, opened_store=None):
    if action == "open":
        opened = open_bundle(request["archive"], control)
        return dict(
            manifest=opened["manifest"],
            lineage=opened["payload"]["lineage.json"],
            status=opened["status"],
            fingerprint=opened["bundle_fingerprint"],
        )
    if action == "rerun":
        opened = open_bundle(request["archive"], control)
        if opened["bundle_fingerprint"] != request["fingerprint"]:
            raise ProjectError("Seçili bundle değişti; yeniden açın.")
        result = rerun(
            request["archive"],
            request.get("data_project", ""),
            request["mode"],
            work,
            control,
            project_view=opened_store if request.get("data_project") else None,
        )
        path = Path(work) / "comparison.vureprotest"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name in (
                "comparison.json",
                "reference-report.json",
                "actual-report.json",
            ):
                z.write(Path(work) / name, name)
        receipt = publish(path, request["destination"], request["project"], control)
        return dict(comparison=result, receipt=receipt, status=result["status"])
    with (
        nullcontext(opened_store)
        if opened_store
        else closing(ProjectStore.open(request["project"], writable=False)) as store
    ):
        if store.commit_id != request["commit_id"]:
            raise ProjectError(
                "Proje commit değişti; lineage/redaction önizlemesini yenileyin."
            )
        if action == "preview":
            return preview(store, request["focus"], request["include_data"])
        if action == "bundle":
            return build(
                store,
                request["focus"],
                request["include_data"],
                request["preview_hash"],
                work,
                request["destination"],
                control,
            )
        raise ProjectError("Repro eylemi desteklenmiyor.")


def worker(action, request, work, cancel, connection, budget):
    try:
        store = (
            RecordedProject(request["project_view"])
            if "project_view" in request
            else None
        )
        apply_process_limits(budget)
        control = Control(cancel, budget=budget)
        control.check()
        value = calculate(action, request, work, control, store)
        if action in ("preview", "open"):
            control.check()
        connection.send(("result", value))
    except Canceled:
        connection.send(("canceled", None))
    except ProjectError as e:
        connection.send(("error", str(e)))
    except Exception as e:
        connection.send(
            (
                "error",
                "Repro işlem tamamlanmadı: "
                + type(e).__name__
                + "; eski kayıt korundu.",
            )
        )
    finally:
        connection.close()
