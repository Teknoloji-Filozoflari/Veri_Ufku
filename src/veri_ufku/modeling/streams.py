"""Bounded immutable-file append simulator; JSON numeric state, no object imports."""

import copy
import json
import math
import platform
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl
import sklearn
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.stream_contracts import StreamSpec
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError


def initial():
    return dict(
        cursor=0,
        last_id=None,
        last_processing=None,
        max_event=None,
        pending=[],
        windows={},
        scaler=None,
        model=None,
        trained=0,
        scored=0,
        errors=0,
        missing=0,
        late=0,
        expired=0,
        closed_windows=0,
        generation=0,
        alarms=0,
        losses=[],
        preview=[],
        late_preview=[],
        peak_pending=0,
    )


def restore(state, seed):
    scaler = StandardScaler()
    model = SGDClassifier(
        loss="log_loss",
        learning_rate="constant",
        eta0=0.01,
        shuffle=False,
        random_state=seed,
    )
    if state["scaler"]:
        for k, v in state["scaler"].items():
            setattr(
                scaler,
                k,
                np.asarray(v) if isinstance(v, list) or k == "n_samples_seen_" else v,
            )
    if state["model"]:
        for k, v in state["model"].items():
            setattr(
                model,
                k,
                np.asarray(v) if isinstance(v, list) or k == "n_samples_seen_" else v,
            )
    return scaler, model


def numeric_state(obj, keys):
    return {k: np.asarray(getattr(obj, k)).tolist() for k in keys}


def validate(data):
    spec = StreamSpec.from_dict(data["stream_spec"])
    if (
        data.get("schema") != "StreamRun/v1"
        or data.get("status")
        not in ("running", "completed", "canceled", "failed", "budget_exhausted")
        or data["epoch"] != 0
        or data["curves"]
    ):
        raise ProjectError("StreamRun schema/status geçersiz.")
    if data.get("details_uri"):
        if not data.get("state_hash") or type(data.get("cursor")) is not int:
            raise ProjectError("Stream immutable summary eksik.")
        return
    s = data["state"]
    if (
        type(s["cursor"]) is not int
        or not 0 <= s["cursor"] <= 100000
        or len(s["pending"]) > spec.buffer
        or len(s["windows"]) > spec.buffer
        or len(s["preview"]) > 64
        or len(s["losses"]) > 32
        or len(s["late_preview"]) > 64
    ):
        raise ProjectError("Stream checkpoint sınırı geçersiz.")
    if len(json.dumps(data, allow_nan=False).encode()) > 2 * 1024**2:
        raise ProjectError("Stream JSON2MiB sınırı.")


