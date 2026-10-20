"""Independent exhaustive null, cluster identity, BCa and family references."""

import itertools
import json
import math
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from threading import Event

import numpy as np
import polars as pl
import pytest
from scipy import stats
from scipy.special import ndtr, ndtri
from test_dataset import column, prepare

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.statistics.contracts import AnalysisSpec
from veri_ufku.statistics.engine import calculate
from veri_ufku.storage.analysis_store import publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def recipe(request, method="bootstrap_percentile", **changes):
    changes.setdefault("resamples", 1000)
    return AnalysisSpec(
        path="resampling",
        method=method,
        x=column(request, "x"),
        question="Önceden belirlenen resampling sorusu",
        hypothesis="H0 exchangeable birim dağılımları / fark0",
        unit="puan",
        observation_unit="bağımsız birim",
        measurement_confirmed=True,
        independent=True,
        assumptions_confirmed=True,
        **changes,
    )


def frame():
    return pl.DataFrame(
        dict(
            x=[1.0, 2.0, 3.0, 5.0, 7.0, 8.0, 9.0, 12.0, 15.0, 17.0, 18.0, 21.0],
            cluster=["c0"] * 2 + ["c1"] * 4 + ["c2"] * 3 + ["c3"] * 3,
            time=list(range(12)),
            label=["A"] * 6 + ["B"] * 6,
            pair=[f"p{i}" for i in range(12)],
            after=[2.0, 5.0, 4.0, 7.0, 7.0, 9.0, 10.0, 14.0, 19.0, 18.0, 20.0, 24.0],
        )
    )


@pytest.mark.parametrize("unit", ["observation", "cluster", "time_block"])
def test_bootstrap_draw_identity_seed_and_quantile_reference(tmp_path, unit):
    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        fields = {c["name"]: c["id"] for c in r["columns"]}
        s = recipe(
            r,
            resampling_unit=unit,
            dependence={
                "observation": "independent",
                "cluster": "grouped",
                "time_block": "temporal",
            }[unit],
            cluster=fields["cluster"] if unit == "cluster" else "",
            time_column=fields["time"] if unit == "time_block" else "",
            block_length=3,
        )
        result = calculate(r, s, work)
        detail = pl.read_parquet(result["paths"]["details"])
        raw = pl.read_parquet(r["path"])
        values = dict(zip(raw["__vu_row_id"].to_list(), raw["x"].to_list()))
        dist = detail.filter(pl.col("kind") == "distribution")["value"].to_numpy()
        mapping = result["unit_members"]
        draws = detail.filter(pl.col("kind") == "draw")
        for b in (0, 1, 13, 999):
            keys = draws.filter(pl.col("replicate") == b)["unit_id"].to_list()
            rows = [rid for k in keys for rid in mapping[k]]
            if unit == "time_block":
                rows = rows[:12]
            assert dist[b] == pytest.approx(np.mean([values[rid] for rid in rows]))
            if unit == "cluster":
                for k in keys:
                    assert set(mapping[k]) == set(
                        raw.filter(pl.col("cluster") == k)["__vu_row_id"].to_list()
                    )
            if unit == "time_block":
                for k in keys:
                    assert len(mapping[k]) == 3
        ci = result["bootstrap"]["confidence_interval"]
        assert [ci["low"], ci["high"]] == pytest.approx(
            np.quantile(dist, [0.025, 0.975])
        )
        assert ci["monte_carlo"]["endpoint_bands"]
        before = Path(result["paths"]["details"]).read_bytes()
        again = calculate(r, s, work)
        assert before == Path(again["paths"]["details"]).read_bytes()
        assert again["bootstrap"] == result["bootstrap"]
        other = calculate(r, replace(s, seed=43), work)
        assert (
            other["bootstrap"]["confidence_interval"]
            != result["bootstrap"]["confidence_interval"]
        )


