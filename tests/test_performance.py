"""Resource faults must preserve immutable commits; bounded/native contracts."""

import errno
import multiprocessing as mp
import os
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest
from test_dataset import column, prepare
from test_import_gui import setup, spin, teardown
from test_preparation import request, specification

from veri_ufku.analytics.cache import PageCache, page_key
from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import page
from veri_ufku.analytics.worker import process_entry
from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import resource_error_text
from veri_ufku.modeling.baseline import calculate
from veri_ufku.modeling.preparation import calculate as preparation
from veri_ufku.modeling.validation import ValidationSpec
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def test_nested_disk_limit_and_real_resource_messages(tmp_path, monkeypatch):
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "spill").write_bytes(b"a" * 100)
    control = Control(
        budget=replace(ComputeBudget(), temp_disk_bytes=50, reserve_disk_bytes=1)
    )
    with pytest.raises(ProjectError, match="disk"):
        control.disk(tmp_path, force=True)
    for error, expected in (
        (MemoryError(), "Bellek"),
        (OSError(errno.ENOMEM, "x"), "Bellek"),
        (OSError(errno.ENOSPC, "x"), "Disk"),
        (OSError(errno.EDQUOT, "x"), "Disk"),
    ):
        assert resource_error_text(error, "fallback").startswith(expected)
    assert resource_error_text(ValueError(), "fallback") == "fallback"
    monkeypatch.setattr("veri_ufku.jobs.resources.rss_bytes", lambda pid: 100)
    with pytest.raises(ProjectError, match="bellek"):
        Control(budget=replace(ComputeBudget(), ram_bytes=10)).check()


def test_lru_bounds_binding_and_cached_source_tamper(tmp_path):
    cache = PageCache(pages=3, bytes_limit=10000)
    for i in range(30):
        cache.put(str(i), {"rows": [[str(i)]]})
    assert len(cache.entries) == 3 and cache.get("0") is None
    cache.put("too-large", {"rows": [["x" * 20000]]})
    assert cache.get("too-large") is None and cache.bytes <= 10000
    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1, 2]}))
    with closing(store):
        parameters = dict(view=ViewSpec().data(), offset=0)
        assert page_key(r, parameters) != page_key(
            dict(r, version_id="changed"), parameters
        )
        cached = page(r, ViewSpec())
        path = Path(r["path"])
        path.write_bytes(path.read_bytes() + b"tamper")
        context = mp.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        cancel = context.Event()
        process = context.Process(
            target=process_entry,
            args=(
                "page",
                dict(
                    r, path=r["path"].replace("/proc/self/", f"/proc/{os.getpid()}/", 1)
                ),
                dict(parameters, cached_page=cached),
                str(work),
                cancel,
                sender,
                ComputeBudget(),
            ),
        )
        process.start()
        sender.close()
        messages = []
        while receiver.poll(10):
            try:
                messages.append(receiver.recv())
            except EOFError:
                break
        process.join(10)
        assert not process.is_alive()
        assert any(kind == "error" for kind, _ in messages)
        assert not any(kind == "result" for kind, _ in messages)
        receiver.close()
        process.close()


def test_model_projection_forecast_and_compact_fit_membership(tmp_path, monkeypatch):
    store, _, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "x": list(range(120)),
                "y": list(range(120)),
                "unused": ["large unrelated text " * 100] * 120,
            }
        ),
    )
    with closing(store):
        r = request(store)
        spec = specification(r, family="linear")
        p = preparation(r, spec, work)
        assert p["provenance"]["help_content_version"] == 33
        assert p["resource_forecast"]["selected_features"] == 1
        assert p["resource_forecast"]["streaming_fit"] is False
        original = pl.read_parquet
        selections = []

        def spy(source, *args, **kwargs):
            if str(source) == r["path"]:
                selections.append(kwargs.get("columns"))
            return original(source, *args, **kwargs)

        monkeypatch.setattr(pl, "read_parquet", spy)
        out = calculate(
            dict(r, preparation=p),
            ValidationSpec(
                prediction_moment="Before",
                availability={column(r, "x"): dict(offset_seconds=0, note="known")},
            ).data(),
            work,
        )
        assert selections and all("unused" not in selected for selected in selections)
        assert out["model_package"]["fingerprint"]["size"] < 100000
        assert out["model_card"]["fit_row_ids"] == out["evaluations"][0]["fit_row_ids"]


def test_enospc_transaction_keeps_active_and_reopens(tmp_path):
    store, _, _ = prepare(tmp_path, pl.DataFrame({"x": [1, 2]}))
    root = store.root
    before = (root / "ACTIVE").read_bytes()
    store.state["name"] = "unpublished"

    def disk_full(point):
        if point == "manifest_written":
            raise OSError(errno.ENOSPC, "Injected disk full")

    with pytest.raises(OSError):
        store.save(checkpoint=disk_full)
    assert (root / "ACTIVE").read_bytes() == before
    store.close()
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state["name"] != "unpublished"
        assert len(reopened.state["datasets"]) == 1


