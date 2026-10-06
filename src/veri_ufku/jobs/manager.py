"""Qt-free supervisor: bounded I/O threads and spawn CPU processes."""

import hashlib
import json
import multiprocessing
import os
import queue
import shutil
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import uuid4

from veri_ufku.domain.capabilities import get_capability
from veri_ufku.domain.contracts import (
    AppError,
    ComputeBudget,
    ExecutionKind,
    JobResult,
    JobSnapshot,
    JobState,
    Progress,
    Provenance,
)
from veri_ufku.jobs.workers import BudgetExceeded, Canceled, process_entry, run_fixture
from veri_ufku.storage.workspace import (
    create_workspace,
    remove_workspace,
    workspace_bytes,
)


def rss_bytes(pid):
    try:
        with open(f"/proc/{pid}/statm") as file:
            return int(file.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        return 0


@dataclass
class _Record:
    snapshot: JobSnapshot
    workspace: object = None
    runner: object = None
    cancel: object = None
    receiver: object = None
    messages: object = None
    outcome: object = None
    forced_error: object = None


class JobManager:
    def __init__(self, cache, budget=ComputeBudget(), event_log=None):
        self.cache = cache
        self.cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.budget = budget
        self.log = event_log
        self._ctx = multiprocessing.get_context("spawn")
        self._records = {}
        self._dirty = set()
        self._lock = threading.RLock()
        self._closing = False
        self._stopped = threading.Event()
        self.peak_rss_bytes = rss_bytes(os.getpid())
        self.peak_temp_bytes = 0
        self.peak_cpu_jobs = 0
        self.peak_io_jobs = 0
        self._thread = threading.Thread(
            target=self._supervise, name="veri-ufku-supervisor", daemon=False
        )
        self._thread.start()

    def submit(self, spec):
        get_capability(spec.capability_id)
        for name in (
            "ram_bytes",
            "temp_disk_bytes",
            "cpu_threads",
            "max_concurrent_cpu_jobs",
            "max_concurrent_io_jobs",
            "max_wall_seconds",
            "sample_limit_rows",
            "cancel_grace_ms",
        ):
            if getattr(spec.budget, name) > getattr(self.budget, name):
                raise ValueError("Requested budget exceeds manager budget")
        with self._lock:
            if self._closing:
                raise RuntimeError("Manager is closing")
            pending = [
                r for r in self._records.values() if not r.snapshot.state.terminal
            ]
            if len(pending) >= 32:
                raise ValueError("Job queue is full")
            # Bounded in-memory history; remove oldest terminal entries only.
            if len(self._records) >= 64:
                for ident, record in list(self._records.items()):
                    if record.snapshot.state.terminal:
                        del self._records[ident]
                        self._dirty.discard(ident)
                        break
            ident = str(uuid4())
            provenance = Provenance(
                str(uuid4()),
                (spec.binding.dataset_version,),
                spec.binding.config_revision,
                spec.capability_id,
                hashlib.sha256(
                    json.dumps(asdict(spec.parameters), sort_keys=True).encode()
                ).hexdigest(),
                (("python", sys.version.split()[0]), ("application", "0.1.0")),
                datetime.now(UTC).isoformat(),
            )
            snapshot = JobSnapshot(
                ident,
                spec,
                JobState.QUEUED,
                Progress("queued"),
                None,
                None,
                provenance,
                time.monotonic(),
                None,
                None,
                None,
                None,
                0,
                0,
            )
            self._records[ident] = _Record(snapshot)
            self._dirty.add(ident)
            self.record_event("submitted", ident)
            return ident

    def record_event(self, event, ident, error=None):
        if self.log:
            self.log.event(event, ident, error)

    def _update(self, record, **changes):
        from dataclasses import replace

        record.snapshot = replace(record.snapshot, **changes)
        self._dirty.add(record.snapshot.job_id)

    def snapshot(self, ident):
        with self._lock:
            return self._records[ident].snapshot

    def drain_updates(self):
        with self._lock:
            snapshots = [self._records[ident].snapshot for ident in self._dirty]
            self._dirty.clear()
            return snapshots

    def cancel(self, ident):
        with self._lock:
            record = self._records[ident]
            if record.snapshot.state.terminal:
                return False  # explicit too-late cancellation; no result mutation
            if record.snapshot.state == JobState.QUEUED:
                self._update(
                    record,
                    state=JobState.CANCELED,
                    ended_at=time.monotonic(),
                    cancel_requested_at=time.monotonic(),
                )
                self.record_event("canceled", ident)
                return True
            if record.snapshot.cancel_requested_at is None:
                self._update(
                    record,
                    state=JobState.CANCEL_REQUESTED,
                    cancel_requested_at=time.monotonic(),
                )
                record.cancel.set()
            return True

    def request_shutdown(self):
        with self._lock:
            self._closing = True
            for ident in list(self._records):
                self.cancel(ident)

    @property
    def closed(self):
        return self._stopped.is_set()

    def shutdown(self, timeout=5):
        self.request_shutdown()
        self._thread.join(timeout)
        return self.closed

    def _io_entry(self, spec, workspace, cancel, messages):
        try:
            value = run_fixture(
                spec.capability_id,
                spec.parameters,
                spec.budget,
                workspace,
                cancel,
                lambda p: messages.put(("progress", p)),
            )
            messages.put(("result", value))
        except Canceled:
            messages.put(("canceled", None))
        except (BudgetExceeded, MemoryError) as error:
            messages.put(("error", ("budget", type(error).__name__)))
        except Exception as error:
            messages.put(("error", ("worker", type(error).__name__)))

    def _start(self, record, execution):
        spec = record.snapshot.spec
        required_temp = (
            0 if execution == ExecutionKind.CPU else spec.parameters.units * 4096
        )
        if required_temp > spec.budget.temp_disk_bytes:
            self._finish(record, "error", ("budget", "TemporaryDiskAdmission"))
            return
        reserved = sum(
            r.snapshot.spec.parameters.units * 4096
            for r in self._records.values()
            if r.runner
            and not r.snapshot.state.terminal
            and get_capability(r.snapshot.spec.capability_id).execution
            == ExecutionKind.IO
        )
        if reserved + required_temp > self.budget.temp_disk_bytes:
            return  # stay queued until other registered I/O fixtures release reservations
        if (
            shutil.disk_usage(self.cache).free
            < max(spec.budget.reserve_disk_bytes, self.budget.reserve_disk_bytes)
            + required_temp
            or rss_bytes(os.getpid()) > spec.budget.ram_bytes
        ):
            self._finish(record, "error", ("budget", "Admission"))
            return
        try:
            record.workspace = create_workspace(self.cache)
            if execution == ExecutionKind.CPU:
                record.cancel = self._ctx.Event()
                receiver, sender = self._ctx.Pipe(duplex=False)
                record.receiver = receiver
                record.runner = self._ctx.Process(
                    target=process_entry,
                    args=(spec, str(record.workspace), record.cancel, sender),
                    name="veri-ufku-cpu",
                )
                record.runner.start()
                sender.close()
                pid = record.runner.pid
            else:
                record.cancel = threading.Event()
                record.messages = queue.SimpleQueue()
                record.runner = threading.Thread(
                    target=self._io_entry,
                    args=(spec, str(record.workspace), record.cancel, record.messages),
                    name="veri-ufku-io",
                    daemon=False,
                )
                record.runner.start()
                pid = os.getpid()
            self._update(
                record,
                state=JobState.RUNNING,
                progress=Progress("starting"),
                started_at=time.monotonic(),
                worker_pid=pid,
            )
            self.record_event("started", record.snapshot.job_id)
        except Exception as error:
            self._finish(record, "error", ("worker", type(error).__name__))

    def _messages(self, record):
        for _ in range(1024):
            try:
                if record.receiver:
                    if not record.receiver.poll():
                        break
                    message = record.receiver.recv()
                else:
                    message = record.messages.get_nowait()
            except (EOFError, OSError, queue.Empty):
                break
            kind, payload = message
            if kind == "progress":
                self._update(record, progress=payload)
            else:
                record.outcome = message

    def _finish(self, record, kind, payload):
        error, result = None, None
        if record.forced_error:
            state, error = JobState.FAILED, record.forced_error
        elif record.snapshot.cancel_requested_at is not None or kind == "canceled":
            state = JobState.CANCELED
        elif kind == "result":
            state = JobState.SUCCEEDED
            result = JobResult(
                str(uuid4()),
                record.snapshot.spec.binding,
                payload,
                record.snapshot.provenance,
            )
        else:
            state = JobState.FAILED
            error = AppError.create(*payload)
        if record.receiver:
            record.receiver.close()
        if isinstance(record.runner, multiprocessing.process.BaseProcess):
            if record.runner.pid is not None:
                record.runner.join(0)
            record.runner.close()
        if record.workspace:
            try:
                remove_workspace(record.workspace)
            except OSError as failure:
                state, result = JobState.FAILED, None
                error = AppError.create("cleanup", type(failure).__name__)
        self._update(
            record, state=state, result=result, error=error, ended_at=time.monotonic()
        )
        self.record_event(state.value, record.snapshot.job_id, error)

    def _supervise(self):
        try:
            while True:
                with self._lock:
                    running = [
                        r
                        for r in self._records.values()
                        if r.runner and not r.snapshot.state.terminal
                    ]
                    total_rss = rss_bytes(os.getpid()) + sum(
                        rss_bytes(r.snapshot.worker_pid)
                        for r in running
                        if get_capability(r.snapshot.spec.capability_id).execution
                        == ExecutionKind.CPU
                    )
                    total_disk = sum(
                        workspace_bytes(r.workspace) for r in running if r.workspace
                    )
                    self.peak_rss_bytes = max(self.peak_rss_bytes, total_rss)
                    self.peak_temp_bytes = max(self.peak_temp_bytes, total_disk)
                    counts = {
                        kind: sum(
                            get_capability(r.snapshot.spec.capability_id).execution
                            == kind
                            for r in running
                        )
                        for kind in ExecutionKind
                    }
                    self.peak_cpu_jobs = max(
                        self.peak_cpu_jobs, counts[ExecutionKind.CPU]
                    )
                    self.peak_io_jobs = max(self.peak_io_jobs, counts[ExecutionKind.IO])
                    for record in running:
                        self._messages(record)
                        snap = record.snapshot
                        self._update(
                            record,
                            peak_rss_bytes=max(snap.peak_rss_bytes, total_rss),
                            peak_temp_bytes=max(
                                snap.peak_temp_bytes, workspace_bytes(record.workspace)
                            ),
                        )
                        now = time.monotonic()
                        if (
                            now - snap.started_at > snap.spec.budget.max_wall_seconds
                            or total_rss > snap.spec.budget.ram_bytes
                            or total_disk
                            > min(
                                snap.spec.budget.temp_disk_bytes,
                                self.budget.temp_disk_bytes,
                            )
                        ):
                            record.forced_error = AppError.create(
                                "budget", "ResourceLimit"
                            )
                            self.cancel(snap.job_id)
                        if (
                            snap.cancel_requested_at is not None
                            and now - snap.cancel_requested_at
                            > snap.spec.budget.cancel_grace_ms / 1000
                        ):
                            if (
                                isinstance(
                                    record.runner, multiprocessing.process.BaseProcess
                                )
                                and record.runner.is_alive()
                            ):
                                record.runner.terminate()
                        if not record.runner.is_alive():
                            # Drain final messages before deciding, including quick exit.
                            self._messages(record)
                            kind, payload = record.outcome or (
                                "error",
                                ("worker", "WorkerExit"),
                            )
                            self._finish(record, kind, payload)
                    for record in self._records.values():
                        if record.snapshot.state != JobState.QUEUED:
                            continue
                        execution = get_capability(
                            record.snapshot.spec.capability_id
                        ).execution
                        limit = min(
                            getattr(
                                self.budget, f"max_concurrent_{execution.value}_jobs"
                            ),
                            getattr(
                                record.snapshot.spec.budget,
                                f"max_concurrent_{execution.value}_jobs",
                            ),
                        )
                        if counts[execution] < limit:
                            self._start(record, execution)
                            if record.snapshot.state == JobState.RUNNING:
                                counts[execution] += 1
                    if self._closing and all(
                        r.snapshot.state.terminal for r in self._records.values()
                    ):
                        break
                time.sleep(0.01)
        except Exception as failure:
            # A supervisor/filesystem failure must not strand workers or expose raw exception text.
            with self._lock:
                self._closing = True
                for record in self._records.values():
                    if record.snapshot.state.terminal:
                        continue
                    record.forced_error = AppError.create(
                        "worker", type(failure).__name__
                    )
                    if record.runner:
                        record.cancel.set()
                        if (
                            isinstance(
                                record.runner, multiprocessing.process.BaseProcess
                            )
                            and record.runner.is_alive()
                        ):
                            record.runner.terminate()
                        record.runner.join(self.budget.cancel_grace_ms / 1000)
                        if record.runner.is_alive():
                            if isinstance(
                                record.runner, multiprocessing.process.BaseProcess
                            ):
                                record.runner.kill()
                                record.runner.join(1)
                            else:
                                continue  # do not delete a workspace still owned by a live thread
                    self._finish(record, "error", ("worker", type(failure).__name__))
        finally:
            if all(r.snapshot.state.terminal for r in self._records.values()):
                self._stopped.set()
