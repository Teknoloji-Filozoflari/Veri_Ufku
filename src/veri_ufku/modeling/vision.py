"""Local image classification first; separate bounded color-pixel detection/segmentation."""

import copy
import hashlib
import json
import time
import zipfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl
from PIL import Image
from scipy.ndimage import label as connected
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.importers.images import annotation, decode, decode_mask, json_data, near
from veri_ufku.importers.sources import safe_member
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.neural import (
    architecture,
    framework,
    pack,
    unpack,
    validate_weights,
)
from veri_ufku.modeling.neural_contracts import NeuralSpec
from veri_ufku.modeling.validation import ValidationSpec, digest, split_plan
from veri_ufku.modeling.vision_contracts import VisionSpec
from veri_ufku.modeling.vision_metrics import detection_metrics, segmentation_metrics
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import file_hash

LIMIT = 16 * 1024**2


def transform(pixels, spec, mask=None):
    h, w = pixels.shape[:2]
    x1, y1, x2, y2 = [int(v * s) for v, s in zip(spec.crop, (w, h, w, h), strict=True)]
    if x1 >= x2 or y1 >= y2:
        raise ProjectError("Crop gerçek pikselde boş.")
    rgb = np.asarray(
        Image.fromarray(pixels[y1:y2, x1:x2]).resize(
            (spec.size, spec.size), Image.Resampling.BILINEAR
        ),
        dtype=np.uint8,
    )
    outmask = (
        np.asarray(
            Image.fromarray(mask[y1:y2, x1:x2]).resize(
                (spec.size, spec.size), Image.Resampling.NEAREST
            ),
            dtype=np.uint8,
        )
        if mask is not None
        else None
    )
    return rgb, outmask, (x1, y1, x2, y2)


def boxes_after(boxes, crop, size):
    x, y, r, b = crop
    out = []
    excluded = []
    for box in boxes:
        left, t, rr, bb = box["xyxy"]
        left = max(left, x)
        t = max(t, y)
        rr = min(rr, r)
        bb = min(bb, b)
        if left >= rr or t >= bb:
            excluded.append(box["id"])
            continue
        out.append(
            dict(
                box,
                xyxy=[
                    (left - x) * size / (r - x),
                    (t - y) * size / (b - y),
                    (rr - x) * size / (r - x),
                    (bb - y) * size / (b - y),
                ],
            )
        )
    return out, excluded


def parse_weights(raw):
    if len(raw) > LIMIT:
        raise ProjectError("Vision model16MiB sınırı.")
    model = json_data(raw)
    if (
        not isinstance(model, dict)
        or set(model)
        != {
            "schema",
            "architecture",
            "size",
            "labels",
            "weights",
            "training_catalog",
            "license",
            "training_dataset",
            "assumptions",
        }
        or model["schema"] != "VisionWeights/v1"
        or model["architecture"] != "tiny_rgb_cnn/v1"
        or type(model["size"]) is not int
        or not 4 <= model["size"] <= 16
        or not isinstance(model["labels"], list)
        or not 2 <= len(model["labels"]) <= 16
        or any(not isinstance(v, str) or not v or len(v) > 100 for v in model["labels"])
        or len(set(model["labels"])) != len(model["labels"])
    ):
        raise ProjectError(
            "Safe VisionWeights/v1 kapalı tiny RGB CNN şeması gerekli; .pt/pickle/remote-code yok."
        )
    for k in ("license", "training_dataset", "assumptions"):
        if not isinstance(model[k], str) or not 1 <= len(model[k]) <= 1000:
            raise ProjectError(
                "Pretrained model lisans/dataset/varsayım beyanı gerekli."
            )
    if (
        not isinstance(model["training_catalog"], list)
        or not 1 <= len(model["training_catalog"]) <= 256
    ):
        raise ProjectError("Pretraining kaynak kimlik/fingerprint kataloğu gerekli.")
    for r in model["training_catalog"]:
        if (
            not isinstance(r, dict)
            or not isinstance(r.get("decoded_sha256"), str)
            or len(r["decoded_sha256"]) != 64
            or not isinstance(r.get("signature"), dict)
            or len(r["signature"].get("dhash", [])) != 64
            or len(r["signature"].get("color", [])) != 3
        ):
            raise ProjectError("Pretrained kaynak hash/near signature geçersiz.")
    # Closed tensor tree only; backend availability is checked on actual use.
    s = NeuralSpec(
        template="cnn",
        image_shape=(3, model["size"], model["size"]),
        image_ack="actual RGB image",
    )
    validate_weights(
        architecture(s, 3 * model["size"] ** 2, len(model["labels"])),
        unpack(model["weights"]),
    )
    return model


