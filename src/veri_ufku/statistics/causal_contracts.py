"""Fixed causal templates and user-justified graph/identification contracts."""

import math

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.storage.project_model import ProjectError

CAUSAL_LABELS = {
    "causal_randomized": "44.1 · Randomize bağımsız iki kol · ATE",
    "causal_adjustment": "44.1 · Outcome adjustment · ATE",
    "causal_ipw": "44.1 · Cross-fitted IPW · ATE",
    "causal_aipw": "44.1 · Cross-fitted AIPW · ATE",
    "causal_matching": "44.2 · Caliper matching · matched ATT",
    "causal_did": "44.3 · Dengeli iki pre / bir post · DiD",
    "causal_iv": "44.4 · İkili instrument/treatment · Wald LATE",
}
CAUSAL_METHODS = tuple(CAUSAL_LABELS)
OBSERVATIONAL = CAUSAL_METHODS[1:5]
PLAN_FIELDS = {
    "dag",
    "assumptions",
    "randomization_evidence",
    "allocation",
    "alternatives",
    "folds",
    "overlap_epsilon",
    "extreme_weight",
    "caliper",
    "post_time",
    "instrument",
    "placebo",
    "placebo_reason",
    "bias_deltas",
}
ASSUMPTIONS = (
    "consistency",
    "exchangeability",
    "positivity",
    "no_interference",
    "time_order",
    "parallel_trends",
    "no_anticipation",
    "exclusion",
    "instrument_independence",
    "monotonicity",
)
ROLES = ("treatment", "outcome", "confounder", "mediator", "collider", "other")


def validate(spec, columns, run=False):
    def reject(s):
        raise ProjectError(s)

    p = spec.causal_plan
    if (
        spec.method not in CAUSAL_METHODS
        or not isinstance(p, dict)
        or set(p) != PLAN_FIELDS
    ):
        reject("Nedensel şablon ve tam declarative plan gerekli.")
    for name in ("question", "unit", "observation_unit"):
        v = getattr(spec, name)
        if not isinstance(v, str) or not v.strip() or len(v) > 1000:
            reject("Soru, outcome birimi ve analiz birimi gerekli.")
    if (
        not isinstance(spec.features, list)
        or len(spec.features) > 5
        or any(not isinstance(v, str) for v in spec.features)
    ):
        reject("En fazla5 ön-tedavi sayısal covariate seçin.")
    if any(
        not isinstance(v, str)
        for v in (spec.time_column, p["instrument"], p["placebo"])
    ):
        reject("Zaman/instrument/placebo ColumnId metin olmalı.")
    ids = {c["id"] for c in columns}
    fields = [spec.x, spec.y, spec.key, spec.time_column] + spec.features
    fields += [v for v in (p["instrument"], p["placebo"]) if v]
    if not set(fields) <= ids or len(set(fields)) != len(fields):
        reject(
            "Farklı mevcut treatment/outcome/covariate/zaman/analiz birimi sütunları seçin."
        )
    if spec.method in OBSERVATIONAL and not spec.features:
        reject("Gözlemsel şablon en az1 ön-tedavi covariate ister; randomize yol ayrı.")
    if spec.method not in OBSERVATIONAL and spec.features:
        reject(
            "Bu randomize/DiD/IV şablonunda covariate adjustment yok; sessizce yok sayılmaz."
        )
    if bool(p["instrument"]) != (spec.method == "causal_iv"):
        reject("Instrument yalnız ikili IV şablonunda gereklidir.")
    if (
        type(p["folds"]) is not int
        or not 2 <= p["folds"] <= 5
        or type(spec.seed) is not int
        or not 0 <= spec.seed < 2**32
    ):
        reject("Fold2–5 ve seed0–2³²−1 olmalı.")
    for name, lo, hi in (
        ("allocation", 0.1, 0.9),
        ("overlap_epsilon", 0.01, 0.2),
        ("extreme_weight", 5, 100),
        ("caliper", 0.001, 0.5),
    ):
        v = p[name]
        if type(v) not in (int, float) or not math.isfinite(v) or not lo <= v <= hi:
            reject("Allocation/overlap/extreme-weight/caliper geçersiz.")
    for name in (
        "alternatives",
        "randomization_evidence",
        "placebo_reason",
        "post_time",
    ):
        if not isinstance(p[name], str) or len(p[name]) > 2000:
            reject("Gerekçe/kanıt/zaman metni geçersiz.")
    if not p["alternatives"].strip():
        reject("Alternatif açıklamaları kaydedin.")
    if p["placebo"] and not p["placebo_reason"].strip():
        reject(
            "Placebo ölçümünün neden tedavi öncesi ve etkilenemez olduğunu açıklayın."
        )
    if spec.method == "causal_randomized" and not p["randomization_evidence"].strip():
        reject(
            "Gerçek randomizasyon plan/kanıt referansı gerekli; gözlemsel veri randomize sayılmaz."
        )
    if spec.method == "causal_did" and not p["post_time"].strip():
        reject("DiD için sayısal post dönemini açık yazın.")
    if (
        not isinstance(p["bias_deltas"], list)
        or not 1 <= len(p["bias_deltas"]) <= 5
        or any(
            type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 1e6
            for x in p["bias_deltas"]
        )
    ):
        reject("1–5 sonlu additive-bias sensitivity senaryosu seçin.")
    a = p["assumptions"]
    if (
        not isinstance(a, dict)
        or set(a) != set(ASSUMPTIONS)
        or any(not isinstance(v, str) or len(v) > 2000 for v in a.values())
    ):
        reject("Varsayım gerekçeleri metin olarak kaydolmalı.")
    # Blank explanations are allowed to yield a durable non-identification result.
    if type(spec.confidence) not in (int, float) or not 0.8 <= spec.confidence <= 0.99:
        reject("CI düzeyi0.8–0.99 olmalı.")
    if spec.scope != "full" or ViewSpec.from_dict(spec.view).filters:
        reject(
            "Bu şablon tam seçili veri sürümü ister; selection/filter estimand sessiz değişmez."
        )
    if (
        spec.weight_type != "none"
        or any(
            (
                spec.weight,
                spec.strata,
                spec.psu,
                spec.group,
                spec.cluster,
                spec.offset,
                spec.exposure,
                spec.interactions,
                spec.random_slopes,
                spec.within,
                spec.experiment_plan,
                spec.bayes_plan,
            )
        )
        or spec.precision != "reject"
        or spec.missing_policy != "reject"
    ):
        reject("Weight/başka model/tasarım/missing kombinasyonu desteklenmez.")
    if (
        any(
            type(getattr(spec, n)) is not bool
            for n in ("independent", "measurement_confirmed", "assumptions_confirmed")
        )
        or not spec.independent
        or not spec.measurement_confirmed
        or run
        and not spec.assumptions_confirmed
    ):
        reject(
            "Analiz birimi, zaman/ölçüm ve önkontrol onayı gerekli; DiD birimleri arasında bağımsızlık."
        )
    validate_dag(p["dag"], spec, ids)