@pytest.mark.parametrize("unit", ["observation", "cluster"])
def test_bca_independent_midrank_jackknife_formula(tmp_path, unit):
    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        s = recipe(
            r,
            "bootstrap_bca",
            resampling_unit=unit,
            dependence="grouped" if unit == "cluster" else "independent",
            cluster=column(r, "cluster") if unit == "cluster" else "",
        )
        result = calculate(r, s, work)
        dist = (
            pl.read_parquet(result["paths"]["details"])
            .filter(pl.col("kind") == "distribution")["value"]
            .to_numpy()
        )
        ci = result["bootstrap"]["confidence_interval"]
        assert ci["status"] == "available"
        raw = pl.read_parquet(r["path"])
        values = dict(zip(raw["__vu_row_id"].to_list(), raw["x"].to_list()))
        j = np.array(
            [
                np.mean([v for rid, v in values.items() if rid not in ids])
                for ids in result["unit_members"].values()
            ]
        )
        center = j.mean() - j
        acc = np.sum(center**3) / (6 * np.sum(center**2) ** 1.5)
        z0 = ndtri(
            (
                np.sum(dist < np.mean(list(values.values())))
                + 0.5 * np.sum(dist == np.mean(list(values.values())))
            )
            / len(dist)
        )
        z = ndtri([0.025, 0.975])
        p = ndtr(z0 + (z0 + z) / (1 - acc * (z0 + z)))
        assert ci["acceleration"] == pytest.approx(acc)
        assert ci["bias_correction"] == pytest.approx(z0)
        assert [ci["low"], ci["high"]] == pytest.approx(np.quantile(dist, p))


@pytest.mark.parametrize("method", ["bootstrap_percentile", "bootstrap_bca"])
def test_constant_bootstrap_never_fabricates_ci(tmp_path, method):
    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [5.0] * 8}))
    with closing(store):
        result = calculate(r, recipe(r, method), work)
        ci = result["bootstrap"]["confidence_interval"]
        assert (
            ci["low"] is None
            and ci["high"] is None
            and ci["status"].startswith("unavailable")
        )


@pytest.mark.parametrize("tail", ["two-sided", "less", "greater"])
def test_small_exhaustive_group_permutation_independent_reference(tmp_path, tail):
    values = [1.0, 2.0, 4.0, 5.0, 6.0, 8.0]
    labels = ["A"] * 3 + ["B"] * 3
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(x=values, label=labels)))
    with closing(store):
        result = calculate(
            r,
            recipe(
                r,
                "permutation",
                group=column(r, "label"),
                before="A",
                after="B",
                exchangeability_confirmed=True,
                alternative=tail,
            ),
            work,
        )
        p = result["permutation"]
        observed = np.mean(values[3:]) - np.mean(values[:3])
        null = []
        for selected in itertools.combinations(range(6), 3):
            null.append(
                np.mean([values[i] for i in selected])
                - np.mean([values[i] for i in range(6) if i not in selected])
            )
        hits = sum(
            abs(v) >= abs(observed) - 1e-12
            if tail == "two-sided"
            else v >= observed - 1e-12
            if tail == "greater"
            else v <= observed + 1e-12
            for v in null
        )
        assert p["performed"] == math.comb(6, 3) and p["exact"]
        assert p["p_value"] == pytest.approx(hits / 20)
        assert p["monte_carlo"] is None


@pytest.mark.parametrize("unit", ["observation", "cluster"])
def test_exact_paired_sign_flip_preserves_keys_and_cluster_sign(tmp_path, unit):
    store, r, work = prepare(
        tmp_path,
        frame()
        .head(6)
        .with_columns(pl.Series("cluster", ["c0"] * 2 + ["c1"] * 2 + ["c2"] * 2)),
    )
    with closing(store):
        s = recipe(
            r,
            "paired_sign_flip",
            y=column(r, "after"),
            key=column(r, "pair"),
            exchangeability_confirmed=True,
            symmetry_confirmed=True,
            resampling_unit=unit,
            dependence="grouped" if unit == "cluster" else "independent",
            cluster=column(r, "cluster") if unit == "cluster" else "",
        )
        result = calculate(r, s, work)
        diff = np.array([1.0, 3.0, 1.0, 2.0, 0.0, 1.0])
        diff = diff.reshape(3, 2).mean(axis=1) if unit == "cluster" else diff
        observed = diff.mean()
        null = [
            np.mean(diff * np.array(sign))
            for sign in itertools.product([-1, 1], repeat=len(diff))
        ]
        expected = np.mean(np.abs(null) >= abs(observed) - 1e-12)
        assert result["permutation"]["p_value"] == pytest.approx(expected)
        assert result["permutation"]["performed"] == 2 ** len(diff)
        assert result["unit_members"]


