"""As-of offline recommendation with explicit candidate protocols and immutable identities."""

import copy
import json
import math
import time
from dataclasses import asdict
from datetime import UTC, datetime

import numpy as np
import polars as pl

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.recommendation_contracts import RecommendationSpec, identity
from veri_ufku.modeling.recommendation_math import diversity, fit, metrics, recommend
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError

WARNINGS = [
    "Offline ranking score is not click probability or a guarantee of real user utility.",
    "Unobserved implicit events are not verified dislikes. Sampled and full-catalog metrics are not comparable.",
    "Historical observed catalog only: future-only and seen relevant items remain in recall/AP/NDCG denominators; unavailable counts explicit.",
    "Development holdout only; final test not scored. Prior final-test use history is preserved across runs.",
    "Numeric content must be available at event time in compatible declared units; no future metadata enrichment or automatic encoding/scaling.",
    "No network, automatic delivery, or serving deployment. Local recommendation lists require explicit export.",
]


def read_rows(request, spec, control):
    checked(request, control)
    if not 2 <= request["row_count"] <= 2000:
        raise ProjectError(
            "Öneri önkontrolü:2..2000 kayıt,32user/128item/16feature CPU sınırı."
        )
    names = {c["id"]: c["name"] for c in request["columns"]}
    roles = [spec.user, spec.item, spec.value, spec.time, *spec.features]
    if spec.task == "ranker":
        roles.append(spec.query)
    if any(c not in names for c in roles):
        raise ProjectError("Öneri ColumnId kaynak sürümünde yok.")
    f = pl.read_parquet(
        request["path"],
        columns=list(
            dict.fromkeys(
                ["__vu_row_id", "__vu_source_record_id", *[names[c] for c in roles]]
            )
        ),
        n_rows=2001,
    )
    if len(f) != request["row_count"]:
        raise ProjectError("Öneri snapshot row count uyuşmuyor.")
    rows = []
    content = {}
    explicit_ties = {}
    groups = {}
    for r in f.iter_rows(named=True):
        control.check()
        user, item = identity(r[names[spec.user]]), identity(r[names[spec.item]])
        v, t = r[names[spec.value]], r[names[spec.time]]
        features = [r[names[c]] for c in spec.features]
        if any(
            type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 1e12
            for x in [v, t, *features]
        ):
            raise ProjectError(
                "Value/time/features finite sayısal olmalı; zaman açık Unix seconds, eksik/drop yok."
            )
        if spec.task == "ranker":
            if not 0 <= v <= 100:
                raise ProjectError(
                    "LTR relevance0..100; sıradan sınıf hedefi değildir."
                )
        elif (
            spec.feedback == "implicit"
            and not 0 < v <= 1e6
            or spec.feedback == "explicit"
            and not spec.rating_min <= v <= spec.rating_max
        ):
            raise ProjectError(
                "Implicit pozitif event strength veya explicit rating aralığı geçersiz."
            )
        if spec.task != "ranker":
            if item in content and content[item] != features:
                raise ProjectError(
                    "Item content zamanla değişiyor; as-of item metadata sözleşmesi gerekli, sessiz son-değer yok."
                )
            content[item] = features
        query = identity(r[names[spec.query]]) if spec.task == "ranker" else ""
        if query:
            if query in groups and groups[query] != (t, user):
                raise ProjectError(
                    "LTR query tek kullanıcı ve tek prediction timestamp içermeli; boundary group bölünmez."
                )
            groups[query] = (t, user)
        key = (user, item, t)
        if (
            spec.feedback == "explicit"
            and key in explicit_ties
            and explicit_ties[key] != v
        ):
            raise ProjectError(
                "Aynı anda çelişen explicit rating; kullanıcı kaynakta çözmeli."
            )
        explicit_ties[key] = v
        rows.append(
            dict(
                row_id=r["__vu_row_id"],
                source_record_id=r["__vu_source_record_id"],
                user=user,
                item=item,
                value=v,
                time=t,
                features=features,
                query=query,
            )
        )
    if (
        len({r["row_id"] for r in rows}) != len(rows)
        or len({r["user"] for r in rows}) > 32
        or len({r["item"] for r in rows}) > 128
    ):
        raise ProjectError("RowId unique;32user/128item sınırı.")
    if spec.task == "ranker":
        pairs = [(r["query"], r["item"]) for r in rows]
        if len(pairs) != len(set(pairs)):
            raise ProjectError("LTR query içinde item tekrar edemez.")
    return rows


