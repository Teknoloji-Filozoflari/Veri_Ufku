"""Small CPU references: cosine content, observed-rating ALS, confidence implicit ALS."""

import math

import numpy as np

from veri_ufku.storage.project_model import ProjectError


def metrics(ranked, relevant, k):
    if len(set(ranked)) != len(ranked) or len(ranked) > k:
        raise ProjectError("Ranking tekrarlı veya K sınırını aşıyor.")
    relevant = set(relevant)
    hits = [int(i in relevant) for i in ranked]
    count = sum(hits)
    ideal = sum(1 / math.log2(j + 2) for j in range(min(k, len(relevant))))
    return dict(
        precision=count / k,
        recall=count / len(relevant) if relevant else None,
        ndcg=sum(h / math.log2(j + 2) for j, h in enumerate(hits)) / ideal
        if ideal
        else None,
        ap=sum(h * sum(hits[: j + 1]) / (j + 1) for j, h in enumerate(hits))
        / min(k, len(relevant))
        if relevant
        else None,
    )


def als_update(other, observations, implicit, regularization, alpha):
    """Unobserved implicit p=0,c=1; explicit missing entries excluded entirely."""
    p = (observations > 0).astype(float) if implicit else observations
    weights = (
        1 + alpha * observations
        if implicit
        else np.isfinite(observations).astype(float)
    )
    p = np.nan_to_num(p)
    return np.linalg.solve(
        other.T @ (weights[:, None] * other) + regularization * np.eye(other.shape[1]),
        other.T @ (weights * p),
    )


def fit(rows, spec, control):
    users = sorted({r["user"] for r in rows})
    items = sorted({r["item"] for r in rows})
    if not users or not items:
        raise ProjectError("Zaman sınırı öncesinde training verisi yok.")
    ui, ii = {u: j for j, u in enumerate(users)}, {v: j for j, v in enumerate(items)}
    implicit = spec.feedback == "implicit"
    matrix = (
        np.zeros((len(users), len(items)))
        if implicit
        else np.full((len(users), len(items)), np.nan)
    )
    # Explicit duplicate ratings: latest *historical* record per pair. Tied conflicts rejected upstream.
    for r in sorted(rows, key=lambda r: (r["time"], r["row_id"])):
        if implicit:
            matrix[ui[r["user"]], ii[r["item"]]] += r["value"]
        else:
            matrix[ui[r["user"]], ii[r["item"]]] = r["value"]
    positive = matrix > 0 if implicit else matrix >= spec.relevant_rating
    popularity = positive.sum(axis=0).astype(float)
    vectors = {}
    for r in rows:
        if r["features"] and spec.task != "ranker":
            vector = np.asarray(r["features"], dtype=float)
            norm = np.linalg.norm(vector)
            vectors[r["item"]] = (vector / norm if norm else vector).tolist()
    model = dict(
        users=users,
        items=items,
        popularity=popularity.tolist(),
        vectors=vectors,
        profiles={},
        seen={u: sorted({r["item"] for r in rows if r["user"] == u}) for u in users},
        kind=spec.task,
        fit_row_ids=[r["row_id"] for r in rows],
    )
    if spec.task == "content":
        for j, u in enumerate(users):
            v = [
                vectors[items[i]]
                for i in np.flatnonzero(positive[j])
                if items[i] in vectors
            ]
            profile = np.mean(v, axis=0) if v else np.zeros(len(spec.features))
            norm = np.linalg.norm(profile)
            model["profiles"][u] = (profile / norm if norm else profile).tolist()
    if spec.task == "factorization":
        rng = np.random.default_rng(spec.seed)
        a = rng.normal(0, 0.1, (len(users), spec.factors))
        b = rng.normal(0, 0.1, (len(items), spec.factors))
        losses = []
        for _ in range(spec.epochs):
            control.check()
            for j in range(len(users)):
                control.check()
                a[j] = als_update(
                    b, matrix[j], implicit, spec.regularization, spec.alpha
                )
            for j in range(len(items)):
                b[j] = als_update(
                    a, matrix[:, j], implicit, spec.regularization, spec.alpha
                )
            estimate = a @ b.T
            weights = 1 + spec.alpha * matrix if implicit else np.isfinite(matrix)
            target = (matrix > 0).astype(float) if implicit else np.nan_to_num(matrix)
            loss = float(
                np.sum(weights * (target - estimate) ** 2)
                + spec.regularization * (np.sum(a * a) + np.sum(b * b))
            )
            if not math.isfinite(loss):
                raise ProjectError(
                    "Factorization nonfinite; güvenilir sonuç üretilmedi."
                )
            losses.append(loss)
        model.update(
            user_factors=a.tolist(),
            item_factors=b.tolist(),
            objective=losses,
            objective_type="confidence weighted implicit ALS"
            if implicit
            else "observed explicit squared error ALS",
        )
    if spec.task == "ranker":
        # Pairwise logistic learning, all pairs remain inside historical query groups.
        pairs = []
        for group in sorted({r["query"] for r in rows}):
            rr = [r for r in rows if r["query"] == group]
            for i, left in enumerate(rr):
                control.check()
                for right in rr[i + 1 :]:
                    if left["value"] != right["value"]:
                        sign = 1 if left["value"] > right["value"] else -1
                        pairs.append(
                            sign * (np.array(left["features"]) - right["features"])
                        )
                        if len(pairs) > 10000:
                            raise ProjectError("LTR10000pair maliyet sınırı.")
        if not pairs:
            raise ProjectError("LTR historical query içinde farklı relevance pair yok.")
        delta = np.asarray(pairs)
        scale = np.maximum(np.sqrt(np.mean(delta**2, axis=0)), 1e-12)
        delta /= scale
        coef = np.zeros(delta.shape[1])
        for _ in range(spec.epochs):
            control.check()
            prob = 1 / (1 + np.exp(np.clip(delta @ coef, -40, 40)))
            coef += 0.1 * (delta.T @ prob / len(delta) - spec.regularization * coef)
        model.update(
            coef=(coef / scale).tolist(),
            pair_count=len(pairs),
            query_ids=sorted({r["query"] for r in rows}),
        )
    return model


