"""Bounded causal templates. A graph and fitted association never certify causality."""

import json
import math
import warnings
from pathlib import Path

import numpy as np
import polars as pl
import scipy
import statsmodels
import statsmodels.api as sm
from scipy import stats
from sklearn.preprocessing import StandardScaler

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked, filtered
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.modeling.validation import ValidationSpec, split_plan
from veri_ufku.statistics.causal_contracts import CAUSAL_LABELS, OBSERVATIONAL
from veri_ufku.storage.project_model import ProjectError, uid

CAUTION = (
    "DAG ve kullanıcı gerekçesi nedensellik kanıtı değildir. Exchangeability/ölçülmemiş "
    "confounding gözlenen veriden doğrulanamaz. Etki yalnız kayıtlı varsayımlar altında; "
    "alternatif açıklamalar ve hedef popülasyon raporun parçasıdır."
)


def identification(spec):
    """Backdoor d-separation using ancestral moralization, not role-name heuristics."""
    p = spec.causal_plan
    required = ["consistency", "positivity", "no_interference", "time_order"]
    if spec.method != "causal_randomized":
        required += ["exchangeability"]
    if spec.method == "causal_did":
        required += ["parallel_trends", "no_anticipation"]
    if spec.method == "causal_iv":
        required += ["exclusion", "instrument_independence", "monotonicity"]
    reasons = [
        "Varsayım gerekçesi eksik: " + k
        for k in required
        if not p["assumptions"][k].strip()
    ]
    nodes = {n["id"]: n for n in p["dag"]["nodes"]}
    edges = [(e["from"], e["to"]) for e in p["dag"]["edges"]]
    selected = set(spec.features)
    if not selected <= nodes.keys():
        reasons.append("Her adjustment covariate DAG üzerinde gerekçeli seçilmeli.")
    descendants = {spec.y}
    while True:
        newer = descendants | {b for a, b in edges if a in descendants}
        if newer == descendants:
            break
        descendants = newer
    if selected & descendants:
        reasons.append(
            "Total etki için tedavi sonrası descendant/mediator adjustment reddi."
        )
    if any(nodes.get(c, {}).get("role") in ("collider", "mediator") for c in selected):
        reasons.append("Collider/mediator adjustment total ATE şablonuna uygun değil.")
    backdoor = [(a, b) for a, b in edges if a != spec.y]
    ancestors = {spec.y, spec.x} | selected
    while True:
        newer = ancestors | {a for a, b in backdoor if b in ancestors}
        if newer == ancestors:
            break
        ancestors = newer
    graph = {v: set() for v in ancestors}
    for a, b in backdoor:
        if a in ancestors and b in ancestors:
            graph[a].add(b)
            graph[b].add(a)
    for child in ancestors:
        parents = [a for a, b in backdoor if b == child and a in ancestors]
        for a in parents:
            graph[a].update(set(parents) - {a})
    reachable = {spec.y}
    while True:
        newer = reachable | {
            b for a in reachable for b in graph[a] if b not in selected
        }
        if newer == reachable:
            break
        reachable = newer
    separated = spec.x not in reachable
    if spec.method in OBSERVATIONAL and not separated:
        reasons.append(
            "Seçili covariate seti beyan edilen DAG'de backdoor yollarını kapatmıyor."
        )
    if spec.method == "causal_randomized" and not separated:
        reasons.append("DAG randomizasyon beyanıyla çelişiyor: açık backdoor yolu.")
    if spec.method == "causal_iv":
        instrument = p["instrument"]
        if instrument not in nodes:
            reasons.append("Instrument DAG üzerinde gerekçeli node olmalı.")
        else:
            # Conservatively reject any incoming cause of Z or directed Z→Y
            # path avoiding treatment. Absence is a hypothesis, not validity proof.
            if any(b == instrument for a, b in edges):
                reasons.append(
                    "IV independence DAG'de gerekçelendirilemiyor: instrument incoming cause."
                )
            reach = {instrument}
            while True:
                newer = reach | {b for a, b in edges if a in reach and b != spec.y}
                if newer == reach:
                    break
                reach = newer
            if spec.x in reach:
                reasons.append(
                    "IV exclusion DAG çelişkisi: treatment dışında outcome yolu."
                )
            if (instrument, spec.y) not in edges:
                reasons.append("DAG instrument→treatment relevance hipotezi içermiyor.")
    # DiD and IV identification is not the ordinary adjustment criterion.
    return dict(
        status="conditional" if not reasons else "not_identified",
        blockers=reasons,
        backdoor_separated=separated,
        assumptions=p["assumptions"],
        dag=p["dag"],
        alternatives=p["alternatives"],
        caveat=CAUTION,
    )