def validate_dag(dag, spec, ids):
    if (
        not isinstance(dag, dict)
        or set(dag) != {"nodes", "edges"}
        or not isinstance(dag["nodes"], list)
        or not 2 <= len(dag["nodes"]) <= 12
        or not isinstance(dag["edges"], list)
        or len(dag["edges"]) > 30
    ):
        raise ProjectError("DAG2–12node/30edge sınırı veya şeması geçersiz.")
    nodes = dag["nodes"]
    names = []
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {
            "id",
            "role",
            "reason",
            "x",
            "y",
        }:
            raise ProjectError("DAG node alanları geçersiz.")
        cid = node["id"]
        if (
            not isinstance(cid, str)
            or len(cid) > 120
            or cid not in ids
            and not cid.startswith("latent:")
            or node["role"] not in ROLES
            or not isinstance(node["reason"], str)
            or not node["reason"].strip()
            or len(node["reason"]) > 2000
        ):
            raise ProjectError(
                "DAG rolü, mevcut/latent node ve kullanıcı gerekçesi gerekli."
            )
        if any(
            type(node[k]) not in (int, float)
            or not math.isfinite(node[k])
            or not 0 <= node[k] <= 1
            for k in ("x", "y")
        ):
            raise ProjectError("DAG konumu0–1 aralığında olmalı.")
        names.append(cid)
    if len(set(names)) != len(names):
        raise ProjectError("DAG node kimliği yineleniyor.")
    byid = {n["id"]: n for n in nodes}
    if (
        spec.y not in byid
        or spec.x not in byid
        or byid[spec.y]["role"] != "treatment"
        or byid[spec.x]["role"] != "outcome"
        or any(
            n["role"] == "treatment"
            and n["id"] != spec.y
            or n["role"] == "outcome"
            and n["id"] != spec.x
            for n in nodes
        )
    ):
        raise ProjectError(
            "DAG treatment/outcome rolleri seçili kolonlarla aynı olmalı."
        )
    edges = set()
    for edge in dag["edges"]:
        if (
            not isinstance(edge, dict)
            or set(edge) != {"from", "to", "reason"}
            or not isinstance(edge["from"], str)
            or not isinstance(edge["to"], str)
            or edge["from"] not in byid
            or edge["to"] not in byid
            or edge["from"] == edge["to"]
            or not isinstance(edge["reason"], str)
            or not edge["reason"].strip()
            or len(edge["reason"]) > 2000
        ):
            raise ProjectError("DAG yönlü edge ve gerekçesi geçersiz.")
        pair = (edge["from"], edge["to"])
        if pair in edges:
            raise ProjectError("DAG edge yineleniyor.")
        edges.add(pair)
    pending = set(names)
    while pending:
        roots = {
            n for n in pending if not any(b == n and a in pending for a, b in edges)
        }
        if not roots:
            raise ProjectError("DAG cycle içeriyor; nedensel DAG acyclic olmalı.")
        pending -= roots