def local_weights(folder):
    path = Path(folder) / "model.json"
    if (
        not folder
        or not path.is_file()
        or path.is_symlink()
        or path.stat().st_size > LIMIT
    ):
        raise ProjectError(
            "Yerel safe VisionWeights/v1 model.json yok veya boyut/link sınırı."
        )
    raw = path.read_bytes()
    model = parse_weights(raw)
    return model, dict(
        sha256=hashlib.sha256(raw).hexdigest(),
        bytes=len(raw),
        license=model["license"],
        training_dataset=model["training_dataset"],
        assumptions=model["assumptions"],
        quality="author supplied provenance; model name does not guarantee quality",
    )


def catalog_arrays(request, spec, control):
    checked(request, control)
    if (
        request["row_count"] > 256
        or file_hash(request["image_bundle"]) != request["image_fingerprint"]
    ):
        raise ProjectError("Görüntü immutable bundle hash/count değişti.")
    f = pl.read_parquet(request["path"])
    records = [json.loads(v) for v in f["metadata"]]
    overrides = request.get("annotations", {})
    catalog = request["image_catalog"]
    images = []
    masks = []
    ground_boxes = []
    excluded = []
    with zipfile.ZipFile(request["image_bundle"]) as bundle:
        for row, r in zip(f.iter_rows(named=True), records, strict=True):
            control.check()
            safe_member(r["member"])
            raw = bundle.read(r["member"])
            if hashlib.sha256(raw).hexdigest() != r["sha256"]:
                raise ProjectError("Görüntü/snapshot eşlemesi hash değişti.")
            pixels, info = decode(raw)
            if info["decoded_sha256"] != r["decoded_sha256"]:
                raise ProjectError("Decoded görüntü fingerprint uyuşmuyor.")
            r["row_id"] = row["__vu_row_id"]
            r["source_record_id"] = row["__vu_source_record_id"]
            r["annotation"] = annotation(
                overrides.get(r["row_id"], r["annotation"]),
                r["size"],
                catalog["classes"],
                catalog["mask_labels"],
            )
            mask = None
            if r["annotation"]["mask"]:
                mask_raw = bundle.read(r["annotation"]["mask"])
                mask = decode_mask(mask_raw, r["size"], catalog["mask_labels"])
            rgb, target, crop = transform(pixels, spec, mask)
            boxes, dropped = boxes_after(r["annotation"]["boxes"], crop, spec.size)
            ground_boxes.append(boxes)
            excluded.extend(
                dict(image_id=r["image_id"], box_id=v, reason="explicit crop outside")
                for v in dropped
            )
            images.append(rgb)
            masks.append(target)
    return f, records, np.stack(images), masks, ground_boxes, excluded


def plan_for(request, spec, f, records):
    ids = f["__vu_row_id"].to_list()
    y = np.asarray([r["annotation"]["label"] or "unlabeled" for r in records])
    groups = np.asarray([r["leakage_component"] for r in records])
    protocol = ValidationSpec(
        structure="group",
        folds=2,
        seed=spec.seed,
        prediction_moment="Image available before prediction",
        availability={
            request["image_column"]: dict(
                offset_seconds=0, note="immutable local image"
            )
        },
    )
    classification = spec.task in ("classification", "transfer") and all(
        r["annotation"]["label"] for r in records
    )
    plan, parts = split_plan(
        ids,
        y,
        groups,
        None,
        protocol,
        "group",
        classification,
        request["version_id"],
        request["fingerprint"],
    )
    frozen = request.get("frozen_plan")
    if frozen and plan != frozen:
        raise ProjectError(
            "Kalıcı görüntü split değişti; review/yeni training test üyeliğini sıfırlayamaz. Aynı seed/config kullanın."
        )
    return protocol, plan, parts


