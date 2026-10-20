"""Phase66 real process admission, quota, allocation and optional chunk backend."""

import multiprocessing as mp
from dataclasses import replace

import pytest

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Canceled, Control
from veri_ufku.jobs.admission import capacity, start
from veri_ufku.jobs.dask_backend import RemotePlan, available, parquet_summary
from veri_ufku.jobs.memory import (
    checked_dense,
    dense_bytes,
    device_plan,
    spill_directory,
)
from veri_ufku.jobs.resources import process_identity, process_tree
from veri_ufku.storage.project_model import ProjectError


def wait_worker(event):
    event.wait(10)


def test_joint_process_and_native_threads():
    ctx = mp.get_context("spawn")
    budget = ComputeBudget(
        cpu_threads=2, threads_per_process=1, max_processes=3, max_concurrent_cpu_jobs=3
    )
    if budget.cpu_threads < 2:
        pytest.skip("fixture requires two visible CPUs")
    event = ctx.Event()
    processes = [ctx.Process(target=wait_worker, args=(event,)) for _ in range(3)]
    try:
        start(processes[0], budget)
        start(processes[1], budget)
        assert not capacity(budget)
        with pytest.raises(ValueError, match="thread"):
            start(processes[2], budget)
        assert processes[2].pid is None
        assert processes[0].pid in process_tree(processes[0].pid)
        assert process_identity(processes[0].pid)
    finally:
        event.set()
        for p in processes:
            if p.pid:
                p.join(5)
                if p.is_alive():
                    p.kill()
                    p.join()
            p.close()
    assert capacity(budget)


def test_process_limit_independent_of_threads():
    ctx = mp.get_context("spawn")
    event = ctx.Event()
    p = ctx.Process(target=wait_worker, args=(event,))
    b = ComputeBudget(cpu_threads=2, max_processes=1)
    try:
        start(p, b)
        assert not capacity(b)
    finally:
        event.set()
        p.join(5)
        p.close()


def test_spill_quota_cleanup_and_cancel(tmp_path):
    control = Control(budget=ComputeBudget(temp_disk_bytes=8, reserve_disk_bytes=1))
    with pytest.raises(ProjectError, match="disk"):
        with spill_directory(tmp_path, control) as spill:
            (spill / "chunk").write_bytes(b"a" * 9)
    assert list(tmp_path.iterdir()) == []
    event = mp.get_context("spawn").Event()
    with pytest.raises(Canceled):
        with spill_directory(tmp_path, Control(cancel=event)):
            event.set()
    assert list(tmp_path.iterdir()) == []


def test_no_implicit_sparse_dense(monkeypatch):
    from scipy.sparse import csr_matrix

    matrix = csr_matrix([[1.0, 0], [0, 2.0]])
    with pytest.raises(ProjectError, match="açık"):
        checked_dense(matrix, ComputeBudget())
    monkeypatch.setattr("veri_ufku.jobs.resources.rss_bytes", lambda _: 0)
    with pytest.raises(ProjectError, match="RAM"):
        checked_dense(matrix, ComputeBudget(ram_bytes=8), explicit=True)
    assert checked_dense(
        matrix, ComputeBudget(ram_bytes=128), explicit=True
    ).tolist() == [[1, 0], [0, 2]]
    assert dense_bytes((10**9, 10**9)) == 16 * 10**18


def test_device_transfer_and_no_silent_fallback():
    b = ComputeBudget(device="cuda:0", device_memory_bytes=100, transfer_bytes=50)
    with pytest.raises(ProjectError, match="fallback"):
        device_plan(b)
    with pytest.raises(ProjectError, match="VRAM"):
        device_plan(b, supports_gpu=True, transfer_bytes=51, available_bytes=100)
    assert (
        device_plan(b, supports_gpu=True, transfer_bytes=40, available_bytes=100)[
            "device"
        ]
        == "cuda:0"
    )


def test_remote_preview_never_connects():
    p = RemotePlan(
        "tls://cluster.example:8786", "user configured site", "keyring-ref", 32
    )
    assert p.preview(ComputeBudget())["available"] is False
    for endpoint in (
        "tcp://cluster:8786",
        "tls://user:secret@cluster:8786",
        "tls://cluster:8786/?token=secret",
    ):
        with pytest.raises(ProjectError):
            replace(p, endpoint=endpoint).preview(ComputeBudget())


def test_real_optional_dask_chunk_summary(tmp_path):
    if not available():
        pytest.skip("Dask absent: runtime NOT validated")
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = tmp_path / "source.parquet"
    pq.write_table(pa.table({"value": [1.0, 2.0, None, float("nan"), 3.0, 4.0]}), path)
    before = path.read_bytes()
    result = parquet_summary(path, "value", Control(), chunk_rows=2)
    assert (result["n"], result["excluded"], result["total"], result["chunks"]) == (
        4,
        2,
        10.0,
        3,
    )
    assert path.read_bytes() == before
    assert result["transfer_bytes"] == 0


def test_missing_backend_safe(monkeypatch, tmp_path):
    monkeypatch.setattr("veri_ufku.jobs.dask_backend.available", lambda: False)
    with pytest.raises(ProjectError, match="kurulu değil"):
        parquet_summary(tmp_path / "absent", "value", Control())


def test_shared_limits_not_relaxed():
    b = ComputeBudget()
    assert b.ram_bytes == 2 * 1024**3
    assert b.temp_disk_bytes == 4 * 1024**3
    assert b.max_wall_seconds == 600
    assert b.max_processes == 1
    assert b.worker_threads <= b.cpu_threads
    for value in (0, -1, True, 1.5):
        with pytest.raises(ValueError):
            ComputeBudget(max_tasks=value)


def test_pidfd_cancel_only_matching_owned_process():
    from veri_ufku.jobs.resources import terminate_identity

    ctx = mp.get_context("spawn")
    event = ctx.Event()
    p = ctx.Process(target=wait_worker, args=(event,))
    p.start()
    try:
        identity = process_identity(p.pid)
        assert identity
        terminate_identity(p.pid, "different-start-time")
        assert p.is_alive()
        terminate_identity(p.pid, identity)
        p.join(5)
        assert not p.is_alive() and p.exitcode != 0
    finally:
        if p.is_alive():
            p.kill()
            p.join()
        p.close()
