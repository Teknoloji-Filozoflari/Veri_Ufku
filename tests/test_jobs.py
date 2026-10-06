import time
from dataclasses import replace

import pytest

from veri_ufku.domain.contracts import (
    Binding,
    ComputeBudget,
    DemoParameters,
    JobSpec,
    JobState,
)
from veri_ufku.jobs.manager import JobManager
from veri_ufku.logging_setup import EventLog


def wait_for(manager, ident, predicate=lambda s: s.state.terminal, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = manager.snapshot(ident)
        if predicate(snapshot):
            return snapshot
        time.sleep(0.01)
    raise AssertionError(
        f"Job did not reach expected state: {manager.snapshot(ident).state}"
    )


@pytest.fixture
def manager(tmp_path):
    instance = JobManager(tmp_path)
    yield instance
    assert instance.shutdown()
    assert not list((tmp_path / "jobs").glob("job-*"))


def spec(kind="demo.cpu", **parameters):
    return JobSpec(kind, Binding("dv:fixture", 2), DemoParameters(**parameters))


def test_process_result_and_bound_provenance(manager):
    request = spec(units=3, chunk_size=10, pause_seconds=0)
    ident = manager.submit(request)
    snapshot = wait_for(manager, ident)
    assert snapshot.state == JobState.SUCCEEDED
    # Independent hand-computed sum 0..29: 30*29/2, not a second library call.
    assert snapshot.result.value == 435
    assert snapshot.worker_pid != __import__("os").getpid()
    assert snapshot.result.provenance.dataset_versions == ("dv:fixture",)
    assert snapshot.result.provenance.config_revision == 2
    assert snapshot.result_for(Binding("dv:other", 2)) is None
    assert snapshot.result_for(Binding("dv:fixture", 3)) is None
    assert snapshot.result_for(request.binding).value == 435


@pytest.mark.parametrize("kind", ["demo.cpu", "demo.io"])
def test_cancel_removes_workspaces_and_never_returns_result(manager, kind):
    ident = manager.submit(spec(kind, units=100, chunk_size=1000))
    wait_for(manager, ident, lambda s: s.state == JobState.RUNNING)
    assert manager.cancel(ident)
    snapshot = wait_for(manager, ident)
    assert snapshot.state == JobState.CANCELED
    assert snapshot.result is None
    assert snapshot.ended_at - snapshot.cancel_requested_at < 2
    assert not manager.cancel(ident)


def test_queued_cancel_and_concurrency_limit(manager):
    first = manager.submit(spec(units=50, chunk_size=100))
    wait_for(manager, first, lambda s: s.state == JobState.RUNNING)
    second = manager.submit(spec(units=1, chunk_size=10))
    assert manager.snapshot(second).state == JobState.QUEUED
    manager.cancel(second)
    assert manager.snapshot(second).state == JobState.CANCELED
    manager.cancel(first)
    wait_for(manager, first)
    assert manager.peak_cpu_jobs <= 1


def test_unknown_progress_is_not_a_fake_percentage(manager):
    ident = manager.submit(spec("demo.unknown", units=30))
    snapshot = wait_for(manager, ident, lambda s: s.progress.done >= 1)
    assert snapshot.progress.total is None
    manager.cancel(ident)
    wait_for(manager, ident)


def test_disk_and_time_budgets_fail_safely(manager):
    request = replace(
        spec("demo.io", units=10), budget=ComputeBudget(temp_disk_bytes=4096)
    )
    ident = manager.submit(request)
    snapshot = wait_for(manager, ident)
    assert snapshot.state == JobState.FAILED
    assert snapshot.error.code == "budget"
    assert snapshot.result is None
    request = replace(spec(units=100), budget=ComputeBudget(max_wall_seconds=0.05))
    ident = manager.submit(request)
    snapshot = wait_for(manager, ident)
    assert snapshot.state == JobState.FAILED
    assert snapshot.error.code == "budget"


def test_failure_redacts_exception_text_and_logs_reference(tmp_path):
    log = EventLog(tmp_path)
    manager = JobManager(tmp_path, event_log=log)
    try:
        ident = manager.submit(spec("demo.failure", units=1))
        snapshot = wait_for(manager, ident)
        assert snapshot.error.code == "worker"
        assert snapshot.error.exception_type == "RuntimeError"
        text = (tmp_path / "application.log").read_text()
        assert snapshot.error.correlation_id in text
        assert "Sensitive sample value" not in text
        assert "RuntimeError" in text
        assert snapshot.result is None
    finally:
        assert manager.shutdown()
        log.close()


def test_shutdown_cancels_cpu_io_and_queue(manager):
    ids = [
        manager.submit(spec(kind, units=100))
        for kind in ["demo.cpu", "demo.io", "demo.cpu"]
    ]
    wait_for(manager, ids[0], lambda s: s.state == JobState.RUNNING)
    assert manager.shutdown()
    assert all(manager.snapshot(ident).state == JobState.CANCELED for ident in ids)
    with pytest.raises(RuntimeError, match="closing"):
        manager.submit(spec())


def test_unsupported_capability_and_invalid_budget_rejected(manager):
    with pytest.raises(ValueError, match="Unsupported"):
        manager.submit(spec("file.supplied.python"))
    with pytest.raises(ValueError):
        ComputeBudget(ram_bytes=0)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "2048", 1.5])
def test_invalid_integer_budget_is_rejected(value):
    with pytest.raises(ValueError):
        ComputeBudget(ram_bytes=value)


def test_shutdown_process_termination_bound(manager):
    request = replace(
        spec(units=1000, chunk_size=1_000_000, pause_seconds=0),
        budget=ComputeBudget(cancel_grace_ms=1),
    )
    ident = manager.submit(request)
    wait_for(manager, ident, lambda s: s.progress.done >= 1)
    manager.cancel(ident)
    snap = wait_for(manager, ident)
    assert snap.state == JobState.CANCELED
    assert snap.ended_at - snap.cancel_requested_at < 2
    assert snap.result is None


def test_ram_admission_fails_without_spawning(manager):
    request = replace(spec(), budget=ComputeBudget(ram_bytes=1))
    ident = manager.submit(request)
    snapshot = wait_for(manager, ident)
    assert snapshot.state == JobState.FAILED
    assert snapshot.error.code == "budget"
    assert snapshot.worker_pid is None


def test_scratch_reservation_queues_jobs_instead_of_overcommitting(tmp_path):
    budget = ComputeBudget(temp_disk_bytes=16_384)
    instance = JobManager(tmp_path, budget)
    try:
        request = JobSpec(
            "demo.io", Binding("dv:fixture", 0), DemoParameters(units=4), budget
        )
        first = instance.submit(request)
        wait_for(instance, first, lambda s: s.state == JobState.RUNNING)
        second = instance.submit(request)
        assert instance.snapshot(second).state == JobState.QUEUED
        assert wait_for(instance, first).state == JobState.SUCCEEDED
        assert wait_for(instance, second).result.value == 16_384
        assert instance.peak_io_jobs == 1
    finally:
        assert instance.shutdown()


def test_supervisor_filesystem_failure_stops_workers_safely(manager, monkeypatch):
    import veri_ufku.jobs.manager as module

    ident = manager.submit(spec(units=100))
    wait_for(manager, ident, lambda s: s.state == JobState.RUNNING)

    def failing_probe(_path):
        raise OSError("private-filesystem-value")

    monkeypatch.setattr(module, "workspace_bytes", failing_probe)
    snapshot = wait_for(manager, ident)
    assert snapshot.state == JobState.FAILED
    assert snapshot.result is None
    assert snapshot.error.exception_type == "OSError"
    assert manager.shutdown()