def component_predictions(model, rgb, labels, threshold, image_id):
    x = rgb.reshape(-1, 3).astype(float) / 255
    scores = np.array(model["intercept"]) + x @ np.asarray(model["coefficients"]).T
    if len(model["classes"]) == 2 and scores.shape[1] == 1:
        p = 1 / (1 + np.exp(-np.clip(scores[:, 0], -50, 50)))
        probs = np.column_stack((1 - p, p))
    else:
        scores -= scores.max(axis=1, keepdims=True)
        e = np.exp(scores)
        probs = e / e.sum(axis=1, keepdims=True)
    index = probs.argmax(1)
    values = np.asarray(model["classes"])[index].reshape(rgb.shape[:2])
    confidence = probs.max(1).reshape(rgb.shape[:2])
    values = np.where(confidence >= threshold, values, 0).astype(np.uint8)
    out = []
    for cls in model["classes"]:
        if cls == 0:
            continue
        parts, n = connected(
            values == cls
        )  # 4-neighbor, separate touching diagonal pixels.
        for number in range(1, n + 1):
            yy, xx = np.where(parts == number)
            out.append(
                dict(
                    id=f"{image_id}:c{cls}:{number}",
                    image_id=image_id,
                    label=labels[cls],
                    xyxy=[
                        int(xx.min()),
                        int(yy.min()),
                        int(xx.max() + 1),
                        int(yy.max() + 1),
                    ],
                    score=float(confidence[parts == number].mean()),
                )
            )
    return values, out


def validate(data):
    spec = VisionSpec.from_dict(data["vision_spec"])
    if (
        data.get("schema") != "VisionRun/v1"
        or data.get("status")
        not in ("running", "completed", "canceled", "failed", "budget_exhausted")
        or data["epoch"] != len(data["curves"])
        or not 0 <= data["epoch"] <= spec.epochs
    ):
        raise ProjectError("Vision run schema/status/epoch geçersiz.")
    p = data["plan"]["membership"]
    train = set(p["train"])
    val = set(p["validation"])
    test = set(p["test"])
    if (
        train & val
        or (train | val) & test
        or set(data["tensor_schema"]["fit_row_ids"]) - train
    ):
        raise ProjectError("Vision train/validation/test sızıntısı.")
    components = {r["row_id"]: r["leakage_component"] for r in data["images"]}
    if any(
        {components[i] for i in a} & {components[i] for i in b}
        for a, b in ((train, val), (train, test), (val, test))
    ):
        raise ProjectError("Near/group/subject/video-source split sızıntısı.")
    if len(json.dumps(data, allow_nan=False).encode()) > LIMIT:
        raise ProjectError("Vision JSON16MiB sınırı.")


