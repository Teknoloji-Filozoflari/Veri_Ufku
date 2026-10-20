"""Independent closed-form, exact enumeration and transaction reference checks."""

import math
from contextlib import closing
from dataclasses import replace
from decimal import Decimal
from statistics import NormalDist

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.statistics.contracts import AnalysisSpec
from veri_ufku.statistics.engine import adjusted, calculate
from veri_ufku.storage.analysis_store import publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def spec(request, path, method, **changes):
    return AnalysisSpec(
        path,
        method,
        column(request, "x"),
        question="Araştırma sorusu",
        hypothesis="Önceden seçilmiş hipotez",
        unit="puan",
        observation_unit="kişi",
        independent=True,
        measurement_confirmed=True,
        assumptions_confirmed=True,
        **changes,
    )


def t3_tail(t):
    return 1 - 2 / math.pi * (
        math.atan(t / math.sqrt(3)) + t * math.sqrt(3) / (t * t + 3)
    )


@pytest.mark.parametrize("method", ["welch_t", "mann_whitney"])
def test_two_groups_closed_t_and_exact_rank_enumeration(tmp_path, method):
    values = [1, 2, 3, 2, 3, 4] if method == "welch_t" else [1, 2, 3, 4, 5, 6]
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=values, g=["A"] * 3 + ["B"] * 3))
    )
    with closing(store):
        result = calculate(
            r, spec(r, "independent", method, group=column(r, "g")), work
        )
        primary = result["primary"]
        assert result["n"] == [3, 3] and result["excluded_rows"] == 0
        if method == "welch_t":
            t = math.sqrt(1.5)
            s = t / math.sqrt(t * t + 4)
            assert primary["statistic"] == pytest.approx(-t, rel=1e-12)
            assert primary["p_value"] == pytest.approx(
                1 - 1.5 * s + 0.5 * s**3, rel=1e-12
            )
            interval = primary["effect"]["confidence_interval"]
            # Independent t4 quantile table, df4, central95%; not SciPy recalc.
            margin = 2.7764451051977987 * math.sqrt(2 / 3)
            assert interval["low"] == pytest.approx(-1 - margin, rel=1e-10)
            assert interval["high"] == pytest.approx(-1 + margin, rel=1e-10)
        else:
            assert primary["statistic"] == 0
            assert primary["p_value"] == pytest.approx(2 / math.comb(6, 3))
            assert primary["effect"]["value"] == -1
            assert primary["effect"]["confidence_interval"] is None


def paired_frame():
    # Deliberately different before/after order; positional subtraction would be wrong.
    return pl.DataFrame(
        dict(
            person=["a", "b", "c", "d", "d", "b", "a", "c"],
            phase=["before"] * 4 + ["after"] * 4,
            x=[10, 20, 30, 40, 44, 22, 11, 33],
        )
    )


@pytest.mark.parametrize("method", ["paired_t", "wilcoxon"])
def test_key_pairing_order_invariance_and_independent_p(tmp_path, method):
    store, r, work = prepare(tmp_path, paired_frame())
    with closing(store):
        result = calculate(
            r,
            spec(
                r,
                "paired",
                method,
                group=column(r, "phase"),
                key=column(r, "person"),
                before="before",
                after="after",
            ),
            work,
        )
        primary = result["primary"]
        assert result["n"] == [4, 4] and result["used_rows"] == 8
        if method == "paired_t":
            assert primary["statistic"] == pytest.approx(math.sqrt(15))
            assert primary["p_value"] == pytest.approx(
                t3_tail(math.sqrt(15)), rel=1e-11
            )
            assert primary["effect"]["value"] == 2.5
            margin = 3.182446305284263 * math.sqrt(5 / 12)
            interval = primary["effect"]["confidence_interval"]
            assert interval["low"] == pytest.approx(2.5 - margin, rel=1e-10)
            assert interval["high"] == pytest.approx(2.5 + margin, rel=1e-10)
        else:
            assert primary["statistic"] == 0 and primary["p_value"] == pytest.approx(
                2 / 2**4
            )
            assert primary["effect"]["value"] == 1
        original = pl.read_parquet(r["path"])
        original.reverse().write_parquet(work / "reordered.parquet")
        from veri_ufku.importers.delimited import Control, hash_artifact

        other = dict(
            r,
            path=str(work / "reordered.parquet"),
            fingerprint=hash_artifact(work / "reordered.parquet", Control()),
        )
        again = calculate(
            other,
            spec(
                r,
                "paired",
                method,
                group=column(r, "phase"),
                key=column(r, "person"),
                before="before",
                after="after",
            ),
            work,
        )
        assert again["primary"] == primary


