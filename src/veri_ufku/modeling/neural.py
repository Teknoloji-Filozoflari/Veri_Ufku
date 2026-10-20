"""Actual CPU autograd, closed architectures and data-only full-state checkpoints."""

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
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.contracts import PreparationSpec
from veri_ufku.modeling.neural_contracts import NeuralSpec
from veri_ufku.modeling.preparation import calculate as prepare
from veri_ufku.modeling.validation import ValidationSpec, digest, split_plan
from veri_ufku.storage.project_model import ProjectError

MAX_BYTES = 16 * 1024**2


def framework():
    import torch

    if str(torch.__version__) != "2.13.0+cpu":
        raise ProjectError(
            "Bu adapter doğrulanmış torch2.13.0+cpu ister; farklı framework ortamı desteklenmiyor."
        )
    return torch


def environment(threads):
    t = framework()
    return dict(
        torch=str(t.__version__),
        cuda=t.version.cuda,
        python=platform.python_version(),
        machine=platform.machine(),
        cpu_threads=threads,
        engine_sha256=digest(Path(__file__).read_text()),
        device="cpu",
        dtype="float32",
        mkldnn=False,
        deterministic_limits="Same CPU/framework/thread state only; seed is not a cross-device bitwise guarantee; GPU not validated",
    )


def pack(value):
    """Only tensor data and primitive trees. No pickle, import, torch.load or object hooks."""
    t = framework()
    if isinstance(value, t.Tensor):
        a = value.detach().cpu()
        if a.numel() > 250000 or a.dtype not in (t.float32, t.int64, t.uint8):
            raise ProjectError("Checkpoint tensor dtype/boyut sınırı.")
        if a.is_floating_point() and not t.isfinite(a).all():
            raise ProjectError("Checkpoint sonlu olmayan tensor içeriyor.")
        return dict(
            tensor=str(a.dtype).removeprefix("torch."),
            shape=list(a.shape),
            data=a.reshape(-1).tolist(),
        )
    if isinstance(value, dict):
        return dict(pairs=[[pack(k), pack(v)] for k, v in value.items()])
    if isinstance(value, (tuple, list)):
        return [pack(v) for v in value]
    if (
        value is None
        or type(value) in (str, int, bool)
        or type(value) is float
        and math.isfinite(value)
    ):
        return value
    raise ProjectError("Checkpoint arbitrary object reddedildi.")


def unpack(value, depth=0):
    t = framework()
    if depth > 20:
        raise ProjectError("Checkpoint nesting sınırı.")
    if isinstance(value, dict):
        if set(value) == {"tensor", "shape", "data"}:
            if (
                value["tensor"] not in ("float32", "int64", "uint8")
                or not isinstance(value["shape"], list)
                or len(value["shape"]) > 4
                or any(
                    type(v) is not int or not 0 <= v <= 250000 for v in value["shape"]
                )
            ):
                raise ProjectError("Checkpoint tensor schema geçersiz.")
            n = math.prod(value["shape"])
            if (
                n > 250000
                or not isinstance(value["data"], list)
                or len(value["data"]) != n
                or any(
                    type(v) not in (int, float) or not math.isfinite(v)
                    for v in value["data"]
                )
            ):
                raise ProjectError("Checkpoint tensor size/value geçersiz.")
            return t.tensor(value["data"], dtype=getattr(t, value["tensor"])).reshape(
                value["shape"]
            )
        if (
            set(value) == {"pairs"}
            and isinstance(value["pairs"], list)
            and len(value["pairs"]) < 1000
        ):
            result = {}
            for pair in value["pairs"]:
                if (
                    not isinstance(pair, list)
                    or len(pair) != 2
                    or type(pair[0]) not in (str, int)
                    or pair[0] in result
                ):
                    raise ProjectError("Checkpoint map schema geçersiz.")
                result[pair[0]] = unpack(pair[1], depth + 1)
            return result
        raise ProjectError("Checkpoint unknown object schema reddedildi.")
    if isinstance(value, list):
        if len(value) > 250000:
            raise ProjectError("Checkpoint liste sınırı.")
        return [unpack(v, depth + 1) for v in value]
    if (
        value is None
        or type(value) in (str, int, bool)
        or type(value) is float
        and math.isfinite(value)
    ):
        return value
    raise ProjectError("Checkpoint primitive schema geçersiz.")