def load(request, spec, control):
    q, schema, names = filtered(request, ViewSpec())
    n = q.select(pl.len()).collect(engine="streaming").item()
    limit = 3000 if spec.method == "causal_did" else 2000
    if not n or n > limit or n * 8192 > control.budget.ram_bytes // 2:
        raise ProjectError("Nedensel tam veri boş veya satır/RAM bütçesi aşıldı.")
    p = spec.causal_plan
    columns = [spec.x, spec.y, spec.key, spec.time_column, *spec.features]
    columns += [v for v in (p["instrument"], p["placebo"]) if v]
    numeric = set(columns) - {spec.key}
    for c in columns:
        dtype = schema[names[c]]
        if c in numeric and (not dtype.is_numeric() or isinstance(dtype, pl.Decimal)):
            raise ProjectError(
                "Bu şablon eksiksiz sayısal ölçüm/zaman ister; tarih açık dönem sütunuyla hazırlanmalı."
            )
        if dtype.is_nested() or dtype == pl.Binary:
            raise ProjectError("Birim kimliği skaler olmalı.")
        if dtype.is_integer() and c in numeric:
            maximum = (
                q.select(pl.col(names[c]).cast(pl.Float64).abs().max()).collect().item()
            )
            if maximum is not None and maximum > 2**53:
                raise ProjectError("Kayıpsız Float64 sınırını aşan integer reddi.")
    frame = q.select(
        "__vu_row_id",
        *[
            pl.col(c)
            for c in (
                "__vu_source_record_id",
                "__vu_source_locator",
                "__vu_expansion_index",
            )
            if c in schema
        ],
        *[pl.col(names[c]).alias(c) for c in columns],
    ).collect(engine="streaming")
    for c in columns:
        vals = frame[c].to_list()
        if any(
            v is None
            or not str(v).strip()
            or isinstance(v, float)
            and not math.isfinite(v)
            for v in vals
        ):
            raise ProjectError(
                "Eksik/sonsuz nedensel alan; sessiz drop/imputasyon yapılmaz."
            )
        if c in numeric and any(abs(float(v)) > 1e20 for v in vals):
            raise ProjectError("Sayısal kararlılık ölçüm sınırı aşıldı.")
    if set(frame[spec.y].to_list()) != {0, 1}:
        raise ProjectError("Treatment eksiksiz ikili0/1 ve iki kol olmalı.")
    if min(frame.filter(pl.col(spec.y) == a).height for a in (0, 1)) < 3:
        raise ProjectError("Her kolda en az3 kayıt gerekli.")
    if spec.method != "causal_did" and frame[spec.key].n_unique() != n:
        raise ProjectError(
            "Bağımsız analiz birimi tek satır olmalı; repeated/cluster uygun şablon ister."
        )
    if p["instrument"] and set(frame[p["instrument"]].to_list()) != {0, 1}:
        raise ProjectError("Bu IV şablonu ikili0/1 instrument ister.")
    control.check()
    return frame.sort("__vu_row_id")


def difference(y, treatment, confidence):
    a, b = y[treatment == 1], y[treatment == 0]
    v1, v0 = np.var(a, ddof=1) / len(a), np.var(b, ddof=1) / len(b)
    se = math.sqrt(v1 + v0)
    df = (v1 + v0) ** 2 / (v1**2 / (len(a) - 1) + v0**2 / (len(b) - 1)) if se else None
    estimate = float(a.mean() - b.mean())
    radius = float(stats.t.ppf((1 + confidence) / 2, df)) * se if se else 0.0
    return dict(
        estimate=estimate,
        se=se,
        interval=[estimate - radius, estimate + radius],
        confidence=confidence,
        inference="Welch t independent-unit CI",
        df=df,
    )


def balance(x, t, w=None):
    w = np.ones(len(t)) if w is None else w
    answer = []
    for col in x.T:
        arms = [col[t == a] for a in (0, 1)]
        denominator = math.sqrt((np.var(arms[0], ddof=1) + np.var(arms[1], ddof=1)) / 2)
        delta = float(
            np.average(arms[1], weights=w[t == 1])
            - np.average(arms[0], weights=w[t == 0])
        )
        answer.append(
            dict(
                smd=delta / denominator
                if denominator
                else (0.0 if not delta else None),
                undefined_constant_with_different_means=not denominator and bool(delta),
            )
        )
    return answer


