"""Hand references, real estimators, impossible evaluation and lossless atomic marking."""

import copy
import threading
from contextlib import closing
from dataclasses import replace
from decimal import Decimal

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.unsupervised import UnsupervisedSpec, calculate, silhouette
from veri_ufku.operations.contracts import active_datasets
from veri_ufku.storage.project_model import ProjectError, validate_state
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.unsupervised_store import load, publish, transfer


def spec(r, method="kmeans", **changes):
    return UnsupervisedSpec(method, (column(r, "x"),), **changes)


@pytest.mark.parametrize("method", ["kmeans", "dbscan", "isolation_forest", "iqr"])
def test_real_algorithms_durable_profiles_members_and_lossless_transfer(
    tmp_path, method
):
    values = [0.0, 0.1, 0.2, 10.0, 10.1, 10.2, 50.0]
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(x=values, cat=["kept"] * 7)))
    root = store.root
    source_bytes = (tmp_path / "source.parquet").read_bytes()
    with closing(store):
        original = pl.read_parquet(r["path"])
        out = calculate(
            r, spec(r, method, clusters=2, scaling="none", eps=0.3, min_samples=3), work
        )
        members = pl.read_parquet(out["assignment_path"])
        assert out["fit_scope"].startswith("full_selected")
        assert out["provenance"]["seed"] == 42
        assert (
            out["evaluation"]["precision"] is None
            and out["evaluation"]["recall"] is None
        )
        if method == "kmeans":
            assert len(out["profiles"]) == 2
            assert sorted(p["count"] for p in out["profiles"]) == [1, 6]
            assert out["silhouette"]["status"] == "unavailable"
        elif method == "dbscan":
            labels = members["cluster"].to_list()
            assert (
                labels[:3] == [0, 0, 0]
                and labels[3:6] == [1, 1, 1]
                and labels[-1] == -1
            )
            assert out["silhouette"]["status"] == "valid"
            assert out["silhouette"]["noise_excluded"] == 1
            assert not out["new_data"]["native_support"]
        else:
            assert members["anomaly_candidate"][-1]
            assert members["anomaly_score"][-1] == max(members["anomaly_score"])
        _, record = publish(store, store.state, out)
        state, version = transfer(store, store.state, record["id"])
        validate_state(state)
        marked = next(d for d in state["datasets"] if d["version_id"] == version)
        marked_frame = pl.read_parquet(store.path(marked["snapshot_uri"]))
        assert marked_frame.select(original.columns).equals(original)
        assert marked_frame.height == original.height == 7
        assert state["datasets"][0]["version_id"] == r["version_id"]
        assert len(active_datasets(state)) == 2
        assert store.results_status()[0]["current"]
        assert (tmp_path / "source.parquet").read_bytes() == source_bytes
    with closing(ProjectStore.open(root)) as reopened:
        saved, assignments, source, _ = load(reopened, record)
        assert saved["method_state"] == out["method_state"]
        assert assignments.equals(members) and source.equals(original)
        assert len(reopened.state["datasets"]) == 2


def test_hand_silhouette_separation_and_invalid_clusters():
    x = np.array([[0.0], [1.0], [2.0], [10.0], [11.0], [12.0]])
    labels = np.array([0, 0, 0, 1, 1, 1])
    # a=(1.5,1,1.5); b=(11,10,9) for first cluster, symmetry for second.
    expected = np.mean([1 - 1.5 / 11, 1 - 1 / 10, 1 - 1.5 / 9] * 2)
    assert silhouette(x, labels)["value"] == pytest.approx(expected, abs=1e-12)
    for bad in (
        [0] * 6,
        [-1] * 6,
        [0, 1, 1, 1, 1, 1],
        [0, 0, 1, 1, 1, 1],
        list(range(6)),
    ):
        out = silhouette(x, np.array(bad))
        assert out["status"] == "unavailable" and out["value"] is None
    assert (
        silhouette(np.zeros((3002, 1)), np.array([0] * 1501 + [1] * 1501))["status"]
        == "unavailable"
    )