@pytest.mark.parametrize("method", ["anova", "welch_anova", "kruskal"])
def test_three_groups_closed_form_and_posthoc_family(tmp_path, method):
    values = list(range(1, 16)) if method == "kruskal" else list(range(1, 10))
    n = len(values) // 3
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=values, g=["A"] * n + ["B"] * n + ["C"] * n))
    )
    with closing(store):
        result = calculate(
            r,
            spec(
                r,
                "groups",
                method,
                group=column(r, "g"),
                posthoc="pairwise",
                correction="holm",
            ),
            work,
        )
        primary = result["primary"]
        if method == "anova":
            assert primary["statistic"] == pytest.approx(27)
            assert primary["p_value"] == pytest.approx(0.001, rel=1e-10)
            assert primary["effect"]["value"] == pytest.approx(0.9)
        elif method == "welch_anova":
            assert primary["statistic"] == pytest.approx(162 / 7)
            assert primary["p_value"] == pytest.approx((7 / 88) ** 2, rel=1e-10)
        else:
            assert primary["statistic"] == pytest.approx(12.5)
            assert primary["p_value"] == pytest.approx(math.exp(-6.25))
            assert primary["effect"]["value"] == pytest.approx(0.875)
        assert primary["effect"]["confidence_interval"] is None
        assert (
            len(result["comparisons"]) == 3 and result["correction"]["family_size"] == 3
        )
        assert result["correction"]["ci_adjusted"] is False


def table_frame(table):
    rows = [
        (str(i), str(j))
        for i, row in enumerate(table)
        for j, n in enumerate(row)
        for _ in range(n)
    ]
    return pl.DataFrame(rows, schema=["x", "y"], orient="row")


@pytest.mark.parametrize("method", ["chi2", "fisher"])
def test_categorical_exact_combinations_and_chi_square_tail(tmp_path, method):
    table = [[30, 10], [10, 30]] if method == "chi2" else [[6, 2], [1, 4]]
    store, r, work = prepare(tmp_path, table_frame(table))
    with closing(store):
        result = calculate(r, spec(r, "categorical", method, y=column(r, "y")), work)
        primary = result["primary"]
        assert result["table"] == table
        if method == "chi2":
            assert primary["statistic"] == 20
            assert primary["p_value"] == pytest.approx(
                math.erfc(math.sqrt(10)), rel=1e-11
            )
            assert primary["effect"]["value"] == 0.5
        else:
            # Fixed margins:13 total,7 in col1,8 row1. Exact two-sided probability ordering.
            def mass(k):
                return math.comb(7, k) * math.comb(6, 8 - k) / math.comb(13, 8)

            observed = mass(6)
            p = sum(mass(k) for k in range(2, 8) if mass(k) <= observed + 1e-15)
            assert primary["statistic"] == 12
            assert primary["p_value"] == pytest.approx(p)
            assert primary["effect"]["confidence_interval"]["method"] == "Koşullu exact"

            # Independently invert a finite noncentral hypergeometric polynomial.
            def expectation(log_theta, target):
                weights = {
                    k: math.comb(7, k) * math.comb(6, 8 - k) * math.exp(log_theta * k)
                    for k in range(2, 8)
                }
                total = sum(weights.values())
                return (
                    sum(
                        w
                        * (
                            k
                            if target == "mean"
                            else k >= 6
                            if target == "upper"
                            else k <= 6
                        )
                        for k, w in weights.items()
                    )
                    / total
                )

            def invert(target, value, increasing=True):
                low, high = -25.0, 25.0
                for _ in range(120):
                    midpoint = (low + high) / 2
                    if (expectation(midpoint, target) < value) == increasing:
                        low = midpoint
                    else:
                        high = midpoint
                return math.exp((low + high) / 2)

            assert primary["effect"]["value"] == pytest.approx(
                invert("mean", 6), rel=1e-10
            )
            interval = primary["effect"]["confidence_interval"]
            assert interval["low"] == pytest.approx(invert("upper", 0.025), rel=1e-9)
            assert interval["high"] == pytest.approx(
                invert("lower", 0.025, False), rel=1e-9
            )


