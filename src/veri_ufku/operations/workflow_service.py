"""Shared launch envelope for desktop and headless workflow runner."""

import copy
import multiprocessing as mp
import os
import tempfile
import time
import uuid
from pathlib import Path

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, configure_threads
from veri_ufku.jobs.manager import rss_bytes
from veri_ufku.jobs.workers import Canceled
from veri_ufku.operations.workflow import references
from veri_ufku.operations.workflow_contracts import DAGSpec
from veri_ufku.storage.experiment_store import capture
from veri_ufku.storage.neural_store import publish
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.validation_store import prior_uses


def request_for(
    store,
    state,
    spec,
    cache,
    output_dir="",
    allow_export=False,
    dry_run=False,
    export_token="",
):
    spec = DAGSpec.from_dict(spec)
    roots = references(store, state)
    source = next((n for n in spec.nodes if n["kind"] == "source"), None)
    if not source or source["params"].get("version_id") not in roots:
        raise ProjectError("DAG bir yerel source node gerektirir.")
    cache = Path(cache).absolute()
    project = Path(store.root).resolve()
    if cache.resolve().is_relative_to(project):
        raise ProjectError("Workflow cache proje dışında olmalı.")
    if type(allow_export) is not bool or type(dry_run) is not bool:
        raise ProjectError("Workflow explicit action flags geçersiz.")
    if allow_export:
        p = Path(output_dir).absolute()
        if (
            not p.is_dir()
            or p.resolve() != p
            or p.is_relative_to(project)
            or p.is_relative_to(cache.resolve())
        ):
            raise ProjectError(
                "Export directory var olan, gerçek, proje/cache dışında yerel dizin olmalı."
            )
        output_dir = str(p)
    elif not dry_run and any(n["kind"] == "export" for n in spec.nodes):
        raise ProjectError("Export için açık allow_export gerekir.")
    token = export_token or str(uuid.uuid4())
    try:
        if str(uuid.UUID(token)) != token:
            raise ValueError()
    except (ValueError, AttributeError):
        raise ProjectError("Export idempotency token canonical UUID olmalı.") from None
    r = copy.deepcopy(roots[source["params"]["version_id"]])
    r.update(
        run_id="run:" + uid(),
        origin_version=r["version_id"],
        workflow_sources=roots,
        workflow_runtime=dict(
            cache=str(cache),
            output_dir=output_dir,
            allow_export=allow_export,
            dry_run=dry_run,
            export_token=token,
        ),
        prior_test_use_ids=prior_uses(state),
        experiment_capture=capture(dict(workflow_spec=spec.data())),
    )
    return r


def worker(
    request,
    parameters,
    workspace,
    cancel,
    connection,
    budget,
    action="train",
    model=None,
):
    try:
        from veri_ufku.operations.workflow import calculate

        apply_process_limits(budget)
        c = Control(cancel, budget=budget)
        value = calculate(request, parameters, workspace, c)
        connection.send(("result", value))
    except Canceled:
        connection.send(("canceled", None))
    except ProjectError as e:
        connection.send(("error", str(e)))
    except Exception as e:
        connection.send(
            (
                "error",
                "DAG worker tamamlanmadı: " + type(e).__name__ + "; kaynak korundu.",
            )
        )
    finally:
        connection.close()


def run_headless(
    store,
    spec,
    cache,
    output_dir="",
    allow_export=False,
    dry_run=False,
    export_token="",
    budget=None,
    cancel=None,
):
    budget = budget or ComputeBudget()
    ctx = mp.get_context("spawn")
    event = cancel or ctx.Event()
    request = request_for(
        store, store.state, spec, cache, output_dir, allow_export, dry_run, export_token
    )
    configure_threads(budget.worker_threads)
    with tempfile.TemporaryDirectory(prefix="vu-dag-cli-") as work:
        parent, child = ctx.Pipe()
        process = ctx.Process(
            target=worker, args=(request, spec, work, event, child, budget)
        )
        process.start()
        child.close()
        started = time.monotonic()
        cancel_at = None
        try:
            while process.is_alive() or parent.poll():
                if (
                    time.monotonic() - started > budget.max_wall_seconds
                    or rss_bytes(os.getpid()) + rss_bytes(process.pid)
                    > budget.ram_bytes
                ):
                    event.set()
                if event.is_set():
                    cancel_at = cancel_at or time.monotonic()
                    if time.monotonic() - cancel_at > budget.cancel_grace_ms / 1000:
                        process.kill()
                        raise ProjectError(
                            "DAG CLI iptal/timeout: son published sonuç korundu."
                        )
                if parent.poll(0.025):
                    try:
                        kind, value = parent.recv()
                    except EOFError:
                        break
                    if kind == "result":
                        # Parent only publishes. Child never receives a ProjectStore/Qt object.
                        state = publish(store, store.state, value)
                        return state
                    raise ProjectError(
                        value if kind == "error" else "DAG canceled; başarı sayılmadı."
                    )
            raise ProjectError("DAG worker sonuç üretmedi; başarılı sayılmadı.")
        finally:
            if process.is_alive():
                process.kill()
            process.join(timeout=2)
            parent.close()