def test_hand_iqr_linear_fences_strict_equality_and_zero_width(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(x=[0, 1, 2, 3, 100])))
    with closing(store):
        out = calculate(r, spec(r, "iqr"), work)
        m = out["method_state"]
        assert (m["q1"], m["q3"], m["iqr"], m["lower"], m["upper"]) == (1, 3, 2, -2, 6)
        members = pl.read_parquet(out["assignment_path"])
        assert members["anomaly_score"].to_list() == [0, 0, 0, 0, 94]
        assert members["anomaly_candidate"].to_list() == [False] * 4 + [True]
        assert not out["scaling_state"]
    other = tmp_path / "zero"
    other.mkdir()
    store, r, work = prepare(other, pl.DataFrame(dict(x=[4, 4, 4, 4, 5])))
    with closing(store):
        out = calculate(r, spec(r, "iqr"), work)
        assert out["method_state"]["iqr"] == 0
        assert pl.read_parquet(out["assignment_path"])[
            "anomaly_candidate"
        ].to_list() == [False] * 4 + [True]


@pytest.mark.parametrize(
    "values",
    [
        [1.0, None, 3.0],
        [1.0, float("nan"), 3.0],
        [1.0, float("inf"), 3.0],
        [2**53, 2**53 + 1, 2**53 + 2],
        [Decimal("0.1"), Decimal("0.2"), Decimal("0.3")],
        ["A", "B", "A"],
    ],
)
def test_missing_nonfinite_precision_and_categories_rejected_without_mutation(
    tmp_path, values
):
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(x=values)))
    with closing(store):
        before = copy.deepcopy(store.state)
        with pytest.raises(ProjectError):
            calculate(r, spec(r), work)
        assert store.state == before


@pytest.mark.parametrize(
    "change",
    [
        dict(clusters=30),
        dict(eps=0),
        dict(seed=True),
        dict(contamination=0),
        dict(score_threshold=float("nan")),
        dict(threshold_mode="unknown"),
    ],
)
def test_invalid_configuration_not_fit(tmp_path, change):
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(x=[0, 1, 2, 3, 4, 5])))
    with closing(store), pytest.raises(ProjectError):
        calculate(r, spec(r, **change), work)


def test_named_identifier_semantic_category_and_iqr_multi_column_reject(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1, 2, 3], customer_id=[1, 2, 3], y=[4, 5, 6]))
    )
    with closing(store):
        with pytest.raises(ProjectError, match="kimlik"):
            calculate(r, UnsupervisedSpec("kmeans", (column(r, "customer_id"),)), work)
        with pytest.raises(ProjectError, match="tek"):
            calculate(
                r, UnsupervisedSpec("iqr", (column(r, "x"), column(r, "y"))), work
            )
        r["semantic_metadata"] = {column(r, "x"): dict(role="category")}
        with pytest.raises(ProjectError, match="kategori"):
            calculate(r, spec(r), work)


def test_budget_cancel_changed_snapshot_and_assignment_tamper(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(x=list(range(8)))))
    with closing(store):
        with pytest.raises(ProjectError, match="bütçe"):
            calculate(dict(r, row_count=3001), spec(r, "dbscan"), work)
        event = threading.Event()
        event.set()
        with pytest.raises(Canceled):
            calculate(r, spec(r), work, Control(event))
        with pytest.raises(ProjectError):
            calculate(
                r,
                spec(r),
                work,
                Control(budget=replace(ComputeBudget(), ram_bytes=100)),
            )
        out = calculate(r, spec(r), work)
        before = copy.deepcopy(store.state)
        members = pl.read_parquet(out["assignment_path"])
        members.reverse().write_parquet(out["assignment_path"])
        from veri_ufku.storage.project_store import file_hash

        out["assignment_fingerprint"] = file_hash(out["assignment_path"])
        with pytest.raises(ProjectError, match="RowId"):
            publish(store, store.state, out)
        assert store.state == before
        r["fingerprint"] = dict(r["fingerprint"], sha256="0" * 64)
        with pytest.raises(ProjectError):
            calculate(r, spec(r), work)


