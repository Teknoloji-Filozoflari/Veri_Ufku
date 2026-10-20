"""Independent temporal leakage, aggregation, baselines and persistence evidence."""

import copy
from contextlib import closing
from datetime import date, datetime, timedelta

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.time_series import (
    TimeSeriesSpec,
    calculate,
    forecast,
    historical_features,
    metrics,
    normalize,
)
from veri_ufku.storage.project_model import ProjectError, validate_state
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.time_series_store import finish, load, reserve


def example(n=60, groups=False):
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(n)]
    y = [10.0 + i * 0.2 + [0, 4, -2, 1][i % 4] for i in range(n)]
    if groups:
        return pl.DataFrame(
            dict(
                day=dates * 2,
                value=y + [v + 1000 for v in y],
                group=["a"] * n + ["b"] * n,
            )
        )
    return pl.DataFrame(dict(day=dates, value=y))


def settings(request, **kwargs):
    return TimeSeriesSpec(
        date=column(request, "day"), measurement=column(request, "value"), **kwargs
    )


def test_future_targets_never_change_selection_features_or_forecast(tmp_path):
    with closing(prepare(tmp_path, example())[0]) as store:
        d = store.state["datasets"][-1]
        from veri_ufku.storage.project_store import file_hash

        request = dict(
            path=str(store.path(d["snapshot_uri"])),
            fingerprint=file_hash(store.path(d["snapshot_uri"])),
            columns=d["import_metadata"]["columns"],
            row_count=60,
            version_id=d["version_id"],
            source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
        )
        spec = settings(request, seasonal_period=4, model="seasonal")
        a = calculate(request, spec.data(), tmp_path)
        changed = pl.read_parquet(request["path"]).with_columns(
            pl.when(pl.int_range(pl.len()) >= 54)
            .then(pl.lit(999999.0))
            .otherwise(pl.col("value"))
            .alias("value")
        )
        path = tmp_path / "future-changed.parquet"
        changed.write_parquet(path)
        b = calculate(
            dict(request, path=str(path), fingerprint=file_hash(path)),
            spec.data(),
            tmp_path,
        )
        assert a["groups"] == b["groups"]
        g = a["groups"][0]
        assert all(p["actual"] is None for p in g["forecast"])
        assert g["future_forecast"][0]["date"] > g["test_end"]
        assert not set(g["train_row_ids"]) & set(g["test_row_ids"])
        for f in g["folds"]:
            assert not set(f["train_row_ids"] + f["validation_row_ids"]) & set(
                g["test_row_ids"]
            )
            assert f["train_end"] < f["validation_start"]
        assert {c["method"] for c in g["comparisons"]} == {
            "naive",
            "seasonal-naive",
            "seasonal",
        }


def test_lag_and_rolling_only_use_strictly_prior_values():
    a = historical_features([1, 2, 3, 100, 999], 2)
    b = historical_features([1, 2, 3, -1000, -999], 2)
    assert a[:4] == b[:4]
    assert a[3]["lag"] == 3 and a[3]["rolling"] == 2.5
    assert a[0]["lag"] is None and a[1]["rolling"] is None


def test_baselines_and_metrics_are_real():
    assert forecast([1, 2, 7], 3, "naive", 0, Control()) == [7, 7, 7]
    assert forecast([1, 2, 5, 8], 5, "seasonal-naive", 2, Control()) == [5, 8, 5, 8, 5]
    m = metrics([0, 2], [1, 4])
    assert m["mae"] == 1.5 and m["rmse"] == pytest.approx(np.sqrt(2.5))
    assert m["mape"] is None


def test_group_isolation_and_short_history(tmp_path):
    store, r, work = prepare(tmp_path, example(groups=True))
    with closing(store):
        s = settings(r, group=column(r, "group"), model="none")
        result = calculate(r, s.data(), work)
        a, b = result["groups"]
        assert b["forecast"][0]["predicted"] - a["forecast"][0][
            "predicted"
        ] == pytest.approx(1000)
        assert not set(a["train_row_ids"] + a["test_row_ids"]) & set(
            b["train_row_ids"] + b["test_row_ids"]
        )
        with pytest.raises(ProjectError, match="çok kısa"):
            calculate(
                r,
                settings(r, group=column(r, "group"), seasonal_period=30).data(),
                work,
            )


