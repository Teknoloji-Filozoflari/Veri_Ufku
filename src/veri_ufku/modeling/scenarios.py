"""CPU bounded simulations and solver adapters, with explicit numerical semantics."""

import json
import math
import time
import warnings
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy import optimize, stats

from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.scenario_contracts import LIMITATIONS, ScenarioSpec
from veri_ufku.modeling.scenario_contracts import public_report as public_report
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import file_hash


class SolverTimeout(Exception):
    pass


class Units:
    def __init__(self, variables):
        import pint

        self.registry = pint.UnitRegistry(autoconvert_offset_to_baseunit=False)
        self.units = [x["unit"] for x in variables]
        for u in self.units:
            self.multiplicative(u)

    def multiplicative(self, u):
        try:
            q = self.registry.Quantity
            # Multiplication rejects offset units; require an explicit absolute unit.
            q(1, u) * q(1, "dimensionless")
            if not math.isfinite(float(q(1, u).to_base_units().magnitude)):
                raise ValueError()
        except Exception as e:
            raise ProjectError(
                "Birim bilinmiyor/offset; cebir için açık multiplicative birime dönüştürün (ör. kelvin)."
            ) from e

    def coefficients(self, entries, output, quadratic=False):
        self.multiplicative(output)
        q = self.registry.Quantity
        try:
            if quadratic:
                return np.array(
                    [
                        [
                            float(
                                (
                                    q(e["value"], e["unit"])
                                    * q(1, self.units[i])
                                    * q(1, self.units[j])
                                )
                                .to(output)
                                .magnitude
                            )
                            for j, e in enumerate(row)
                        ]
                        for i, row in enumerate(entries)
                    ]
                )
            return np.array(
                [
                    float(
                        (q(e["value"], e["unit"]) * q(1, self.units[i]))
                        .to(output)
                        .magnitude
                    )
                    for i, e in enumerate(entries)
                ]
            )
        except Exception as e:
            raise ProjectError(
                "Objective/constraint katsayısı × input birimi output birimiyle uyumsuz."
            ) from e


def algebra(s):
    u = Units(s["variables"])
    obj = s["objective"]
    c = (
        u.coefficients(
            obj.get(
                "linear", [dict(value=0, unit="dimensionless")] * len(s["variables"])
            ),
            obj["unit"],
        )
        if "model" not in s
        else None
    )
    matrix = (
        u.coefficients(obj["quadratic"], obj["unit"], True)
        if "quadratic" in obj
        else np.zeros((len(s["variables"]),) * 2)
    )
    if not np.allclose(matrix, matrix.T, rtol=0, atol=1e-12):
        raise ProjectError("Quadratic matrix simetrik olmalı; otomatik symmetrize yok.")
    constraints = [
        (u.coefficients(con["linear"], con["unit"]), con)
        for con in s.get("constraints", [])
    ]
    return c, matrix, constraints


def polynomial(x, c, matrix, offset):
    v = np.asarray(x)
    y = offset + v @ c + 0.5 * np.einsum("...i,ij,...j->...", v, matrix, v)
    if not np.isfinite(y).all():
        raise ProjectError("Objective sonlu değil; ölçek/parametreleri kontrol edin.")
    return y


