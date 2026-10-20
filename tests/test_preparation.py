"""Independent preparation counts, identity/history boundaries and atomic plans."""

import copy
import json
from contextlib import closing
from dataclasses import replace
from datetime import date

import polars as pl
import pytest
from test_cleaning import run as clean
from test_dataset import column, prepare
from test_operations import request_for

from veri_ufku.modeling.contracts import PreparationSpec, validate_saved
from veri_ufku.modeling.history import ancestors, audit
from veri_ufku.modeling.preparation import calculate
from veri_ufku.storage.preparation_store import publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def request(store, dataset=None, origin=None):
    d = dataset or store.state["datasets"][-1]
    return dict(
        request_for(store, d),
        snapshot_uri=d["snapshot_uri"],
        semantic_metadata=d.get("semantic_metadata", {}),
        origin_version=origin or d["version_id"],
        history_state=copy.deepcopy(store.state),
    )


def specification(r, purpose="regression", **changes):
    return PreparationSpec(
        purpose,
        tuple(
            column(r, n)
            for n in ("x", "cat", "when")
            if any(c["name"] == n for c in r["columns"])
        ),
        target=column(r, "y") if purpose in ("regression", "classification") else "",
        source_version=r["version_id"],
        **changes,
    )


def frame():
    return pl.DataFrame(
        dict(
            id=["a", "b", "c", "d", "e", "f"],
            x=[1.0, None, 3.0, 4.0, 5.0, 6.0],
            cat=["A", "A", "B", "B", None, "B"],
            y=[0, 0, 1, 1, None, 1],
            when=[date(2024, 1, i) for i in range(1, 7)],
            group=["A", "A", "B", "B", "C", "C"],
        )
    )


@pytest.mark.parametrize(
    "purpose,family",
    [
        ("regression", "linear"),
        ("classification", "tree"),
        ("clustering", "distance"),
        ("anomaly", "tree"),
    ],
)
def test_purpose_counts_unfitted_names_and_source_immutable(tmp_path, purpose, family):
    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        r = request(store)
        before = store.path(r["snapshot_uri"]).read_bytes()
        out = calculate(
            r,
            specification(
                r,
                purpose,
                family=family,
                group=column(r, "group"),
                time=column(r, "when"),
            ),
            work,
        )
        assert out["dataset_n"] == 6 and out["eligible_n"] == (
            5 if purpose in ("regression", "classification") else 6
        )
        assert out["fitted"] is False and out["plan"]["fitted_parameters"] == {}
        assert out["plan"]["category_vocabulary"] is None
        assert any(v["code"] == "identifier_candidate" for v in out["risks"])
        assert any(v["code"] == "group_structure" for v in out["risks"])
        assert any(v["code"] == "temporal_structure" for v in out["risks"])
        mapping = out["plan"]["column_lineage"]
        assert {item["input_column_id"] for item in mapping} == set(
            out["spec"]["features"]
        )
        assert all(item["source_name"] in ("x", "cat", "when") for item in mapping)
        names = [n for item in mapping for n in item["output_names"]]
        assert len(set(names)) == len(names) and any(
            "{training_index}" in n for n in names
        )
        assert any(s["kind"] == "standard_scale" for s in out["plan"]["steps"]) == (
            family != "tree"
        )
        assert all(
            s["learned_scope"] == "training_fold"
            for s in out["plan"]["steps"]
            if s["kind"]
            in ("standard_scale", "impute_numeric", "impute_category", "encode_onehot")
        )
        if purpose == "classification":
            assert out["target"]["class_distribution"] == [
                dict(label="1", count=3),
                dict(label="0", count=2),
            ]
            assert out["target"]["min_class_count"] == 2
        state = publish(store, store.state, out)
        assert (
            len(state["results"]) == 1
            and store.path(r["snapshot_uri"]).read_bytes() == before
        )
        assert store.state["datasets"] == r["history_state"]["datasets"]
        root = store.root
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state["results"][-1]["preparation"]["plan"] == out["plan"]


