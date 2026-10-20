"""Real atomic checkpoint artifacts, source validation, journal protection and safe reopen."""

import copy
import threading
from contextlib import closing

import pytest
from test_search import run_fixture

from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.search import calculate
from veri_ufku.modeling.search_contracts import SearchSpec
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.search_store import load_search, publish
from veri_ufku.storage.validation_store import transaction


def test_atomic_source_bound_artifact_and_reopen_no_fit(tmp_path, monkeypatch):
    store, r, work, p, s = run_fixture(tmp_path)
    root = store.root
    with closing(store):
        data = calculate(r, p.data(), s.data(), work)
        state = publish(store, store.state, data)
        record = state["results"][-1]
        assert record["search"]["details_uri"] in store.manifest["artifacts"]
        assert load_search(store, record) == data
        assert "trials" not in record["search"]
        state = publish(store, state, data)
        assert state["results"][-1]["search"]["checkpoint_index"] == 1
        with pytest.raises(ProjectError, match="defteri silinemez"):
            transaction(
                store, dict(state, results=state["results"][:-1]), lambda d: None
            )
    import veri_ufku.modeling.search as engine

    monkeypatch.setattr(
        engine,
        "calculate",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("read must not fit")),
    )
    with closing(ProjectStore.open(root)) as reopened:
        assert load_search(reopened, reopened.state["results"][-1]) == data


@pytest.mark.parametrize("tamper", ["fit", "metric", "winner", "source", "curve"])
def test_bad_checkpoint_rejected_and_previous_state_preserved(tmp_path, tamper):
    store, r, work, p, _ = run_fixture(tmp_path)
    s = SearchSpec(method="grid", curves=True)
    with closing(store):
        data = calculate(r, p.data(), s.data(), work)
        state = publish(store, store.state, data)
        before = copy.deepcopy(store.state)
        active = store._read("ACTIVE", 4096)
        bad = copy.deepcopy(data)
        if tamper == "fit":
            bad["trials"][0]["folds"][0]["fit_row_ids"].append(
                data["plan"]["membership"]["test"][0]
            )
        elif tamper == "metric":
            bad["trials"][0]["folds"][0]["metrics"]["mae"] += 10
        elif tamper == "winner":
            bad["outer_evaluations"][0]["winner_trial"] = "wrong"
        elif tamper == "source":
            bad["source_snapshot_id"] = "snapshot:wrong"
        else:
            bad["curves"][0]["folds"][0]["evaluation_row_ids"][0] = data["plan"][
                "membership"
            ]["test"][0]
        with pytest.raises(ProjectError):
            publish(store, state, bad)
        assert store._read("ACTIVE", 4096) == active and store.state == before


def test_canceled_checkpoint_resume_terminal_attempts_immutable(tmp_path):
    store, r, work, p, s = run_fixture(tmp_path)
    with closing(store):
        cancel = threading.Event()
        saved = None

        def checkpoint(value):
            nonlocal saved
            saved = publish(store, store.state, value)
            if any(t["status"] == "completed" for t in value["trials"]):
                cancel.set()

        partial = calculate(
            r, p.data(), s.data(), work, Control(cancel=cancel), checkpoint=checkpoint
        )
        assert partial["status"] == "canceled"
        state = publish(store, store.state, partial)
        stored = load_search(store, state["results"][-1])
        out = calculate(r, p.data(), s.data(), work, resume=stored)
        state = publish(store, state, out)
        assert state["results"][-1]["search"]["status"] == "completed"
        changed = copy.deepcopy(out)
        changed["trials"][0]["loss"] += 1
        with pytest.raises(ProjectError):
            publish(store, state, changed)


def test_checkpoint_write_fault_rolls_back(tmp_path):
    store, r, work, p, s = run_fixture(tmp_path)
    with closing(store):
        data = calculate(r, p.data(), s.data(), work)
        state = copy.deepcopy(store.state)
        active = store._read("ACTIVE", 4096)
        original = store.save

        def fail(*args, **kwargs):
            raise OSError("simulated disk failure")

        store.save = fail
        with pytest.raises(OSError):
            publish(store, state, data)
        store.save = original
        assert store.state == state and store._read("ACTIVE", 4096) == active
        assert not store.pending


def test_archived_json_fingerprint_tamper_is_rejected(tmp_path):
    store, r, work, p, s = run_fixture(tmp_path)
    with closing(store):
        data = calculate(r, p.data(), s.data(), work)
        state = publish(store, store.state, data)
        record = state["results"][-1]
        path = store.path(record["search"]["details_uri"])
        # Synthetic artifact corruption, never a source dataset edit.
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        with pytest.raises(ProjectError, match="artifact"):
            load_search(store, record)
        path.write_bytes(original)


def test_search_early_stopping_checkpoint_source_revalidated(tmp_path):
    store, r, work, p, _ = run_fixture(tmp_path)
    with closing(store):
        s = SearchSpec(
            trials=1,
            curves=False,
            early_stopping=True,
            space={
                "methods": ["gradient_boosting"],
                "parameters": [{"name": "trees", "values": [20]}],
            },
        )
        out = calculate(r, p.data(), s.data(), work)
        assert out["status"] == "completed"
        state = publish(store, store.state, out)
        bad = copy.deepcopy(out)
        bad["trials"][0]["folds"][0]["early_stopping"][0]["validation_row_ids"] = out[
            "plan"
        ]["membership"]["test"]
        with pytest.raises(ProjectError, match="Stopping"):
            publish(store, state, bad)


def test_history_export_new_file_only_preserves_sources(tmp_path):
    import json

    from veri_ufku.storage.search_store import export_history

    store, r, work, p, s = run_fixture(tmp_path)
    with closing(store):
        out = calculate(r, p.data(), s.data(), work)
        target = tmp_path / "export.json"
        assert export_history(out, str(target)) == str(target)
        assert json.loads(target.read_text()) == out
        before = target.read_bytes()
        with pytest.raises(ProjectError, match="mevcut"):
            export_history(out, str(target))
        assert target.read_bytes() == before
        with pytest.raises(ProjectError):
            export_history(out, r["path"])
