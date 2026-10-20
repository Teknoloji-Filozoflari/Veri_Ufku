"""Roundtrip, hostile package, schema contract and exact RowId inference acceptance."""

import copy
import json
import multiprocessing as mp
import pickle
import zipfile
from contextlib import closing
from pathlib import Path

import numpy as np
import polars as pl
import pytest
import skops.io as sio
from sklearn.cluster import DBSCAN
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from test_classification import synthetic as classification
from test_dataset import prepare
from test_regression import synthetic
from test_unsupervised import spec

from veri_ufku.domain.contracts import Progress
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.baseline import FoldPreparation, calculate
from veri_ufku.modeling.lifecycle import (
    load_package,
    predict,
    preview,
    raw_json,
    save_package,
    sha,
)
from veri_ufku.modeling.lifecycle_worker import calculate as apply
from veri_ufku.modeling.lifecycle_worker import publish_file
from veri_ufku.modeling.unsupervised import calculate as unsupervised
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore, file_hash
from veri_ufku.storage.validation_store import complete


@pytest.mark.parametrize(
    "estimator",
    [
        DummyRegressor(),
        LinearRegression(),
        Ridge(alpha=1),
        RandomForestRegressor(n_estimators=5, max_depth=4, random_state=42),
    ],
)
def test_regression_roundtrip_exact_predictions_all_supported_estimators(
    tmp_path, estimator
):
    store, r, w, v = synthetic(tmp_path)
    with closing(store):
        out = calculate(r, v.data(), w)
        model, card = load_package(out["model_package"]["path"])
        frame = pl.read_parquet(r["path"])
        training = frame.filter(pl.col("__vu_row_id").is_in(card["fit_row_ids"]))
        estimator.fit(
            model.named_steps["prepare"].transform(training), training["y"].to_numpy()
        )
        model.steps[-1] = ("baseline", estimator)
        card["estimator"] = type(estimator).__name__
        path = Path(w) / "roundtrip.vumodel"
        before = model.predict(frame)
        save_package(path, model, card)
        loaded, newcard = load_package(path)
        np.testing.assert_array_equal(before, loaded.predict(frame))
        assert card == newcard
        assert card["features"][0]["type"] == "Float64"
        assert card["target"]["unit"] == "TL"
        assert card["candidate_selection"]["parameters"] == r["regression"]
        assert set(card["importance"]["row_ids"]) == set(
            out["plan"]["membership"]["validation"]
        )
        assert not set(card["importance"]["row_ids"]) & set(
            out["plan"]["membership"]["test"]
        )


@pytest.mark.parametrize(
    "estimator",
    [
        DummyClassifier(strategy="prior"),
        LogisticRegression(),
        RandomForestClassifier(n_estimators=5, max_depth=4, random_state=42),
    ],
)
def test_classification_roundtrip_labels_probabilities_threshold_and_no_fit(
    tmp_path, monkeypatch, estimator
):
    store, r, w, v = classification(tmp_path, multiclass=True)
    with closing(store):
        out = calculate(r, v.data(), w)
        model, card = load_package(out["model_package"]["path"])
        frame = pl.read_parquet(r["path"])
        training = frame.filter(pl.col("__vu_row_id").is_in(card["fit_row_ids"]))
        estimator.fit(
            model.named_steps["prepare"].transform(training), training["y"].to_numpy()
        )
        model.steps[-1] = ("baseline", estimator)
        card["estimator"] = type(estimator).__name__
        path = Path(w) / "roundtrip.vumodel"
        before = model.predict(frame)
        prob = model.predict_proba(frame)
        save_package(path, model, card)
        restored, other = load_package(path)
        np.testing.assert_array_equal(before, restored.predict(frame))
        np.testing.assert_array_equal(prob, restored.predict_proba(frame))

        def forbidden(*args, **kwargs):
            pytest.fail("Yeni veride fit çağrısı")

        monkeypatch.setattr(FoldPreparation, "fit", forbidden)
        monkeypatch.setattr(type(estimator), "fit", forbidden)
        result, details = predict(restored, other, frame, r["columns"], batch_size=7)
        assert result["vu_prediction"].to_list() == before.tolist()
        assert (
            details["label_order"] == estimator.classes_.tolist() == card["label_order"]
        )
        np.testing.assert_array_equal(result["vu_probability_0"].to_numpy(), prob[:, 0])


