"""Real temporal backtests, reference metrics and no future covariate/target leakage."""

import copy
from contextlib import closing
from dataclasses import replace
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.modeling.temporal import croston, hierarchy_leaves, scores, token
from veri_ufku.modeling.temporal_contracts import TemporalSpec
from veri_ufku.modeling.time_series import TimeSeriesSpec, calculate, validate_run
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore, file_hash
from veri_ufku.storage.time_series_store import finish, load, reserve


def fixture(tmp_path, method="arima", groups=2, task="forecast", **options):
    rng = np.random.default_rng(53)
    n = 80
    days = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    series = []
    cov = []
    other = []
    for g in range(groups):
        x = rng.normal(size=n)
        y = np.zeros(n)
        z = np.zeros(n)
        for i in range(1, n):
            y[i] = 0.4 * y[i - 1] + 0.1 * z[i - 1] + 0.7 * x[i] + rng.normal(scale=0.3)
            z[i] = 0.5 * z[i - 1] + rng.normal(scale=0.4)
        series.extend(y + g * 0.4)
        cov.extend(x)
        other.extend(z)
    frame = pl.DataFrame(
        dict(
            day=days * groups,
            value=series,
            x=cov,
            z=other,
            group=sum(([f"g{g}"] * n for g in range(groups)), []),
            label=sum((["A" if g % 2 == 0 else "B"] * n for g in range(groups)), []),
        )
    )
    store, _, work = prepare(tmp_path, frame)
    d = store.state["datasets"][-1]
    r = dict(
        path=str(store.path(d["snapshot_uri"])),
        fingerprint=file_hash(store.path(d["snapshot_uri"])),
        columns=d["import_metadata"]["columns"],
        row_count=frame.height,
        version_id=d["version_id"],
        source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
    )
    if (
        method == "sarimax"
        and "known_future" not in options
        and "past_covariates" not in options
    ):
        options.update(
            known_future=[column(r, "x")],
            availability={
                column(r, "x"): "Scheduled and known at each historical origin"
            },
        )
    if method == "var":
        options.update(
            var_columns=[column(r, "z")],
            var_assumption="Stable generated stationary autoregression; observational assumption",
        )
    extra = TemporalSpec(method=method, task=task, lags=4, **options)
    base = TimeSeriesSpec(
        date=column(r, "day"),
        measurement=column(r, "value"),
        group=column(r, "group"),
        seasonal_period=4
        if method in ("sarima", "sarimax")
        or set(extra.diagnostics) & {"stl", "decomposition"}
        else 0,
        test_periods=8,
        horizon=3,
        folds=2,
        advanced=extra.data(),
    )
    return store, r, work, base


@pytest.mark.parametrize(
    "method",
    ["arima", "sarima", "sarimax", "var", "global-ridge", "croston", "seasonal-naive"],
)
def test_real_model_by_horizon_backtest_and_panel_ids(tmp_path, method):
    store, r, work, base = fixture(tmp_path, method)
    with closing(store):
        if method == "seasonal-naive":
            base = replace(base, seasonal_period=4)
        if method == "croston":
            frame = pl.read_parquet(r["path"]).with_columns(pl.col("value").abs())
            frame.write_parquet(r["path"])
            r["fingerprint"] = file_hash(r["path"])
        result = calculate(r, base.data(), work)
        validate_run(result, store.state["datasets"][-1])
        assert len(result["groups"]) == 2
        for group in result["groups"]:
            assert method in {m["method"] for m in group["comparisons"]}, group[
                "invalid_models"
            ]
            fs = [f for f in group["folds"] if f["method"] == method]
            assert len(fs) == 2 and all(
                f["train_end"] < f["validation_start"] for f in fs
            )
            assert all(
                not set(f["validation_row_ids"]) & set(group["test_row_ids"])
                for f in fs
            )
            assert all(p["lead"] == p["horizon"] for f in fs for p in f["points"])
            assert [
                h["n"]
                for h in next(c for c in group["comparisons"] if c["method"] == method)[
                    "per_horizon"
                ]
            ] == [2, 2, 2]
            assert {group["series_id"]} == {token(group)}
        assert result["advanced"]["provenance"]["seed"] == 53