def calculate(request, parameters, work, control=None, checkpoint=lambda value: None):
    control = control or Control()
    start = time.monotonic()
    checked(request, control)
    spec = StreamSpec.from_dict(parameters)
    if not 1 <= request["row_count"] <= 100000:
        raise ProjectError("Stream replay1–100000row önkontrolü.")
    names = {c["id"]: c["name"] for c in request["columns"]}
    if any(
        c not in names
        for c in (
            spec.event_id,
            spec.event_time,
            spec.processing_time,
            spec.feedback_time,
            spec.target,
            *spec.features,
        )
    ):
        raise ProjectError("Stream ColumnId kaynakta yok.")
    selected = list(
        dict.fromkeys(
            [
                names[c]
                for c in (
                    spec.event_id,
                    spec.event_time,
                    spec.processing_time,
                    spec.feedback_time,
                    spec.target,
                    *spec.features,
                )
            ]
            + ["__vu_row_id", "__vu_source_record_id"]
        )
    )
    source = pl.scan_parquet(request["path"]).select(selected)
    schema = source.collect_schema()
    if not schema[names[spec.event_id]].is_integer() or any(
        not (
            schema[names[c]].is_integer()
            or schema[names[c]].is_float()
            or (c in (spec.feedback_time, spec.target) and schema[names[c]] == pl.Null)
        )
        for c in (
            spec.event_time,
            spec.processing_time,
            spec.feedback_time,
            spec.target,
            *spec.features,
        )
    ):
        raise ProjectError(
            "Stream physical integer/float seconds/features gerektirir; label/feedback Null olabilir. Unselected columns okunmaz."
        )
    compat = digest(
        dict(
            source=request["fingerprint"],
            spec=spec.data(),
            sklearn=sklearn.__version__,
            engine=digest(Path(__file__).read_text()),
            numpy=np.__version__,
            python=platform.python_version(),
        )
    )
    previous = request.get("stream_resume")
    if previous:
        validate(previous)
        if previous["compat_id"] != compat or previous[
            "prior_test_use_ids"
        ] != request.get("prior_test_use_ids", []):
            raise ProjectError("Resume source/spec/environment/test-use uyuşmuyor.")
    state = copy.deepcopy(previous["state"] if previous else initial())
    scaler, model = restore(state, spec.seed)
    now = datetime.now(UTC).isoformat()
    scope = "local immutable snapshot append simulator; prequential development, no final-test access"
    data = dict(
        schema="StreamRun/v1",
        run_id=request["run_id"],
        training_id=request["run_id"],
        dataset_version=request["version_id"],
        origin_version=request["origin_version"],
        source_snapshot_id=request["source_snapshot_id"],
        snapshot_fingerprint=request["fingerprint"],
        seed=spec.seed,
        spec={},
        stream_spec=spec.data(),
        epoch=0,
        curves=[],
        elapsed_seconds=0,
        created_at=now,
        data_access_at=now,
        prior_test_use_ids=request.get("prior_test_use_ids", []),
        state=state,
        plan=dict(
            split_id="prequential:" + compat,
            membership=dict(train=[], validation=[], test=[]),
            scope=scope,
        ),
        tensor_schema={},
        model_weights=None,
        runtime=None,
        compat_id=compat,
        metrics={},
        mode="prequential",
        environment=dict(
            sklearn=sklearn.__version__,
            numpy=np.__version__,
            python=platform.python_version(),
            engine=digest(Path(__file__).read_text()),
            device="cpu",
        ),
        experiment_capture=request.get("experiment_capture", {}),
        resume_from=previous["run_id"] if previous else None,
        warnings=[
            "Local immutable file replay only; no live watcher/network broker/external side effects.",
            "Replay requires identical snapshot, recipe, order and sklearn version; device/version independent bitwise equivalence is not promised.",
            "Integer event IDs must strictly increase; resume starts at next durable cursor. Duplicate/out-of-order IDs fail, never silently retrain.",
            "Feedback beyond last processing time remains pending; missing labels never become negatives. Predictions precede scaler/model updates.",
            "Drift is a bounded two-half error-rate heuristic, not proof of distribution change. Reset only under explicit reset policy.",
        ],
    )
    data["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + compat,
            dataset_versions=tuple(
                dict.fromkeys([request["version_id"], request["origin_version"]])
            ),
            config_revision=request.get("config_revision", 0),
            capability_id="model.stream.replay",
            parameters_hash=digest(spec.data()),
            environment=(("sklearn", sklearn.__version__),),
            created_at=now,
            scope=scope,
            seed=spec.seed,
            source_snapshot_ids=(request["source_snapshot_id"],),
            row_lineage_ref="cursor:" + compat,
        )
    )

    durable = copy.deepcopy(state)

    def rollback():
        nonlocal state, scaler, model
        state = copy.deepcopy(durable)
        data["state"] = state
        scaler, model = restore(state, spec.seed)

    def emit(status):
        nonlocal durable
        state["scaler"] = (
            numeric_state(
                scaler, ("mean_", "var_", "scale_", "n_samples_seen_", "n_features_in_")
            )
            if hasattr(scaler, "mean_")
            else None
        )
        state["model"] = (
            numeric_state(
                model,
                ("coef_", "intercept_", "classes_", "t_", "n_iter_", "n_features_in_"),
            )
            if hasattr(model, "coef_")
            else None
        )
        data.update(
            status=status,
            elapsed_seconds=time.monotonic() - start,
            metrics=dict(
                scored=state["scored"],
                accuracy=1 - state["errors"] / state["scored"]
                if state["scored"]
                else None,
                trained=state["trained"],
            ),
        )
        validate(data)
        checkpoint(copy.deepcopy(data))
        durable = copy.deepcopy(state)

    def feedback(clock):
        nonlocal scaler, model
        remaining = []
        for e in sorted(state["pending"], key=lambda e: (e["due"], e["id"])):
            control.check()
            if e["due"] > clock:
                remaining.append(e)
                continue
            if e["prediction"] is not None:
                error = int(e["prediction"] != e["y"])
                state["scored"] += 1
                state["errors"] += error
                state["losses"] = (state["losses"] + [error])[-32:]
                if (
                    len(state["losses"]) == 32
                    and sum(state["losses"][16:]) / 16 - sum(state["losses"][:16]) / 16
                    > spec.drift_threshold
                ):
                    state["alarms"] += 1
                    state["losses"] = []
                    if spec.retrain == "reset":
                        scaler, model = restore(initial(), spec.seed)
                        state["generation"] += 1
            x = np.asarray([e["x"]], dtype=float)
            old_mean = scaler.mean_.copy() if hasattr(scaler, "mean_") else None
            old_scale = scaler.scale_.copy() if old_mean is not None else None
            scaler.partial_fit(x)
            if hasattr(model, "coef_"):
                # Preserve the raw-input decision function when coordinate scaling changes.
                w = model.coef_.copy() / old_scale
                model.intercept_ += np.sum(w * (scaler.mean_ - old_mean), axis=1)
                model.coef_ = w * scaler.scale_
            model.partial_fit(scaler.transform(x), [e["y"]], classes=[0, 1])
            state["trained"] += 1
        state["pending"] = remaining

    emit("running")
    try:
        while state["cursor"] < request["row_count"]:
            control.check()
            frame = source.slice(state["cursor"], spec.checkpoint_every).collect(
                engine="streaming"
            )
            if not len(frame):
                raise ProjectError("Stream snapshot cursor eksik.")
            for row in frame.iter_rows(named=True):
                control.check()
                eid = row[names[spec.event_id]]
                et, pt, ft = (
                    row[names[c]]
                    for c in (spec.event_time, spec.processing_time, spec.feedback_time)
                )
                x = [row[names[c]] for c in spec.features]
                y = row[names[spec.target]]
                if (
                    type(eid) is not int
                    or state["last_id"] is not None
                    and eid <= state["last_id"]
                ):
                    raise ProjectError(
                        "Stream event ID strictly increasing integer olmalı; duplicate/reorder reddedildi."
                    )
                if (
                    any(
                        type(v) not in (int, float)
                        or not math.isfinite(v)
                        or abs(v) > 1e12
                        for v in (et, pt, *x)
                    )
                    or state["last_processing"] is not None
                    and pt < state["last_processing"]
                ):
                    raise ProjectError(
                        "Stream finite features/time ve monotonic processing time gerektirir."
                    )
                if y is not None and (
                    type(y) not in (int, float)
                    or y not in (0, 1)
                    or type(ft) not in (int, float)
                    or not math.isfinite(ft)
                    or ft < pt
                ):
                    raise ProjectError(
                        "Feedback binary0/1 ve due>=processing time olmalı."
                    )
                if y is None and ft is not None:
                    raise ProjectError(
                        "Missing feedback için target ve feedback time null olmalı."
                    )
                # Earlier feedback is available before this event; tied feedback arrives AFTER its prediction.
                feedback(np.nextafter(float(pt), -np.inf))
                watermark = (
                    state["max_event"] - spec.lateness
                    if state["max_event"] is not None
                    else -math.inf
                )
                late = spec.clock == "event" and et < watermark
                if late and spec.late_policy == "reject":
                    raise ProjectError("Late event explicit reject policy.")
                if late:
                    state["late"] += 1
                    state["late_preview"] = (
                        state["late_preview"]
                        + [
                            dict(
                                id=eid,
                                row_id=row["__vu_row_id"],
                                source_record_id=row["__vu_source_record_id"],
                                event_time=et,
                                watermark=watermark,
                            )
                        ]
                    )[-64:]
                else:
                    prediction = (
                        int(model.predict(scaler.transform([x]))[0])
                        if hasattr(model, "coef_")
                        else None
                    )
                    if y is None:
                        state["missing"] += 1
                    else:
                        if len(state["pending"]) >= spec.buffer:
                            raise ProjectError(
                                "Pending feedback bounded buffer dolu; veri düşürülmedi."
                            )
                        state["pending"].append(
                            dict(
                                id=eid,
                                x=x,
                                y=int(y),
                                due=ft,
                                prediction=prediction,
                                row_id=row["__vu_row_id"],
                                source_record_id=row["__vu_source_record_id"],
                            )
                        )
                        state["peak_pending"] = max(
                            state["peak_pending"], len(state["pending"])
                        )
                    state["preview"] = (
                        state["preview"]
                        + [
                            dict(
                                id=eid,
                                row_id=row["__vu_row_id"],
                                source_record_id=row["__vu_source_record_id"],
                                prediction=prediction,
                                generation=state["generation"],
                                trained_before=state["trained"],
                            )
                        ]
                    )[-64:]
                state["max_event"] = (
                    max(et, state["max_event"])
                    if state["max_event"] is not None
                    else et
                )
                watermark = (
                    state["max_event"] - spec.lateness if spec.clock == "event" else pt
                )
                for k in list(state["windows"]):
                    if (int(k) + 1) * spec.window <= watermark:
                        del state["windows"][k]
                        state["closed_windows"] += 1
                if not late:
                    k = str(
                        math.floor((et if spec.clock == "event" else pt) / spec.window)
                    )
                    if (
                        k not in state["windows"]
                        and len(state["windows"]) >= spec.buffer
                    ):
                        raise ProjectError("Active window buffer dolu.")
                    state["windows"][k] = state["windows"].get(k, 0) + 1
                feedback(pt)
                state.update(
                    last_id=eid, last_processing=pt, cursor=state["cursor"] + 1
                )
            emit("running")
        emit("completed")
    except Canceled:
        rollback()
        emit("canceled")
    except ProjectError as e:
        rollback()
        data["warnings"].append(str(e))
        emit("failed")
    return data