def test_missing_constant_targets_and_suspicious_copy_are_honest(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                x=[1.0, 2.0, 3.0, 4.0],
                y=[2.0, 2.0, None, float("nan")],
                y_copy=[2.0, 2.0, None, 0.0],
            )
        ),
    )
    with closing(store):
        r = request(store)
        s = specification(r)
        s = replace(s, features=(*s.features, column(r, "y_copy")))
        out = calculate(r, s, work)
        assert out["eligible_n"] == 2 and out["excluded_target_n"] == 2
        assert (
            out["target"]["null_count"] == 1 and out["target"]["nonfinite_count"] == 1
        )
        codes = {risk["code"] for risk in out["risks"]}
        assert {
            "missing_target",
            "constant_target",
            "suspect_target_derivative",
        } <= codes
        assert out["status"] == "blocked" and out["leakage_certified"] is False
        derivative = next(
            r for r in out["risks"] if r["code"] == "suspect_target_derivative"
        )
        assert derivative["certainty"] == "candidate"


def test_all_missing_rare_classes_high_cardinality_and_identifiers(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                id=range(30),
                x=range(30),
                cat=[str(i) for i in range(30)],
                y=["A"] * 29 + ["B"],
            )
        ),
    )
    with closing(store):
        r = request(store)
        s = specification(r, "classification")
        s = replace(s, features=(*s.features, column(r, "id")))
        out = calculate(r, s, work)
        assert {
            "identifier_candidate",
            "rare_class",
            "class_imbalance",
            "high_cardinality",
        } <= {v["code"] for v in out["risks"]}
        assert out["status"] == "blocked"
        allowed = calculate(r, replace(s, allow_identifiers=True), work)
        assert not any(
            code.startswith("identifier_candidate") for code in allowed["blockers"]
        )


@pytest.mark.parametrize("action", ["review", "raw", "relocate"])
def test_learned_history_really_restarts_from_source(tmp_path, action):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1.0, 2.0, 6.0, None], y=[0.0, 1.0, 2.0, 3.0]))
    )
    with closing(store):
        raw = copy.deepcopy(store.state["datasets"][-1])
        original = store.path(raw["snapshot_uri"]).read_bytes()
        _, cleaned, _, _ = clean(store, work, "x", "fill", {"method": "mean"})
        r = request(store)
        s = specification(r, history_action=action)
        if action != "review":
            with pytest.raises(ProjectError, match="riski|kaynak"):
                calculate(r, s, work)
            r = request(store, raw, cleaned["version_id"])
            s = specification(r, history_action=action)
        out = calculate(r, s, work)
        assert out["history"]["findings"][0]["kind"] == "fill"
        assert out["history"]["findings"][0]["removed_from_source"] == (
            action != "review"
        )
        assert any(v["code"] == "history_learned" for v in out["risks"]) == (
            action == "review"
        )
        x = next(p for p in out["columns"] if p["name"] == "x")
        assert x["null_count"] == (0 if action == "review" else 1)
        if action == "relocate":
            step = next(
                s for s in out["plan"]["steps"] if s["kind"] == "impute_numeric"
            )
            assert step["parameters"]["strategy"] == "mean"
            assert step["parameters"]["relocated_from_operation_id"]
            assert "fill_values" not in json.dumps(step)
        publish(store, store.state, out)
        assert store.path(raw["snapshot_uri"]).read_bytes() == original
        assert (
            store.state["workflow"]["heads"][cleaned["dataset_id"]]
            == cleaned["version_id"]
        )


def test_copy_fork_history_not_hidden_and_risky_source_rejected(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1.0, 2.0, 6.0, None], y=[0.0, 1.0, 2.0, 3.0]))
    )
    with closing(store):
        _, filled, _, _ = clean(store, work, "x", "fill", {"method": "mean"})
        _, copied, _, _ = clean(store, work, "x", "outlier", destination="copy")
        info = audit(store.state, copied["version_id"], copied["version_id"], "review")
        assert len(info["unresolved_source_operations"]) == 2
        assert filled["version_id"] in ancestors(store.state, copied["version_id"])
        raw = store.state["datasets"][0]
        moved = audit(store.state, copied["version_id"], raw["version_id"], "relocate")
        assert len(moved["findings"]) == 2 and all(
            f["removed_from_source"] for f in moved["findings"]
        )