def simulate(s, control):
    c, matrix, _ = algebra(s)
    n, dimensions = s["draws"], len(s["variables"])
    if (
        n * dimensions * 8 * 8 > control.budget.ram_bytes // 4
        or control.budget.device != "cpu"
    ):
        raise ProjectError(
            "Simulation RAM/device önkontrolü başarısız; CPU ve daha küçük draw bütçesi seçin."
        )
    rng = np.random.Generator(np.random.PCG64(s["seed"]))
    corr = None
    if s["dependence"] == "normal-correlation":
        corr = np.asarray(s["correlation"], float)
        if (
            not np.allclose(corr, corr.T, rtol=0, atol=1e-12)
            or not np.allclose(np.diag(corr), 1, rtol=0, atol=1e-12)
            or np.max(np.abs(corr)) > 1
            or np.linalg.eigvalsh(corr).min() < -1e-12
        ):
            raise ProjectError(
                "Correlation simetrik, diagonal1, PSD olmalı; otomatik onarım yok."
            )
    inputs = np.empty((n, dimensions))
    distributions = [x["distribution"] for x in s["variables"]]
    for start in range(0, n, 1024):
        control.check()
        count = min(1024, n - start)
        if corr is not None:
            block = rng.multivariate_normal(
                [d["mean"] for d in distributions],
                corr
                * np.outer(
                    [d["sd"] for d in distributions], [d["sd"] for d in distributions]
                ),
                size=count,
                check_valid="raise",
                method="eigh",
            )
        else:
            block = np.empty((count, dimensions))
            for i, d in enumerate(distributions):
                block[:, i] = (
                    rng.normal(d["mean"], d["sd"], count)
                    if d["kind"] == "normal"
                    else rng.uniform(d["low"], d["high"], count)
                    if d["kind"] == "uniform"
                    else rng.triangular(d["low"], d["mode"], d["high"], count)
                )
        inputs[start : start + count] = block
        control.progress("Monte Carlo", start + count, n)
    output = polynomial(inputs, c, matrix, s["objective"].get("offset", 0))
    probabilities = [0.025, 0.25, 0.5, 0.75, 0.975]
    batches = np.array_split(output, 16)
    quantile_mcse = (
        np.std(
            [np.quantile(b, probabilities, method="linear") for b in batches],
            axis=0,
            ddof=1,
        )
        / 4
    )
    sensitivity = []
    centre = inputs.mean(axis=0)
    for i, x in enumerate(s["variables"]):
        control.check()
        constant = np.ptp(output) == 0 or np.ptp(inputs[:, i]) == 0
        rho = (
            None if constant else float(stats.spearmanr(inputs[:, i], output).statistic)
        )
        sensitivity.append(
            dict(
                input=x["name"],
                spearman=rho,
                derivative_at_sample_mean=float(c[i] + (matrix @ centre)[i]),
                derivative_unit=s["objective"]["unit"] + "/(" + x["unit"] + ")",
                interpretation="marginal association and local algebraic derivative; not causal, not variance allocation",
            )
        )
    analytic = None
    if all(d["kind"] == "normal" for d in distributions) and not matrix.any():
        means = np.array([d["mean"] for d in distributions])
        sd = np.array([d["sd"] for d in distributions])
        covariance = np.outer(sd, sd) * (
            corr if corr is not None else np.eye(dimensions)
        )
        analytic = dict(
            mean=float(s["objective"].get("offset", 0) + means @ c),
            variance=float(c @ covariance @ c),
            assumption="affine joint normal template only",
        )
    return dict(
        status="completed",
        draws=n,
        rng="PCG64",
        chunk_rows=1024,
        output_unit=s["objective"]["unit"],
        mean=float(output.mean()),
        sd=float(output.std(ddof=1)),
        mean_mcse=float(output.std(ddof=1) / np.sqrt(n)),
        quantiles=[
            dict(probability=p, value=float(v), mcse_approx=float(e))
            for p, v, e in zip(
                probabilities,
                np.quantile(output, probabilities, method="linear"),
                quantile_mcse,
                strict=True,
            )
        ],
        quantile_method="linear; approximate MCSE from16 independent blocks, sd(block quantile)/sqrt16; unstable tails/small draws",
        sensitivity=sensitivity,
        analytic_reference=analytic,
        input_correlation=np.atleast_2d(np.corrcoef(inputs.T)).tolist()
        if dimensions > 1
        else [[1.0]],
        uncertainty_types={x["name"]: x["uncertainty"] for x in s["variables"]},
        uncertainty_scope="joint propagation only; no nested epistemic/measurement variance decomposition",
    )


def feasibility(x, s, constraints):
    if x is None or not np.isfinite(x).all():
        return dict(feasible=False, checks=[], reason="no finite candidate")
    checks = []
    for val, v in zip(x, s["variables"], strict=True):
        violation = max(
            0,
            v.get("lower") - val if v.get("lower") is not None else 0,
            val - v.get("upper") if v.get("upper") is not None else 0,
        )
        checks.append(
            dict(
                name=v["name"],
                kind="bounds",
                violation=float(violation),
                unit=v["unit"],
            )
        )
        if v.get("integer"):
            checks.append(
                dict(
                    name=v["name"],
                    kind="integrality",
                    violation=float(abs(val - round(val))),
                    unit="dimensionless",
                )
            )
    for i, (a, con) in enumerate(constraints):
        residual = float(a @ x - con["rhs"])
        violation = (
            abs(residual)
            if con["sense"] == "eq"
            else max(0, residual if con["sense"] == "le" else -residual)
        )
        checks.append(
            dict(name=str(i), kind="constraint", violation=violation, unit=con["unit"])
        )
    return dict(
        feasible=all(c["violation"] <= s["tolerance"] for c in checks),
        checks=checks,
        tolerance=s["tolerance"],
        tolerance_scope="absolute in each displayed constraint/variable unit; integrality dimensionless",
    )


