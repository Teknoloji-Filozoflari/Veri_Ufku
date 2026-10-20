"""Fixed CPU PyMC NUTS templates with explicit predictive/diagnostic contracts."""

import json
import math
import os
import warnings
from pathlib import Path

import numpy as np
import polars as pl
from scipy import stats

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked, filtered
from veri_ufku.importers.delimited import hash_artifact
from veri_ufku.statistics.bayes_contracts import BAYES_LABELS
from veri_ufku.storage.project_model import ProjectError, uid

CAUTION = "Posterior olasılığı p-değeri değildir. Credible interval seçili model ve prior koşulundadır. PPC eğitim verisinde model misfit kontrolüdür; held-out tahmin başarısı değildir. Tanı geçmesi modelin doğru veya nedensel olduğunu kanıtlamaz."


def backend():
    # Interpreter-only graphs: no user code, compiler/cache execution or GPU.
    os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
    os.environ.setdefault("PYTENSOR_FLAGS", "cxx=,mode=FAST_COMPILE,linker=py")
    try:
        import arviz as az
        import pymc as pm
    except ImportError:
        raise ProjectError(
            "İsteğe bağlı yerel bayes extra (PyMC/ArviZ) kurulu değil; temel uygulama çalışmaya devam eder."
        ) from None
    if pm.__version__ != "5.28.5" or az.__version__ != "0.23.4":
        raise ProjectError(
            "Bu backend sürümü doğrulanmadı; kilitli PyMC5.28.5/ArviZ0.23.4 gerekli."
        )
    return pm, az


def prepare(request, spec, control):
    checked(request, control)
    query, schema, names = filtered(
        request, ViewSpec.from_dict(spec.view) if spec.scope == "view" else ViewSpec()
    )
    chosen = [spec.x] + spec.features + ([spec.group] if spec.group else [])
    n = query.select(pl.len()).collect(engine="streaming").item()
    p = spec.bayes_plan
    cells = n * p["chains"] * p["draws"]
    work = n * p["chains"] * (p["draws"] + p["warmup"]) * 2
    required = cells * 8 * 12 + 32 * 1024**2
    if (
        not 4 <= n <= 1000
        or cells > 2000000
        or work > 8000000
        or control.budget
        and required > control.budget.ram_bytes // 2
    ):
        raise ProjectError(
            "Bayes bütçesi:4–1000 satır;2M likelihood hücresi/8M iki-prior iş; RAM önkontrolü. Kolon veya draws azaltın, açık yeni örneklem kullanın."
        )
    for c in [spec.x] + spec.features:
        dtype = schema[names[c]]
        if not (
            dtype.is_integer()
            or dtype.is_float()
            or c == spec.x
            and dtype == pl.Boolean
        ):
            raise ProjectError(
                "Bayes sayısal kolon ister; Decimal/nested/time sessiz çevrilmez."
            )
    f = query.select(
        [pl.col("__vu_row_id")] + [pl.col(names[c]).alias(c) for c in chosen]
    ).collect(engine="streaming")
    if any(f[c].null_count() for c in chosen):
        raise ProjectError(
            "Eksik gözlem/predictor/grup var; otomatik drop veya imputasyon yok."
        )
    for c in [spec.x] + spec.features:
        a = f[c].to_numpy().astype(float)
        if (
            not np.isfinite(a).all()
            or np.max(np.abs(a)) > 1e9
            or schema[names[c]].is_integer()
            and any(abs(int(v)) > 2**53 for v in f[c])
        ):
            raise ProjectError(
                "Sonlu olmayan veya hassasiyet kaybı yaratan ölçüm reddedildi."
            )
    y = f[spec.x].to_numpy().astype(float)
    if spec.method == "bayes_beta_binomial" and not np.isin(y, [0, 1]).all():
        raise ProjectError(
            "Beta-binomial bu şablonda bir satır bir bağımsız Bernoulli0/1 gözlem ister; toplam başarı/deneme sütunu değildir."
        )
    X = (
        f.select(spec.features).to_numpy().astype(float)
        if spec.features
        else np.empty((n, 0))
    )
    if X.size and (
        np.linalg.matrix_rank(np.column_stack([np.ones(n), X])) != X.shape[1] + 1
    ):
        raise ProjectError(
            "Sabit veya doğrusal bağımlı predictor; tasarım tam rank olmalı."
        )
    groups, gi = [], None
    if spec.group:
        if schema[names[spec.group]] not in (pl.String, pl.Int64, pl.Int32):
            raise ProjectError(
                "Grup kimliği String/Int32/Int64 olmalı; sürekli grup mesafesi kullanılmaz."
            )
        labels = list(map(str, f[spec.group].to_list()))
        groups = sorted(set(labels))
        if not 3 <= len(groups) <= 30 or any(labels.count(g) < 2 for g in groups):
            raise ProjectError(
                "Random intercept:3–30 grup ve her grupta en az2 gözlem gerekli."
            )
        gi = np.array([groups.index(g) for g in labels])
    control.check()
    return (
        f,
        y,
        X,
        groups,
        gi,
        dict(
            rows=n,
            likelihood_cells=cells,
            two_prior_work=work,
            estimated_ram_bytes=required,
            predictor_scaling="raw, no automatic standardization",
            coefficient_units=[
                spec.unit + " / " + spec.bayes_feature_units[cid]
                for cid in spec.features
            ],
        ),
    )