def contexts(rows, spec):
    if spec.task == "ranker":
        queries = []
        for q in sorted({r["query"] for r in rows if r["time"] >= spec.cutoff}):
            held = [r for r in rows if r["query"] == q]
            queries.append(
                dict(user=held[0]["user"], time=held[0]["time"], query=q, held=held)
            )
    elif spec.split == "temporal":
        queries = [
            dict(
                user=u,
                time=spec.cutoff,
                query=u,
                held=[r for r in rows if r["user"] == u and r["time"] >= spec.cutoff],
            )
            for u in sorted({r["user"] for r in rows if r["time"] >= spec.cutoff})
        ]
    else:
        queries = []
        for u in sorted({r["user"] for r in rows}):
            when = max(r["time"] for r in rows if r["user"] == u)
            queries.append(
                dict(
                    user=u,
                    time=when,
                    query=u,
                    held=[r for r in rows if r["user"] == u and r["time"] == when],
                )
            )
    protected = {r["row_id"] for q in queries for r in q["held"]}
    if not 1 <= len(queries) <= 64:
        raise ProjectError(
            "1..64 evaluation query gerekli; temporal cutoff'u kontrol edin."
        )
    for q in queries:
        q["train"] = [
            r for r in rows if r["time"] < q["time"] and r["row_id"] not in protected
        ]
        if not q["train"]:
            raise ProjectError(
                "Query öncesinde bağımsız tarihsel training yok; cutoff/leave-last-out uygulanamıyor."
            )
    return queries


def plan_for(rows, queries):
    train = sorted({r["row_id"] for q in queries for r in q["train"]})
    held = sorted({r["row_id"] for q in queries for r in q["held"]})
    return dict(
        split_id="recommendation-asof:"
        + digest(
            [
                dict(
                    time=q["time"],
                    query=q["query"],
                    train=[r["row_id"] for r in q["train"]],
                    validation=[r["row_id"] for r in q["held"]],
                )
                for q in queries
            ]
        ),
        membership=dict(
            train=train,
            validation=held,
            test=[],
            excluded=sorted({r["row_id"] for r in rows} - set(train) - set(held)),
        ),
        scope="strict global historical prefix per query; all heldout rows excluded from every fit; no final test scoring",
    )


def validate(data):
    RecommendationSpec.from_dict(data["recommendation_spec"])
    if (
        data.get("schema") != "RecommendationRun/v1"
        or data.get("status")
        not in ("running", "completed", "canceled", "failed", "budget_exhausted")
        or data["epoch"] != 0
        or data["curves"]
    ):
        raise ProjectError("Recommendation kapalı run/status şeması geçersiz.")
    if "details_uri" in data:
        if (
            not data.get("split_id")
            or not data.get("lineage_hash")
            or not isinstance(data.get("fit_row_count"), int)
        ):
            raise ProjectError("Recommendation artifact özeti/lineage hash eksik.")
        return
    rows = data["rows"]
    by_id = {r["row_id"]: r for r in rows}
    plan = data["plan"]["membership"]
    sides = [set(plan[k]) for k in ("train", "validation", "test", "excluded")]
    if (
        len(by_id) != len(rows)
        or set.union(*sides) != set(by_id)
        or sum(map(len, sides)) != len(by_id)
        or sides[2]
    ):
        raise ProjectError("Recommendation split/RowId lineage uyuşmuyor.")
    for q in data["queries"]:
        if (
            any(
                r not in sides[0] or by_id[r]["time"] >= q["time"]
                for r in q["fit_row_ids"]
            )
            or set(q["held_row_ids"]) - sides[1]
        ):
            raise ProjectError(
                "Recommendation future/protected evaluation fit sızıntısı."
            )
        if len(set(q.get("candidate_ids", []))) != len(q.get("candidate_ids", [])):
            raise ProjectError("Candidate universe tekrarlı.")
    if len(json.dumps(data, allow_nan=False).encode()) > 16 * 1024**2:
        raise ProjectError("Recommendation safe JSON16MiB sınırı.")