def model_function(request, s, workspace, control):
    import polars as pl

    from veri_ufku.analytics.dataset import checked
    from veri_ufku.modeling.lifecycle import MAX_BYTES, load_package

    package = request["model"]
    if package["fingerprint"]["size"] > MAX_BYTES:
        raise ProjectError("Frozen model boyut bütçesini aşıyor.")
    with Path(package["path"]).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    from veri_ufku.domain.json import sha

    if (
        len(raw) > MAX_BYTES
        or dict(size=len(raw), sha256=sha(raw)) != package["fingerprint"]
    ):
        raise ProjectError("Frozen model hash/boyut değişmiş.")
    private = Path(workspace) / "scenario.vumodel"
    private.write_bytes(raw)
    model, card = load_package(private)
    if card != package["card"] or card["purpose"] != "regression":
        raise ProjectError("Model senaryosu yalnız frozen safe regression destekler.")
    features = card["features"]
    if [x["name"] for x in s["variables"]] != [f["id"] for f in features] or any(
        f["type"] not in ("float64", "Float64") for f in features
    ):
        raise ProjectError(
            "Model senaryosu bütün Float64 özellikleri eğitim ColumnId sırasında ister; kategorik/integer optimize edilmez."
        )
    if (
        any(
            (f["unit"] or "dimensionless") != v["unit"]
            for f, v in zip(features, s["variables"], strict=True)
        )
        or (card["target"].get("unit") or "dimensionless") != s["objective"]["unit"]
    ):
        raise ProjectError(
            "Model input/target birimleri kartla aynı olmalı; sessiz dönüşüm yok."
        )
    source = request["sources"][card["dataset_version"]]
    checked(source, control)
    if source["fingerprint"] != card["snapshot_fingerprint"] or source[
        "row_count"
    ] > min(10000, control.budget.sample_limit_rows):
        raise ProjectError(
            "Model training snapshot hash/bounded row kontrolü başarısız."
        )
    frame = pl.read_parquet(
        source["path"],
        columns=["__vu_row_id", "__vu_source_record_id"]
        + [f["name"] for f in features],
    )
    fit_ids = card["fit_row_ids"]
    fit = frame.filter(pl.col("__vu_row_id").is_in(fit_ids))
    if (
        not fit_ids
        or len(fit) != len(set(fit_ids))
        or len(fit_ids) != len(set(fit_ids))
    ):
        raise ProjectError("Model fit RowId kökeni eksik.")
    domains = []
    for f in features:
        a = fit[f["name"]].to_numpy()
        if not np.isfinite(a).all():
            raise ProjectError(
                "Model geçerlilik aralığı için fit özellikleri finite/complete olmalı."
            )
        domains.append(
            dict(
                column_id=f["id"],
                lower=float(a.min()),
                upper=float(a.max()),
                unit=f["unit"] or "dimensionless",
            )
        )
    if s["method"] == "model-optimize" and any(
        v["lower"] < d["lower"] or v["upper"] > d["upper"]
        for v, d in zip(s["variables"], domains, strict=True)
    ):
        raise ProjectError(
            "Optimizasyon sınırları model fit geçerlilik aralığı dışına çıkıyor; daraltın."
        )
    calls = 0

    def predict(x):
        nonlocal calls
        control.check()
        calls += 1
        if calls > 20000:
            raise ProjectError("Model prediction call bütçesi20000 aşıldı.")
        data = pl.DataFrame(
            {
                f["name"]: pl.Series([float(v)], dtype=pl.Float64)
                for f, v in zip(features, x, strict=True)
            }
        )
        y = float(np.asarray(model.predict(data))[0])
        if not math.isfinite(y):
            raise ProjectError("Model prediction finite değil.")
        return y

    return predict, dict(
        fit_rows=len(fit),
        fit_row_ids=fit["__vu_row_id"].to_list(),
        fit_source_record_ids=fit["__vu_source_record_id"].to_list(),
        domain=domains,
        joint_support="not established; marginal bounds only",
        training_labels_read=False,
    )