@pytest.mark.parametrize("issue", ["duplicate", "missing", "offset"])
def test_irregular_never_silently_regular(tmp_path, issue):
    f = example()
    if issue == "duplicate":
        f = pl.concat([f, f.head(1)])
    elif issue == "missing":
        f = f.filter(pl.col("day") != date(2026, 1, 10))
    else:
        f = f.with_columns(pl.col("day").cast(pl.Datetime) + pl.duration(hours=2))
    store, r, work = prepare(tmp_path, f)
    with closing(store), pytest.raises(ProjectError, match="duplicate|düzensiz"):
        calculate(r, settings(r, timezone="UTC").data(), work)


def test_explicit_resampling_sum_mean_and_missing_bins(tmp_path):
    f = pl.concat([example(), example()])
    store, r, work = prepare(tmp_path, f)
    with closing(store):
        s = settings(r, resample=True, aggregation="sum", model="none")
        total = calculate(r, s.data(), work)["groups"][0]
        mean = calculate(
            r, settings(r, resample=True, aggregation="mean", model="none").data(), work
        )["groups"][0]
        assert total["forecast"][0]["predicted"] == 2 * mean["forecast"][0]["predicted"]
        assert total["duplicate_dates"] == 60
        missing = (
            f.filter(pl.col("day") != date(2026, 1, 10))
            .with_row_index("x")
            .with_columns(pl.col("x").cast(pl.String).alias("__vu_row_id"))
        )
        with pytest.raises(ProjectError, match="eksik dönem"):
            normalize(missing, r["columns"], s)


def test_timezone_naive_requires_choice_dst_rejected(tmp_path):
    store, r, work = prepare(
        tmp_path, example().with_columns(pl.col("day").cast(pl.Datetime))
    )
    with closing(store):
        with pytest.raises(ProjectError, match="IANA"):
            calculate(r, settings(r).data(), work)
        assert (
            calculate(
                r, settings(r, timezone="Europe/Istanbul", model="none").data(), work
            )["groups"][0]["timezone"]
            == "Europe/Istanbul"
        )
        frame = pl.DataFrame(
            dict(day=[datetime(2026, 3, 29, 2, 30)], value=[1.0], __vu_row_id=["row"])
        )
        spec = settings(r, timezone="Europe/Berlin", frequency="h")
        with pytest.raises(ProjectError, match="DST"):
            normalize(frame, r["columns"], spec)


def test_final_frozen_choice_journal_and_reopen(tmp_path):
    store, r, work = prepare(tmp_path, example())
    s = settings(r, model="trend")
    dev = calculate(r, s.data(), work)
    state, record = finish(store, store.state, dev)
    restored = load(store, record)
    state, use_id = reserve(store, state, restored)
    final = calculate(dict(r, mode="final", development=restored), s.data(), work)
    assert final["groups"][0]["chosen"] == dev["groups"][0]["chosen"]
    assert len(final["groups"][0]["final_metrics"]) >= 1
    state, result = finish(store, state, final, use_id)
    path = store.root
    store.close()
    with closing(ProjectStore.open(path)) as reopened:
        assert load(reopened, result)["groups"] == final["groups"]
        state, use2 = reserve(reopened, reopened.state, restored)
        state, _ = finish(reopened, state, None, use2, "canceled")
        nextdev = calculate(
            dict(
                r,
                path=str(reopened.path(reopened.state["datasets"][-1]["snapshot_uri"])),
            ),
            s.data(),
            work,
        )
        state, rec = finish(reopened, state, nextdev)
        assert load(reopened, rec)["prior_test_use_ids"] == [use_id, use2]
        assert "keşifsel" in load(reopened, rec)["interpretation"]
        bad = copy.deepcopy(state)
        next(x for x in bad["results"] if x["id"] == use_id)["time_series_test_use"][
            "development_run_id"
        ] = "missing"
        with pytest.raises(ProjectError):
            validate_state(bad)