def calculate(request, parameters, work, control=None, checkpoint=lambda value: None):
    control = control or Control()
    start = time.monotonic()
    spec = RecommendationSpec.from_dict(parameters)
    rows = read_rows(request, spec, control)
    qq = contexts(rows, spec)
    plan = plan_for(rows, qq)
    now = datetime.now(UTC).isoformat()
    compat = digest(dict(spec=spec.data(), source=request["fingerprint"], plan=plan))
    data = dict(
        schema="RecommendationRun/v1",
        run_id=request["run_id"],
        training_id=request["run_id"],
        dataset_version=request["version_id"],
        origin_version=request["origin_version"],
        source_snapshot_id=request["source_snapshot_id"],
        snapshot_fingerprint=request["fingerprint"],
        seed=spec.seed,
        spec={},
        recommendation_spec=spec.data(),
        protocol=dict(
            structure="time",
            split=spec.split,
            cutoff=spec.cutoff,
            candidate_protocol=spec.candidates,
        ),
        plan=plan,
        epoch=0,
        curves=[],
        elapsed_seconds=0,
        created_at=now,
        data_access_at=now,
        prior_test_use_ids=request.get("prior_test_use_ids", []),
        rows=rows,
        queries=[],
        metrics={},
        model_weights=None,
        runtime=None,
        mode="offline_development_ranking",
        tensor_schema=dict(
            fit_row_ids=plan["membership"]["train"],
            columns=[spec.user, spec.item, spec.value, spec.time, *spec.features],
            time_unit="Unix seconds",
            shape="bounded user/item observations; IDs preserve original scalar types",
        ),
        compat_id=compat,
        warnings=WARNINGS.copy(),
        experiment_capture=request.get("experiment_capture", {}),
        environment=dict(device="cpu", numpy=np.__version__, polars=pl.__version__),
    )
    data["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + compat,
            dataset_versions=(request["version_id"],),
            config_revision=request.get("config_revision", 0),
            capability_id="model.recommendation." + spec.task,
            parameters_hash=digest(spec.data()),
            environment=(("device", "cpu"),),
            created_at=now,
            scope=plan["scope"],
            seed=spec.seed,
            source_snapshot_ids=(request["source_snapshot_id"],),
            row_lineage_ref=plan["split_id"],
        )
    )

    def emit(status):
        data.update(status=status, elapsed_seconds=time.monotonic() - start)
        validate(data)
        checkpoint(copy.deepcopy(data))

    emit("running")
    try:
        for qi, q in enumerate(sorted(qq, key=lambda v: (v["time"], v["query"]))):
            control.check()
            model = fit(q["train"], spec, control)
            relevant = sorted(
                {
                    r["item"]
                    for r in q["held"]
                    if (
                        r["value"] > 0
                        if spec.task == "ranker" or spec.feedback == "implicit"
                        else r["value"] >= spec.relevant_rating
                    )
                }
            )
            universe = (
                sorted({r["item"] for r in q["held"]})
                if spec.task == "ranker"
                else model["items"].copy()
            )
            seen = (
                set(model["seen"].get(q["user"], ()))
                if spec.seen_filter and spec.task != "ranker"
                else set()
            )
            eligible = sorted(set(universe) - seen)
            candidates = eligible.copy()
            if spec.candidates == "sampled":
                positives = set(relevant) & set(eligible)
                negative_pool = sorted(
                    set(eligible)
                    - set(relevant)
                    - set(model["seen"].get(q["user"], ()))
                )
                rng = np.random.default_rng(np.random.SeedSequence([spec.seed, qi]))
                sampled = rng.choice(
                    negative_pool,
                    min(spec.negatives, len(negative_pool)),
                    replace=False,
                ).tolist()
                candidates = sorted(positives | set(sampled))
            feats = (
                {r["item"]: r["features"] for r in q["held"]}
                if spec.task == "ranker"
                else None
            )
            ranked = recommend(model, q["user"], candidates, spec.k, False, feats)
            ids = [r["item"] for r in ranked]
            baseline = dict(model, kind="popularity")
            baseline_ids = [
                r["item"]
                for r in recommend(baseline, q["user"], candidates, spec.k, False)
            ]
            lineage = {
                i: [
                    dict(row_id=r["row_id"], source_record_id=r["source_record_id"])
                    for r in q["train"]
                    if r["item"] == i
                ]
                for i in ids
            }
            for r in ranked:
                r["source_records"] = lineage.get(r["item"], [])
                if spec.task == "ranker":
                    r["source_records"] = [
                        dict(row_id=t["row_id"], source_record_id=t["source_record_id"])
                        for t in q["held"]
                        if t["item"] == r["item"]
                    ]
            data["queries"].append(
                dict(
                    query=q["query"],
                    user=q["user"],
                    time=q["time"],
                    fit_row_ids=model["fit_row_ids"],
                    held_row_ids=[r["row_id"] for r in q["held"]],
                    historical_catalog_ids=model["items"],
                    universe_ids=universe,
                    candidate_ids=candidates,
                    candidate_hash=digest(candidates),
                    candidate_protocol=spec.candidates,
                    negative_sampling="uniform without replacement from unobserved as-of candidates; held relevant included"
                    if spec.candidates == "sampled"
                    else "none",
                    relevant_ids=relevant,
                    unseen_relevant_ids=sorted(set(relevant) - set(universe)),
                    seen_relevant_ids=sorted(set(relevant) & seen),
                    unknown_user=q["user"] not in model["users"],
                    recommendations=ranked,
                    metrics=metrics(ids, relevant, spec.k),
                    baseline=metrics(baseline_ids, relevant, spec.k),
                    diversity=diversity(ids, model["vectors"]),
                )
            )
            data["model_weights"] = dict(
                model=model,
                as_of=q["time"],
                source_records=[
                    dict(
                        row_id=r["row_id"],
                        source_record_id=r["source_record_id"],
                        item=r["item"],
                    )
                    for r in q["train"]
                ],
            )
        results = data["queries"]
        aggregate = {
            m: float(
                np.mean(
                    [r["metrics"][m] for r in results if r["metrics"][m] is not None]
                )
            )
            if any(r["metrics"][m] is not None for r in results)
            else None
            for m in ("precision", "recall", "ndcg", "ap")
        }
        catalogs = set.union(*(set(q["universe_ids"]) for q in results))
        recommended = {r["item"] for q in results for r in q["recommendations"]}
        data["metrics"] = dict(
            **aggregate,
            n_queries=len(results),
            n_relevant_queries=sum(bool(q["relevant_ids"]) for q in results),
            k=spec.k,
            candidate_protocol=spec.candidates,
            catalog_coverage=len(recommended) / len(catalogs) if catalogs else None,
            diversity=float(
                np.mean([q["diversity"] for q in results if q["diversity"] is not None])
            )
            if any(q["diversity"] is not None for q in results)
            else None,
            cold_user_queries=sum(q["unknown_user"] for q in results),
            cold_item_relevant=sum(len(q["unseen_relevant_ids"]) for q in results),
            seen_relevant=sum(len(q["seen_relevant_ids"]) for q in results),
            aggregation="macro query mean; precision denominator K incl missing slots; AP denominator min(K,total relevant); binary NDCG; empty relevance excluded from recall/AP/NDCG",
            comparability_key=digest(
                dict(
                    split=plan,
                    candidate_protocol=spec.candidates,
                    candidates=[q["candidate_hash"] for q in results],
                    k=spec.k,
                    feedback=spec.feedback,
                    relevance=spec.relevant_rating,
                    seen=spec.seen_filter,
                )
            ),
        )
        emit("completed")
        return data
    except Canceled:
        data["model_weights"] = None
        emit("canceled")
        return data