@pytest.mark.parametrize("method", ["pearson", "spearman"])
def test_numeric_closed_correlation_t_and_fisher_z(tmp_path, method):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[-2, -1, 0, 1, 2], y=[-2, 0, -1, 2, 1]))
    )
    with closing(store):
        result = calculate(r, spec(r, "numeric", method, y=column(r, "y")), work)
        primary = result["primary"]
        assert primary["statistic"] == pytest.approx(0.8)
        assert primary["p_value"] == pytest.approx(
            t3_tail(0.8 * math.sqrt(3 / (1 - 0.8**2))), rel=1e-11
        )
        ci = primary["effect"]["confidence_interval"]
        if method == "pearson":
            z = NormalDist().inv_cdf(0.975) / math.sqrt(2)
            assert ci["low"] == pytest.approx(math.tanh(math.atanh(0.8) - z))
            assert ci["high"] == pytest.approx(math.tanh(math.atanh(0.8) + z))
        else:
            assert ci is None and "asimptotik" in " ".join(result["warnings"])


def test_multiple_adjustments_hand_reference():
    assert adjusted([0.01, 0.04, 0.2], "holm") == pytest.approx([0.03, 0.08, 0.2])
    assert adjusted([0.01, 0.04, 0.2], "bonferroni") == pytest.approx([0.03, 0.12, 0.6])
    assert adjusted([0.2, 0.01, 0.04], "bh") == pytest.approx([0.2, 0.03, 0.06])
    assert adjusted([0.01, 0.04, 0.2], "none") == [0.01, 0.04, 0.2]


def test_missing_nonfinite_and_no_automatic_selection(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                x=[1.0, 2.0, 3.0, None, float("nan"), float("inf"), 4.0, 5.0, 6.0],
                g=["A"] * 6 + ["B"] * 3,
            )
        ),
    )
    with closing(store):
        s = spec(r, "independent", "welch_t", group=column(r, "g"))
        result = calculate(r, s, work, preflight=True)
        assert result["n"] == [3, 3] and result["excluded_rows"] == 3
        assert (
            result["exclusions"]["null_rows"] == 1
            and result["exclusions"]["nonfinite_rows"] == 2
        )
        assert result["method"] == "welch_t"
        with pytest.raises(ProjectError, match="onay"):
            calculate(r, replace(s, assumptions_confirmed=False), work)


@pytest.mark.parametrize(
    "bad", ["duplicate", "unmatched", "key_missing", "zero", "few"]
)
def test_pairing_and_degenerate_failures_are_explained(tmp_path, bad):
    frame = paired_frame()
    if bad == "duplicate":
        frame = pl.concat([frame, frame.head(1)])
    if bad == "unmatched":
        frame = frame.head(7)
    if bad == "key_missing":
        frame = frame.with_columns(
            pl.when(pl.col("person") == "a")
            .then(None)
            .otherwise(pl.col("person"))
            .alias("person")
        )
    if bad == "zero":
        frame = frame.with_columns(pl.lit(1).alias("x"))
    if bad == "few":
        frame = frame.filter(pl.col("person") == "a")
    store, r, work = prepare(tmp_path, frame)
    with closing(store):
        s = spec(
            r,
            "paired",
            "paired_t",
            group=column(r, "phase"),
            key=column(r, "person"),
            before="before",
            after="after",
        )
        with pytest.raises(
            ProjectError,
            match={
                "duplicate": "birden çok",
                "unmatched": "yalnız bir",
                "key_missing": "anahtarı",
                "zero": "Sıfır varyans",
                "few": "Yetersiz",
            }[bad],
        ):
            calculate(r, s, work)
        if bad == "unmatched":
            value = calculate(r, replace(s, pair_policy="complete"), work)
            assert value["exclusions"]["unmatched_people"] == 1 and value["n"] == [3, 3]