def architecture(spec, inputs, outputs):
    t = framework()
    if spec.template == "mlp":
        return t.nn.Sequential(
            t.nn.Linear(inputs, spec.hidden),
            t.nn.ReLU(),
            t.nn.Linear(spec.hidden, outputs),
        )
    return t.nn.Sequential(
        t.nn.Conv2d(spec.image_shape[0], 4, 3, padding=1),
        t.nn.ReLU(),
        t.nn.AdaptiveAvgPool2d((2, 2)),
        t.nn.Flatten(),
        t.nn.Linear(16, outputs),
    )


def context(request, protocol, spec, work, control):
    checked(request, control)
    p = request["preparation"]
    fresh = prepare(request, p["spec"], work, control)
    if (
        fresh["blockers"]
        or fresh["spec"] != p["spec"]
        or {k: v for k, v in fresh["plan"].items() if k != "version_id"}
        != {k: v for k, v in p["plan"].items() if k != "version_id"}
    ):
        raise ProjectError("Tensor hazırlığı immutable kaynakla uyuşmuyor.")
    prep = PreparationSpec.from_dict(p["spec"])
    if (
        prep.purpose not in ("regression", "classification")
        or prep.text
        or prep.scaling not in ("auto", "standard")
        or prep.selection != "none"
        or prep.missing_indicator
        or prep.numeric_imputation not in ("median", "mean", "none")
    ):
        raise ProjectError(
            "Tensor şablonu yalnız sayısal dense özellikler; ileri selection/text/imputation bu adapterde kapalı."
        )
    if request["row_count"] > 2000 or len(prep.features) > 1024:
        raise ProjectError(
            "Tensor preflight: en fazla2000satır/1024özellik; açık kapsam daraltın."
        )
    method, strategy, _ = protocol.resolved(p)
    f = pl.read_parquet(request["path"])
    names = {c["id"]: c["name"] for c in request["columns"]}
    feature_names = [names[c] for c in prep.features]
    if any(not f[n].dtype.is_numeric() for n in feature_names):
        raise ProjectError(
            "Tensor MLP/CNN yalnız sayısal kolonlar; kategorilere doğal uzaklık atanmaz."
        )
    target = f[names[prep.target]]
    mask = target.is_not_null()
    if target.dtype.is_float():
        mask &= target.is_finite()
    excluded = f.filter(~mask)["__vu_row_id"].to_list()
    f = f.filter(mask)
    y = (
        np.asarray([str(v) for v in f[names[prep.target]]])
        if prep.purpose == "classification"
        else np.asarray(f[names[prep.target]], dtype=np.float32)
    )
    if prep.purpose == "regression" and not np.isfinite(y).all():
        raise ProjectError("Hedef sonlu olmalı.")
    groups = (
        np.asarray(f[names[prep.group]].to_list(), dtype=object) if prep.group else None
    )
    times = None
    if prep.time:
        col = f[names[prep.time]]
        if col.dtype != pl.Date and not isinstance(col.dtype, pl.Datetime):
            raise ProjectError("Tensor zaman anahtarı Date/Datetime olmalı.")
        times = np.asarray(
            [
                np.nan
                if v is None
                else v.timestamp()
                if hasattr(v, "timestamp")
                else (v.toordinal() - 719163) * 86400
                for v in col
            ]
        )
    plan, parts = split_plan(
        f["__vu_row_id"].to_list(),
        y,
        groups,
        times,
        protocol,
        method,
        prep.purpose == "classification",
        request["version_id"],
        request["fingerprint"],
    )
    a, b, _, _, _ = parts
    x = np.column_stack([np.asarray(f[n], dtype=np.float64) for n in feature_names])
    if np.isinf(x).any():
        raise ProjectError("Sonsuz özellik reddedildi.")
    if spec.template == "cnn" and math.prod(spec.image_shape) != x.shape[1]:
        raise ProjectError("CNN explicit tensor shape × kolon sayısı uyuşmuyor.")
    if prep.purpose != "classification" and spec.class_weights != "none":
        raise ProjectError("Class weights yalnız sınıflandırma eğitim loss'u içindir.")
    estimated = x.nbytes * 12 + spec.hidden * x.shape[1] * 4 * 12
    if estimated > control.budget.ram_bytes // 4:
        raise ProjectError("Tensor/gradient/optimizer preflight RAM bütçesini aşıyor.")
    return f, x, y, a, b, prep, plan, excluded, strategy, estimated


