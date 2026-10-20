"""Bounded nested tuning. Outer evaluation and final test never direct trial choice."""

import copy
import math
import os
import time
import warnings
from dataclasses import replace
from datetime import UTC, datetime

import numpy as np
import polars as pl
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
)

from veri_ufku.analytics.dataset import checked
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.baseline import numeric
from veri_ufku.modeling.contracts import PreparationSpec
from veri_ufku.modeling.families import FamilyClassifier, FamilyRegressor
from veri_ufku.modeling.family_contracts import FamilyOptions, validate_family
from veri_ufku.modeling.preparation import calculate as prepare
from veri_ufku.modeling.search_contracts import SearchSpec, environment
from veri_ufku.modeling.validation import (
    ValidationSpec,
    development_folds,
    digest,
    split_plan,
)
from veri_ufku.storage.project_model import ProjectError


class SearchBudget(ProjectError):
    pass


def context(request, protocol, search, work, control):
    checked(request, control)
    p = request["preparation"]
    fresh = prepare(request, p["spec"], work, control)
    if (
        fresh["blockers"]
        or fresh["spec"] != p["spec"]
        or {k: v for k, v in fresh["plan"].items() if k != "version_id"}
        != {k: v for k, v in p["plan"].items() if k != "version_id"}
    ):
        raise ProjectError("Arama hazırlık tarifi güncel immutable kaynakla uyuşmuyor.")
    spec = PreparationSpec.from_dict(p["spec"])
    method, _, _ = protocol.resolved(p)
    if (
        not 2 <= protocol.folds <= 4
        or request["row_count"] > 1000
        or len(spec.features) > 32
    ):
        raise ProjectError(
            "Nested search en fazla1000kayit/32feature/2–4outerfold; açık kapsam daraltın."
        )
    pool = search.candidates(spec.purpose)
    for candidate in pool:
        validate_family(
            candidate["method"],
            spec.purpose,
            FamilyOptions.from_dict(candidate["options"]),
            spec.data(),
            protocol,
        )
    frame = pl.read_parquet(request["path"])
    names = {c["id"]: c["name"] for c in request["columns"]}
    target = names[spec.target]
    valid = frame[target].is_not_null()
    if frame[target].dtype.is_float():
        valid &= frame[target].is_finite()
    excluded = frame.filter(~valid)["__vu_row_id"].to_list()
    frame = frame.filter(valid)
    y = (
        np.asarray([str(v) for v in frame[target]])
        if spec.purpose == "classification"
        else numeric(frame[target].to_list(), spec).ravel()
    )
    groups = (
        np.asarray(frame[names[spec.group]].to_list(), dtype=object)
        if spec.group
        else None
    )
    if groups is not None and any(
        g is None or isinstance(g, float) and not math.isfinite(g) for g in groups
    ):
        raise ProjectError("Arama grup anahtarı eksik/sonlu değil.")
    times = None
    if spec.time:
        col = frame[names[spec.time]]
        if col.dtype != pl.Date and not isinstance(col.dtype, pl.Datetime):
            raise ProjectError("Arama zaman anahtarı Date/Datetime olmalı.")
        times = np.asarray(
            [
                float("nan")
                if v is None
                else v.timestamp()
                if hasattr(v, "timestamp")
                else (v.toordinal() - 719163) * 86400
                for v in col.to_list()
            ]
        )
    plan, parts = split_plan(
        frame["__vu_row_id"].to_list(),
        y,
        groups,
        times,
        protocol,
        method,
        spec.purpose == "classification",
        request["version_id"],
        request["fingerprint"],
        allow_missing_test_class=spec.purpose == "classification",
    )
    train, val, dev, test, outer = parts
    scopes = []
    inner_spec = replace(protocol, folds=search.inner_folds)
    for i, (a, b) in enumerate(outer):
        ip, folds = development_folds(
            frame[a.tolist()]["__vu_row_id"].to_list(),
            y[a],
            groups[a] if groups is not None else None,
            times[a] if times is not None else None,
            inner_spec,
            method,
            spec.purpose == "classification",
        )
        scopes.append(
            dict(
                name=f"outer:{i}",
                train=a,
                evaluation=b,
                inner_plan=ip,
                folds=[(a[x], a[z]) for x, z in folds],
            )
        )
    # Full-development tuning is separate from the nested outer estimate.
    scopes.append(
        dict(
            name="development",
            train=dev,
            evaluation=None,
            inner_plan=dict(
                schema="DevelopmentFolds/v1",
                method=method,
                folds=[
                    dict(
                        train=frame[a.tolist()]["__vu_row_id"].to_list(),
                        validation=frame[b.tolist()]["__vu_row_id"].to_list(),
                    )
                    for a, b in outer
                ],
                plan_id="inner:" + digest(plan["membership"]["folds"]),
            ),
            folds=outer,
        )
    )
    factor = max(
        10
        if c["method"] == "bagging"
        else 2 * (c["options"]["inner_folds"] + 1) + 1
        if c["method"] == "stacking"
        else 2
        if c["method"] == "voting"
        else 1
        for c in pool
    )
    fits = min(search.trials, len(pool)) * (
        len(outer) * search.inner_folds + len(outer)
    ) + len(outer)
    if search.curves:
        fits += len(outer) * (2 + min(10, len(pool)))
    if search.early_stopping:
        fits *= 10
    if fits * factor > 600:
        raise ProjectError(
            f"Nested/stacking/curve üst fit maliyeti {fits * factor};600 sınırını aşıyor."
        )
    cost = dict(
        fit_upper=fits,
        native_fit_upper=fits * factor,
        concurrency=1,
        trial_limit_per_scope=min(search.trials, len(pool)),
        scope_count=len(scopes),
        ram_bytes=min(search.ram_bytes, control.budget.ram_bytes),
        wall_seconds=search.wall_seconds,
        stacking_extra_splits="every candidate inner training contains its own independent/group OOF"
        if any(c["method"] == "stacking" for c in pool)
        else "none",
        calibration="unsupported; additional calibration partition required",
    )
    scope_plans = [
        dict(
            name=s["name"],
            train_row_ids=frame[s["train"].tolist()]["__vu_row_id"].to_list(),
            outer_evaluation_row_ids=frame[s["evaluation"].tolist()][
                "__vu_row_id"
            ].to_list()
            if s["evaluation"] is not None
            else [],
            inner_plan=s["inner_plan"],
        )
        for s in scopes
    ]
    identity = dict(
        source_version=request["version_id"],
        origin_version=request["origin_version"],
        fingerprint=request["fingerprint"],
        source_snapshot_id=request["source_snapshot_id"],
        preparation=dict(spec=p["spec"], plan=p["plan"], history=p.get("history")),
        columns=request["columns"],
        semantic_metadata=request.get("semantic_metadata", {}),
        protocol=protocol.data(),
        plan=plan,
        scope_plans=scope_plans,
        search_spec=search.data(),
        environment=dict(environment(), cpu_threads=control.budget.cpu_threads),
    )
    return (
        frame,
        y,
        groups,
        times,
        spec,
        pool,
        plan,
        scopes,
        scope_plans,
        cost,
        excluded,
        "compat:" + digest(identity),
    )