def nuisance(frame, spec, request, control):
    y = frame[spec.x].to_numpy().astype(float)
    t = frame[spec.y].to_numpy().astype(int)
    x = frame.select(spec.features).to_numpy().astype(float)
    rowids = frame["__vu_row_id"].to_list()
    v = ValidationSpec(
        method="stratified", folds=spec.causal_plan["folds"], seed=spec.seed
    )
    plan, indices = split_plan(
        rowids,
        t,
        None,
        None,
        v,
        "stratified",
        True,
        request.get("version_id", "verification"),
        request.get("fingerprint", {}),
    )
    _, _, development, test, folds = indices
    blocks = [(a, b) for a, b in folds] + [(development, test)]
    e, m0, m1 = (np.empty(len(t)) for _ in range(3))
    evaluated = np.zeros(len(t), dtype=int)
    membership = []
    for j, (train, evaluation) in enumerate(blocks):
        control.check()
        if set(train) & set(evaluation):
            raise ProjectError("Nuisance fold sızıntısı.")
        scaler = StandardScaler().fit(x[train])
        a = sm.add_constant(scaler.transform(x[train]), has_constant="add")
        b = sm.add_constant(scaler.transform(x[evaluation]), has_constant="add")
        if np.linalg.matrix_rank(a) < a.shape[1]:
            raise ProjectError(
                "Nuisance tasarımı rank deficient; covariate değiştirin."
            )
        with warnings.catch_warnings(record=True) as messages:
            warnings.simplefilter("always")
            fitted = sm.Logit(t[train], a).fit(disp=False, maxiter=100)
        if messages or not fitted.mle_retvals["converged"]:
            raise ProjectError(
                "Propensity separation/nonconvergence; positivity doğrulanamadı."
            )
        e[evaluation] = fitted.predict(b)
        for arm, destination in ((0, m0), (1, m1)):
            armrows = t[train] == arm
            if (
                sum(armrows) <= a.shape[1] + 1
                or np.linalg.matrix_rank(a[armrows]) < a.shape[1]
            ):
                raise ProjectError("Outcome nuisance arm örneklemi/rank yetersiz.")
            destination[evaluation] = (
                sm.OLS(y[train][armrows], a[armrows]).fit().predict(b)
            )
        evaluated[evaluation] += 1
        membership.append(
            dict(
                block=j,
                train=[rowids[i] for i in train],
                evaluation=[rowids[i] for i in evaluation],
            )
        )
        control.check()
    if not np.all(evaluated == 1) or not all(np.isfinite(z).all() for z in (e, m0, m1)):
        raise ProjectError("Out-of-fold kapsamı/sonlu nuisance doğrulanamadı.")
    if np.any((e <= 0) | (e >= 1)):
        raise ProjectError(
            "Propensity exact0/1: positivity yok; infinite weights hesaplanmaz."
        )
    return (
        x,
        e,
        m0,
        m1,
        dict(
            validation_plan=plan,
            nuisance_blocks=membership,
            test_role="reserved block evaluated using development only; not a model benchmark",
            preprocessing="StandardScaler fitted on each training block only",
            backend="unpenalized Logit + arm-specific linear OLS",
        ),
    )