def predict(model, request, control=None):
    control = control or Control()
    validate(model)
    if model["status"] != "completed" or not model.get("model_weights"):
        raise ProjectError("Completed recommendation model gerekli.")
    payload = request["recommendation_request"]
    if set(payload) - {"user", "items", "features"} or "user" not in payload:
        raise ProjectError("Öneri isteği user, isteğe bağlı items/features şemasıdır.")
    weights = model["model_weights"]
    saved = weights["model"]
    spec = RecommendationSpec.from_dict(model["recommendation_spec"])
    user = identity(payload["user"])
    items = (
        [identity(v) for v in payload["items"]]
        if "items" in payload
        else saved["items"]
    )
    ff = payload.get("features", [])
    if not isinstance(ff, list) or len(ff) > 128:
        raise ProjectError("LTR candidate features en fazla128 satır.")
    feats = {}
    for row in ff:
        v = row["values"]
        if len(v) != len(spec.features) or any(
            type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 1e12
            for x in v
        ):
            raise ProjectError("Yeni LTR feature şeması geçersiz.")
        feats[identity(row["item"])] = v
    control.check()
    out = recommend(
        saved,
        user,
        items,
        spec.k,
        spec.seen_filter if spec.task != "ranker" else False,
        feats,
    )
    for r in out:
        r["source_records"] = [
            v for v in weights["source_records"] if v["item"] == r["item"]
        ]
    return dict(
        schema="RecommendationList/v1",
        model_training_id=model["training_id"],
        dataset_version=model["dataset_version"],
        source_snapshot_id=model["source_snapshot_id"],
        as_of=weights["as_of"],
        user=user,
        candidate_ids=items,
        candidate_protocol="explicit requested list"
        if "items" in payload
        else "saved historical catalog",
        seen_filter=spec.seen_filter,
        recommendations=out,
        warnings=WARNINGS.copy(),
        fit=False,
    )
