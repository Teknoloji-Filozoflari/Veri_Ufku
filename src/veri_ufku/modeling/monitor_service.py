"""Same immutable worker envelope for GUI, CLI and explicit loopback API."""

import multiprocessing as mp
import tempfile
import time
from pathlib import Path

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.admission import start
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.resources import rss_bytes
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError


def worker(request, spec, workspace, cancel, sender, budget):
    try:
        apply_process_limits(budget)
        from veri_ufku.modeling.monitoring import calculate

        sender.send(
            (
                "result",
                calculate(request, spec, workspace, Control(cancel, budget=budget)),
            )
        )
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
                    "Monitoring tamamlanamadı ("
                    + type(e).__name__
                    + "); önceki kayıt korundu.",
                ),
            )
        )
    finally:
        sender.close()


def run_headless(store, spec, cache, budget=None, cancel=None):
    import os

    from veri_ufku.storage.monitor_store import publish, request_for

    budget = budget or ComputeBudget()
    ctx = mp.get_context("spawn")
    cancel = cancel or ctx.Event()
    if store.read_only:
        raise ProjectError(
            "Batch scoring için yazılabilir proje gerekli; başka writer kapatılmalı."
        )
    cache = Path(cache).absolute()
    if cache.resolve().is_relative_to(Path(store.root).resolve()):
        raise ProjectError("Monitoring scratch proje dışında olmalı.")
    cache.mkdir(parents=True, exist_ok=True)
    request = request_for(store, store.state, spec)
    with tempfile.TemporaryDirectory(prefix="monitor-", dir=cache) as workspace:
        receiver, sender = ctx.Pipe(False)
        process = ctx.Process(
            target=worker, args=(request, spec, workspace, cancel, sender, budget)
        )
        try:
            start(process, budget)
            sender.close()
            started = time.monotonic()
            guard = Control(cancel, budget=budget)
            while not receiver.poll(0.05):
                if cancel.is_set():
                    raise Canceled()
                if not process.is_alive():
                    raise ProjectError("Monitoring worker eksik sonuçla durdu.")
                if (
                    time.monotonic() - started > budget.max_wall_seconds
                    or rss_bytes(os.getpid()) + rss_bytes(process.pid)
                    > budget.ram_bytes
                ):
                    raise ProjectError("Monitoring toplam süre/RAM bütçesini aştı.")
                guard.disk(workspace)
            kind, value = receiver.recv()
            if kind == "canceled" or cancel.is_set():
                raise Canceled()
            if kind == "error":
                raise ProjectError(value)
            return publish(store, store.state, value, Control(cancel, budget=budget))
        finally:
            if process.pid:
                process.join(0.1)
                if process.is_alive():
                    process.kill()
                    process.join(2)
            process.close()
            receiver.close()
            sender.close()