def test_future_target_and_past_covariate_poison_do_not_change_backtest(tmp_path):
    store, r, work, base = fixture(
        tmp_path, "sarimax", known_future=[], past_covariates=[], availability={}
    )
    with closing(store):
        x = column(r, "x")
        extra = TemporalSpec(
            method="sarimax",
            lags=12,
            past_covariates=[x],
            availability={x: "Observed only once recorded in history"},
        )
        base = replace(base, advanced=extra.data())
        a = calculate(r, base.data(), work)
        changed = pl.read_parquet(r["path"]).with_columns(
            pl.when(pl.col("day") >= date(2024, 1, 1) + timedelta(days=72))
            .then(99999.0)
            .otherwise(pl.col("x"))
            .alias("x"),
            pl.when(pl.col("day") >= date(2024, 1, 1) + timedelta(days=72))
            .then(-99999.0)
            .otherwise(pl.col("value"))
            .alias("value"),
        )
        dest = work / "poison.parquet"
        changed.write_parquet(dest)
        b = calculate(
            dict(r, path=str(dest), fingerprint=file_hash(dest)), base.data(), work
        )
        assert a["groups"] == b["groups"]
        assert "sarimax" in {c["method"] for c in a["groups"][0]["comparisons"]}, a[
            "groups"
        ][0]["invalid_models"]
        with pytest.raises(ProjectError):
            replace(base, advanced=replace(extra, lags=1).data()).validate(r["columns"])


def test_mase_training_only_and_probabilistic_hand_reference():
    a = scores([5.0, 7.0], [4.0, 5.0], [1.0, 2.0, 3.0, 4.0])
    assert a["mase_denominator"] == 1 and a["mase"] == 1.5
    assert a["mae"] == 1.5 and a["rmse"] == pytest.approx(np.sqrt(2.5))
    assert scores([1000.0], [0.0], [1.0, 1.0, 1.0])["mase"] is None
    p = scores([0.0], [0.0], [1.0, 2.0, 3.0], distribution={"sd": [1.0]})[
        "probabilistic"
    ]
    assert p["coverage"] == 1 and p["crps"] == pytest.approx(
        (np.sqrt(2) - 1) / np.sqrt(np.pi)
    )
    assert p["pinball"][1]["value"] == 0


@pytest.mark.parametrize(
    "diagnostic",
    ["decomposition", "stl", "acf", "pacf", "stationarity", "change-point"],
)
def test_real_diagnostic_only_development_and_safe_archive(tmp_path, diagnostic):
    store, r, work, base = fixture(
        tmp_path, task="diagnostics", diagnostics=[diagnostic]
    )
    with closing(store):
        value = calculate(r, base.data(), work)
        assert value["groups"][0]["diagnostics"][diagnostic]["status"] == "available"
        assert not value["groups"][0]["comparisons"]
        state, record = finish(store, store.state, value)
        assert load(store, record) == dict(
            value,
            prior_test_use_ids=[],
            interpretation="Bu projede önceki final test kullanımı yok; proje dışı kullanım bilinmez.",
        )
        root = store.root
    with closing(ProjectStore.open(root)) as reopened:
        assert (
            load(reopened, reopened.state["results"][-1])["advanced"]["spec"]["task"]
            == "diagnostics"
        )


def test_gap_global_cutoff_and_bottom_up_reference(tmp_path):
    store, r, work, base = fixture(
        tmp_path,
        "global-ridge",
        gap=2,
        embargo=1,
        hierarchy=[
            ["total", json_token] for json_token in ('["str", "g0"]', '["str", "g1"]')
        ],
    )
    with closing(store):
        v = calculate(r, base.data(), work)
        for g in v["groups"]:
            for f in g["folds"]:
                assert f["gap"] == 3 and f["points"][0]["lead"] == 4
                if f["method"] == "global-ridge":
                    assert not set(f["backend"]["fit_row_ids"]) & set(g["test_row_ids"])
        rec = next(
            p for p in v["advanced"]["reconciliation"] if p["method"] == "global-ridge"
        )
        fs = [
            next(
                f
                for f in g["folds"]
                if f["method"] == "global-ridge" and f["origin"] == rec["origin"]
            )
            for g in v["groups"]
        ]
        np.testing.assert_allclose(
            rec["predicted"],
            np.sum([[p["predicted"] for p in f["points"]] for f in fs], axis=0),
        )
    with pytest.raises(ProjectError):
        hierarchy_leaves([["a", "b"], ["b", "a"]], [])
    with pytest.raises(ProjectError):
        hierarchy_leaves([["a", "leaf"], ["b", "leaf"]], ["leaf"])
    assert croston([0, 2, 0, 0], 0.1) == 1.0


@pytest.mark.parametrize("task", ["classification", "clustering"])
def test_whole_series_tasks_not_tabular_random_segments(tmp_path, task):
    store, r, work, base = fixture(tmp_path, groups=6, task=task, diagnostics=[])
    with closing(store):
        options = (
            dict(
                label=column(r, "label"),
                training_series=[
                    '["str", "g0"]',
                    '["str", "g1"]',
                    '["str", "g2"]',
                    '["str", "g3"]',
                ],
                validation_series=['["str", "g4"]', '["str", "g5"]'],
            )
            if task == "classification"
            else {}
        )
        base = replace(
            base, advanced=TemporalSpec(task=task, diagnostics=[], **options).data()
        )
        v = calculate(r, base.data(), work)
        validate_run(v, store.state["datasets"][-1])
        result = v["advanced"]["series_task"]
        if task == "classification":
            assert result["n"] == 2 and len(result["predictions"]) == 2
            validation_ids = set(sum([g["train_row_ids"] for g in v["groups"][4:]], []))
            assert not set(result["fit_row_ids"]) & validation_ids
        else:
            assert len(result["members"]) == 6