@pytest.mark.parametrize("method", ["permutation", "paired_sign_flip"])
def test_monte_carlo_plus_one_tail_uncertainty_and_seed(tmp_path, method):
    f = frame()
    f = pl.concat([f, f.with_columns(pl.col("time") + 12, pl.col("pair") + "extra")])
    store, r, work = prepare(tmp_path, f)
    with closing(store):
        s = recipe(
            r,
            method,
            exchangeability_confirmed=True,
            group=column(r, "label") if method == "permutation" else "",
            before="A",
            after="B",
            y=column(r, "after") if method == "paired_sign_flip" else "",
            key=column(r, "pair") if method == "paired_sign_flip" else "",
            symmetry_confirmed=method == "paired_sign_flip",
        )
        result = calculate(r, s, work)
        p = result["permutation"]
        assert not p["exact"] and p["performed"] == 1000
        assert p["p_value"] == (p["extreme_count"] + 1) / 1001
        assert (
            p["monte_carlo"]["low"]
            <= p["extreme_count"] / 1000
            <= p["monte_carlo"]["high"]
        )
        again = calculate(r, s, work)
        assert result["permutation"] == again["permutation"]


def test_cluster_permutation_exhaustive_unit_mean(tmp_path):
    f = pl.DataFrame(
        dict(
            x=[1.0, 1.0, 3.0, 5.0, 5.0, 5.0, 8.0, 8.0],
            cluster=["c0", "c0", "c1", "c2", "c2", "c2", "c3", "c3"],
            label=["A", "A", "A", "B", "B", "B", "B", "B"],
        )
    )
    store, r, work = prepare(tmp_path, f)
    with closing(store):
        result = calculate(
            r,
            recipe(
                r,
                "permutation",
                resampling_unit="cluster",
                dependence="grouped",
                cluster=column(r, "cluster"),
                group=column(r, "label"),
                before="A",
                after="B",
                exchangeability_confirmed=True,
            ),
            work,
        )
        assert result["permutation"]["estimate"] == 4.5
        assert result["permutation"]["performed"] == 6


@pytest.mark.parametrize(
    "method,expected",
    [
        ("adjust_holm", [0.04, 0.09, 0.09, 0.2]),
        ("adjust_bonferroni", [0.04, 0.16, 0.12, 0.8]),
        ("adjust_bh", [0.04, 0.0533333333333, 0.0533333333333, 0.2]),
    ],
)
def test_family_explicit_ids_independent_correction_and_atomic_reopen(
    tmp_path, method, expected
):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                x=[0.01, 0.04, 0.03, 0.2, 0.000001],
                test_id=["t1", "t2", "t3", "t4", "outside"],
            )
        ),
    )
    with closing(store):
        s = recipe(
            r,
            method,
            key=column(r, "test_id"),
            family_name="planned endpoints",
            family_ids=["t1", "t2", "t3", "t4"],
            family_dependence="independent" if method == "adjust_bh" else "arbitrary",
        )
        result = calculate(r, s, work)
        fam = result["family"]
        assert [t["p_adjusted"] for t in fam["tests"]] == pytest.approx(expected)
        assert fam["outside_family"] == ["outside"]
        assert fam["size"] == 4
        assert result["used_rows"] == 4
        state = publish(store, store.state, result)
        root = store.root
        store.close()
        reopened = ProjectStore.open(root)
        with closing(reopened):
            assert (
                reopened.state["results"][-1]["analysis"]["family"]
                == state["results"][-1]["analysis"]["family"]
            )
        export = json.loads(Path(result["paths"]["result"]).read_text())
        assert (
            export["family"]["ids"] == s.family_ids
            and export["correction"]["family"] == "planned endpoints"
        )


def test_one_selected_hypothesis_family(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[0.03, 0.04, 0.5], test_id=["a", "b", "c"]))
    )
    with closing(store):
        result = calculate(
            r,
            recipe(
                r,
                "adjust_holm",
                key=column(r, "test_id"),
                family_name="single planned",
                family_ids=["a"],
            ),
            work,
        )
        assert result["family"]["tests"][0]["p_adjusted"] == 0.03