def test_precision_sparse_table_filter_and_transaction_integrity(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                x=[
                    Decimal("0.1"),
                    Decimal("0.2"),
                    Decimal("0.3"),
                    Decimal("0.4"),
                    Decimal("0.5"),
                    Decimal("0.6"),
                ],
                g=["A"] * 3 + ["B"] * 3,
            )
        ),
    )
    with closing(store):
        s = spec(r, "independent", "welch_t", group=column(r, "g"))
        with pytest.raises(ProjectError, match="hassasiyet"):
            calculate(r, s, work)
        result = calculate(r, replace(s, precision="approximate"), work)
        assert result["precision_loss_values"] > 0
        original = store.path(store.state["datasets"][-1]["snapshot_uri"]).read_bytes()
        before = store.path("ACTIVE").read_bytes()
        with pytest.raises(RuntimeError):
            publish(
                store,
                store.state,
                result,
                lambda p: (
                    (_ for _ in ()).throw(RuntimeError("fault"))
                    if p == "analysis_copy_chunk"
                    else None
                ),
            )
        assert store.path("ACTIVE").read_bytes() == before
        state = publish(store, store.state, result)
        assert len(state["results"]) == 1
        assert (
            store.path(store.state["datasets"][-1]["snapshot_uri"]).read_bytes()
            == original
        )
        root = store.root
    with closing(ProjectStore.open(root, recover_lock=True)) as reopened:
        assert (
            reopened.state["results"][0]["analysis"]["primary"]["p_value"]
            == result["primary"]["p_value"]
        )
    result["primary"]["p_value"] = 0.99
    with closing(ProjectStore.open(root, recover_lock=True)) as reopened:
        with pytest.raises(ProjectError, match="uyuşmuyor"):
            publish(reopened, reopened.state, result)


def test_sparse_chi_square_and_constant_correlation_rejected(tmp_path):
    store, r, work = prepare(tmp_path, table_frame([[1, 1], [1, 1]]))
    with closing(store), pytest.raises(ProjectError, match="Beklenen"):
        calculate(r, spec(r, "categorical", "chi2", y=column(r, "y")), work)


@pytest.mark.parametrize("method", ["pearson", "spearman"])
def test_constant_numeric_preflight_clear_error(tmp_path, method):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1, 1, 1, 1], y=[1, 2, 3, 4]))
    )
    with closing(store), pytest.raises(ProjectError, match="Sıfır varyans"):
        calculate(r, spec(r, "numeric", method, y=column(r, "y")), work, preflight=True)


def test_group_with_all_missing_does_not_silently_disappear(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1, 2, 3, None, None], g=["A"] * 3 + ["B"] * 2))
    )
    with closing(store), pytest.raises(ProjectError, match="Yetersiz"):
        calculate(r, spec(r, "independent", "welch_t", group=column(r, "g")), work)


def test_explicit_scope_and_resource_limit(tmp_path):
    from veri_ufku.domain.contracts import ComputeBudget
    from veri_ufku.importers.delimited import Control

    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(dict(x=[1, 2, 3, 4, 3, 4, 5, 6], g=["A"] * 4 + ["B"] * 4)),
    )
    with closing(store):
        s = spec(
            r,
            "independent",
            "welch_t",
            group=column(r, "g"),
            view=dict(
                filters=[dict(column_id=column(r, "x"), operator="ge", value="2")]
            ),
        )
        out = calculate(r, s, work)
        assert out["population_n"] == 7 and out["dataset_n"] == 8 and out["n"] == [3, 4]
        assert calculate(r, replace(s, scope="full"), work)["n"] == [4, 4]
        with pytest.raises(ProjectError, match="bütçe"):
            calculate(r, s, work, Control(budget=ComputeBudget(ram_bytes=2048)))


def test_rank_ties_and_zero_difference_policy(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1, 1, 2, 2, 2, 3], g=["A"] * 3 + ["B"] * 3))
    )
    with closing(store):
        out = calculate(
            r, spec(r, "independent", "mann_whitney", group=column(r, "g")), work
        )
        assert out["primary"]["statistic"] == 1
        assert out["primary"]["details"]["p_algorithm"] == "asymptotic"
        assert out["primary"]["effect"]["value"] == pytest.approx(-7 / 9)
    paired = tmp_path / "pairs"
    paired.mkdir()
    frame = pl.DataFrame(
        dict(
            person=["a", "b", "c"] * 2,
            phase=["before"] * 3 + ["after"] * 3,
            x=[10, 20, 30, 10, 21, 31],
        )
    )
    store, r, work = prepare(paired, frame)
    with closing(store):
        out = calculate(
            r,
            spec(
                r,
                "paired",
                "wilcoxon",
                group=column(r, "phase"),
                key=column(r, "person"),
                before="before",
                after="after",
            ),
            work,
        )
        assert out["primary"]["details"]["zero_differences"] == 1
        assert out["primary"]["details"]["ranked_pairs"] == 2
        assert out["primary"]["effect"]["value"] == 1
        assert out["primary"]["effect"]["confidence_interval"] is None