def solve(s, control, function=None, domain=None):
    c, matrix, constraints = algebra(s)
    sign = 1 if s["direction"] == "min" else -1
    deadline = time.monotonic() + min(s["seconds"], control.budget.max_wall_seconds)
    best = None
    evaluations = 0

    def objective(x):
        nonlocal best, evaluations
        control.check()
        if time.monotonic() >= deadline:
            raise SolverTimeout()
        evaluations += 1
        y = float(
            function(x)
            if function
            else polynomial(x, c, matrix, s["objective"].get("offset", 0))
        )
        if feasibility(x, s, constraints)["feasible"] and (
            best is None or sign * y < sign * best[1]
        ):
            best = (np.asarray(x).copy(), y)
        return sign * y

    bounds = [(v.get("lower"), v.get("upper")) for v in s["variables"]]
    method = s["method"]
    raw_status = None
    gap = None
    bound = None
    forwarded = []
    try:
        control.check()
        if method == "what-if":
            x = np.asarray(s["point"], float)
            outside = [
                d["column_id"]
                for val, d in zip(x, domain["domain"], strict=True)
                if val < d["lower"] or val > d["upper"]
            ]
            value = objective(x) / sign
            return dict(
                status="scenario_prediction",
                point=x.tolist(),
                objective=value,
                output_unit=s["objective"]["unit"],
                feasibility=feasibility(x, s, constraints),
                outside_model_domain=outside,
                model_domain=domain,
                optimal=False,
                causal=False,
            )
        if method in ("linear", "mixed-integer"):
            if control.budget.device != "cpu":
                raise ProjectError("Solver yalnız CPU; sessiz GPU fallback yok.")
            options = dict(
                time_limit=s["seconds"],
                presolve=method == "linear",
                threads=control.budget.worker_threads,
                parallel=False,
                disp=False,
            )
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                if method == "linear":
                    aub = []
                    bub = []
                    aeq = []
                    beq = []
                    for a, con in constraints:
                        if con["sense"] == "eq":
                            aeq.append(a)
                            beq.append(con["rhs"])
                        else:
                            k = 1 if con["sense"] == "le" else -1
                            aub.append(a * k)
                            bub.append(con["rhs"] * k)
                    res = optimize.linprog(
                        sign * c,
                        A_ub=aub or None,
                        b_ub=bub or None,
                        A_eq=aeq or None,
                        b_eq=beq or None,
                        bounds=bounds,
                        method="highs",
                        options=dict(
                            options,
                            maxiter=s["maxiter"],
                            primal_feasibility_tolerance=s["tolerance"],
                            dual_feasibility_tolerance=s["tolerance"],
                        ),
                    )
                else:
                    lo = [
                        v.get("lower") if v.get("lower") is not None else -np.inf
                        for v in s["variables"]
                    ]
                    hi = [
                        v.get("upper") if v.get("upper") is not None else np.inf
                        for v in s["variables"]
                    ]
                    lc = [
                        optimize.LinearConstraint(
                            a,
                            con["rhs"] if con["sense"] in ("eq", "ge") else -np.inf,
                            con["rhs"] if con["sense"] in ("eq", "le") else np.inf,
                        )
                        for a, con in constraints
                    ]
                    res = optimize.milp(
                        sign * c,
                        integrality=[
                            int(v.get("integer", False)) for v in s["variables"]
                        ],
                        bounds=optimize.Bounds(lo, hi),
                        constraints=lc,
                        options=dict(
                            options, node_limit=s["maxiter"], mip_rel_gap=s["gap"]
                        ),
                    )
                forwarded = [str(w.message) for w in caught]
            raw_status = int(res.status)
            status = {
                0: "optimal_within_tolerance",
                1: "limit_reached",
                2: "infeasible",
                3: "unbounded",
                4: "solver_failure_or_ambiguous",
            }.get(raw_status, "solver_failure")
            x = res.x
            gap = getattr(res, "mip_gap", None) if method == "mixed-integer" else None
            bound = (
                getattr(res, "mip_dual_bound", None)
                if method == "mixed-integer"
                else None
            )
            if bound is not None and math.isfinite(bound):
                bound = float(sign * bound + s["objective"].get("offset", 0))
            else:
                bound = None
        else:
            scipy_constraints = [
                dict(
                    type="eq" if con["sense"] == "eq" else "ineq",
                    fun=lambda x, a=a, con=con: (
                        (1 if con["sense"] in ("eq", "ge") else -1)
                        * (a @ x - con["rhs"])
                    ),
                )
                for a, con in constraints
            ]
            res = optimize.minimize(
                objective,
                [v["initial"] for v in s["variables"]],
                method="SLSQP",
                bounds=bounds,
                constraints=scipy_constraints,
                options=dict(maxiter=s["maxiter"], ftol=s["tolerance"], disp=False),
            )
            raw_status = int(res.status)
            x = res.x
            status = (
                "local_candidate"
                if res.success
                else "iteration_limit"
                if raw_status == 9
                else "no_convergence"
            )
        control.check()
        if time.monotonic() >= deadline:
            status = "timeout"
    except SolverTimeout:
        x = best[0] if best else None
        status = "timeout"
    feasible = feasibility(x, s, constraints)
    if (
        status in ("optimal_within_tolerance", "local_candidate")
        and not feasible["feasible"]
    ):
        status = "failed_feasibility_check"
    val = (
        float(
            function(x)
            if function
            else polynomial(x, c, matrix, s["objective"].get("offset", 0))
        )
        if x is not None and np.isfinite(x).all()
        else None
    )
    return dict(
        status=status,
        solver="HiGHS LP"
        if method == "linear"
        else "HiGHS MILP"
        if method == "mixed-integer"
        else "SLSQP bounded local",
        raw_status=raw_status,
        optimal=status == "optimal_within_tolerance",
        global_optimum_claim=method in ("linear", "mixed-integer")
        and status == "optimal_within_tolerance",
        point=x.tolist() if x is not None and np.isfinite(x).all() else None,
        objective=val,
        output_unit=s["objective"]["unit"],
        feasibility=feasible,
        mip_relative_gap=float(gap) if gap is not None and math.isfinite(gap) else None,
        objective_bound=bound,
        bound_scope="linear objective excludes constant during solver gap calculation; bound shifted back; SLSQP has no global bound/gap",
        requested_tolerance=s["tolerance"],
        requested_gap=s["gap"] if method == "mixed-integer" else None,
        seconds=s["seconds"],
        maxiter_or_nodes=s["maxiter"],
        evaluations=evaluations,
        backend_warnings=forwarded,
        model_domain=domain,
        causal=False,
    )