def fitted_input(x, indices, method):
    train = x[indices]
    if np.isnan(train).all(axis=0).any() or method == "none" and np.isnan(x).any():
        raise ProjectError(
            "Train tamamen eksik kolon/imputasyonsuz missing reddedildi."
        )
    center = (np.nanmean if method == "mean" else np.nanmedian)(train, axis=0)
    filled = np.where(np.isnan(train), center, train)
    mean, scale = filled.mean(axis=0), filled.std(axis=0)
    scale[scale == 0] = 1
    return dict(
        impute=center.tolist(),
        mean=mean.tolist(),
        scale=scale.tolist(),
        fit_indices=indices.tolist(),
    )


def transform(x, prep, spec):
    t = framework()
    z = (
        np.where(np.isnan(x), np.asarray(prep["impute"]), x) - np.asarray(prep["mean"])
    ) / np.asarray(prep["scale"])
    z = np.asarray(z, dtype=np.float32)
    if not np.isfinite(z).all():
        raise ProjectError("Tensor float32 taşması/geçersiz yeni veri.")
    v = t.from_numpy(z)
    return v.reshape(-1, *spec.image_shape) if spec.template == "cnn" else v


def validate_weights(model, weights):
    expected = model.state_dict()
    if set(weights) != set(expected) or any(
        not hasattr(v, "shape")
        or v.shape != expected[k].shape
        or v.dtype != expected[k].dtype
        or not framework().isfinite(v).all()
        for k, v in weights.items()
    ):
        raise ProjectError("Safe ağırlıklar kapalı mimariyle uyuşmuyor.")
    model.load_state_dict(weights, strict=True)