@pytest.mark.parametrize("policy", ["keep", "mad_exclude", "winsorize"])
def test_robust_summary_reference_and_explicit_outlier_policy(tmp_path, policy):
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]
    store, r, work = prepare(tmp_path, pl.DataFrame({"x": values}))
    with closing(store):
        result = calculate(
            r,
            recipe(
                r, "robust_summary", outlier_policy=policy, statistic="trimmed_mean"
            ),
            work,
        )
        s = result["summary"]
        a = np.array(values)
        if policy == "mad_exclude":
            a = a[:5]
        if policy == "winsorize":
            a = np.clip(a, *np.quantile(a, [0.2, 0.8]))
        assert s["mean"] == pytest.approx(a.mean())
        assert s["median"] == pytest.approx(np.median(a))
        assert s["trimmed_mean"] == pytest.approx(stats.trim_mean(a, 0.2))
        assert s["mad"] == pytest.approx(np.median(np.abs(a - np.median(a))))
        assert not s["inference"]


def scenario(r, name="filtered median", **changes):
    return dict(
        name=name,
        view={},
        statistic="median",
        outlier_policy="keep",
        missing_policy="complete",
        missing_assumption="MAR",
        missing_delta=0.0,
        **changes,
    )


def test_sensitivity_filter_outlier_missing_delta_and_rowid_union(tmp_path):
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 100.0, None]
    store, r, work = prepare(tmp_path, pl.DataFrame({"x": values}))
    with closing(store):
        scenarios = [
            scenario(r),
            dict(
                scenario(r, "filtered"),
                view=dict(
                    filters=[dict(column_id=column(r, "x"), operator="lt", value="10")]
                ),
            ),
            dict(
                scenario(r, "outliers"), outlier_policy="mad_exclude", statistic="mean"
            ),
            dict(
                scenario(r, "MNAR delta"),
                missing_policy="delta",
                missing_assumption="MNAR",
                missing_delta=10.0,
                statistic="mean",
            ),
            dict(scenario(r, "reject missing"), missing_policy="reject"),
        ]
        result = calculate(
            r,
            recipe(r, "sensitivity", missing_policy="complete", scenarios=scenarios),
            work,
        )
        rows = result["sensitivity"]
        assert rows[0]["estimate"] == pytest.approx(115 / 6)
        assert rows[1]["estimate"] == 3.5
        assert rows[2]["estimate"] == 3
        assert rows[3]["estimate"] == 3
        assert rows[4]["imputed"] == 1
        assert rows[4]["estimate"] == pytest.approx((115 + 115 / 6 + 10) / 7)
        assert rows[5]["estimate"] is None
        assert rows[1]["change"] == pytest.approx(3.5 - 115 / 6)
        assert result["used_rows"] == 7
        publish(store, store.state, result)


@pytest.mark.parametrize(
    "change",
    [
        dict(resampling_unit="observation", dependence="grouped"),
        dict(
            resampling_unit="time_block",
            dependence="temporal",
            time_column="time",
            statistic="median",
            method="bootstrap_bca",
        ),
        dict(method="bootstrap_bca", statistic="trimmed_mean"),
        dict(
            method="permutation",
            group="label",
            before="A",
            after="B",
            exchangeability_confirmed=False,
        ),
        dict(
            method="permutation",
            group="label",
            before="A",
            after="B",
            exchangeability_confirmed=True,
            null_value=1.0,
        ),
        dict(
            method="paired_sign_flip",
            y="after",
            key="pair",
            exchangeability_confirmed=True,
            symmetry_confirmed=False,
        ),
        dict(seed=-1),
        dict(resamples=99),
        dict(resamples=10001),
        dict(
            method="adjust_bh",
            key="pair",
            family_name="planned",
            family_ids=["p1"],
            family_dependence="arbitrary",
        ),
    ],
)
def test_unsupported_or_unacknowledged_design_is_rejected(tmp_path, change):
    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        cols = {c["name"]: c["id"] for c in r["columns"]}
        fields = {
            k: cols.get(v, v) if isinstance(v, str) else v for k, v in change.items()
        }
        method = fields.pop("method", "bootstrap_percentile")
        with pytest.raises(ProjectError):
            calculate(r, recipe(r, method, **fields), work)