def calculate(request, parameters, work, control=None, checkpoint=lambda v: None):
    control = control or Control()
    spec = VisionSpec.from_dict(parameters)
    start = time.monotonic()
    f, records, rgb, masks, boxes, excluded = catalog_arrays(request, spec, control)
    protocol, plan, parts = plan_for(request, spec, f, records)
    a, b, _, _, _ = parts
    now = datetime.now(UTC).isoformat()
    t = None
    data = dict(
        schema="VisionRun/v1",
        run_id=request["run_id"],
        training_id=request["run_id"],
        status="running",
        dataset_version=request["version_id"],
        origin_version=request["origin_version"],
        source_snapshot_id=request["source_snapshot_id"],
        snapshot_fingerprint=request["fingerprint"],
        image_fingerprint=request["image_fingerprint"],
        seed=spec.seed,
        spec={},
        vision_spec=spec.data(),
        protocol=protocol.data(),
        plan=plan,
        epoch=0,
        curves=[],
        elapsed_seconds=0.0,
        created_at=now,
        data_access_at=now,
        prior_test_use_ids=request.get("prior_test_use_ids", []),
        images=records,
        annotations={r["row_id"]: r["annotation"] for r in records},
        classes=request["image_catalog"]["classes"],
        mask_labels=request["image_catalog"]["mask_labels"],
        metrics={},
        predictions=[],
        tensor_schema=dict(
            fit_row_ids=[],
            validation_row_ids=f[b.tolist()]["__vu_row_id"].to_list(),
            shape=[3, spec.size, spec.size],
            layout="real RGB NCHW",
        ),
        model_weights=None,
        runtime=None,
        mode="vision_development_holdout",
        warnings=[
            "Validation holdout only; final test unused; no independent general quality claim.",
            "Near-duplicate heuristic is not exhaustive.",
            "Pre-extracted video frames only; saliency not provided as causal explanation.",
            "Model bbox/mask output is resized/cropped pixel coordinates; human annotation uses original EXIF-oriented pixels, never silently promoted.",
        ],
        transform=dict(
            resize=[spec.size, spec.size],
            crop=spec.crop,
            normalization="RGB/255 then fixed mean0.5/std0.5 for CNN; pixel model RGB/255",
            orientation="EXIF-oriented source; bbox/mask already oriented",
            augmentation="horizontal flip train only" if spec.flip else "none",
            excluded_boxes=excluded,
            preview=[
                dict(
                    row_id=r["row_id"],
                    original_size=r["size"],
                    transformed=rgb[i].tolist(),
                    annotation_status=r["annotation"]["status"],
                    boxes=boxes[i],
                    mask=masks[i].tolist() if masks[i] is not None else None,
                    partition="train" if i in a else "validation" if i in b else "test",
                    train_augmentation_preview=rgb[i][:, ::-1].tolist()
                    if spec.flip and i in a
                    else None,
                )
                for i in list(
                    dict.fromkeys([int(a[0]), int(b[0]), int(a[min(1, len(a) - 1)])])
                )
                for r in [records[i]]
            ],
        ),
        experiment_capture=request.get("experiment_capture", {}),
        environment=dict(backend="Pillow12.3.0/scikit-learn1.9.1 CPU", device="cpu"),
    )
    data["compat_id"] = digest(
        dict(
            source=request["fingerprint"],
            bundle=request["image_fingerprint"],
            spec=spec.data(),
            annotations=data["annotations"],
            plan=plan,
        )
    )
    data["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + data["compat_id"],
            dataset_versions=(request["version_id"],),
            config_revision=request.get("config_revision", 0),
            capability_id="model.vision." + spec.task,
            parameters_hash=digest(spec.data()),
            environment=(("device", "cpu"),),
            created_at=now,
            scope="immutable images; whole-component train/validation/test; only validation evaluated",
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
    if spec.task == "scan":
        emit("completed")
        return data
    for i in np.concatenate((a, b)):
        ann = records[i]["annotation"]
        if (
            ann["status"] != "human"
            or spec.task in ("classification", "transfer")
            and not ann["label"]
            or spec.task == "segmentation"
            and masks[i] is None
        ):
            raise ProjectError(
                "Fit/evaluation yalnız insan onaylı label/bbox/mask ile; model/proposed ground truth değildir."
            )
    data["tensor_schema"]["fit_row_ids"] = f[a.tolist()]["__vu_row_id"].to_list()
    try:
        if spec.task in ("classification", "transfer"):
            t = framework()
            t.set_num_threads(control.budget.worker_threads)
            t.backends.mkldnn.enabled = False
            t.use_deterministic_algorithms(True)
            t.manual_seed(spec.seed)
            labels = sorted({records[i]["annotation"]["label"] for i in a})
            if len(labels) < 2 or any(
                records[i]["annotation"]["label"] not in labels for i in b
            ):
                raise ProjectError(
                    "Train en az2sınıf ve validation sınıfları train'de bulunmalı."
                )
            ns = NeuralSpec(
                template="cnn",
                image_shape=(3, spec.size, spec.size),
                image_ack="verified local RGB images",
            )
            model = architecture(ns, 3 * spec.size**2, len(labels))
            pretrained = None
            if spec.task == "transfer":
                pretrained, info = local_weights(spec.model_folder)
                held = [records[i] for i in np.concatenate((b, parts[3]))]
                if any(
                    near(p, h)
                    or any(
                        p.get(k)
                        and p.get(k)
                        == (
                            hashlib.sha256(h.get(k, "").encode()).hexdigest()
                            if p.get("identity_policy") == "sha256"
                            else h.get(k)
                        )
                        for k in ("group", "subject", "video_source")
                    )
                    for p in pretrained["training_catalog"]
                    for h in held
                ):
                    raise ProjectError(
                        "Pretrained kaynakları held validation/test ile near/group örtüşüyor; transfer reddedildi."
                    )
                if pretrained["size"] != spec.size:
                    raise ProjectError("Transfer preprocessing/input size uyuşmuyor.")
                old = unpack(pretrained["weights"])
                current = model.state_dict()
                for key in ("0.weight", "0.bias"):
                    current[key] = old[key]
                validate_weights(model, current)
                for param in model[0].parameters():
                    param.requires_grad_(False)
                data["pretrained"] = info
            before = pack(model[0].state_dict())
            optimizer = t.optim.Adam(
                [v for v in model.parameters() if v.requires_grad],
                lr=spec.learning_rate,
            )
            x = t.from_numpy(rgb.astype(np.float32) / 255).permute(0, 3, 1, 2)
            x = (x - 0.5) / 0.5
            y = t.tensor(
                [
                    labels.index(r["annotation"]["label"])
                    if r["annotation"]["label"] in labels
                    else -1
                    for r in records
                ],
                dtype=t.int64,
            )
            rng = t.Generator().manual_seed(spec.seed + 1)
            criterion = t.nn.CrossEntropyLoss()
            best = None
            best_loss = float("inf")
            for epoch in range(spec.epochs):
                model.train()
                loader = t.utils.data.DataLoader(
                    t.utils.data.TensorDataset(x[a], y[a]),
                    batch_size=8,
                    shuffle=True,
                    generator=rng,
                    num_workers=0,
                )
                for xb, yb in loader:
                    control.check()
                    if spec.flip:
                        flip = t.rand(len(xb), generator=rng) < 0.5
                        xb = xb.clone()
                        xb[flip] = xb[flip].flip(-1)
                    optimizer.zero_grad(set_to_none=True)
                    loss = criterion(model(xb), yb)
                    loss.backward()
                    t.nn.utils.clip_grad_norm_(
                        model.parameters(), 5, error_if_nonfinite=True
                    )
                    optimizer.step()
                model.eval()
                with t.no_grad():
                    tl = float(criterion(model(x[a]), y[a]))
                    vl = float(criterion(model(x[b]), y[b]))
                if not np.isfinite(tl + vl):
                    raise ProjectError("Vision loss nonfinite.")
                if vl < best_loss:
                    best_loss = vl
                    best = copy.deepcopy(model.state_dict())
                data["epoch"] = epoch + 1
                data["curves"].append(
                    dict(
                        epoch=epoch + 1,
                        training_loss=tl,
                        validation_loss=vl,
                        train_n=len(a),
                        validation_n=len(b),
                    )
                )
                data["runtime"] = pack(
                    dict(
                        weights=model.state_dict(),
                        optimizer=optimizer.state_dict(),
                        rng=rng.get_state(),
                        best=best,
                    )
                )
                emit("running")
                control.progress("CPU görüntü epoch", epoch + 1, spec.epochs)
            validate_weights(model, best)
            model.eval()
            with t.no_grad():
                prob = model(x[b]).softmax(1).numpy()
                pred = prob.argmax(1)
            truth = y[b].numpy()
            baseline = (
                DummyClassifier(strategy="prior")
                .fit(np.zeros((len(a), 1)), y[a].numpy())
                .predict(np.zeros((len(b), 1)))
            )
            data["metrics"] = dict(
                labels=labels,
                confusion=confusion_matrix(
                    truth, pred, labels=list(range(len(labels)))
                ).tolist(),
                accuracy=float(accuracy_score(truth, pred)),
                baseline_accuracy=float(accuracy_score(truth, baseline)),
                n=len(b),
                loss="cross_entropy",
                scope="same holdout; final test untouched",
            )
            data["model_weights"] = pack(best)
            data["model_kind"] = "tiny_rgb_cnn/v1"
            data["model_labels"] = labels
            data["backbone_frozen"] = (
                before == pack(model[0].state_dict()) if pretrained else False
            )
            data["predictions"] = [
                dict(
                    row_id=records[i]["row_id"],
                    image_id=records[i]["image_id"],
                    label=labels[int(pred[j])],
                    probabilities=prob[j].tolist(),
                    status="model",
                )
                for j, i in enumerate(b)
            ]
            data["environment"].update(
                torch=str(t.__version__),
                cuda=t.version.cuda,
                determinism="fixed CPU/thread/seed only; no cross-device guarantee",
            )
        else:
            targets = []
            for i, r in enumerate(records):
                if spec.task == "segmentation":
                    target = masks[i]
                else:
                    target = np.zeros((spec.size, spec.size), dtype=np.uint8)
                    for box in boxes[i]:
                        left, top, right, bottom = box["xyxy"]
                        cls = data["mask_labels"].index(box["label"])
                        area = (
                            slice(int(np.floor(top)), int(np.ceil(bottom))),
                            slice(int(np.floor(left)), int(np.ceil(right))),
                        )
                        if (target[area] > 0).any():
                            raise ProjectError(
                                "Overlapping weak bbox pixel targets ambiguous; native template rejects."
                            )
                        target[area] = cls
                targets.append(target)
            if any(targets[i] is None for i in np.concatenate((a, b))):
                raise ProjectError("Human mask gerekli.")
            trainx = np.concatenate([rgb[i].reshape(-1, 3) / 255 for i in a])
            trainy = np.concatenate([targets[i].ravel() for i in a])
            if len(set(trainy)) < 2:
                raise ProjectError(
                    "Pixel eğitiminde background ve foreground sınıfı gerekir."
                )
            control.check()
            classifier = LogisticRegression(
                C=10, max_iter=100, class_weight="balanced", random_state=spec.seed
            ).fit(trainx, trainy)
            control.check()
            payload = dict(
                classes=[int(v) for v in classifier.classes_],
                coefficients=classifier.coef_.tolist(),
                intercept=classifier.intercept_.tolist(),
            )
            values = []
            preds = []
            gt = []
            for i in b:
                mask, found = component_predictions(
                    payload,
                    rgb[i],
                    data["mask_labels"],
                    spec.score_threshold,
                    records[i]["image_id"],
                )
                values.append(mask)
                preds.extend(found)
                gt.extend(
                    dict(box, image_id=records[i]["image_id"]) for box in boxes[i]
                )
            data["metrics"] = (
                detection_metrics(
                    gt, preds, data["mask_labels"][1:], spec.iou_thresholds
                )
                if spec.task == "detection"
                else segmentation_metrics(
                    [targets[i] for i in b], values, data["mask_labels"]
                )
            )
            data["predictions"] = [
                dict(
                    row_id=records[i]["row_id"],
                    image_id=records[i]["image_id"],
                    mask=values[j].tolist(),
                    boxes=[p for p in preds if p["image_id"] == records[i]["image_id"]],
                    status="model",
                )
                for j, i in enumerate(b)
            ]
            data["model_weights"] = payload
            data["model_kind"] = "rgb_pixel_logistic/v1"
            data["warnings"].append(
                "Bounded RGB color classifier; bbox supervision weak. Not general YOLO/U-Net; no neural detection/segmentation quality guarantee."
            )
        emit("completed")
        return data
    except Canceled:
        data["model_weights"] = None
        data["metrics"] = {}
        emit("canceled")
        return data


def predict(data, request, control=None):
    control = control or Control()
    spec = VisionSpec.from_dict(data["vision_spec"])
    if data["status"] != "completed" or not data["model_weights"]:
        raise ProjectError("Completed trained vision model gerekli.")
    f, records, rgb, _, _, _ = catalog_arrays(request, spec, control)
    if data["model_kind"] == "tiny_rgb_cnn/v1":
        t = framework()
        t.set_num_threads(control.budget.worker_threads)
        model = architecture(
            NeuralSpec(
                template="cnn",
                image_shape=(3, spec.size, spec.size),
                image_ack="actual RGB",
            ),
            3 * spec.size**2,
            len(data["model_labels"]),
        )
        validate_weights(model, unpack(data["model_weights"]))
        model.eval()
        with t.no_grad():
            values = (
                model(
                    (
                        t.from_numpy(rgb.astype(np.float32) / 255).permute(0, 3, 1, 2)
                        - 0.5
                    )
                    / 0.5
                )
                .softmax(1)
                .numpy()
            )
        predictions = [
            dict(
                row_id=r["row_id"],
                image_id=r["image_id"],
                label=data["model_labels"][int(values[i].argmax())],
                probabilities=values[i].tolist(),
                status="model",
            )
            for i, r in enumerate(records)
        ]
    else:
        predictions = []
        for r, image in zip(records, rgb, strict=True):
            mask, boxes = component_predictions(
                data["model_weights"],
                image,
                data["mask_labels"],
                spec.score_threshold,
                r["image_id"],
            )
            predictions.append(
                dict(
                    row_id=r["row_id"],
                    image_id=r["image_id"],
                    mask=mask.tolist(),
                    boxes=boxes,
                    status="model",
                )
            )
    control.check()
    return dict(
        dataset_version=request["version_id"],
        source_snapshot_id=request["source_snapshot_id"],
        training_id=data["training_id"],
        fit=False,
        predictions=predictions,
    )