@pytest.mark.parametrize("method", ["kmeans", "isolation_forest", "iqr"])
def test_unsupervised_roundtrip_scores_and_no_new_fit(tmp_path, monkeypatch, method):
    store, r, w = prepare(
        tmp_path, pl.DataFrame(dict(x=[0.0, 0.1, 0.2, 10.0, 10.1, 10.2, 50.0]))
    )
    with closing(store):
        out = unsupervised(r, spec(r, method, clusters=2), w)
        model, card = load_package(out["model_package"]["path"])
        frame = pl.read_parquet(r["path"])
        assignments = pl.read_parquet(out["assignment_path"])
        if hasattr(type(model.named_steps["baseline"]), "fit"):
            monkeypatch.setattr(
                type(model.named_steps["baseline"]),
                "fit",
                lambda *a, **k: pytest.fail("new fit"),
            )
        results, details = predict(model, card, frame, r["columns"], batch_size=2)
        assert results["__vu_row_id"].to_list() == assignments["__vu_row_id"].to_list()
        if method == "kmeans":
            assert (
                results["vu_prediction"].to_list() == assignments["cluster"].to_list()
            )
        else:
            np.testing.assert_array_equal(
                results["vu_anomaly_score"].to_numpy(),
                assignments["anomaly_score"].to_numpy(),
            )
            assert (
                results["vu_anomaly_candidate"].to_list()
                == assignments["anomaly_candidate"].to_list()
            )
        assert not card["probability_supported"] and details["fit_calls"] == 0


def test_rowid_filter_sort_duplicate_invalid_and_partial_batches(tmp_path, monkeypatch):
    store, r, w, v = synthetic(tmp_path)
    with closing(store):
        out = calculate(r, v.data(), w)
        model, card = load_package(out["model_package"]["path"])
        source = pl.read_parquet(r["path"])
        # Unique RowIds with equal measurement content; subset/filter, reverse sort, bad middle row.
        frame = source.filter(pl.col("x") > 0).sort("x", descending=True).head(17)
        frame = frame.with_columns(
            pl.Series("x", [1.0, 1.0, float("inf"), *frame["x"].to_list()[3:]])
        )
        source_ids = frame["__vu_row_id"].to_list()

        def forbidden(*args, **kwargs):
            pytest.fail("Yeni veride fit")

        monkeypatch.setattr(FoldPreparation, "fit", forbidden)
        monkeypatch.setattr(type(model.named_steps["baseline"]), "fit", forbidden)
        report = preview(model, card, frame, r["columns"])
        assert report["invalid_row_ids"] == [source_ids[2]]
        with pytest.raises(ProjectError, match="Geçersiz"):
            predict(model, card, frame, r["columns"])
        result, detail = predict(
            model, card, frame, r["columns"], invalid="drop", batch_size=6
        )
        assert result["__vu_row_id"].to_list() == source_ids
        assert result.select(frame.columns).equals(frame)
        assert (
            result["vu_prediction_status"].to_list()
            == ["predicted", "predicted", "invalid_dropped"] + ["predicted"] * 14
        )
        assert result["vu_prediction"][2] is None
        assert (
            detail["dropped_row_ids"] == [source_ids[2]]
            and detail["predicted_rows"] == 16
        )
        for row in result.iter_rows(named=True):
            if row["__vu_row_id"] != source_ids[2]:
                assert row["vu_prediction"] == pytest.approx(
                    3 * row["x"] + 7, abs=1e-10
                )
        assert result["vu_prediction"][0] == result["vu_prediction"][1]
        for size in (1, 5, 4096):
            alternate, _ = predict(
                model, card, frame, r["columns"], invalid="drop", batch_size=size
            )
            np.testing.assert_allclose(
                alternate["vu_prediction"].to_numpy(),
                result["vu_prediction"].to_numpy(),
                atol=1e-12,
                equal_nan=True,
            )


