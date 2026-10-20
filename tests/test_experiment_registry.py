"""Local registry reuses persistent runs/test journal and rejects false comparisons."""

import copy
from contextlib import closing

import pytest
from test_validation import setup_run

from veri_ufku.modeling.baseline import calculate
from veri_ufku.storage import experiment_store as registry
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.validation_store import choice, complete


def setup(tmp_path):
    store, request, work, protocol = setup_run(tmp_path)
    from dataclasses import replace

    protocol = replace(protocol, prediction_moment="sentinel-password-secret-123")
    from veri_ufku.storage.project_model import uid

    rid = request["run_id"] = "run:" + uid()
    choice(
        store,
        store.state,
        request["version_id"],
        protocol.data(),
        request["preparation"]["plan"]["version_id"],
        rid,
    )
    result = calculate(request, protocol.data(), work)
    complete(store, store.state, result=result, run_id=rid)
    return store, request, result


def test_existing_identity_capture_integrity_revision_reopen_masked_export(tmp_path):
    store, request, result = setup(tmp_path)
    with closing(store):
        before = copy.deepcopy(store.state["results"])
        row = registry.rows(store)[0]
        assert row["run_id"] == request["run_id"] and row["data_access_at"]
        assert row["code_hash"] and row["environment_hash"] and row["config_hash"]
        from veri_ufku.storage.project_model import digest, encode

        assert row["config_hash"] == digest(
            encode(
                dict(
                    spec=result["spec"],
                    regression=None,
                    classification=None,
                    pipeline_id=result["pipeline_id"],
                )
            )
        )
        for kind, value in [
            ("tags", ["demo"]),
            ("model_status", "selected"),
            ("metric_revision", "mae"),
        ]:
            registry.event(store, store.state, row["run_id"], kind, value)
        assert store.state["results"][: len(before)] == before
        assert registry.rows(store, tag="demo")[0]["model_status"] == "selected"
        report = registry.compare(store, [row["run_id"]])
        assert report["comparable"] and len(report["rows"][0]["folds"]) == 3
        assert report["points"][0]["pareto"]
        path = tmp_path / "export.json"
        # Arbitrary original card/config strings must not reach export.
        safe = registry.export(store, [row["run_id"]], path)
        assert "params" not in safe["rows"][0] and "model_card" not in safe["rows"][0]
        assert b"sentinel-password-secret-123" not in path.read_bytes()
        assert "tags" not in safe["rows"][0] and "capture" not in safe["rows"][0]
        with pytest.raises((ProjectError, FileExistsError)):
            registry.export(store, [row["run_id"]], path)
        root = store.root
    with closing(ProjectStore.open(root)) as reopened:
        assert registry.rows(reopened, tag="demo")[0]["model_status"] == "selected"
        assert registry.compare(reopened, [row["run_id"]])["comparable"]
        package = reopened.path(row["artifact_uri"])
        package.write_bytes(package.read_bytes() + b"corruption")
        with pytest.raises(ProjectError, match="artifact"):
            registry.compare(reopened, [row["run_id"]])


def test_split_mismatch_canceled_run_not_success_and_legacy_unknown(tmp_path):
    store, request, result = setup(tmp_path)
    with closing(store):
        import uuid

        rid = "run:" + str(uuid.uuid4())
        request = dict(request, run_id=rid)
        parameters = dict(result["spec"], seed=result["seed"] + 1)
        choice(
            store,
            store.state,
            request["version_id"],
            parameters,
            request["preparation"]["plan"]["version_id"],
            rid,
        )
        (tmp_path / "second").mkdir()
        complete(
            store,
            store.state,
            result=calculate(request, parameters, tmp_path / "second"),
            run_id=rid,
        )
        report = registry.compare(store, [result["run_id"], rid])
        assert not report["comparable"] and report["warnings"]
        assert not any(p["pareto"] for p in report["points"])
        canceled = "run:" + str(uuid.uuid4())
        choice(
            store,
            store.state,
            request["version_id"],
            parameters,
            request["preparation"]["plan"]["version_id"],
            canceled,
        )
        complete(store, store.state, run_id=canceled, status="canceled")
        r = registry.rows(store, status="canceled")[0]
        assert r["run_id"] == canceled and not r["model_version"]
        assert registry.compare(store, [canceled])["points"] == []
        with pytest.raises(ProjectError):
            registry.event(store, store.state, canceled, "model_status", "selected")
        legacy = copy.deepcopy(store.state)
        for r in legacy["results"]:
            if "model_choice" in r:
                r["model_choice"].pop("experiment_capture", None)
        assert registry.rows(store, legacy)[0]["code_hash"] is None