def test_source_fingerprint_and_final_protocol_cannot_change(tmp_path):
    store, r, work = prepare(tmp_path, example())
    with closing(store):
        s = settings(r, model="none")
        dev = calculate(r, s.data(), work)
        with pytest.raises(ProjectError, match="aynı ayar"):
            calculate(
                dict(r, mode="final", development=dev),
                settings(r, model="none", horizon=2).data(),
                work,
            )
        with pytest.raises(ProjectError, match="snapshot"):
            calculate(
                dict(r, fingerprint=dict(size=1, sha256="0" * 64)), s.data(), work
            )


def test_ets_fit_receives_only_training_prefixes(tmp_path, monkeypatch):
    import veri_ufku.modeling.time_series as module

    store, r, work = prepare(tmp_path, example())
    real = module.ExponentialSmoothing
    seen = []

    def spy(endog, **kwargs):
        seen.append(list(endog))
        return real(endog, **kwargs)

    monkeypatch.setattr(module, "ExponentialSmoothing", spy)
    with closing(store):
        result = calculate(r, settings(r, model="trend").data(), work)
        past = example()["value"].to_list()[:54]
        assert seen and all(y == past[: len(y)] and len(y) <= 54 for y in seen)
        assert result["groups"][0]["chosen"] in ("naive", "trend")


@pytest.mark.parametrize(
    "frequency,start,step",
    [("W-MON", date(2026, 1, 5), 7), ("MS", date(2026, 1, 1), 0)],
)
def test_calendar_frequency_and_explicit_bins(tmp_path, frequency, start, step):
    dates = (
        [start + timedelta(days=i * step) for i in range(40)]
        if step
        else [date(2026 + i // 12, i % 12 + 1, 1) for i in range(40)]
    )
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(day=dates, value=[1.0] * 40)))
    with closing(store):
        result = calculate(
            r, settings(r, frequency=frequency, model="none").data(), work
        )
        assert result["groups"][0]["missing_periods"] == 0
        assert (
            result["groups"][0]["future_forecast"][0]["date"]
            > result["groups"][0]["test_end"]
        )


def test_publish_fault_preserves_active_and_cross_path_test_history(tmp_path):
    from veri_ufku.storage.validation_store import prior_uses

    store, r, work = prepare(tmp_path, example())
    with closing(store):
        dev = calculate(r, settings(r, model="none").data(), work)
        before = store.commit_id

        seen = []

        def checkpoint(point):
            seen.append(point)
            if point == "artifact_promoted":
                raise OSError("injected")

        with pytest.raises(OSError):
            finish(store, store.state, dev, checkpoint=checkpoint)
        assert "artifact_promoted" in seen and store.commit_id == before
        state, record = finish(store, store.state, dev)
        state, ident = reserve(store, state, load(store, record))
        assert prior_uses(state) == [ident]
        state, _ = finish(store, state, None, ident, "failed")
        assert prior_uses(state) == [ident]


def test_history_with_full_data_fit_or_ordered_fill_is_blocked(monkeypatch):
    from veri_ufku.storage.time_series_store import check_history

    monkeypatch.setattr(
        "veri_ufku.modeling.history.audit",
        lambda *args: dict(findings=[dict(risk="dataset_learned", kind="fill")]),
    )
    with pytest.raises(ProjectError, match="geleceğin"):
        check_history({}, "dv:any")


@pytest.mark.parametrize("model", ["level", "trend", "seasonal"])
def test_each_supported_ets_candidate_has_real_baseline_comparison(tmp_path, model):
    store, request, work = prepare(tmp_path, example())
    with closing(store):
        spec = settings(request, model=model, seasonal_period=4)
        result = calculate(request, spec.data(), work)
        g = result["groups"][0]
        assert not g["invalid_models"]
        assert {c["method"] for c in g["comparisons"]} == {
            "naive",
            "seasonal-naive",
            model,
        }
        best = min(g["comparisons"], key=lambda c: c["mae"])
        assert g["chosen"] == best["method"]
        assert result["interval"] is None