def test_fisher_infinite_odds_is_explicit_and_json_safe(tmp_path):
    store, r, work = prepare(tmp_path, table_frame([[3, 0], [0, 3]]))
    with closing(store):
        out = calculate(r, spec(r, "categorical", "fisher", y=column(r, "y")), work)
        assert out["primary"]["statistic"] == "∞"
        assert out["primary"]["p_value"] == pytest.approx(2 / math.comb(6, 3))
        assert out["primary"]["effect"]["confidence_interval"]["high"] == "∞"
        assert out["primary"]["effect"]["confidence_interval"]["low"] > 0


@pytest.mark.parametrize("point", ["pointer_written", "pointer_replaced"])
def test_statistical_real_sigkill_preserves_complete_commit(tmp_path, point):
    import json
    import signal
    import subprocess
    import sys

    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1, 2, 3, 2, 3, 4], g=["A"] * 3 + ["B"] * 3))
    )
    with closing(store):
        result = calculate(
            r, spec(r, "independent", "welch_t", group=column(r, "g")), work
        )
        result_path = tmp_path / "job.json"
        result_path.write_text(json.dumps(result))
        root = store.root
        before = store.commit_id
    program = """import json,os,signal,sys
from pathlib import Path
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.analysis_store import publish
s=ProjectStore.open(sys.argv[1])
def hook(p):
    if p==sys.argv[3]:os.kill(os.getpid(),signal.SIGKILL)
publish(s,s.state,json.loads(Path(sys.argv[2]).read_text()),hook)
"""
    child = subprocess.run(
        [sys.executable, "-c", program, str(root), str(result_path), point],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    with closing(ProjectStore.open(root, recover_lock=True)) as reopened:
        assert len(reopened.state["results"]) == (
            1 if point == "pointer_replaced" else 0
        )
        assert (reopened.commit_id == before) == (point != "pointer_replaced")
        if point == "pointer_replaced":
            saved = reopened.state["results"][0]["analysis"]
            assert saved["primary"] == result["primary"]
            assert all(
                reopened.path(uri).is_file() for uri in saved["artifact_uris"].values()
            )
        with closing(ProjectStore.open(root, recover_lock=True)) as readonly:
            assert readonly.read_only
            with pytest.raises(ProjectError):
                publish(readonly, readonly.state, result)
    assert (tmp_path / "source.parquet").is_file()


def test_saved_analysis_report_preserves_limits_and_escapes_question(tmp_path):
    from veri_ufku.exports.reports import ReportSpec, build
    from veri_ufku.importers.delimited import Control

    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1, 2, 3, 4, 5, 6], g=["A"] * 3 + ["B"] * 3))
    )
    with closing(store):
        result = calculate(
            r, spec(r, "independent", "mann_whitney", group=column(r, "g")), work
        )
        state = publish(store, store.state, result)
        saved = state["results"][0]["analysis"]
        saved["spec"]["question"] = "<script>q</script>"
        r["report_context"] = {"analyses": [saved]}
        document, _, _ = build(r, ReportSpec("html"), Control())
        assert "İstatistiksel analizler" in document
        assert (
            "&lt;script&gt;q&lt;/script&gt;" in document and "<script>" not in document
        )
        assert "ci_limitation" in document and "sunulmuyor" in document
        assert "artifact_uris" not in document


def test_statistical_second_process_cannot_publish(tmp_path):
    import json
    import subprocess
    import sys

    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(x=[1, 2, 3, 2, 3, 4], g=["A"] * 3 + ["B"] * 3))
    )
    with closing(store):
        result = calculate(
            r, spec(r, "independent", "welch_t", group=column(r, "g")), work
        )
        path = tmp_path / "result.json"
        path.write_text(json.dumps(result))
        active = store.path("ACTIVE").read_bytes()
        program = """import json,sys
from pathlib import Path
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.analysis_store import publish
from veri_ufku.storage.project_model import ProjectError
s=ProjectStore.open(sys.argv[1],recover_lock=True)
assert s.read_only
try:publish(s,s.state,json.loads(Path(sys.argv[2]).read_text()))
except ProjectError:print('STATISTICS_READONLY_REJECTED')
else:raise AssertionError('second writer admitted')
s.close()
"""
        child = subprocess.run(
            [sys.executable, "-c", program, str(store.root), str(path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert (
            child.returncode == 0 and "STATISTICS_READONLY_REJECTED" in child.stdout
        ), child.stderr
        assert (
            store.path("ACTIVE").read_bytes() == active and not store.state["results"]
        )