def test_permutation_importance_matches_analytic_linear_loss_on_validation(tmp_path):
    store, request, work, protocol = synthetic(tmp_path)
    with closing(store):
        out = calculate(request, protocol.data(), work)
        importance = out["model_card"]["importance"]
        frame = pl.read_parquet(request["path"]).filter(
            pl.col("__vu_row_id").is_in(importance["row_ids"])
        )
        by_id = dict(zip(frame["__vu_row_id"], frame["x"], strict=True))
        x = np.array([by_id[row] for row in importance["row_ids"]])
        rng = np.random.default_rng(importance["seed"])
        # Closed-form y=3x+7: shuffling x incurs 3*mean(abs(x-x_shuffled)).
        reference = [3 * sum(abs(x - rng.permutation(x))) / len(x) for _ in range(3)]
        assert importance["values"][0]["mean"] == pytest.approx(
            sum(reference) / 3, abs=1e-10
        )
        variance = sum((v - sum(reference) / 3) ** 2 for v in reference) / 3
        assert importance["values"][0]["std"] == pytest.approx(variance**0.5, abs=1e-10)
        assert importance["metric"] == "negative_MAE"
        assert not set(importance["row_ids"]) & set(out["plan"]["membership"]["test"])


def rewrite(path, output, mutate):
    with zipfile.ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    mutate(parts)
    parts["integrity.json"] = raw_json(
        {n: sha(parts[n]) for n in ("card.json", "pipeline.skops")}
    )
    with zipfile.ZipFile(output, "w") as z:
        for n, value in parts.items():
            z.writestr(n, value)


@pytest.mark.parametrize(
    "change",
    ["version", "features", "label", "type", "missing", "extra", "hash", "estimator"],
)
def test_incompatible_packages_rejected_before_prediction(tmp_path, change):
    store, r, w, v = synthetic(tmp_path)
    with closing(store):
        out = calculate(r, v.data(), w)
        original = out["model_package"]["path"]
        path = Path(w) / "bad.vumodel"

        def mutate(parts):
            card = json.loads(parts["card.json"])
            if change == "version":
                card["versions"]["scikit-learn"] = "0.0"
            elif change == "features":
                card["features"][0]["id"] = "col:wrong"
            elif change == "label":
                card["label_order"] = ["made_up"]
            elif change == "type":
                card["features"][0]["type"] = "String"
            elif change == "missing":
                card.pop("split")
            elif change == "extra":
                parts["execute.py"] = b"raise RuntimeError"
            elif change == "hash":
                parts["pipeline.skops"] = b"tampered"
            elif change == "estimator":
                card["estimator"] = "SVC"
            parts["card.json"] = raw_json(card)

        rewrite(original, path, mutate)
        with pytest.raises(ProjectError):
            load_package(path)


def test_unsafe_pickle_joblib_and_unreviewed_type_never_executed(tmp_path):
    # Malicious reduction creates a marker only if unpickled. Loader must never do so.
    marker = tmp_path / "executed"

    class Exploit:
        def __reduce__(self):
            return (Path.write_text, (marker, "bad"))

    for suffix in ("pkl", "joblib", "vumodel"):
        path = tmp_path / ("evil." + suffix)
        path.write_bytes(pickle.dumps(Exploit()))
        with pytest.raises(ProjectError):
            load_package(path)
    assert not marker.exists()
    (tmp_path / "safe").mkdir()
    store, r, w, v = synthetic(tmp_path / "safe")
    with closing(store):
        out = calculate(r, v.data(), w)
        bad = Path(w) / "untrusted.vumodel"
        rewrite(
            out["model_package"]["path"],
            bad,
            lambda parts: parts.update({"pipeline.skops": sio.dumps(Exploit())}),
        )
        with pytest.raises(ProjectError, match="izin verilmeyen"):
            load_package(bad)
        assert not marker.exists()