def conjugate(y, spec, p):
    q = (1 - spec.confidence) / 2
    if spec.method == "bayes_beta_binomial":
        a, b = p["alpha"] + float(y.sum()), p["beta"] + len(y) - float(y.sum())
        return dict(
            distribution="Beta",
            alpha=a,
            beta=b,
            mean=a / (a + b),
            credible_interval=stats.beta.ppf([q, 1 - q], a, b).tolist(),
            probability_above_zero=1.0,
        )
    if spec.method == "bayes_normal_mean":
        var = 1 / (1 / p["scale"] ** 2 + len(y) / p["noise_scale"] ** 2)
        mean = var * (p["location"] / p["scale"] ** 2 + y.sum() / p["noise_scale"] ** 2)
        return dict(
            distribution="Normal",
            mean=float(mean),
            sd=math.sqrt(var),
            credible_interval=stats.norm.ppf([q, 1 - q], mean, math.sqrt(var)).tolist(),
            probability_above_zero=float(stats.norm.sf(0, mean, math.sqrt(var))),
        )
    return None


def prior_preview(y, X, gi, groups, spec, p):
    rng = np.random.default_rng(spec.seed)
    size = 200
    if spec.method == "bayes_beta_binomial":
        theta = rng.beta(p["alpha"], p["beta"], size)
        predictions = rng.binomial(len(y), theta) / len(y)
        target = "sample success fraction"
    else:
        location = rng.normal(p["location"], p["scale"], (size, 1)) + np.zeros(
            (size, len(y))
        )
        if X.size:
            location += rng.normal(0, p["scale"], (size, X.shape[1])) @ X.T
        if gi is not None:
            sd = np.abs(rng.normal(0, p["group_scale"], (size, 1)))
            location += (rng.normal(size=(size, len(groups))) * sd)[:, gi]
        noise = (
            p["noise_scale"]
            if spec.method == "bayes_normal_mean"
            else np.abs(rng.normal(0, p["noise_scale"], (size, 1)))
        )
        predictions = rng.normal(location, noise).mean(axis=1)
        target = "sample outcome mean"
    return dict(
        draws=size,
        seed=spec.seed,
        target=target,
        unit=spec.unit,
        quantiles=np.quantile(predictions, [0.025, 0.5, 0.975]).tolist(),
        observed=float(y.mean()),
        interpretation="Prior predictive: veri likelihood olarak kullanılmadan seçili tasarım/n üzerinde simülasyon; posterior değildir.",
    )


def fit(y, X, gi, groups, spec, p, control, label, row_ids=None):
    pm, az = backend()
    control.check()
    coords = {"observation": row_ids or list(range(len(y)))}
    if X.size:
        coords["predictor"] = spec.features
    if groups:
        coords["group"] = groups
    with pm.Model(coords=coords):
        if spec.method == "bayes_beta_binomial":
            theta = pm.Beta("theta", p["alpha"], p["beta"])
            pm.Bernoulli("outcome", p=theta, observed=y, dims="observation")
        else:
            mu = pm.Normal("intercept", p["location"], p["scale"])
            if X.size:
                beta = pm.Normal("beta", 0, p["scale"], dims="predictor")
                mu = mu + pm.math.dot(X, beta)
            if gi is not None:
                tau = pm.HalfNormal("group_sd", p["group_scale"])
                z = pm.Normal("group_z", 0, 1, dims="group")
                effect = pm.Deterministic("group_effect", z * tau, dims="group")
                mu = mu + effect[gi]
            sigma = (
                p["noise_scale"]
                if spec.method == "bayes_normal_mean"
                else pm.HalfNormal("noise_sd", p["noise_scale"])
            )
            pm.Normal("outcome", mu=mu, sigma=sigma, observed=y, dims="observation")

        def callback(trace, draw):
            control.check()
            if draw.draw_idx % 25 == 0:
                control.progress(
                    label + " · NUTS chain " + str(draw.chain),
                    draw.draw_idx,
                    p["draws"] + p["warmup"],
                )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            idata = pm.sample(
                draws=p["draws"],
                tune=p["warmup"],
                chains=p["chains"],
                cores=1,
                random_seed=spec.seed,
                target_accept=p["target_accept"],
                progressbar=False,
                callback=callback,
                compute_convergence_checks=False,
                idata_kwargs={"log_likelihood": True},
            )
        control.check()
    return idata, [str(w.message) for w in caught], pm.__version__, az.__version__