@pytest.mark.parametrize(
    "changes",
    [
        dict(features=[]),
        dict(features=["col:bad"]),
        dict(target="bad"),
        dict(purpose="fit_all"),
        dict(scaling="fake"),
        dict(date_features="yes"),
    ],
)
def test_invalid_plan_rejected(tmp_path, changes):
    store, r, work = prepare(tmp_path, frame())
    with closing(store), pytest.raises(ProjectError):
        r = request(store)
        s = specification(r).data()
        s.update(changes)
        calculate(r, s, work)


def test_target_and_group_exclusion_ordinal_order_and_tampered_mapping(tmp_path):
    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        r = request(store)
        s = specification(r)
        with pytest.raises(ProjectError, match="Hedef"):
            calculate(r, replace(s, features=(*s.features, s.target)), work)
        with pytest.raises(ProjectError, match="Ordinal"):
            calculate(r, replace(s, encoding="ordinal"), work)
        out = calculate(r, s, work)
        state = publish(store, store.state, out)
        record = copy.deepcopy(state["results"][-1])
        record["preparation"]["plan"]["column_lineage"][0]["output_names"] = ["wrong"]
        with pytest.raises(ProjectError, match="eşlemesi"):
            validate_saved(record, {d["version_id"]: d for d in state["datasets"]})


def test_publish_fault_preserves_active_and_plan_never_fits(tmp_path):
    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        r = request(store)
        out = calculate(r, specification(r, selection="variance"), work)
        assert out["plan"]["feature_selection_mask"] is None
        before = store.path("ACTIVE").read_bytes()

        def fault(point):
            if point == "pointer_written":
                raise OSError("fault")

        with pytest.raises(OSError):
            publish(store, store.state, out, fault)
        assert (
            store.path("ACTIVE").read_bytes() == before and not store.state["results"]
        )


def test_relocated_steps_preserve_policy_order_and_duplicate_is_rejected(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1.0, 2.0, 6.0, None], y=[0, 1, 2, 3]))
    )
    with closing(store):
        raw = copy.deepcopy(store.state["datasets"][0])
        clean(store, work, "x", "fill", {"method": "mean"})
        _, head, _, _ = clean(store, work, "x", "outlier", {"multiplier": "3"})
        r = request(store, raw, head["version_id"])
        out = calculate(
            r,
            specification(
                r, history_action="relocate", numeric_imputation="none", family="linear"
            ),
            work,
        )
        kinds = [s["kind"] for s in out["plan"]["steps"]]
        assert kinds.index("impute_numeric") < kinds.index("standard_scale")
        mark = next(s for s in out["plan"]["steps"] if s["kind"] == "outlier_iqr_mark")
        assert (
            mark["parameters"]["multiplier"] == "3"
            and mark["parameters"]["thresholds"] is None
        )
        assert "__outlier_iqr" not in out["plan"]["steps"][0]["output_names"][0]
        _, head, _, _ = clean(store, work, "x", "fill", {"method": "median"})
        r = request(store, raw, head["version_id"])
        with pytest.raises(ProjectError, match="birden fazla"):
            calculate(r, specification(r, history_action="relocate"), work)


def test_all_missing_nonfinite_and_explicit_no_imputation(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(x=[None, None, None], y=[0, 1, 2], z=[float("inf"), 1.0, 2.0])
        ),
    )
    with closing(store):
        r = request(store)
        out = calculate(r, specification(r), work)
        assert any(
            v["code"] == "constant_feature" and v["severity"] == "blocker"
            for v in out["risks"]
        )
        s = replace(
            specification(r),
            features=(column(r, "z"),),
            invalid_numeric="as_missing",
            numeric_imputation="none",
        )
        out = calculate(r, s, work)
        assert "missing_feature:" + column(r, "z") in out["blockers"]
        r["semantic_metadata"] = {column(r, "z"): dict(role="category")}
        out = calculate(
            r,
            replace(s, numeric_imputation="median", categorical_imputation="none"),
            work,
        )
        assert "missing_feature:" + column(r, "z") in out["blockers"]