@pytest.mark.parametrize(
    "kind,value",
    [
        ("tags", ["password"]),
        ("tags", ["https://secret"]),
        ("quota", -1),
        ("model_status", "deployed"),
        ("metric_revision", "test_accuracy"),
        ("threshold", 0.7),
    ],
)
def test_invalid_revision_atomic(tmp_path, kind, value):
    store, request, result = setup(tmp_path)
    with closing(store):
        before = copy.deepcopy(store.state)
        commit = store.commit_id
        with pytest.raises(ProjectError):
            registry.event(
                store,
                store.state,
                None if kind == "quota" else result["run_id"],
                kind,
                value,
            )
        assert store.state == before and store.commit_id == commit


def test_revision_tampering_stale_draft_and_disk_quota(tmp_path):
    store, request, result = setup(tmp_path)
    with closing(store):
        stale = copy.deepcopy(store.state)
        registry.event(store, store.state, result["run_id"], "model_status", "archived")
        with pytest.raises(ProjectError):
            registry.event(store, stale, result["run_id"], "tags", ["demo"])
        damaged = copy.deepcopy(store.state)
        damaged["results"][-1]["experiment_event"]["value"] = "selected"
        with pytest.raises(ProjectError):
            registry.validate(damaged)
        registry.event(store, store.state, None, "quota", 16 * 1024**2)
        before = store.commit_id
        huge = store.path("sources") / "quota-test.bin"
        with huge.open("wb") as stream:
            stream.truncate(17 * 1024**2)
        with pytest.raises(ProjectError, match="kota"):
            store.save()
        assert store.commit_id == before and huge.exists()


def test_integrity_scan_cancel_and_timeout_preserve_run(tmp_path):
    import threading

    from veri_ufku.domain.contracts import ComputeBudget
    from veri_ufku.importers.delimited import Control
    from veri_ufku.jobs.workers import Canceled

    store, request, result = setup(tmp_path)
    with closing(store):
        before = copy.deepcopy(store.state)
        cancel = threading.Event()
        cancel.set()
        with pytest.raises(Canceled):
            registry.compare(store, [result["run_id"]], control=Control(cancel=cancel))
        control = Control(budget=ComputeBudget(max_wall_seconds=1))
        control.started -= 2
        with pytest.raises(ProjectError, match="süre"):
            registry.compare(store, [result["run_id"]], control=control)
        assert store.state == before


def test_pending_canceled_final_reservation_visible_without_success(tmp_path):
    from veri_ufku.storage.project_model import uid
    from veri_ufku.storage.validation_store import reserve_test

    store, request, result = setup(tmp_path)
    with closing(store):
        rid = "run:" + uid()
        state, ident = reserve_test(store, store.state, result, rid)
        assert any(
            r["run_id"] == rid and r["status"] == "pending"
            for r in registry.rows(store)
        )
        complete(store, state, test_use_id=ident, run_id=rid, status="canceled")
        assert any(
            r["run_id"] == rid
            and r["status"] == "canceled"
            and r["model_version"] is None
            for r in registry.rows(store)
        )
        assert registry.compare(store, [rid])["points"] == []


def test_same_split_different_metric_averaging_is_not_same_protocol(tmp_path):
    from test_classification import synthetic

    from veri_ufku.storage.project_model import uid

    store, request, work, protocol = synthetic(tmp_path)
    with closing(store):
        ids = []
        for avg in ("macro", "weighted"):
            rid = "run:" + uid()
            from veri_ufku.modeling.classification import settings

            config = settings(
                dict(candidates=["baseline"], positive_class="risk", averaging=avg)
            )
            r = dict(request, run_id=rid, classification=config)
            choice(
                store,
                store.state,
                r["version_id"],
                protocol.data(),
                r["preparation"]["plan"]["version_id"],
                rid,
                classification=config,
            )
            result = calculate(r, protocol.data(), work)
            complete(store, store.state, result=result, run_id=rid)
            ids.append(rid)
        assert (
            registry.rows(store)[0]["split_id"] == registry.rows(store)[1]["split_id"]
        )
        report = registry.compare(store, ids, "f1")
        assert not report["comparable"] and report["warnings"]