def diagnostic_summary(idata, spec):
    _, az = backend()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rhat, bulk, tail = (
            az.rhat(idata, method="rank"),
            az.ess(idata, method="bulk"),
            az.ess(idata, method="tail"),
        )
        summary = []
        q = (1 - spec.confidence) / 2
        for name, arr in idata.posterior.data_vars.items():
            a = arr.transpose("chain", "draw", ...).values
            shape = a.shape[2:]
            for index in np.ndindex(shape) if shape else [()]:
                v = a[(slice(None), slice(None)) + index]

                def value(dataset):
                    return float(dataset[name].values[index])

                summary.append(
                    dict(
                        parameter=name + (str(index) if index else ""),
                        mean=float(v.mean()),
                        sd=float(v.std(ddof=1)),
                        credible_interval=np.quantile(v, [q, 1 - q]).tolist(),
                        interval_method="equal-tailed posterior",
                        level=spec.confidence,
                        probability_above_zero=float((v > 0).mean()),
                        r_hat=value(rhat),
                        ess_bulk=value(bulk),
                        ess_tail=value(tail),
                    )
                )
        ss = idata.sample_stats
        divergences = int(ss["diverging"].sum())
        tree = (
            int(ss["reached_max_treedepth"].sum())
            if "reached_max_treedepth" in ss
            else None
        )
        bfmi = np.asarray(az.bfmi(idata)).tolist()
    failed = [
        s["parameter"]
        for s in summary
        if not all(math.isfinite(s[k]) for k in ("r_hat", "ess_bulk", "ess_tail"))
        or s["r_hat"] > 1.01
        or min(s["ess_bulk"], s["ess_tail"]) < 100 * spec.bayes_plan["chains"]
    ]
    ok = (
        not failed
        and divergences == 0
        and tree == 0
        and all(math.isfinite(x) and x >= 0.3 for x in bfmi)
    )
    # Never emit NaN/Infinity JSON or award a reliability badge.
    for s in summary:
        for k in ("r_hat", "ess_bulk", "ess_tail"):
            if not math.isfinite(s[k]):
                s[k] = None
    return dict(
        status="diagnostics_passed" if ok else "diagnostic_fail",
        reliable_badge=False,
        thresholds=dict(
            rhat_max=1.01, ess_min=100 * spec.bayes_plan["chains"], bfmi_min=0.3
        ),
        failed_parameters=failed,
        divergences=divergences,
        max_treedepth_hits=tree,
        bfmi=[x if math.isfinite(x) else None for x in bfmi],
        summary=summary,
        warnings=[str(w.message) for w in caught],
    )