def calculate(request, parameters, workspace, control=None):
    control = control or Control()
    s = ScenarioSpec.from_dict(parameters).data()
    if control.budget.device != "cpu":
        raise ProjectError("Senaryo backend CPU gerektirir.")
    now = datetime.now(UTC).isoformat()
    started = time.monotonic()
    if s["method"] == "monte-carlo":
        output = simulate(s, control)
    else:
        function, domain = (
            model_function(request, s, workspace, control)
            if "model" in s
            else (None, None)
        )
        output = solve(s, control, function, domain)
    for source in request["sources"].values():
        if file_hash(Path(source["path"])) != source["fingerprint"]:
            raise ProjectError("Senaryo kaynak hash değişmiş.")
    if (
        request["model"]
        and file_hash(Path(request["model"]["path"])) != request["model"]["fingerprint"]
    ):
        raise ProjectError("Senaryo model hash değişmiş.")
    value = dict(
        schema="ScenarioRun/v1",
        run_id="run:" + uid(),
        status="completed",
        spec=s,
        output=output,
        limitations=LIMITATIONS,
        fit_calls=0,
        duration_seconds=time.monotonic() - started,
        experiment_capture=request["experiment_capture"],
        prior_test_use_ids=request["prior_test_use_ids"],
        source_refs={
            k: dict(
                fingerprint=v["fingerprint"], source_snapshot_id=v["source_snapshot_id"]
            )
            for k, v in request["sources"].items()
        },
        model_refs={
            request["model"]["record_id"]: {
                k: request["model"][k] for k in ("fingerprint", "record_id", "run_id")
            }
        }
        if request["model"]
        else {},
        compute_budget=asdict(control.budget),
    )
    value["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + uid(),
            dataset_versions=tuple(request["sources"]),
            config_revision=0,
            capability_id="scenario." + s["method"],
            parameters_hash=digest(s),
            environment=(("backend", "numpy/scipy/Pint CPU"),),
            created_at=now,
            scope="synthetic assumptions; no source mutation; model fit-range inspection only when selected",
            seed=s.get("seed"),
            seed_reason="PCG64 draw stream"
            if s["method"] == "monte-carlo"
            else "deterministic solver; numeric/platform tolerance applies",
            source_snapshot_ids=tuple(
                v["source_snapshot_id"] for v in request["sources"].values()
            ),
        )
    )
    value = json.loads(json.dumps(value, allow_nan=False))
    value["identity"] = digest(value)
    control.check()
    return value