def test_dbscan_unsupported_save_explicitly_blocked(tmp_path):
    store, r, w, v = synthetic(tmp_path)
    with closing(store):
        out = calculate(r, v.data(), w)
        model, card = load_package(out["model_package"]["path"])
        model.steps[-1] = ("baseline", DBSCAN().fit(np.arange(20).reshape(-1, 1)))
        card["estimator"] = "DBSCAN"
        with pytest.raises(ProjectError, match="estimator"):
            save_package(Path(w) / "unsupported.vumodel", model, card)
        assert not (Path(w) / "unsupported.vumodel").exists()


def test_preview_explicit_name_identity_type_unit_missing_extra_and_duplicates(
    tmp_path,
):
    store, r, w, v = synthetic(tmp_path)
    with closing(store):
        out = calculate(r, v.data(), w)
        model, card = load_package(out["model_package"]["path"])
        frame = pl.read_parquet(r["path"])
        feature = card["features"][0]
        renamed = frame.rename({"x": "measurement"})
        columns = copy.deepcopy(r["columns"])
        col = next(c for c in columns if c["name"] == "x")
        col.update(id="col:new", name="measurement")
        assert preview(model, card, renamed, columns)["blockers"]
        mapping = {feature["id"]: "col:new"}
        report = preview(model, card, renamed, columns, mapping)
        assert not report["blockers"] and "y" in report["extra_columns"]
        typed = renamed.with_columns(pl.col("measurement").cast(pl.String))
        assert preview(model, card, typed, columns, mapping)["blockers"]
        card["features"][0]["unit"] = "kg"
        assert preview(model, card, renamed, columns, mapping)["blockers"]
        assert not preview(
            model, card, renamed, columns, mapping, {"col:new": {"unit": "kg"}}
        )["blockers"]
        with pytest.raises(ProjectError, match="RowId"):
            preview(model, card, pl.concat([frame, frame]), r["columns"])


def test_worker_preview_binding_publication_roundtrip_reopen_source_preserved(tmp_path):
    store, r, w, v = synthetic(tmp_path)
    root = store.root
    with closing(store):
        before = Path(r["path"]).read_bytes()
        out = calculate(r, v.data(), w)
        state = complete(store, store.state, out)
        run = state["results"][-1]["baseline"]
        source = dict(r, columns=r["columns"])
        request = dict(
            package=str(store.path(run["model_package_uri"])),
            package_fingerprint=run["model_package_fingerprint"],
            expected_card=run["model_card"],
            source=source,
            mapping={},
            invalid="reject",
            batch_size=13,
        )
        report = apply(request, "preview", w, Control())
        destination = tmp_path / "predicted.parquet"
        request.update(preview_token=report["token"], destination=str(destination))
        progress = []
        applied = apply(
            request,
            "predict",
            w,
            Control(
                progress=lambda phase, done, total: progress.append(
                    Progress(phase, done, total)
                )
            ),
        )
        assert progress[-1].done == progress[-1].total == 120
        frame = pl.read_parquet(destination)
        assert (
            frame["__vu_row_id"].to_list()
            == pl.read_parquet(r["path"])["__vu_row_id"].to_list()
        )
        assert (
            applied["details"]["fit_calls"] == 0
            and Path(r["path"]).read_bytes() == before
        )
        with pytest.raises(ProjectError, match="zaten var"):
            apply(request, "predict", w, Control())
        request["batch_size"] = 3
        with pytest.raises(ProjectError, match="önizleme"):
            apply(request, "predict", w, Control())
    with closing(ProjectStore.open(root)) as reopened:
        restored, card = load_package(reopened.path(run["model_package_uri"]))
        assert card == run["model_card"]
        assert (
            file_hash(reopened.path(run["model_package_uri"]))
            == run["model_package_fingerprint"]
        )