def information_criteria(idata, diagnostics):
    _, az = backend()
    if diagnostics["status"] != "diagnostics_passed":
        return dict(
            available=False,
            reason="Sampling tanısı başarısız; LOO/WAIC ranking kapalı.",
        )
    ll = getattr(idata, "log_likelihood", None)
    if (
        ll is None
        or "outcome" not in ll
        or ll.outcome.dims != ("chain", "draw", "observation")
        or not np.isfinite(ll.outcome.values).all()
    ):
        return dict(
            available=False,
            reason="Sonlu pointwise log-likelihood ve aynı gözlem kimlikleri gerekli.",
        )
    out = dict(available=True, scale="log", warnings=[])
    for name, fn in (("loo", az.loo), ("waic", az.waic)):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            score = fn(idata, var_name="outcome", pointwise=True, scale="log")
        if (
            not all(
                math.isfinite(float(v))
                for v in (score["elpd_" + name], score.se, score["p_" + name])
            )
            or not np.isfinite(score[name + "_i"].values).all()
        ):
            return dict(
                available=False,
                reason="LOO/WAIC nonfinite diagnostic; ranking kapalı.",
                warnings=[str(w.message) for w in caught],
            )
        out["warnings"].extend(str(w.message) for w in caught)
        out[name] = dict(
            elpd=float(score["elpd_" + name]),
            se=float(score.se),
            effective_parameters=float(score["p_" + name]),
            warning=bool(score.warning),
            pointwise=score[name + "_i"].values.tolist(),
        )
        if name == "loo":
            if not np.isfinite(score.pareto_k.values).all():
                return dict(
                    available=False,
                    reason="LOO Pareto-k nonfinite; ranking kapalı.",
                    warnings=out["warnings"] + ["Nonfinite Pareto-k diagnostic."],
                )
            out[name].update(
                pareto_k=score.pareto_k.values.tolist(), good_k=float(score.good_k)
            )
    out["ranking_allowed"] = not out["warnings"] and not any(
        out[k]["warning"] for k in ("loo", "waic")
    )
    return out


def predictive(idata, y, X, gi, spec):
    rng = np.random.default_rng(spec.seed + 1)
    post = idata.posterior
    if spec.method == "bayes_beta_binomial":
        prob = post.theta.values.reshape(-1, 1)
        rep = rng.binomial(1, prob, size=(len(prob), len(y)))
    else:
        mu = post.intercept.values.reshape(-1, 1) + np.zeros(
            (post.sizes["chain"] * post.sizes["draw"], len(y))
        )
        if X.size:
            mu += post.beta.values.reshape(-1, X.shape[1]) @ X.T
        if gi is not None:
            mu += post.group_effect.values.reshape(len(mu), -1)[:, gi]
        sd = (
            spec.bayes_plan["noise_scale"]
            if spec.method == "bayes_normal_mean"
            else post.noise_sd.values.reshape(-1, 1)
        )
        rep = rng.normal(mu, sd)
    checks = []
    for name, fn in (
        ("mean", lambda a: a.mean(axis=-1)),
        ("sd", lambda a: a.std(axis=-1)),
        ("max", lambda a: a.max(axis=-1)),
    ):
        obs = float(fn(y))
        values = fn(rep)
        qs = np.quantile(values, [0.025, 0.5, 0.975]).tolist()
        checks.append(
            dict(
                statistic=name,
                observed=obs,
                replicate_quantiles=qs,
                posterior_predictive_tail_probability=float((values >= obs).mean()),
                misfit_flag=obs < qs[0] or obs > qs[2],
            )
        )
    return rep, dict(
        checks=checks,
        misfit=any(c["misfit_flag"] for c in checks),
        interpretation="Descriptive in-sample posterior predictive discrepancies; tail probability frequentist p değildir.",
    )


def compare_results(a, b):
    if (
        a["dataset_version"] != b["dataset_version"]
        or a["observation_ids"] != b["observation_ids"]
        or a["spec"]["x"] != b["spec"]["x"]
        or a["spec"]["unit"] != b["spec"]["unit"]
        or ("beta_binomial" in a["method"]) != ("beta_binomial" in b["method"])
    ):
        raise ProjectError(
            "LOO/WAIC aynı veri sürümü, outcome/ölçü birimi, likelihood ailesi ve sıralı RowId evreni ister."
        )
    if not all(r["criteria"].get("ranking_allowed") for r in (a, b)):
        raise ProjectError(
            "LOO/WAIC veya sampling diagnostic uyarısı var; otomatik model ranking yok."
        )
    out = {}
    for name in ("loo", "waic"):
        delta = np.array(a["criteria"][name]["pointwise"]) - np.array(
            b["criteria"][name]["pointwise"]
        )
        out[name] = dict(
            elpd_difference=float(delta.sum()),
            paired_se=float(np.sqrt(len(delta) * np.var(delta, ddof=1))),
            interpretation="positive favors current; predictive score, not posterior model probability",
        )
    return out