def calculate(
    request,
    protocol_value,
    parameters,
    work,
    control=None,
    resume=None,
    checkpoint=lambda v: None,
    pause=None,
):
    control = control or Control()
    spec = NeuralSpec.from_dict(parameters)
    protocol = ValidationSpec.from_dict(protocol_value)
    t = framework()
    t.set_num_threads(control.budget.worker_threads)
    # Small CPU templates avoid oneDNN convolution workspace inflation.
    t.backends.mkldnn.enabled = False
    t.use_deterministic_algorithms(spec.deterministic)
    t.manual_seed(spec.seed)
    started = time.monotonic()
    accessed = datetime.now(UTC).isoformat()
    f, x, y, a, b, prep, plan, excluded, strategy, estimated = context(
        request, protocol, spec, work, control
    )
    env = environment(control.budget.cpu_threads)
    labels = sorted(set(y[a])) if prep.purpose == "classification" else []
    outputs = len(labels) if labels else 1
    model = architecture(spec, x.shape[1], outputs)
    optimizer = (
        t.optim.Adam(model.parameters(), lr=spec.lr)
        if spec.optimizer == "adam"
        else t.optim.SGD(model.parameters(), lr=spec.lr, momentum=0.9)
    )
    scheduler = (
        t.optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.8)
        if spec.scheduler == "step"
        else None
    )
    identity = dict(
        spec=spec.data(),
        protocol=protocol.data(),
        plan=plan,
        source=request["fingerprint"],
        version=request["version_id"],
        preparation=request["preparation"],
        environment=env,
        prior_test_use_ids=request.get("prior_test_use_ids", []),
    )
    compat = digest(identity)
    preprocess = fitted_input(x, a, prep.numeric_imputation)
    rng = t.Generator().manual_seed(spec.seed + 1)
    baseline = (
        DummyClassifier(strategy=strategy, random_state=protocol.seed)
        if labels
        else DummyRegressor(strategy=strategy)
    ).fit(x[a], y[a])
    baseline_prediction = baseline.predict(x[b])
    baseline_metric = float(
        accuracy_score(y[b], baseline_prediction)
        if labels
        else mean_absolute_error(y[b], baseline_prediction)
    )
    if labels:
        yi = t.tensor([labels.index(v) for v in y], dtype=t.int64)
        counts = np.array([np.count_nonzero(y[a] == c) for c in labels])
        weights = (
            t.tensor(len(a) / (len(labels) * counts), dtype=t.float32)
            if spec.class_weights == "balanced"
            else None
        )
        criterion = t.nn.CrossEntropyLoss(weight=weights)
    else:
        yi = t.tensor(y, dtype=t.float32).reshape(-1, 1)
        weights = None
        criterion = t.nn.MSELoss()
    data = dict(
        schema="NeuralRun/v1",
        run_id=request["run_id"],
        training_id=request.get("training_id", request["run_id"]),
        status="running",
        dataset_version=request["version_id"],
        origin_version=request["origin_version"],
        source_snapshot_id=request["source_snapshot_id"],
        snapshot_fingerprint=request["fingerprint"],
        seed=spec.seed,
        spec=spec.data(),
        protocol=protocol.data(),
        plan=plan,
        preparation_spec=prep.data(),
        environment=env,
        compat_id=compat,
        prior_test_use_ids=request.get("prior_test_use_ids", []),
        data_access_at=accessed,
        created_at=accessed,
        elapsed_seconds=0.0,
        mode="development_holdout",
        curves=[],
        epoch=0,
        best_loss=None,
        bad_epochs=0,
        tensor_schema=dict(
            dtype="float32",
            layout="NCHW row-major" if spec.template == "cnn" else "N×features",
            shape=list(spec.image_shape) or [x.shape[1]],
            column_ids=list(prep.features),
            feature_names=[
                next(c["name"] for c in request["columns"] if c["id"] == i)
                for i in prep.features
            ],
            class_labels=labels,
            missing="training-only mean/median; none rejects",
            fit_row_ids=f[a.tolist()]["__vu_row_id"].to_list(),
            validation_row_ids=f[b.tolist()]["__vu_row_id"].to_list(),
            excluded_row_ids=excluded,
        ),
        estimated_ram_bytes=estimated,
        class_weights=weights.tolist() if weights is not None else [],
        warnings=[
            "Validation holdout guides early stopping; not independent final-test inference or CV ranking.",
            "Same seed does not guarantee identical results across devices/framework versions.",
            "GPU/mixed precision and arbitrary/pretrained .pt/.pkl imports unsupported; no automatic deserialization.",
        ],
        comparison=dict(
            metric="accuracy" if labels else "mae",
            scope="same train/validation membership; final test untouched",
            sklearn_baseline=baseline_metric,
        ),
        preprocessing=preprocess,
        runtime=None,
    )
    data["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + compat,
            dataset_versions=(request["version_id"],),
            config_revision=request.get("config_revision", 0),
            capability_id="model.neural." + spec.template,
            parameters_hash=digest(spec.data()),
            environment=tuple((k, str(v)) for k, v in env.items()),
            created_at=accessed,
            scope="training-only fit; same validation holdout; final test untouched",
            seed=spec.seed,
            seed_reason="explicit CPU framework and loader seeds",
            source_snapshot_ids=(request["source_snapshot_id"],),
            row_lineage_ref=plan["split_id"],
            column_lineage_ref=digest(list(prep.features)),
            exclusions=tuple(excluded),
        )
    )
    data["experiment_capture"] = request.get("experiment_capture", {})
    best = copy.deepcopy(model.state_dict())
    elapsed_before = 0.0
    if resume:
        if (
            resume["compat_id"] != compat
            or resume["status"] not in ("paused", "canceled", "running")
            or resume["epoch"] >= spec.epochs
        ):
            raise ProjectError(
                "Resume uyumsuz: kaynak/split/ayar/framework/thread/test geçmişi değişti veya terminal checkpoint."
            )
        data = copy.deepcopy(resume)
        data.update(run_id=request["run_id"], status="running")
        state = unpack(data["runtime"])
        if set(state) != {
            "weights",
            "best",
            "optimizer",
            "scheduler",
            "torch_rng",
            "loader_rng",
        }:
            raise ProjectError(
                "Tam resume optimizer/scheduler/RNG gerektirir; weight reload yeterli değil."
            )
        validate_weights(model, state["weights"])
        validate_weights(architecture(spec, x.shape[1], outputs), state["best"])
        best = state["best"]
        optimizer.load_state_dict(state["optimizer"])
        if scheduler:
            scheduler.load_state_dict(state["scheduler"])
        t.set_rng_state(state["torch_rng"])
        rng.set_state(state["loader_rng"])
        elapsed_before = data["elapsed_seconds"]
        if data["preprocessing"] != preprocess:
            raise ProjectError("Resume train preprocessing uyuşmuyor.")
    tensors = transform(x, preprocess, spec)

    def snapshot(status):
        data["status"] = status
        data["elapsed_seconds"] = elapsed_before + time.monotonic() - started
        data["runtime"] = pack(
            dict(
                weights=model.state_dict(),
                best=best,
                optimizer=optimizer.state_dict(),
                scheduler=scheduler.state_dict() if scheduler else None,
                torch_rng=t.get_rng_state(),
                loader_rng=rng.get_state(),
            )
        )
        if len(json.dumps(data, allow_nan=False).encode()) > MAX_BYTES:
            raise ProjectError("Checkpoint16MiB sınırını aşıyor.")
        control.disk(work, force=True)
        checkpoint(copy.deepcopy(data))

    snapshot("running")
    # Pause/cancel completes at an epoch boundary. An interrupted partial epoch
    # is discarded and resumed from the previous optimizer/RNG boundary.
    boundary = copy.deepcopy(data)
    try:
        for epoch in range(data["epoch"], spec.epochs):
            control.check()
            if pause is not None and pause.is_set():
                snapshot("paused")
                return data
            if elapsed_before + time.monotonic() - started > min(
                spec.wall_seconds, control.budget.max_wall_seconds
            ):
                data = copy.deepcopy(boundary)
                data["status"] = "budget_exhausted"
                data["elapsed_seconds"] = elapsed_before + time.monotonic() - started
                checkpoint(copy.deepcopy(data))
                return data
            model.train()
            loader = t.utils.data.DataLoader(
                t.utils.data.TensorDataset(tensors[a], yi[a]),
                batch_size=spec.batch,
                shuffle=True,
                generator=rng,
                num_workers=0,
            )
            gradients = []
            for xb, yb in loader:
                control.check()
                if spec.augmentation == "horizontal_flip":
                    flip = t.rand(len(xb), generator=rng) < 0.5
                    xb = xb.clone()
                    xb[flip] = xb[flip].flip(-1)
                optimizer.zero_grad(set_to_none=True)
                loss = criterion(model(xb), yb)
                if not t.isfinite(loss):
                    raise ProjectError(
                        "Training loss sonlu değil; convergence başarısız."
                    )
                loss.backward()
                grad = t.nn.utils.clip_grad_norm_(
                    model.parameters(), spec.gradient_clip, error_if_nonfinite=True
                )
                gradients.append(float(grad))
                optimizer.step()
            model.eval()
            with t.no_grad():
                train_loss = float(criterion(model(tensors[a]), yi[a]))
                val_loss = float(criterion(model(tensors[b]), yi[b]))
            if not math.isfinite(val_loss):
                raise ProjectError("Validation loss sonlu değil.")
            data["curves"].append(
                dict(
                    epoch=epoch + 1,
                    training_loss=train_loss,
                    validation_loss=val_loss,
                    lr=optimizer.param_groups[0]["lr"],
                    gradient_norm_max=max(gradients),
                    train_n=len(a),
                    validation_n=len(b),
                )
            )
            data["epoch"] = epoch + 1
            if data["best_loss"] is None or val_loss < data["best_loss"]:
                data["best_loss"], data["bad_epochs"] = val_loss, 0
                best = copy.deepcopy(model.state_dict())
            else:
                data["bad_epochs"] += 1
            if scheduler:
                scheduler.step()
            snapshot("running")
            boundary = copy.deepcopy(data)
            control.progress("Tensor epoch / validation", epoch + 1, spec.epochs)
            if control.cancel.is_set() if control.cancel is not None else False:
                raise Canceled()
            if pause is not None and pause.is_set():
                snapshot("paused")
                return data
            if data["bad_epochs"] >= spec.patience:
                data["stop_reason"] = "early_stopping_validation"
                break
    except Canceled:
        data = copy.deepcopy(boundary)
        data["status"] = "canceled"
        data["elapsed_seconds"] = elapsed_before + time.monotonic() - started
        checkpoint(copy.deepcopy(data))
        return data
    validate_weights(model, best)
    model.eval()
    with t.no_grad():
        raw = model(tensors[b])
        prediction = (
            np.asarray([labels[i] for i in raw.argmax(1).tolist()])
            if labels
            else raw.numpy().ravel()
        )
    data["comparison"]["neural"] = float(
        accuracy_score(y[b], prediction)
        if labels
        else mean_absolute_error(y[b], prediction)
    )
    data["validation_predictions"] = dict(
        row_ids=f[b.tolist()]["__vu_row_id"].to_list(), values=prediction.tolist()
    )
    data["model_weights"] = pack(best)
    snapshot("completed")
    return data