def score(y, pred, purpose):
    if purpose == "classification":
        return dict(
            accuracy=float(accuracy_score(y, pred)),
            f1_macro=float(f1_score(y, pred, average="macro", zero_division=0)),
        )
    return dict(
        mae=float(mean_absolute_error(y, pred)),
        rmse=float(math.sqrt(mean_squared_error(y, pred))),
    )


def loss(value, metric):
    return -value if metric in ("accuracy", "f1_macro") else value


def feasible(metrics, constraints):
    return all(
        metrics["rmse"] <= v if k == "max_rmse" else metrics["accuracy"] >= v
        for k, v in constraints.items()
    )


def _train_model(
    frame, y, a, b, candidate, request, spec, protocol, search, groups, times, check
):
    check()
    cls = FamilyClassifier if spec.purpose == "classification" else FamilyRegressor
    options = FamilyOptions.from_dict(candidate["options"])
    if min(len(a), len(b)) < 2 or set(a) & set(b):
        raise ProjectError("Trial/curve training ve validation boş/küçük/örtüşüyor.")
    if protocol.structure in ("group", "group_time") and set(groups[a]) & set(
        groups[b]
    ):
        raise ProjectError("Trial/curve grup ayrılığı bozuldu.")
    if protocol.structure in ("time", "group_time") and max(
        times[a] + protocol.horizon_seconds
    ) >= min(times[b]):
        raise ProjectError(
            "Trial/curve geleceği veya hedef ufkunu eğitimde kullanıyor."
        )
    if protocol.entity_use == "same_future" and not set(groups[b]) <= set(groups[a]):
        raise ProjectError(
            "Learning curve bu training kapsamıyla aynı varlığın geleceğini doğrulayamıyor."
        )
    if spec.purpose == "classification" and set(y[a]) != set(y[b]):
        raise ProjectError(
            "Learning/validation training veya evaluation sınıfları eksik."
        )
    fit = a
    stopping = []

    def learner(params):
        return cls(
            candidate["method"],
            params.data(),
            spec,
            request["columns"],
            request["preparation"]["plan"],
            protocol.seed,
            min(4000000, search.ram_bytes // 64),
            next((c["name"] for c in request["columns"] if c["id"] == spec.group), ""),
            protocol.structure,
        )

    if search.early_stopping:
        inner = replace(protocol, folds=2)
        _, part = development_folds(
            frame[a.tolist()]["__vu_row_id"].to_list(),
            y[a],
            groups[a] if groups is not None else None,
            times[a] if times is not None else None,
            inner,
            protocol.resolved(request["preparation"])[0],
            spec.purpose == "classification",
        )
        x, z = part[-1]
        fit = a[x]
        stop = a[z]
        model = learner(replace(options, trees=10)).fit(frame[fit.tolist()], y[fit])
        best = None
        best_loss = math.inf
        stale = 0
        metric = search.selected_metric(spec.purpose)
        for trees in range(10, options.trees + 1, 10):
            check()
            if trees > 10:
                model.estimator_.set_params(warm_start=True, n_estimators=trees)
                values = model.preparation_.transform(frame[fit.tolist()])
                target = (
                    np.asarray([list(model.classes_).index(v) for v in y[fit]])
                    if spec.purpose == "classification"
                    else y[fit]
                )
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    model.estimator_.fit(values, target)
                if caught:
                    raise ProjectError(
                        "Early stopping native convergence/numerical warning."
                    )
            m = score(y[stop], model.predict(frame[stop.tolist()]), spec.purpose)
            stopping.append(
                dict(
                    trees=trees,
                    metrics=m,
                    validation_row_ids=frame[stop.tolist()]["__vu_row_id"].to_list(),
                )
            )
            value = loss(m[metric], metric)
            if value < best_loss:
                best_loss = value
                best = copy.deepcopy(model)
                stale = 0
            else:
                stale += 1
            if stale >= search.patience:
                break
        model = best
    else:
        model = learner(options).fit(frame[fit.tolist()], y[fit])
    check()
    pred = model.predict(frame[b.tolist()])
    metrics = score(y[b], pred, spec.purpose)
    result = dict(
        fit_row_ids=frame[fit.tolist()]["__vu_row_id"].to_list(),
        evaluation_row_ids=frame[b.tolist()]["__vu_row_id"].to_list(),
        predictions=np.asarray(pred).tolist(),
        metrics=metrics,
        early_stopping=stopping,
        fit_scope="inner training only"
        if not search.early_stopping
        else "inner training subpartition; stopping validation separate from scoring validation",
        child_fit_scopes=[c.fit_row_ids_.tolist() for c in model.children_],
        stacking_oof=model.oof_,
        selected_trees=int(model.estimator_.n_estimators)
        if search.early_stopping
        else None,
    )
    check()
    return result


def train_model(*args, **kwargs):
    try:
        return _train_model(*args, **kwargs)
    except ProjectError:
        raise
    except (ValueError, TypeError, ArithmeticError, MemoryError) as error:
        raise ProjectError(
            f"Model computation failed ({type(error).__name__}); raw values are not logged."
        ) from error


def training_subset(a, fraction, protocol, search, groups, times):
    if fraction >= 1:
        return a
    if protocol.structure == "independent":
        return np.sort(
            np.random.default_rng(search.seed).choice(
                a, max(2, int(len(a) * fraction)), replace=False
            )
        )
    if protocol.structure == "time":
        keys = sorted(set(times[a]))
        keep = keys[: max(1, int(len(keys) * fraction))]
        return a[np.isin(times[a], keep)]
    if protocol.structure == "group":
        keys = sorted(set(groups[a]), key=str)
        keep = np.random.default_rng(search.seed).choice(
            keys, max(1, int(len(keys) * fraction)), replace=False
        )
        return a[np.isin(groups[a], keep)]
    # Keep complete connected overlapping group intervals, ordered in time.
    intervals = sorted(
        (
            min(times[a[groups[a] == g]]),
            max(times[a[groups[a] == g]]) + protocol.horizon_seconds,
            str(g),
            g,
        )
        for g in set(groups[a])
    )
    units = []
    members = []
    end = None
    for start, stop, _, group in intervals:
        if end is not None and start > end:
            units.append(members)
            members = []
            end = None
        members.append(group)
        end = stop if end is None else max(end, stop)
    if members:
        units.append(members)
    keep = [g for unit in units[: max(1, int(len(units) * fraction))] for g in unit]
    return a[np.isin(groups[a], keep)]


def bayesian_index(pool, history, scope, seed):
    import optuna

    optuna.logging.set_verbosity(optuna.logging.ERROR)
    past = [
        t
        for t in history
        if t["scope"] == scope and t["status"] in ("completed", "failed", "pruned")
    ]
    choices = list(range(len(pool)))
    study = optuna.create_study(
        direction="minimize",
        sampler=optuna.samplers.TPESampler(
            seed=(seed + len(past)) % 2**32, n_startup_trials=2
        ),
    )
    distribution = optuna.distributions.CategoricalDistribution(choices)
    for t in past:
        state = (
            optuna.trial.TrialState.COMPLETE
            if t["status"] == "completed"
            else optuna.trial.TrialState.PRUNED
            if t["status"] == "pruned"
            else optuna.trial.TrialState.FAIL
        )
        study.add_trial(
            optuna.trial.create_trial(
                params={"configuration": t["candidate_index"]},
                distributions={"configuration": distribution},
                value=t.get("loss")
                if state == optuna.trial.TrialState.COMPLETE
                else None,
                state=state,
            )
        )
    used = {t["candidate_index"] for t in past}
    for _ in range(20):
        trial = study.ask()
        idx = trial.suggest_categorical("configuration", choices)
        if idx not in used:
            return idx
        study.tell(trial, state=optuna.trial.TrialState.FAIL)
    return None


def calculate(
    request,
    protocol_value,
    search_value,
    workspace,
    control=None,
    resume=None,
    checkpoint=lambda value: None,
):
    control = control or Control()
    start = time.monotonic()
    protocol = ValidationSpec.from_dict(protocol_value)
    search = SearchSpec.from_dict(search_value)
    if (
        search.ram_bytes > control.budget.ram_bytes
        or search.wall_seconds > control.budget.max_wall_seconds
    ):
        raise ProjectError(
            "Arama RAM/wall bütçesi birleşik ComputeBudget sınırını aşıyor."
        )
    (
        frame,
        y,
        groups,
        times,
        spec,
        pool,
        plan,
        scopes,
        scope_plans,
        cost,
        excluded,
        compat,
    ) = context(request, protocol, search, workspace, control)
    if resume is not None and (
        resume["compat_id"] != compat
        or resume["status"] not in ("canceled", "budget_exhausted", "failed", "running")
    ):
        raise ProjectError(
            "Resume uyumsuz: source/seed/space/protocol/preprocessing/environment değişti veya arama terminal."
        )
    data = (
        copy.deepcopy(resume)
        if resume
        else dict(
            schema="SearchRun/v1",
            search_id=request["search_id"],
            dataset_version=request["version_id"],
            origin_version=request["origin_version"],
            source_snapshot_id=request["source_snapshot_id"],
            snapshot_fingerprint=request["fingerprint"],
            preparation=request["preparation"],
            protocol=protocol.data(),
            search_spec=search.data(),
            environment=dict(environment(), cpu_threads=control.budget.cpu_threads),
            compat_id=compat,
            plan=plan,
            scope_plans=scope_plans,
            estimated_cost=cost,
            excluded_target_row_ids=excluded,
            trials=[],
            native_fit_reservations=0,
            outer_evaluations=[],
            curves=[],
            elapsed_seconds=0.0,
            created_at=datetime.now(UTC).isoformat(),
            test_usage_epochs=[],
            session_run_ids=[],
        )
    )
    data["prior_test_use_ids"] = list(request.get("prior_test_use_ids", []))
    if request.get("run_id") and request["run_id"] not in data["session_run_ids"]:
        data["session_run_ids"].append(request["run_id"])
    data["test_usage_epochs"].append(
        dict(at=datetime.now(UTC).isoformat(), ids=data["prior_test_use_ids"])
    )
    data["interpretation"] = (
        "exploratory after final test use; external project use unknown"
        if data["prior_test_use_ids"]
        else "nested estimate of bounded search procedure; no optimum guarantee; final test untouched"
    )
    data["status"] = "running"
    data["recommended"] = None
    # Interrupted attempts remain visible and are retried as new attempts, never overwritten.
    for trial in data["trials"]:
        if trial["status"] == "running":
            trial["status"] = "canceled"
            trial["reason"] = "interrupted worker; new attempt required"
    previous_elapsed = data["elapsed_seconds"]
    active = None

    def emit():
        data["elapsed_seconds"] = previous_elapsed + time.monotonic() - start
        checkpoint(copy.deepcopy(data))

    def check():
        control.check()
        from veri_ufku.jobs.manager import rss_bytes

        if rss_bytes(os.getpid()) > search.ram_bytes:
            raise SearchBudget("Search RAM budget exhausted.")
        if previous_elapsed + time.monotonic() - start >= search.wall_seconds:
            raise SearchBudget("Search wall budget exhausted.")

    metric = search.selected_metric(spec.purpose)

    def fit(a, b, candidate):
        check()
        factor = (
            10
            if candidate["method"] == "bagging"
            else 2 * (candidate["options"]["inner_folds"] + 1) + 1
            if candidate["method"] == "stacking"
            else 2
            if candidate["method"] == "voting"
            else 1
        )
        if search.early_stopping:
            factor *= candidate["options"]["trees"] // 10
        if data["native_fit_reservations"] + factor > 600:
            raise SearchBudget(
                "Cumulative native fit reservation budget exhausted; resume cannot reset it."
            )
        data["native_fit_reservations"] += factor
        emit()
        return train_model(
            frame,
            y,
            a,
            b,
            candidate,
            request,
            spec,
            protocol,
            search,
            groups,
            times,
            check,
        )

    order = (
        list(range(len(pool)))
        if search.method == "grid"
        else np.random.default_rng(search.seed).permutation(len(pool)).tolist()
    )
    order = order[: search.trials]
    try:
        emit()
        for scope in scopes:
            check()
            done = [
                t
                for t in data["trials"]
                if t["scope"] == scope["name"]
                and t["status"] in ("completed", "failed", "pruned")
            ]
            indices = [t["candidate_index"] for t in done]
            while len(indices) < min(search.trials, len(pool)):
                if len(data["trials"]) >= search.attempts:
                    raise SearchBudget(
                        "Cumulative trial attempt budget exhausted; retry is charged."
                    )
                idx = (
                    bayesian_index(pool, data["trials"], scope["name"], search.seed)
                    if search.method == "bayesian"
                    else next(i for i in order if i not in indices)
                )
                if idx is None:
                    break
                candidate = pool[idx]
                active = dict(
                    id=f"trial:{data['search_id']}:{scope['name']}:{idx}:{sum(t['scope'] == scope['name'] and t['candidate_index'] == idx for t in data['trials'])}",
                    scope=scope["name"],
                    candidate_index=idx,
                    parameters=candidate,
                    status="running",
                    folds=[],
                    prior_test_use_ids=data["prior_test_use_ids"],
                    started_at=datetime.now(UTC).isoformat(),
                )
                data["trials"].append(active)
                emit()
                t0 = time.monotonic()
                try:
                    for a, b in scope["folds"]:
                        result = fit(a, b, candidate)
                        active["folds"].append(result)
                        interim = float(
                            np.mean(
                                [
                                    loss(f["metrics"][metric], metric)
                                    for f in active["folds"]
                                ]
                            )
                        )
                        if (
                            search.prune_after_folds
                            and len(active["folds"]) >= search.prune_after_folds
                            and len(active["folds"]) < len(scope["folds"])
                            and interim > search.prune_loss_above
                        ):
                            active.update(
                                status="pruned",
                                reason="explicit inner-validation loss threshold",
                                intermediate_loss=interim,
                            )
                            break
                        emit()
                    if active["status"] == "running":
                        metrics = {
                            k: float(
                                np.mean([f["metrics"][k] for f in active["folds"]])
                            )
                            for k in active["folds"][0]["metrics"]
                        }
                        active.update(
                            status="completed",
                            metrics=metrics,
                            loss=loss(metrics[metric], metric),
                            feasible=feasible(metrics, search.constraints),
                        )
                except ProjectError as error:
                    if isinstance(error, SearchBudget):
                        raise
                    active.update(status="failed", reason=str(error)[:1000])
                active["duration_seconds"] = time.monotonic() - t0
                emit()
                indices.append(idx)
                active = None
            candidates = [
                t
                for t in data["trials"]
                if t["scope"] == scope["name"]
                and t["status"] == "completed"
                and t["feasible"]
            ]
            if not candidates:
                raise ProjectError(
                    "No feasible completed trial; pruning/fail/constraints are visible."
                )
            winner = min(candidates, key=lambda t: (t["loss"], t["candidate_index"]))
            if scope["name"] == "development":
                data["recommended"] = copy.deepcopy(winner["parameters"])
                if search.early_stopping:
                    data["recommended"]["options"]["trees"] = min(
                        f["selected_trees"] for f in winner["folds"]
                    )
            elif not any(
                e["scope"] == scope["name"] for e in data["outer_evaluations"]
            ):
                result = fit(scope["train"], scope["evaluation"], winner["parameters"])
                data["outer_evaluations"].append(
                    dict(
                        scope=scope["name"],
                        winner_trial=winner["id"],
                        selection_scope="inner CV only",
                        **result,
                    )
                )
                emit()
        if search.curves and not data["curves"]:
            selected = data["recommended"]
            scope = scopes[-1]
            # Controlled validation curve: vary exactly one active numeric/categorical parameter.
            active_params = [
                p
                for p in search.space["parameters"]
                if selected["method"]
                in p.get("when", {}).get("method", search.space["methods"])
                and spec.purpose in p.get("when", {}).get("purpose", [spec.purpose])
            ]
            variants = [("learning", fraction, selected) for fraction in (0.5, 1.0)]
            if active_params:
                param = active_params[0]
                variants += [
                    (
                        "validation",
                        v,
                        dict(
                            method=selected["method"],
                            options=dict(selected["options"], **{param["name"]: v}),
                        ),
                    )
                    for v in param["values"]
                ]
            for kind, value, candidate in variants:
                check()
                points = []
                for a, b in scope["folds"]:
                    if kind == "learning":
                        a = training_subset(a, value, protocol, search, groups, times)
                    try:
                        points.append(fit(a, b, candidate))
                    except ProjectError as error:
                        if isinstance(error, SearchBudget):
                            raise
                        points.append(dict(status="unavailable", reason=str(error)))
                valid = [p for p in points if "metrics" in p]
                data["curves"].append(
                    dict(
                        kind=kind,
                        x=value,
                        parameter=active_params[0]["name"]
                        if kind == "validation"
                        else "training_fraction",
                        fixed_parameters=candidate,
                        folds=points,
                        value=float(np.mean([p["metrics"][metric] for p in valid]))
                        if len(valid) == len(points)
                        else None,
                        metric=metric,
                        scope="development inner validation; exploratory, no final test",
                    )
                )
                emit()
        data["status"] = "completed"
    except (Canceled, SearchBudget) as error:
        if active is not None and active["status"] == "running":
            active.update(
                status="canceled",
                reason="cancel or budget interruption; retry is a new attempt",
            )
        data["status"] = (
            "canceled" if isinstance(error, Canceled) else "budget_exhausted"
        )
    except ProjectError as error:
        data["status"] = "failed"
        data["reason"] = str(error)[:1000]
        if active is not None:
            active.update(status="failed", reason=data["reason"])
    emit()
    return data