def test_atomic_publish_transfer_fault_readonly_and_stale(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(x=list(range(20)))))
    root = store.root

    def fail(point):
        if point == "parquet_chunk_written":
            raise OSError("injected")

    # Existing save checkpoint is authoritative; inject before ACTIVE instead.
    def crash(point):
        if point == "before_active":
            raise OSError("injected")

    with closing(store):
        out = calculate(r, spec(r, "iqr"), work)
        _, record = publish(store, store.state, out)
        before = copy.deepcopy(store.state)
        reached = []

        def probe(point):
            reached.append(point)
            if point == "manifest_written":
                raise OSError("injected")

        with pytest.raises(OSError):
            transfer(store, store.state, record["id"], checkpoint=probe)
        assert store.state == before and "manifest_written" in reached
        with closing(ProjectStore.open(root)) as second:
            assert second.read_only
            with pytest.raises(ProjectError):
                transfer(second, second.state, record["id"])
        # A metadata update makes old transfer invalid despite identical physical rows.
        from veri_ufku.analytics.contracts import metadata_version

        new = metadata_version(
            store.state["datasets"][0], column(r, "x"), "measurement", "", [], ""
        )
        store.state["datasets"].append(new)
        store.save()
        with pytest.raises(ProjectError, match="Eski"):
            transfer(store, store.state, record["id"])
        with pytest.raises(ProjectError, match="eski"):
            publish(store, store.state, out)


def test_explicit_if_threshold_scores_are_not_probability(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(x=[0.0] * 20 + [100.0])))
    with closing(store):
        out = calculate(
            r,
            spec(r, "isolation_forest", threshold_mode="score", score_threshold=0.6),
            work,
        )
        members = pl.read_parquet(out["assignment_path"])
        assert out["threshold"] == 0.6
        assert (
            members["anomaly_candidate"].to_list()
            == (members["anomaly_score"] > 0.6).to_list()
        )
        assert out["evaluation"]["precision"] is None
        assert out["new_data"]["native_support"] and out["new_data"]["available"]


def test_csv_marked_dataset_can_be_reopened_and_used_by_existing_operations(tmp_path):
    from test_operations import request_for

    from veri_ufku.importers.delimited import ImportSettings, capture, import_snapshot
    from veri_ufku.operations.contracts import build
    from veri_ufku.operations.engine import calculate as transform

    source = tmp_path / "source.csv"
    source.write_text("x;code\n0;001\n1;002\n2;003\n3;004\n100;005\n")
    work = tmp_path / "work"
    work.mkdir()
    captured = capture(source, work)
    imported = import_snapshot(
        captured, ImportSettings(delimiter=";", types=("float64", "text")), work
    )
    root = tmp_path / "project"
    with closing(ProjectStore.create(root)) as store:
        store.publish_import(imported)
        parent = store.state["datasets"][-1]
        r = dict(request_for(store, parent), snapshot_uri=parent["snapshot_uri"])
        out = calculate(r, spec(r, "iqr"), work)
        _, record = publish(store, store.state, out)
        _, version = transfer(store, store.state, record["id"])
        marked = next(d for d in store.state["datasets"] if d["version_id"] == version)
        original = pl.read_parquet(store.path(parent["snapshot_uri"]))
        assert (
            pl.read_parquet(store.path(marked["snapshot_uri"]))
            .select(original.columns)
            .equals(original)
        )
        request2 = request_for(store, marked)
        change = transform(
            request2,
            build(request2, "rename", [column(request2, "x")], {"name": "measurement"}),
            work,
        )
        store.publish_operation(change)
    with closing(ProjectStore.open(root)) as reopened:
        dataset = active_datasets(reopened.state)[-1]
        frame = pl.read_parquet(reopened.path(dataset["snapshot_uri"]))
        assert frame["code"].to_list() == ["001", "002", "003", "004", "005"]
        assert frame["anomali_adayi"].to_list() == [False, False, False, False, True]
        assert frame.height == 5 and "measurement" in frame.columns


def test_actual_single_cluster_all_noise_and_equal_iqr_fence(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(x=[0, 1, 2, 3, 6])))
    with closing(store):
        single = calculate(r, spec(r, clusters=1), work)
        assert single["silhouette"]["status"] == "unavailable"
        noise = calculate(r, spec(r, "dbscan", eps=0.00001, min_samples=2), work)
        assert noise["noise_count"] == 5 and noise["silhouette"]["value"] is None
        iqr = calculate(r, spec(r, "iqr"), work)
        assert iqr["method_state"]["upper"] == 6 and iqr["flagged_count"] == 0