def test_publish_existing_or_symlink_refused(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"unchanged")
    with pytest.raises(ProjectError):
        publish_file(source, source, Control())
    link = tmp_path / "link"
    link.symlink_to(source)
    with pytest.raises(ProjectError):
        publish_file(source, link, Control())
    assert source.read_bytes() == b"unchanged"


def test_onehot_unknown_missing_feature_order_and_variance_preserved(
    tmp_path, monkeypatch
):
    from test_validation import setup_run

    store, r, w, v = setup_run(tmp_path)
    with closing(store):
        out = calculate(r, v.data(), w)
        model, card = load_package(out["model_package"]["path"])
        frame = pl.read_parquet(r["path"]).head(5)
        original = model.named_steps["prepare"].transform(frame)
        # Missing gets TRAIN mean; unknown onehot all-zero. Different physical column order.
        frame = frame.with_columns(
            pl.Series("x", [None, 2.0, 3.0, 4.0, 5.0], dtype=pl.Float64),
            pl.Series("cat", ["NEW", "A", None, "B", "A"]),
        )
        frame = frame.select(list(reversed(frame.columns)))
        report = preview(model, card, frame, r["columns"])
        assert not report["blockers"]
        assert report["features"][0]["missing"] == 1
        assert report["features"][1]["unknown_categories"] == 1

        def nofit(*args, **kwargs):
            pytest.fail("new data fit")

        monkeypatch.setattr(FoldPreparation, "fit", nofit)
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import OneHotEncoder, StandardScaler

        for cls in (OneHotEncoder, StandardScaler, SimpleImputer):
            monkeypatch.setattr(cls, "fit", nofit)
        before = copy.deepcopy(model.named_steps["prepare"].summary_)
        result, details = predict(model, card, frame, r["columns"], batch_size=2)
        assert result["__vu_row_id"].to_list() == frame["__vu_row_id"].to_list()
        assert details["fit_calls"] == 0
        assert model.named_steps["prepare"].summary_ == before
        assert (
            card["fitted_preprocessing"] == before
            and original.shape[1]
            == model.named_steps["prepare"].transform(frame).shape[1]
        )
        changed = copy.deepcopy(card)
        changed["features"].reverse()
        with pytest.raises(ProjectError, match="sırası"):
            save_package(Path(w) / "wrong-order.vumodel", model, changed)


def test_all_invalid_preserves_null_predictions_and_source_rows(tmp_path):
    store, r, w, v = synthetic(tmp_path)
    with closing(store):
        out = calculate(r, v.data(), w)
        model, card = load_package(out["model_package"]["path"])
        frame = (
            pl.read_parquet(r["path"])
            .head(3)
            .with_columns(pl.lit(float("inf")).alias("x"))
        )
        result, details = predict(
            model, card, frame, r["columns"], invalid="drop", batch_size=1
        )
        assert result.select(frame.columns).equals(frame)
        assert (
            result["vu_prediction"].null_count() == 3 and details["predicted_rows"] == 0
        )
        assert result["vu_prediction_status"].to_list() == ["invalid_dropped"] * 3


def publish_contender(source, destination, ready, go, queue):
    ready.set()
    go.wait(10)
    try:
        publish_file(source, destination, Control())
        queue.put("published")
    except (OSError, ProjectError):
        queue.put("refused")


def test_two_process_publication_never_overwrites_the_winner(tmp_path):
    ctx = mp.get_context("spawn")
    sources = [tmp_path / "one", tmp_path / "two"]
    for i, source in enumerate(sources):
        source.write_bytes(bytes([i + 1]) * 1024)
    destination = tmp_path / "result"
    go, queue = ctx.Event(), ctx.Queue()
    ready = [ctx.Event(), ctx.Event()]
    processes = [
        ctx.Process(
            target=publish_contender,
            args=(str(source), str(destination), ready[i], go, queue),
        )
        for i, source in enumerate(sources)
    ]
    try:
        for process in processes:
            process.start()
        assert all(event.wait(10) for event in ready)
        go.set()
        assert sorted([queue.get(timeout=10), queue.get(timeout=10)]) == [
            "published",
            "refused",
        ]
        for process in processes:
            process.join(10)
            assert process.exitcode == 0
        assert destination.read_bytes() in [s.read_bytes() for s in sources]
        assert not list(tmp_path.glob(".vu-model-*"))
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(10)
        queue.close()