def calculate(request, spec, workspace, control, preflight=False):
    f, y, X, groups, gi, cost = prepare(request, spec, control)
    p = spec.bayes_plan
    prior = prior_preview(y, X, gi, groups, spec, p)
    common = dict(
        bayes=True,
        method=spec.method,
        method_label=BAYES_LABELS[spec.method],
        spec=spec.data(),
        dataset_version=request["version_id"],
        config_revision=request.get("config_revision", 0),
        n=dict(population=request["row_count"], used=len(y)),
        used_rows=len(y),
        excluded_rows=dict(outside_view=request["row_count"] - len(y)),
        warnings=[CAUTION],
        budget=cost,
        prior_predictive=prior,
        source_columns=request["columns"],
    )
    if preflight:
        return common
    idata, w, pmv, azv = fit(
        y, X, gi, groups, spec, p, control, "Ana prior", f["__vu_row_id"].to_list()
    )
    diagnostics = diagnostic_summary(idata, spec)
    criteria = information_criteria(idata, diagnostics)
    rep, ppc = predictive(idata, y, X, gi, spec)
    alternate = dict(p)
    if spec.method == "bayes_beta_binomial":
        alternate["alpha"] *= p["sensitivity_factor"]
        alternate["beta"] *= p["sensitivity_factor"]
    else:
        for k in ("scale", "group_scale"):
            alternate[k] *= p["sensitivity_factor"]
    alternative, w2, _, _ = fit(
        y,
        X,
        gi,
        groups,
        spec,
        alternate,
        control,
        "Alternatif prior",
        f["__vu_row_id"].to_list(),
    )
    alt_diag = diagnostic_summary(alternative, spec)
    _, alt_ppc = predictive(alternative, y, X, gi, spec)
    result = dict(
        common,
        primary=dict(method=spec.method, p_value=None, statistic=None, effect=None),
        comparisons=[],
        correction=dict(method="none", family="Bayesian posterior; no p-value"),
        observation_ids=f["__vu_row_id"].to_list(),
        group_labels=groups,
        diagnostics=diagnostics,
        criteria=criteria,
        posterior_predictive=ppc,
        conjugate_reference=conjugate(y, spec, p),
        prior_sensitivity=dict(
            alternative_prior=alternate,
            diagnostics=alt_diag,
            posterior_predictive=alt_ppc,
            conjugate_reference=conjugate(y, spec, alternate),
            interpretation="İki önceden seçilen prior; sensitivity model seçimi veya yeni veri değildir.",
        ),
        result_version="analysis:" + uid(),
        method_version=1,
        parameter_version=1,
        provenance=dict(
            schema="AnalysisResult/v1",
            backend="PyMC CPU NUTS",
            pymc_version=pmv,
            arviz_version=azv,
            snapshot_fingerprint=request["fingerprint"],
            snapshot_uri=request["snapshot_uri"],
            source_snapshot_id=request["source_snapshot_id"],
            seed=spec.seed,
            help_content_version=59,
            chains=p["chains"],
            draws=p["draws"],
            warmup=p["warmup"],
            predictor_scaling="raw",
            serialization="numeric h5netcdf; gzip4; draw chunks<=128; no model code/pickle",
        ),
    )
    result["warnings"] += (
        w
        + w2
        + diagnostics["warnings"]
        + alt_diag["warnings"]
        + criteria.get("warnings", [])
    )
    if diagnostics["status"] != "diagnostics_passed":
        result["warnings"].append(
            "DIAGNOSTIC FAIL: yakınsama güvenilir sayılmaz; trace/R-hat/ESS/divergence/BFMI inceleyin."
        )
    checked(request, control)
    directory = Path(workspace)
    paths = {
        k: directory / name
        for k, name in dict(
            result="bayes-result.json",
            members="bayes-members.parquet",
            details="bayes-observations.parquet",
            chains="bayes-chains.nc",
            diagnostic_png="bayes-trace.png",
        ).items()
    }
    # Store posterior + pointwise likelihood + PPC + alternative posterior as safe numeric groups.
    import xarray as xr

    idata.add_groups(
        {
            "posterior_predictive": xr.Dataset(
                {
                    "outcome": (
                        ("chain", "draw", "observation"),
                        rep.reshape(p["chains"], p["draws"], len(y)),
                    )
                },
                coords={"observation": f["__vu_row_id"].to_list()},
            ),
            "sensitivity_posterior": alternative.posterior,
            "sensitivity_sample_stats": alternative.sample_stats,
        }
    )
    for i, group in enumerate(idata.groups()):
        ds = getattr(idata, group)
        encoding = {
            name: dict(
                zlib=True,
                complevel=4,
                chunksizes=tuple(
                    min(128, ds.sizes[d]) if d == "draw" else ds.sizes[d]
                    for d in arr.dims
                ),
            )
            for name, arr in ds.data_vars.items()
            if arr.ndim
        }
        ds.to_netcdf(
            paths["chains"],
            group=group,
            engine="h5netcdf",
            mode="w" if i == 0 else "a",
            encoding=encoding,
        )
        control.disk(directory)
        control.check()
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    variables = list(idata.posterior.data_vars)
    fig = Figure(figsize=(10, 2.4 * len(variables)))
    FigureCanvasAgg(fig)
    for i, name in enumerate(variables):
        ax = fig.add_subplot(len(variables), 1, i + 1)
        values = idata.posterior[name].transpose("chain", "draw", ...).values
        for chain, arr in enumerate(values):
            # Multivariate coefficients/group effects share a panel; full chains stored.
            ax.plot(
                arr.reshape(len(arr), -1),
                lw=0.5,
                alpha=0.7,
                color="C" + str(chain),
                label="chain " + str(chain),
            )
        ax.set(
            xlabel="post-warmup draw",
            ylabel=name,
            title=diagnostics["status"] + " · " + name + " · all chains/components",
        )
        handles, labels = ax.get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        ax.legend(unique.values(), unique.keys(), fontsize=7)
    fig.tight_layout()
    fig.savefig(paths["diagnostic_png"], dpi=120)
    pl.DataFrame({"row_id": result["observation_ids"]}).write_parquet(paths["members"])
    f.rename({"__vu_row_id": "row_id"}).write_parquet(paths["details"])
    paths["result"].write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    result["paths"] = {k: str(v) for k, v in paths.items()}
    result["fingerprints"] = {k: hash_artifact(v, control) for k, v in paths.items()}
    control.check()
    return result