def test_past_covariate_current_origin_realized_future_is_inaccessible(tmp_path):
    from veri_ufku.importers.delimited import Control
    from veri_ufku.modeling.temporal import covariates, predict
    from veri_ufku.modeling.time_series import normalize

    store, r, work, base = fixture(tmp_path, "sarimax")
    with closing(store):
        x = column(r, "x")
        extra = TemporalSpec(
            method="sarimax",
            lags=12,
            past_covariates=[x],
            availability={x: "Only historically observed, fixed lag6"},
        )
        base = replace(base, advanced=extra.data())
        frame = pl.read_parquet(r["path"])
        g = normalize(frame, r["columns"], base)[0]
        origin = 60
        steps = 3
        a, b, ids = covariates(frame, g, base, extra, origin, steps, r["columns"])
        poisoned = frame.with_columns(
            pl.when(pl.col("day") >= date(2024, 1, 1) + timedelta(days=origin))
            .then(999999.0)
            .otherwise(pl.col("x"))
            .alias("x")
        )
        c, d, ids2 = covariates(poisoned, g, base, extra, origin, steps, r["columns"])
        np.testing.assert_array_equal(a, c)
        np.testing.assert_array_equal(b, d)
        assert ids == ids2 and not set(ids) & set(sum(g["members"][origin:], []))
        p1, _, _ = predict(
            "sarimax", g["series"].iloc[:origin], steps, base, extra, Control(), (a, b)
        )
        p2, _, _ = predict(
            "sarimax", g["series"].iloc[:origin], steps, base, extra, Control(), (c, d)
        )
        np.testing.assert_array_equal(p1, p2)


def test_registry_temporal_protocol_and_source_metric_tamper(tmp_path):
    from veri_ufku.storage.experiment_store import compare

    store, r, work, base = fixture(tmp_path, "arima")
    with closing(store):
        v = calculate(r, base.data(), work)
        _, record = finish(store, store.state, v)
        report = compare(store, [v["run_id"]], "mase")
        assert report["comparable"] and report["rows"][0]["folds"]
        bad = copy.deepcopy(v)
        bad["groups"][0]["folds"][0]["metrics"]["mase_denominator"] *= 2
        with pytest.raises(ProjectError, match="MASE"):
            finish(store, store.state, bad)


def test_final_frozen_forecast_journal_and_cancel_timeout(tmp_path):
    import threading

    from veri_ufku.domain.contracts import ComputeBudget
    from veri_ufku.importers.delimited import Control
    from veri_ufku.jobs.workers import Canceled

    store, r, work, base = fixture(tmp_path, "arima")
    with closing(store):
        v = calculate(r, base.data(), work)
        _, record = finish(store, store.state, v)
        state, ident = reserve(store, store.state, v)
        final = calculate(dict(r, mode="final", development=v), base.data(), work)
        state, item = finish(store, state, final, ident)
        assert load(store, item)["mode"] == "final"
        from veri_ufku.storage.experiment_store import rows

        assert any(
            row["test_uses"] for row in rows(store) if row["kind"] == "time_series"
        )
        assert state["results"][-2]["time_series_test_use"]["status"] == "completed"
        event = threading.Event()
        event.set()
        with pytest.raises(Canceled):
            calculate(r, base.data(), work, Control(cancel=event))
        c = Control(budget=ComputeBudget(max_wall_seconds=1))
        c.started -= 2
        with pytest.raises(ProjectError, match="süre"):
            calculate(r, base.data(), work, c)


def test_temporal_registry_export_omits_raw_group_names(tmp_path):
    from test_time_series import example

    from veri_ufku.storage.experiment_store import export

    data = example(groups=True).with_columns(
        pl.when(pl.col("group") == "a")
        .then(pl.lit("sentinel-password-secret-name"))
        .otherwise(pl.col("group"))
        .alias("group")
    )
    store, _, work = prepare(tmp_path, data)
    with closing(store):
        d = store.state["datasets"][-1]
        r = dict(
            path=str(store.path(d["snapshot_uri"])),
            fingerprint=file_hash(store.path(d["snapshot_uri"])),
            columns=d["import_metadata"]["columns"],
            row_count=data.height,
            version_id=d["version_id"],
            source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
        )
        base = TimeSeriesSpec(
            date=column(r, "day"),
            measurement=column(r, "value"),
            group=column(r, "group"),
            advanced=TemporalSpec(method="naive", diagnostics=[]).data(),
        )
        v = calculate(r, base.data(), work)
        finish(store, store.state, v)
        target = tmp_path / "masked-registry.json"
        export(store, [v["run_id"]], target)
        assert "sentinel-password-secret-name" not in target.read_text()