@pytest.mark.parametrize(
    "kind",
    [
        "cluster_missing",
        "time_missing",
        "duplicate_pair",
        "duplicate_time",
        "cluster_labels",
        "family_missing",
        "family_duplicate",
        "bad_p",
        "mad_zero",
    ],
)
def test_structural_integrity_and_invalid_distribution_errors(tmp_path, kind):
    f = frame()
    sfields = {}
    method = "bootstrap_percentile"
    if kind.endswith("missing") and not kind.startswith("family"):
        f = f.with_columns(
            pl.when(pl.col("time") == 0).then(None).otherwise(pl.col("x")).alias("x")
        )
        sfields["missing_policy"] = "complete"
    if kind == "cluster_missing":
        sfields.update(
            resampling_unit="cluster", dependence="grouped", cluster="cluster"
        )
    if kind in ("time_missing", "duplicate_time"):
        sfields.update(
            resampling_unit="time_block",
            dependence="temporal",
            time_column="time",
            block_length=3,
        )
        if kind == "duplicate_time":
            f = f.with_columns(pl.lit(0).alias("time"))
    if kind == "duplicate_pair":
        method = "paired_sign_flip"
        sfields.update(
            y="after",
            key="pair",
            exchangeability_confirmed=True,
            symmetry_confirmed=True,
        )
        f = f.with_columns(pl.lit("same").alias("pair"))
    if kind == "cluster_labels":
        method = "permutation"
        sfields.update(
            resampling_unit="cluster",
            dependence="grouped",
            cluster="cluster",
            group="label",
            exchangeability_confirmed=True,
            before="A",
            after="B",
        )
        f = f.with_columns(pl.Series("label", ["A", "B"] * 6))
    if kind.startswith("family") or kind == "bad_p":
        method = "adjust_holm"
        f = pl.DataFrame(
            dict(
                x=[
                    0.01,
                    None
                    if kind == "family_missing"
                    else 2.0
                    if kind == "bad_p"
                    else 0.02,
                    0.03,
                ],
                pair=["a", "a" if kind == "family_duplicate" else "b", "c"],
            )
        )
        sfields.update(key="pair", family_name="planned", family_ids=["a", "b", "c"])
    if kind == "mad_zero":
        method = "robust_summary"
        f = pl.DataFrame({"x": [5.0] * 8})
        sfields.update(outlier_policy="mad_exclude")
    store, r, work = prepare(tmp_path, f)
    with closing(store):
        cols = {c["name"]: c["id"] for c in r["columns"]}
        sfields = {
            k: cols.get(v, v) if isinstance(v, str) else v for k, v in sfields.items()
        }
        with pytest.raises(ProjectError):
            calculate(r, recipe(r, method, **sfields), work)


def test_cancel_hash_tamper_and_admission(tmp_path):
    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        event = Event()
        event.set()
        with pytest.raises(Canceled):
            calculate(r, recipe(r), work, Control(event))
        bad = dict(r, fingerprint=dict(r["fingerprint"], sha256="0" * 64))
        with pytest.raises(ProjectError, match="snapshot"):
            calculate(bad, recipe(r), work)
        with pytest.raises(ProjectError, match="bütçesi"):
            calculate(
                r,
                replace(recipe(r), resamples=10000),
                work,
                Control(budget=replace(Control().budget, ram_bytes=1024)),
            )


def test_nonzero_constant_pair_difference_has_valid_sign_null(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                x=[1.0, 2.0, 3.0, 4.0],
                after=[2.0, 3.0, 4.0, 5.0],
                pair=["a", "b", "c", "d"],
            )
        ),
    )
    with closing(store):
        result = calculate(
            r,
            recipe(
                r,
                "paired_sign_flip",
                y=column(r, "after"),
                key=column(r, "pair"),
                exchangeability_confirmed=True,
                symmetry_confirmed=True,
            ),
            work,
        )
        assert result["permutation"]["p_value"] == 2 / 16


def test_missing_bootstrap_distribution_has_no_fake_interval():
    from veri_ufku.statistics.resampling import interval

    s = AnalysisSpec("resampling", "bootstrap_percentile", "x")
    ci = interval([1.0, 2.0, None, 3.0], 2.0, s, [])
    assert ci["low"] is None and ci["high"] is None and ci["invalid_replicates"] == 1


def test_cluster_source_mapping_tamper_rejected(tmp_path):
    import copy

    from veri_ufku.statistics.resampling import verify_source

    store, r, work = prepare(tmp_path, frame())
    with closing(store):
        result = calculate(
            r,
            recipe(
                r,
                resampling_unit="cluster",
                dependence="grouped",
                cluster=column(r, "cluster"),
            ),
            work,
        )
        verify_source(r["path"], r["columns"], result)
        fake = copy.deepcopy(result)
        fake["unit_members"]["c0"], fake["unit_members"]["c1"] = (
            fake["unit_members"]["c1"],
            fake["unit_members"]["c0"],
        )
        with pytest.raises(ProjectError, match="mapping"):
            verify_source(r["path"], r["columns"], fake)