@pytest.mark.parametrize("point", ["pointer_written", "pointer_replaced"])
def test_preparation_real_sigkill_recovery_and_second_process_readonly(tmp_path, point):
    import signal
    import subprocess
    import sys

    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        r = request(store)
        result = calculate(r, specification(r), work)
        file = tmp_path / "result.json"
        file.write_text(json.dumps(result))
        root = store.root
        previous = store.commit_id
    program = """import json,os,signal,sys
from pathlib import Path
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.preparation_store import publish
s=ProjectStore.open(sys.argv[1])
def hook(p):
    if p==sys.argv[3]:os.kill(os.getpid(),signal.SIGKILL)
publish(s,s.state,json.loads(Path(sys.argv[2]).read_text()),hook)
"""
    child = subprocess.run(
        [sys.executable, "-c", program, str(root), str(file), point],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    with closing(ProjectStore.open(root, recover_lock=True)) as reopened:
        assert len(reopened.state["results"]) == (
            1 if point == "pointer_replaced" else 0
        )
        assert (reopened.commit_id == previous) == (point == "pointer_written")
        if point == "pointer_replaced":
            assert reopened.state["results"][0]["preparation"]["plan"] == result["plan"]
        program = """import json,sys
from pathlib import Path
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.preparation_store import publish
from veri_ufku.storage.project_model import ProjectError
s=ProjectStore.open(sys.argv[1]);assert s.read_only
try:publish(s,s.state,json.loads(Path(sys.argv[2]).read_text()))
except ProjectError:print('READONLY_REJECTED')
else:raise AssertionError('readonly writer accepted')
s.close()
"""
        child = subprocess.run(
            [sys.executable, "-c", program, str(root), str(file)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert child.returncode == 0 and "READONLY_REJECTED" in child.stdout, (
            child.stderr
        )


def test_explicit_ordinal_and_class_distribution_bounds(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                x=range(30),
                cat=["low", "high"] * 15,
                y=["X" * 1000] * 2 + [str(i) for i in range(28)],
            )
        ),
    )
    with closing(store):
        r = request(store)
        cat = column(r, "cat")
        r["semantic_metadata"] = {
            cat: dict(role="ordinal", ordinal_order=["low", "high"])
        }
        out = calculate(r, specification(r, "classification", encoding="ordinal"), work)
        encode = next(s for s in out["plan"]["steps"] if s["kind"] == "encode_ordinal")
        assert (
            encode["parameters"]["order"] == ["low", "high"]
            and encode["learned_scope"] == "row_local"
        )
        assert len(out["target"]["class_distribution"]) == 20
        assert (
            out["target"]["distribution_truncated"]
            and out["target"]["min_class_count"] == 1
        )
        assert all(len(c["label"]) <= 257 for c in out["target"]["class_distribution"])


def test_preparation_has_no_learning_calls_or_oversize_silent_sampling(tmp_path):
    import ast
    import inspect

    from veri_ufku.modeling import plan, preparation

    for module in (plan, preparation):
        code = ast.parse(inspect.getsource(module))
        assert not any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr
            in ("fit", "fit_transform", "partial_fit", "train_test_split", "sample")
            for n in ast.walk(code)
        )
    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        r = request(store)
        r["row_count"] = 100001
        with pytest.raises(ProjectError, match="bütçeyi"):
            calculate(r, specification(r), work)


def test_reopening_rejects_erased_persistent_history(tmp_path):
    from veri_ufku.storage.project_model import validate_state

    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1.0, 2.0, 6.0, None], y=[0, 1, 2, 3]))
    )
    with closing(store):
        clean(store, work, "x", "fill", {"method": "mean"})
        r = request(store)
        out = calculate(r, specification(r), work)
        state = publish(store, store.state, out)
        tampered = copy.deepcopy(state)
        history = tampered["results"][-1]["preparation"]["history"]
        history["findings"] = []
        history["unresolved_source_operations"] = []
        with pytest.raises(ProjectError, match="geçmişi"):
            validate_state(tampered)