def test_real_gui_aggregate_memory_cancel_and_shared_admission(tmp_path, monkeypatch):
    app, window, bridge, projects, imports = setup(tmp_path, monkeypatch)
    source = tmp_path / "large.csv"
    source.write_text("x,y\n" + "1,2\n" * 100000)
    engine = app._veri_ufku_resources[0]
    supervisor = engine._resource_supervisor
    try:
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        assert imports.ready
        before = (projects.store.root / "ACTIVE").read_bytes()
        workspace = Path(imports.workspace)
        imports.importData()
        bridge.start("demo.cpu")
        assert not bridge._active
        supervisor.budget = replace(ComputeBudget(), ram_bytes=1)
        supervisor.poll()
        spin(app, lambda: not imports.busy)
        assert "bellek" in imports.errorText.lower()
        assert not workspace.exists()
        assert before == (projects.store.root / "ACTIVE").read_bytes()
        assert supervisor.peak_cpu_jobs == 1
        bridge.start("demo.cpu")
        assert bridge._active and projects.busy
        bridge.cancel()
        spin(app, lambda: not bridge._active)
        supervisor.budget = ComputeBudget()
        imports.choose(str(source))
        spin(app, lambda: not imports.busy)
        workspace = Path(imports.workspace)
        imports.importData()
        supervisor.budget = replace(
            ComputeBudget(), temp_disk_bytes=1, reserve_disk_bytes=1
        )
        supervisor.poll()
        spin(app, lambda: not imports.busy)
        assert "disk" in imports.errorText.lower()
        assert not workspace.exists()
        assert before == (projects.store.root / "ACTIVE").read_bytes()
    finally:
        teardown(app, window)


def _native_probe(connection):
    from threadpoolctl import threadpool_info

    from veri_ufku.jobs.limits import apply_process_limits

    apply_process_limits(ComputeBudget(cpu_threads=2))
    import numpy as np

    np.ones((20, 20)) @ np.ones((20, 20))
    connection.send(
        dict(
            affinity=len(os.sched_getaffinity(0)),
            pools=threadpool_info(),
            polars=pl.thread_pool_size(),
        )
    )
    connection.close()


def test_actual_native_thread_pools_are_bounded(monkeypatch):
    from veri_ufku.jobs.limits import configure_threads

    configure_threads(2)
    context = mp.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_native_probe, args=(sender,))
    process.start()
    sender.close()
    assert receiver.poll(15)
    result = receiver.recv()
    process.join(10)
    assert result["affinity"] <= 2 and result["polars"] == 2
    assert all(p["num_threads"] <= 2 for p in result["pools"])
    assert process.exitcode == 0
    receiver.close()
    process.close()


def test_excessive_configured_thread_budget_is_clamped_to_visible_cpus():
    budget = ComputeBudget(cpu_threads=1000000)
    assert budget.cpu_threads == len(os.sched_getaffinity(0))


def test_actual_sqlite_spill_capacity_error_is_actionable(tmp_path):
    import sqlite3

    with sqlite3.connect(tmp_path / "limited-spool.sqlite") as connection:
        connection.execute("PRAGMA max_page_count=2")
        connection.execute("CREATE TABLE spill (value BLOB)")
        with pytest.raises(sqlite3.Error) as caught:
            connection.execute("INSERT INTO spill VALUES (?)", (b"x" * 100000,))
        assert caught.value.sqlite_errorcode == sqlite3.SQLITE_FULL
        assert resource_error_text(caught.value, "fallback").startswith("Disk")


def test_cancel_during_import_publication_removes_only_owned_staging(tmp_path):
    from veri_ufku.importers.delimited import capture
    from veri_ufku.importers.native import StructuredSettings
    from veri_ufku.importers.registry import get_adapter
    from veri_ufku.jobs.workers import Canceled

    store, _, work = prepare(tmp_path, pl.DataFrame({"x": [1, 2]}))
    with closing(store):
        before = (store.root / "ACTIVE").read_bytes()
        source = tmp_path / "new.parquet"
        pl.DataFrame({"x": [3, 4]}).write_parquet(source)
        captured = capture(source, work, any_format=True)
        result = get_adapter("parquet").import_data(
            captured, StructuredSettings(adapter_id="parquet"), work, Control()
        )
        retained = store.path("staging") / "earlier-draft"
        retained.mkdir()
        (retained / "keep").write_text("preserved")

        def cancel(point):
            if point == "import_copy_chunk":
                raise Canceled()

        with pytest.raises(Canceled):
            store.publish_import(result, checkpoint=cancel)
        assert (store.root / "ACTIVE").read_bytes() == before
        assert len(store.state["datasets"]) == 1 and not store.pending
        assert list(store.path("staging").iterdir()) == [retained]
        assert (retained / "keep").read_text() == "preserved"


def test_earlier_fitted_membership_representation_still_loads():
    from veri_ufku.modeling.baseline import FoldPreparation

    old = object.__new__(FoldPreparation)
    old.__dict__["fit_row_ids_"] = ["row:a", "row:b"]
    assert old.fit_row_ids_ == ["row:a", "row:b"]
    old.fit_row_ids_ = old.fit_row_ids_
    assert old.fit_row_ids_array_.dtype.kind == "U"
    assert old.fit_row_ids_ == ["row:a", "row:b"]