def analyze(frame, spec, request, control):
    p = spec.causal_plan
    ident = identification(spec)
    y = frame[spec.x].to_numpy().astype(float)
    t = frame[spec.y].to_numpy().astype(int)
    rowids = frame["__vu_row_id"].to_list()
    result = dict(
        identification=ident,
        diagnostics={},
        effect=None,
        sensitivity=[],
        pairs=[],
        split_plan=None,
        estimand="ATE on selected full population",
        inference_limitations=[],
    )
    blockers = ident["blockers"]
    if spec.method == "causal_randomized":
        srm = float(stats.binomtest(int(t.sum()), len(t), p["allocation"]).pvalue)
        result["diagnostics"]["srm"] = dict(
            p_value=srm,
            allocation=p["allocation"],
            scheme="user-declared independent Bernoulli",
            evidence=p["randomization_evidence"],
        )
        if srm < 0.001:
            blockers.append(
                "Randomizasyon allocation/SRM uyumsuzluğu; ITT yorumu engelli."
            )
        if not blockers:
            result["effect"] = difference(y, t, spec.confidence)
    elif spec.method in OBSERVATIONAL:
        try:
            x, e, m0, m1, plan = nuisance(frame, spec, request, control)
        except (ProjectError, np.linalg.LinAlgError) as exc:
            blockers.append(
                str(exc) if isinstance(exc, ProjectError) else "Nuisance singularity."
            )
        else:
            result["split_plan"] = plan
            epsilon = p["overlap_epsilon"]
            weights = np.where(t == 1, 1 / e, 1 / (1 - e))
            overlap = dict(
                outside_epsilon=int(np.sum((e < epsilon) | (e > 1 - epsilon))),
                epsilon=epsilon,
                maximum_weight=float(weights.max()),
                extreme_threshold=p["extreme_weight"],
                ess=[
                    float(weights[t == a].sum() ** 2 / np.sum(weights[t == a] ** 2))
                    for a in (0, 1)
                ],
                arms=[
                    dict(
                        min=float(e[t == a].min()),
                        max=float(e[t == a].max()),
                        histogram=np.histogram(e[t == a], bins=np.linspace(0, 1, 11))[
                            0
                        ].tolist(),
                    )
                    for a in (0, 1)
                ],
                propensity_by_row=[
                    dict(row_id=r, propensity=float(v)) for r, v in zip(rowids, e)
                ],
                balance_before=balance(x, t),
                balance_ipw=balance(x, t, weights),
            )
            result["diagnostics"]["overlap"] = overlap
            if (
                overlap["outside_epsilon"]
                or overlap["maximum_weight"] > p["extreme_weight"]
            ):
                blockers.append(
                    "Positivity/extreme weights sorunu: clipping/trimming otomatik yapılmaz."
                )
            if max(e[t == 0].min(), e[t == 1].min()) > min(
                e[t == 0].max(), e[t == 1].max()
            ):
                blockers.append("Propensity iki kol aralıkları örtüşmüyor.")
            if not blockers:
                if spec.method == "causal_matching":
                    result["estimand"] = (
                        "ATT only among successfully matched treated units; not full ATE/ATT"
                    )
                    available = set(np.flatnonzero(t == 0).tolist())
                    deltas, selected = [], []
                    for i in np.flatnonzero(t == 1):
                        control.check()
                        if not available:
                            break
                        j = min(available, key=lambda j: (abs(e[i] - e[j]), rowids[j]))
                        if abs(e[i] - e[j]) <= p["caliper"]:
                            available.remove(j)
                            deltas.append(y[i] - y[j])
                            selected.extend([i, j])
                            result["pairs"].append(
                                dict(
                                    treated_row_id=rowids[i],
                                    control_row_id=rowids[j],
                                    treated_source_record_id=frame[
                                        "__vu_source_record_id"
                                    ][int(i)]
                                    if "__vu_source_record_id" in frame.columns
                                    else None,
                                    control_source_record_id=frame[
                                        "__vu_source_record_id"
                                    ][int(j)]
                                    if "__vu_source_record_id" in frame.columns
                                    else None,
                                    propensity_distance=float(abs(e[i] - e[j])),
                                )
                            )
                    if len(deltas) < 3:
                        blockers.append("Caliper içinde en az3 matched pair yok.")
                    else:
                        result["effect"] = dict(
                            estimate=float(np.mean(deltas)),
                            se=None,
                            interval=None,
                            inference="Point only; matching non-smooth inference not implemented",
                        )
                        result["diagnostics"]["matching"] = dict(
                            caliper=p["caliper"],
                            replacement=False,
                            pairs=len(deltas),
                            unmatched_treated=int(t.sum()) - len(deltas),
                            unmatched_control=len(available),
                            balance_matched=balance(x[selected], t[selected]),
                        )
                else:
                    psi = m1 - m0
                    if spec.method == "causal_ipw":
                        psi = t * y / e - (1 - t) * y / (1 - e)
                    if spec.method == "causal_aipw":
                        psi += t * (y - m1) / e - (1 - t) * (y - m0) / (1 - e)
                    effect = dict(
                        estimate=float(psi.mean()),
                        se=None,
                        interval=None,
                        inference="Point only; nuisance uncertainty CI unavailable for this template",
                    )
                    if spec.method == "causal_aipw" and len(t) >= 100:
                        se = float(psi.std(ddof=1) / math.sqrt(len(t)))
                        radius = float(stats.norm.ppf((1 + spec.confidence) / 2)) * se
                        effect.update(
                            se=se,
                            interval=[
                                effect["estimate"] - radius,
                                effect["estimate"] + radius,
                            ],
                            confidence=spec.confidence,
                            inference="Asymptotic cross-fitted influence-function CI; iid, overlap and nuisance product-rate consistency required",
                        )
                    result["effect"] = effect
    elif spec.method == "causal_did":
        result["estimand"] = (
            "DiD ATT in balanced two-pre/one-post panel; common adoption only"
        )
        periods = sorted(frame[spec.time_column].unique().to_list())
        try:
            post = float(p["post_time"])
        except ValueError:
            raise ProjectError("Post dönem sayısal olmalı.") from None
        if len(periods) != 3 or post != periods[-1]:
            raise ProjectError(
                "DiD tam2pre/1post ortak dönem ister; staggered/TWFE desteklenmez."
            )
        deltas, pre, arms = [], [], []
        for unit in frame.partition_by(spec.key):
            unit = unit.sort(spec.time_column)
            if (
                unit.height != 3
                or unit[spec.time_column].to_list() != periods
                or unit[spec.y].n_unique() != 1
            ):
                raise ProjectError(
                    "DiD balanced unique unit×period ve sabit ever-treated group ister."
                )
            values = unit[spec.x].to_list()
            deltas.append(values[2] - values[1])
            pre.append(values[1] - values[0])
            arms.append(unit[spec.y][0])
        arms = np.array(arms)
        if min(np.sum(arms == a) for a in (0, 1)) < 3:
            raise ProjectError("DiD her grupta en az3 bağımsız birim ister.")
        trend = difference(np.array(pre), arms, spec.confidence)
        trend["interpretation"] = (
            "Two pre periods only; non-rejection does not establish parallel trends; no anticipation assumption required."
        )
        result["diagnostics"]["pretrend_placebo"] = trend
        if trend["interval"][0] > 0 or trend["interval"][1] < 0:
            blockers.append(
                "Pretrend placebo farkı görünür; parallel-trends şablonu desteklenmiyor."
            )
        if not blockers:
            result["effect"] = difference(np.array(deltas), arms, spec.confidence)
    else:
        result["estimand"] = (
            "Wald LATE among compliers under valid binary instrument, exclusion and monotonicity"
        )
        z = frame[p["instrument"]].to_numpy().astype(int)
        if min(np.sum(z == a) for a in (0, 1)) < 3:
            raise ProjectError("IV her instrument kolunda en az3 birim ister.")
        first = difference(t.astype(float), z, spec.confidence)
        reduced = difference(y, z, spec.confidence)
        f = first["estimate"] ** 2 / first["se"] ** 2 if first["se"] else None
        result["diagnostics"]["iv"] = dict(
            first_stage=first,
            reduced_form=reduced,
            first_stage_f=f,
            validity="Exclusion/independence/monotonicity not testable from first stage; F is a heuristic, not validity proof.",
        )
        if (
            first["interval"][0] <= 0 <= first["interval"][1]
            or f is not None
            and f < 10
        ):
            blockers.append(
                "Weak/relevance instrument sorunu; weak-IV robust inference yok."
            )
        if not blockers:
            estimate = reduced["estimate"] / first["estimate"]
            effect = dict(
                estimate=estimate,
                se=None,
                interval=None,
                inference="Point only for n<100; validity remains assumed",
            )
            if len(z) >= 100:
                residual = y - estimate * t
                vari = (
                    sum(
                        float(np.var(residual[z == a], ddof=1) / np.sum(z == a))
                        for a in (0, 1)
                    )
                    / first["estimate"] ** 2
                )
                se = math.sqrt(vari)
                radius = float(stats.norm.ppf((1 + spec.confidence) / 2)) * se
                effect.update(
                    se=se,
                    interval=[estimate - radius, estimate + radius],
                    confidence=spec.confidence,
                    inference="Strong-IV asymptotic delta CI using joint outcome/treatment covariance; not weak-IV robust",
                )
            result["effect"] = effect
    if p["placebo"]:
        result["diagnostics"]["placebo"] = dict(
            association=difference(
                frame[p["placebo"]].to_numpy().astype(float), t, spec.confidence
            ),
            reason=p["placebo_reason"],
            interpretation="Pretreatment arm association only; null is not causal validation.",
        )
    if blockers:
        ident["status"] = "not_identified"
        result["effect"] = None
        result["conclusion"] = "Bu veri/varsayımla belirlenemiyor."
    else:
        result["conclusion"] = (
            "Kayıtlı varsayımlar altında koşullu etki; nedensellik kanıtı değil."
        )
        effect = result["effect"]
        for delta in p["bias_deltas"]:
            result["sensitivity"].append(
                dict(
                    additive_bias=delta,
                    estimate=effect["estimate"] - delta,
                    interval=[v - delta for v in effect["interval"]]
                    if effect["interval"]
                    else None,
                    interpretation="Hypothetical bias in outcome units, not an estimated confounding correction",
                )
            )
    control.check()
    return result