def predict(data, frame, mapping=None, control=None):
    control = control or Control()
    control.check()
    if data["status"] != "completed":
        raise ProjectError(
            "Yeni veri prediction yalnız completed safe modelle yapılır."
        )
    spec = NeuralSpec.from_dict(data["spec"])
    schema = data["tensor_schema"]
    mapping = mapping or {n: n for n in schema["feature_names"]}
    if (
        set(mapping) != set(schema["feature_names"])
        or len(set(mapping.values())) != len(mapping)
        or any(
            v not in frame.columns or not frame[v].dtype.is_numeric()
            for v in mapping.values()
        )
        or frame.height > 2000
    ):
        raise ProjectError(
            "Yeni veri kolon mapping/dtype/boyut geçersiz; hedef gerekmez."
        )
    x = np.column_stack(
        [
            np.asarray(frame[mapping[n]], dtype=np.float64)
            for n in schema["feature_names"]
        ]
    )
    if (
        np.isinf(x).any()
        or data["preparation_spec"]["numeric_imputation"] == "none"
        and np.isnan(x).any()
    ):
        raise ProjectError("Yeni veri missing/nonfinite kuralı ihlali.")
    t = framework()
    model = architecture(spec, len(mapping), len(schema["class_labels"]) or 1)
    validate_weights(model, unpack(data["model_weights"]))
    model.eval()
    with t.no_grad():
        output = model(transform(x, data["preprocessing"], spec))
        labels = schema["class_labels"]
        values = (
            [labels[i] for i in output.argmax(1).tolist()]
            if labels
            else output.numpy().ravel().tolist()
        )
        probabilities = output.softmax(1).tolist() if labels else []
    control.check()
    return dict(
        row_ids=frame["__vu_row_id"].to_list(),
        values=values,
        class_labels=labels,
        probabilities=probabilities,
        fit=False,
    )