def verify_source(path, columns, result, details, members):
    from veri_ufku.importers.delimited import Control
    from veri_ufku.statistics.contracts import AnalysisSpec

    spec = AnalysisSpec.from_dict(result["spec"])
    request = dict(
        path=str(path), columns=columns, fingerprint=hash_artifact(path, Control())
    )
    f, *_ = prepare(request, spec, Control())
    if (
        not f.rename({"__vu_row_id": "row_id"}).equals(details)
        or members["row_id"].to_list() != result["observation_ids"]
        or members["row_id"].to_list() != f["__vu_row_id"].to_list()
        or columns != result["source_columns"]
    ):
        raise ProjectError("Bayes gözlem/RowId/ColumnId/source eşlemesi uyuşmuyor.")


def verify_chains(path, result):
    """Numeric data reader only; validate retained draws and exact source row coordinate."""
    import h5py

    p = result["spec"]["bayes_plan"]
    shape = (p["chains"], p["draws"])
    with h5py.File(path, "r") as h:
        for group in (
            "posterior",
            "sample_stats",
            "log_likelihood",
            "posterior_predictive",
            "sensitivity_posterior",
            "sensitivity_sample_stats",
        ):
            if group not in h:
                raise ProjectError("Bayes numeric chain grupları eksik.")
        for group in ("posterior", "sensitivity_posterior"):
            summary = result[
                "diagnostics" if group == "posterior" else "prior_sensitivity"
            ]
            if group != "posterior":
                summary = summary["diagnostics"]
            for item in summary["summary"]:
                label = item["parameter"]
                name = label.split("(")[0]
                ds = h[group].get(name)
                if ds is None or ds.shape[:2] != shape or ds.dtype.kind not in "fiu":
                    raise ProjectError("Bayes draw boyutu/türü uyuşmuyor.")
                array = ds[:]
                index = label[len(name) :]
                if index:
                    # JSON template labels are generated numeric index tuples, never evaluated.
                    indices = tuple(
                        int(v.strip())
                        for v in index.strip("()").split(",")
                        if v.strip()
                    )
                    array = array[(slice(None), slice(None)) + indices]
                if not np.isfinite(array).all() or not math.isclose(
                    float(array.mean()), item["mean"], rel_tol=1e-12, abs_tol=1e-12
                ):
                    raise ProjectError("Bayes summary/chain uyuşmuyor.")
        for group in ("log_likelihood", "posterior_predictive"):
            ds = h[group]["outcome"]
            if (
                ds.shape != shape + (result["used_rows"],)
                or not np.isfinite(ds[:]).all()
            ):
                raise ProjectError(
                    "Bayes likelihood/predictive boyutu/sonluluk hatası."
                )
            ids = h[group]["observation"].asstr()[:].tolist()
            if ids != result["observation_ids"]:
                raise ProjectError("Bayes chain Source RowId koordinatı uyuşmuyor.")