def test_save_exports_the_validated_snapshot_even_if_external_package_changes(
    tmp_path, monkeypatch
):
    from veri_ufku.modeling import lifecycle

    store, r, w, v = synthetic(tmp_path)
    with closing(store):
        out = calculate(r, v.data(), w)
        path = Path(out["model_package"]["path"])
        before = path.read_bytes()
        loader = lifecycle.load_package

        def changing_loader(snapshot):
            loaded = loader(snapshot)
            path.write_bytes(b"replaced while loading")
            return loaded

        monkeypatch.setattr(lifecycle, "load_package", changing_loader)
        destination = tmp_path / "export.vumodel"
        apply(
            dict(
                package=str(path),
                package_fingerprint=out["model_package"]["fingerprint"],
                destination=str(destination),
            ),
            "save",
            w,
            Control(),
        )
        assert destination.read_bytes() == before
        loader(destination)


@pytest.mark.parametrize(
    "member", ["../escape", "/absolute", "duplicate", "symlink", "bad-integrity"]
)
def test_hostile_archive_contract_and_integrity_rejected(tmp_path, member):
    store, r, w, v = synthetic(tmp_path)
    with closing(store):
        out = calculate(r, v.data(), w)
        with zipfile.ZipFile(out["model_package"]["path"]) as z:
            parts = {name: z.read(name) for name in z.namelist()}
        bad = Path(w) / "hostile.vumodel"
        with zipfile.ZipFile(bad, "w") as z:
            for name, value in parts.items():
                z.writestr(
                    name,
                    b"{}"
                    if member == "bad-integrity" and name == "integrity.json"
                    else value,
                )
            if member == "duplicate":
                with pytest.warns(UserWarning):
                    z.writestr("card.json", parts["card.json"])
            elif member == "symlink":
                info = zipfile.ZipInfo("link")
                info.external_attr = (0o120777) << 16
                z.writestr(info, b"/tmp/target")
            elif member != "bad-integrity":
                z.writestr(member, b"bad")
        with pytest.raises(ProjectError):
            load_package(bad)


def test_delimited_aliases_allow_exact_type_only_without_refit(tmp_path):
    store, request, workspace, validation = synthetic(tmp_path)
    with closing(store):
        # A delimited dataset records float64/text aliases, while Parquet exposes
        # canonical Polars names. This is the same training/new-file GUI path.
        aliases = {"Float64": "float64", "String": "text", "Int64": "int64"}
        for column in request["columns"]:
            column["type"] = aliases.get(column["type"], column["type"])
        from veri_ufku.modeling.preparation import calculate as prepare_model

        request["preparation"] = prepare_model(
            request, request["preparation"]["spec"], workspace
        )
        result = calculate(request, validation.data(), workspace)
        model, card = load_package(result["model_package"]["path"])
        frame = pl.read_parquet(request["path"])
        semantics = {f["id"]: {"unit": f["unit"]} for f in card["features"]}
        report = preview(model, card, frame, request["columns"], semantics=semantics)
        assert not report["blockers"]
        # A declared type matching the card cannot disguise narrower actual data.
        feature = next(f for f in card["features"] if f["type"] == "float64")
        narrowed = frame.with_columns(pl.col(feature["name"]).cast(pl.Float32))
        assert preview(model, card, narrowed, request["columns"], semantics=semantics)[
            "blockers"
        ]
        before = model.named_steps["prepare"].fit_row_ids_
        model.predict(frame)
        assert model.named_steps["prepare"].fit_row_ids_ == before
