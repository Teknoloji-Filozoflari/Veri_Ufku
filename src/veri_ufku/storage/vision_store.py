"""Vision review/export extends existing neural artifacts and immutable ProjectStore."""

import copy
import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from veri_ufku.importers.images import annotation, decode_mask
from veri_ufku.modeling.validation import digest
from veri_ufku.modeling.vision import parse_weights
from veri_ufku.storage.experiment_store import capture
from veri_ufku.storage.neural_store import publish
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.validation_store import prior_uses


def review(store, state, data, row_id, value, reviewer):
    if (
        data["schema"] != "VisionRun/v1"
        or not isinstance(reviewer, str)
        or not reviewer.strip()
        or len(reviewer) > 200
    ):
        raise ProjectError("İnsan reviewer ve Vision run gerekli.")
    current = next(
        (
            r["neural"]
            for r in reversed(state["results"])
            if r.get("neural", {}).get("schema") == "VisionRun/v1"
            and r["neural"]["dataset_version"] == data["dataset_version"]
        ),
        None,
    )
    if not current or current["run_id"] != data["run_id"]:
        raise ProjectError("Review eski revision; en yeni kayıt açılmalı.")
    result = copy.deepcopy(data)
    image = next((r for r in result["images"] if r["row_id"] == row_id), None)
    if image is None:
        raise ProjectError("Annotation kaynak RowId bulunamadı.")
    a = annotation(
        dict(
            value,
            status="human",
            reviewer=reviewer,
            reviewed_at=datetime.now(UTC).isoformat(),
        ),
        image["size"],
        result["classes"],
        result["mask_labels"],
    )
    if a["mask"]:
        dataset = next(
            d for d in state["datasets"] if d["version_id"] == data["dataset_version"]
        )
        source = next(r for r in state["sources"] if r["id"] == dataset["source_id"])
        with zipfile.ZipFile(store.path(source["copy_uri"])) as bundle:
            if a["mask"] not in bundle.namelist():
                raise ProjectError("Review mask immutable source içinde bulunamadı.")
            decode_mask(bundle.read(a["mask"]), image["size"], result["mask_labels"])
    image["annotation"] = a
    result["annotations"][row_id] = a
    result.update(
        run_id="run:" + uid(),
        training_id="run:" + uid(),
        annotation_parent=data["run_id"],
        status="completed",
        mode="annotation_revision",
        epoch=0,
        curves=[],
        metrics={},
        predictions=[],
        model_weights=None,
        runtime=None,
        elapsed_seconds=0,
        prior_test_use_ids=prior_uses(state),
    )
    result["tensor_schema"]["fit_row_ids"] = []
    result["transform"]["preview"] = []
    result["transform"]["excluded_boxes"] = []
    result.pop("model_kind", None)
    result.pop("model_labels", None)
    result["compat_id"] = digest(
        dict(
            source=result["snapshot_fingerprint"],
            bundle=result["image_fingerprint"],
            spec=result["vision_spec"],
            annotations=result["annotations"],
            plan=result["plan"],
        )
    )
    result["created_at"] = datetime.now(UTC).isoformat()
    result["provenance"].update(
        provenance_id="provenance:" + result["compat_id"],
        parameters_hash=digest(result["annotations"]),
        created_at=result["created_at"],
        scope="Human annotation revision; frozen source/split, fit invalidated",
    )
    result["experiment_capture"] = capture(
        dict(
            annotation_parent=data["run_id"],
            annotations=result["annotations"],
            inherited_source=result["dataset_version"],
        )
    )
    result["warnings"].append(
        "Human annotation revision invalidates previous metrics/model; refit required; original model remains archived."
    )
    return publish(store, state, result), result


def export_annotations(data, target):
    rows = []
    for r in data["images"]:
        a = copy.deepcopy(r["annotation"])
        a["reviewer"] = (
            "sha256:" + hashlib.sha256(a["reviewer"].encode()).hexdigest()
            if a["reviewer"]
            else ""
        )
        rows.append(
            dict(
                row_id=r["row_id"],
                source_record_id=r["source_record_id"],
                image_id=r["image_id"],
                member=r["member"],
                sha256=r["sha256"],
                orientation=r["orientation"],
                size=r["size"],
                annotation=a,
                sequence=r["sequence"],
                frame_index=r["frame_index"],
                time_seconds=r["time_seconds"],
                video_source_hash=hashlib.sha256(r["video_source"].encode()).hexdigest()
                if r["video_source"]
                else None,
            )
        )
    payload = dict(
        schema="VisionAnnotations/v1",
        dataset_version=data["dataset_version"],
        source_snapshot_id=data["source_snapshot_id"],
        revision=data["run_id"],
        parent=data.get("annotation_parent"),
        classes=data["classes"],
        mask_labels=data["mask_labels"],
        coordinates="EXIF-oriented half-open XYXY pixels; masks referenced in source snapshot",
        split=data["plan"],
        images=rows,
    )
    write_new(target, payload)


def write_new(target, payload):
    path = Path(target)
    if not path.is_absolute() or path.is_symlink() or path.exists():
        raise ProjectError(
            "Export için yeni mutlak dosya yolu seçin; mevcut dosya üzerine yazılmaz."
        )
    raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2).encode()
    if len(raw) > 16 * 1024**2:
        raise ProjectError("Vision export16MiB sınırı.")
    with path.open("xb") as f:
        f.write(raw)


def export_weights(data, target, license_text, dataset_note):
    if (
        data.get("model_kind") != "tiny_rgb_cnn/v1"
        or not data.get("model_weights")
        or not license_text
        or not dataset_note
    ):
        raise ProjectError(
            "Trained CNN ve lisans/dataset beyanı gerekli; arbitrary object export yok."
        )
    train = set(data["tensor_schema"]["fit_row_ids"])
    catalog = [
        {
            k: r[k]
            for k in ("decoded_sha256", "signature", "group", "subject", "video_source")
        }
        for r in data["images"]
        if r["row_id"] in train
    ]
    for item in catalog:
        for key in ("group", "subject", "video_source"):
            item[key] = (
                hashlib.sha256(item[key].encode()).hexdigest() if item[key] else ""
            )
        item["identity_policy"] = "sha256"
    payload = dict(
        schema="VisionWeights/v1",
        architecture="tiny_rgb_cnn/v1",
        size=data["vision_spec"]["size"],
        labels=data["model_labels"],
        weights=data["model_weights"],
        training_catalog=catalog,
        license=license_text,
        training_dataset=dataset_note,
        assumptions="Closed local tiny CNN, RGB/255 then mean0.5/std0.5, not ImageNet pretrained; provenance author supplied; no quality guarantee",
    )
    parse_weights(json.dumps(payload).encode())
    write_new(target, payload)