def recommend(model, user, candidates, k, seen_filter=True, features=None):
    if len(candidates) != len(set(candidates)) or len(candidates) > 128:
        raise ProjectError("Aday kimlikler unique ve en fazla128 olmalı.")
    features = features or {}
    items = {item: i for i, item in enumerate(model["items"])}
    users = {u: i for i, u in enumerate(model["users"])}
    seen = set(model["seen"].get(user, ())) if seen_filter else set()
    ranked = []
    for item in candidates:
        if item in seen:
            continue
        index = items.get(item)
        score = model["popularity"][index] if index is not None else 0.0
        reason = "popularity" if index is not None else "unknown_item_zero_popularity"
        if model["kind"] == "ranker":
            if item not in features:
                raise ProjectError(
                    "LTR query candidate feature eksik; sessiz fallback yok."
                )
            score = float(np.dot(model["coef"], features[item]))
            reason = "pairwise_query_score"
        elif user not in users:
            reason = (
                "unknown_user_popularity"
                if index is not None
                else "unknown_user_item_zero_popularity"
            )
        elif model["kind"] == "factorization" and index is not None:
            score = float(
                np.dot(model["user_factors"][users[user]], model["item_factors"][index])
            )
            reason = "latent_dot_product"
        elif model["kind"] == "content" and index is not None:
            profile = model["profiles"][user]
            if any(profile) and any(model["vectors"].get(item, [])):
                score = float(np.dot(profile, model["vectors"][item]))
                reason = "content_cosine"
            else:
                reason = "empty_content_profile_popularity"
        ranked.append(dict(item=item, score=score, reason=reason))
    return sorted(ranked, key=lambda r: (-r["score"], r["item"]))[:k]


def diversity(ranked, vectors):
    if len(ranked) < 2 or any(
        item not in vectors or not any(vectors[item]) for item in ranked
    ):
        return None
    return float(
        np.mean(
            [
                1 - np.dot(vectors[a], vectors[b])
                for i, a in enumerate(ranked)
                for b in ranked[i + 1 :]
            ]
        )
    )