def calculate(request, spec, workspace, control, preflight=False):
    spec.validate(request["columns"], run=not preflight)
    checked(request, control)
    frame = load(request, spec, control)
    payload = analyze(frame, spec, request, control)
    common = dict(
        budget=dict(
            rows=frame.height,
            selected_columns=frame.width - 1,
            estimated_working_bytes=frame.height * 8192,
            ram_limit=control.budget.ram_bytes,
            limits="2000 iid /3000 DiD /5 covariates; bounded fold fitting and no matching replacement",
        ),
        causal=True,
        method=spec.method,
        method_label=CAUSAL_LABELS[spec.method],
        n=dict(population=frame.height, analysis_units=frame[spec.key].n_unique()),
        used_rows=frame.height,
        excluded_rows={},
        warnings=[CAUTION],
        plan=spec.causal_plan,
        causal_analysis=payload,
    )
    if preflight:
        return dict(
            common,
            spec=spec.data(),
            dataset_version=request["version_id"],
            config_revision=request.get("config_revision", 0),
        )
    result = dict(
        common,
        primary=dict(
            method=spec.method, p_value=None, statistic=None, effect=payload["effect"]
        ),
        spec=spec.data(),
        comparisons=[],
        correction=dict(
            method="none",
            family="one declared causal estimand",
            family_size=1,
            ci_adjusted=False,
        ),
        dataset_version=request["version_id"],
        config_revision=request.get("config_revision", 0),
        result_version="analysis:" + uid(),
        method_version=1,
        parameter_version=1,
        provenance=dict(
            schema="AnalysisResult/v1",
            backend="bounded causal NumPy/SciPy/statsmodels",
            numpy_version=np.__version__,
            scipy_version=scipy.__version__,
            statsmodels_version=statsmodels.__version__,
            snapshot_fingerprint=request["fingerprint"],
            snapshot_uri=request["snapshot_uri"],
            source_snapshot_id=request["source_snapshot_id"],
            help_content_version=60,
            seed=spec.seed,
        ),
    )
    checked(request, control)
    directory = Path(workspace)
    paths = dict(
        result=str(directory / "causal-result.json"),
        members=str(directory / "causal-members.parquet"),
        details=str(directory / "causal-details.parquet"),
    )
    frame.select(pl.col("__vu_row_id").alias("row_id")).write_parquet(paths["members"])
    frame.rename({"__vu_row_id": "row_id"}).write_parquet(paths["details"])
    Path(paths["result"]).write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    result["paths"] = paths
    result["fingerprints"] = {
        k: hash_artifact(Path(v), control) for k, v in paths.items()
    }
    control.disk(directory)
    control.check()
    return result


def verify_source(path, columns, result, details, members):
    """Check original data and deterministic estimator again before parent publication."""
    from veri_ufku.statistics.contracts import AnalysisSpec

    spec = AnalysisSpec.from_dict(result["spec"])
    spec.validate(columns, run=True)
    control = Control()
    frame = load(dict(path=str(path), columns=columns), spec, control)
    if not frame.rename({"__vu_row_id": "row_id"}).equals(details) or not frame.select(
        pl.col("__vu_row_id").alias("row_id")
    ).equals(members):
        raise ProjectError("Nedensel kaynak/RowId üyeliği değişmiş.")
    request = dict(
        version_id=result["dataset_version"],
        fingerprint=result["provenance"]["snapshot_fingerprint"],
    )
    if analyze(frame, spec, request, control) != result["causal_analysis"]:
        raise ProjectError("Nedensel hesap/split/pair/varsayım source bağı uyuşmuyor.")
