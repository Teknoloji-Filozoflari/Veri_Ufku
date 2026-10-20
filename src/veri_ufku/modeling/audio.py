"""Offline immutable audio features and whole-component heldout classification."""

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
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.preprocessing import StandardScaler

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.audio import decode
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.audio_contracts import AudioSpec
from veri_ufku.modeling.audio_features import features, resample
from veri_ufku.modeling.audio_speech import errors, local_model, transcribe
from veri_ufku.modeling.validation import ValidationSpec, digest, split_plan
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import file_hash


def samples(request, spec, control):
    checked(request, control)
    if file_hash(request["audio_bundle"]) != request["audio_fingerprint"]:
        raise ProjectError("Ses snapshot hash değişti; kaynakla eşleşmiyor.")
    f = pl.read_parquet(request["path"])
    if not 1 <= len(f) <= 256:
        raise ProjectError("Audio256segment sınırı.")
    total_frames = 0
    rows = []
    signals = []
    cache = {}
    bundle = (
        zipfile.ZipFile(request["audio_bundle"])
        if zipfile.is_zipfile(request["audio_bundle"])
        else None
    )
    try:
        for row in f.iter_rows(named=True):
            control.check()
            r = json.loads(row["metadata"])
            if r["member"] not in cache:
                raw = (
                    bundle.read(r["member"])
                    if bundle
                    else Path(request["audio_bundle"]).read_bytes()
                )
                if hashlib.sha256(raw).hexdigest() != r["sha256"]:
                    raise ProjectError("Ses dosya/segment hash kimliği değişti.")
                y, info = decode(raw)
                if info["decoded_sha256"] != r["decoded_sha256"]:
                    raise ProjectError("Decoded PCM kimliği uyuşmuyor.")
                # Keep at most one decoded recording; memory does not grow with dataset.
                cache = {r["member"]: y}
            y = cache[r["member"]]
            if spec.channel >= y.shape[1]:
                raise ProjectError(
                    "Seçilen kanal kaynakta yok; sessiz downmix yapılmaz."
                )
            segment = y[r["start_frame"] : r["end_frame"], spec.channel]
            if not len(segment) or r["end_frame"] > len(y):
                raise ProjectError("Audio segment kaynak frame aralığı geçersiz.")
            r.update(
                row_id=row["__vu_row_id"], source_record_id=row["__vu_source_record_id"]
            )
            estimate = int(
                np.ceil(
                    len(segment)
                    * (spec.target_rate or r["sample_rate"])
                    / r["sample_rate"]
                )
            )
            total_frames += estimate
            if estimate > 2_000_000 or total_frames > 4_000_000:
                raise ProjectError(
                    "Audio2Mframe/segment ve4M toplam işleme önkontrolü; daha kısa segment seçin."
                )
            source_level = dict(
                clipped_sample_fraction=float(
                    np.mean(np.abs(segment) >= spec.clip_level)
                ),
                outside_fullscale_fraction=float(np.mean(np.abs(segment) > 1)),
                rms=float(np.sqrt(np.mean(segment * segment))),
                silence_sample_fraction=float(
                    np.mean(np.abs(segment) <= 10 ** (spec.silence_dbfs / 20))
                ),
                clip_level=spec.clip_level,
                silence_dbfs=spec.silence_dbfs,
                scope="original selected channel/segment before resampling; silence sample fraction, not speech VAD",
            )
            r["source_quality"] = source_level
            out, rate, recipe = resample(segment, r["sample_rate"], spec.target_rate)
            r["processing"] = dict(
                channel=spec.channel,
                resampling=recipe,
                source_start_seconds=r["start_frame"] / r["sample_rate"],
                source_end_seconds=r["end_frame"] / r["sample_rate"],
            )
            rows.append(r)
            signals.append((out, rate))
    finally:
        if bundle:
            bundle.close()
    return f, rows, signals


def plan_for(request, spec, frame, rows):
    protocol = ValidationSpec(
        structure="group",
        folds=2,
        seed=spec.seed,
        prediction_moment="Audio segment available before prediction",
        availability={
            request["audio_column"]: dict(
                offset_seconds=0, note="immutable recorded audio"
            )
        },
    )
    if spec.task != "classification":
        plan = request.get("frozen_plan") or dict(
            split_id="audio-no-evaluation:"
            + digest(dict(version=request["version_id"], seed=spec.seed)),
            membership=dict(
                train=frame["__vu_row_id"].to_list(), validation=[], test=[]
            ),
            scope="deterministic per-segment features/transcription; no statistical evaluation split",
        )
    else:
        plan, _ = split_plan(
            frame["__vu_row_id"].to_list(),
            np.array([r["label"] for r in rows]),
            np.array([r["leakage_component"] for r in rows]),
            None,
            protocol,
            "group",
            True,
            request["version_id"],
            request["fingerprint"],
        )
        frozen = request.get("frozen_plan")
        if frozen and frozen != plan:
            raise ProjectError(
                "Kalıcı classification split değişti; test kullanım geçmişi sıfırlanamaz."
            )
    return protocol, plan


def validate(data):
    AudioSpec.from_dict(data["audio_spec"])
    if (
        data.get("schema") != "AudioRun/v1"
        or data.get("status")
        not in ("running", "completed", "canceled", "failed", "budget_exhausted")
        or data["epoch"] != 0
        or data["curves"]
    ):
        raise ProjectError("Audio run kapalı şema/status hatası.")
    p = data["plan"]["membership"]
    sides = [set(p[k]) for k in ("train", "validation", "test")]
    ids = {r["row_id"]: r["leakage_component"] for r in data["segments"]}
    if (
        set(ids) != set.union(*sides)
        or set(data["tensor_schema"]["fit_row_ids"]) - sides[0]
        or any(
            a & b or {ids[i] for i in a} & {ids[i] for i in b}
            for a, b in (
                (sides[0], sides[1]),
                (sides[0], sides[2]),
                (sides[1], sides[2]),
            )
        )
    ):
        raise ProjectError("Speaker/session/recording/segment split sızıntısı.")
    if len(json.dumps(data, allow_nan=False).encode()) > 16 * 1024**2:
        raise ProjectError("Audio safeJSON16MiB sınırı.")


def calculate(request, parameters, work, control=None, checkpoint=lambda v: None):
    control = control or Control()
    spec = AudioSpec.from_dict(parameters)
    start = time.monotonic()
    if spec.task == "transcribe":
        local_model(spec.stt_folder, spec.language)
    frame, rows, signals = samples(request, spec, control)
    protocol, plan = plan_for(request, spec, frame, rows)
    now = datetime.now(UTC).isoformat()
    compat = digest(
        dict(
            source=request["fingerprint"],
            bundle=request["audio_fingerprint"],
            spec=spec.data(),
            plan=plan,
        )
    )
    data = dict(
        schema="AudioRun/v1",
        run_id=request["run_id"],
        training_id=request["run_id"],
        status="running",
        dataset_version=request["version_id"],
        origin_version=request["origin_version"],
        source_snapshot_id=request["source_snapshot_id"],
        snapshot_fingerprint=request["fingerprint"],
        audio_fingerprint=request["audio_fingerprint"],
        seed=spec.seed,
        spec={},
        audio_spec=spec.data(),
        protocol=protocol.data(),
        plan=plan,
        epoch=0,
        curves=[],
        elapsed_seconds=0,
        created_at=now,
        data_accessed_at=now,
        prior_test_use_ids=request.get("prior_test_use_ids", []),
        segments=rows,
        metrics={},
        previews=[],
        features=[],
        predictions=[],
        model_weights=None,
        runtime=None,
        mode="audio_offline_development",
        tensor_schema=dict(
            fit_row_ids=[],
            validation_row_ids=plan["membership"]["validation"],
            shape="fixed MFCC/logmel segment summary; original channel/frame IDs preserved",
        ),
        compat_id=compat,
        warnings=[
            "Unknown speakers/sessions cannot be inferred; all declared identities/source recordings/decoded duplicates unioned.",
            "MFCC/logmel not calibrated SPL; silence/clipping thresholds explicit, no automatic trim/normalization.",
            "Holdout development only; final test metric not produced. No diarization/event detection/microphone recording.",
            "Preview spectrogram time frames reduced explicitly; statistics use full selected segment.",
        ],
        experiment_capture=request.get("experiment_capture", {}),
        environment=dict(
            device="cpu", soundfile="0.13.1", scipy="1.18.0", sklearn="1.9.1"
        ),
    )
    data["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + compat,
            dataset_versions=(request["version_id"],),
            config_revision=request.get("config_revision", 0),
            capability_id="model.audio." + spec.task,
            parameters_hash=digest(spec.data()),
            environment=(("device", "cpu"),),
            created_at=now,
            scope="immutable recording/segment/channel/frame; offline fixed features; whole-component split",
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
        x = []
        for r, (y, rate) in zip(rows, signals, strict=True):
            control.check()
            vector, view = features(y, rate, spec)
            x.append(vector)
            data["features"].append(
                dict(
                    row_id=r["row_id"],
                    segment_id=r["segment_id"],
                    mfcc_mean=view["mfcc_mean"],
                    logmel_mean=view["logmel_mean"],
                    quality=view["quality"],
                )
            )
            if len(data["previews"]) < 3:
                data["previews"].append(
                    dict(
                        row_id=r["row_id"],
                        segment_id=r["segment_id"],
                        recording_id=r["recording_id"],
                        source_sample_rate=r["sample_rate"],
                        source_channels=r["channels"],
                        source_quality=r["source_quality"],
                        **view,
                    )
                )
            control.progress("CPU ses feature", len(x), len(rows))
        if spec.task == "classification":
            a = np.array(
                [
                    i
                    for i, r in enumerate(rows)
                    if r["row_id"] in plan["membership"]["train"]
                ]
            )
            b = np.array(
                [
                    i
                    for i, r in enumerate(rows)
                    if r["row_id"] in plan["membership"]["validation"]
                ]
            )
            if any(
                rows[i]["label_status"] != "human" or not rows[i]["label"]
                for i in np.concatenate([a, b])
            ):
                raise ProjectError(
                    "Train/validation insan audio etiketi gerekli; model önerisi GT değildir."
                )
            labels = sorted({rows[i]["label"] for i in a})
            if len(labels) < 2 or any(rows[i]["label"] not in labels for i in b):
                raise ProjectError("Train2classes/validation unseen class kontrolü.")
            x = np.stack(x)
            trainx = x[a]
            trainy = [rows[i]["label"] for i in a]
            if spec.gain_db:
                augmented = []
                for i in a:
                    control.check()
                    y, rate = signals[i]
                    z = y * 10 ** (spec.gain_db / 20)
                    if np.abs(z).max() > 1:
                        raise ProjectError(
                            "Gain augmentation clipping üretir; sessiz normalize/clip yok."
                        )
                    augmented.append(features(z, rate, spec)[0])
                trainx = np.concatenate([trainx, np.stack(augmented)])
                trainy = trainy * 2
            scaler = StandardScaler().fit(trainx)
            model = LogisticRegression(max_iter=500, random_state=spec.seed).fit(
                scaler.transform(trainx), trainy
            )
            control.check()
            pred = model.predict(scaler.transform(x[b]))
            truth = [rows[i]["label"] for i in b]
            baseline = (
                DummyClassifier(strategy="prior")
                .fit(x[a], [rows[i]["label"] for i in a])
                .predict(x[b])
            )
            data["metrics"] = dict(
                labels=list(model.classes_),
                confusion=confusion_matrix(truth, pred, labels=model.classes_).tolist(),
                accuracy=float(accuracy_score(truth, pred)),
                baseline_accuracy=float(accuracy_score(truth, baseline)),
                n=len(b),
                scope="same component holdout; final test untouched",
                train_n=len(a),
                augmented_n=len(a) if spec.gain_db else 0,
            )
            data["model_kind"] = "audio_summary_logistic/v1"
            data["model_weights"] = dict(
                labels=list(model.classes_),
                mean=scaler.mean_.tolist(),
                scale=scaler.scale_.tolist(),
                coefficients=model.coef_.tolist(),
                intercept=model.intercept_.tolist(),
            )
            data["tensor_schema"]["fit_row_ids"] = [rows[i]["row_id"] for i in a]
            data["augmentation"] = dict(
                gain_db=spec.gain_db,
                fit_row_ids=data["tensor_schema"]["fit_row_ids"],
                source_rate_preserved=True,
                clipping_policy="reject",
            )
            data["predictions"] = [
                dict(
                    row_id=rows[i]["row_id"],
                    segment_id=rows[i]["segment_id"],
                    label=str(pred[j]),
                    status="model",
                )
                for j, i in enumerate(b)
            ]
        elif spec.task == "transcribe":
            for r, (y, rate) in zip(rows, signals, strict=True):
                control.check()
                v = transcribe(
                    y, rate, spec, control, r["start_frame"] / r["sample_rate"]
                )
                metric = (
                    errors(r["reference"], v["text"])
                    if r["reference_status"] == "human"
                    and r["reference"]
                    and r["start_frame"] == 0
                    and r["end_frame"] == r["frames"]
                    else dict(
                        wer=None,
                        cer=None,
                        reason="No human reference matching this exact segment; whole-recording reference not reused for subsegments",
                    )
                )
                data["predictions"].append(
                    dict(
                        row_id=r["row_id"],
                        source_record_id=r["source_record_id"],
                        segment_id=r["segment_id"],
                        status="model",
                        metrics=metric,
                        **v,
                    )
                )
        control.check()
        emit("completed")
        return data
    except Canceled:
        data.update(model_weights=None, metrics={}, predictions=[])
        emit("canceled")
        return data


def predict(data, request, control=None):
    control = control or Control()
    validate(data)
    if (
        data["status"] != "completed"
        or data.get("model_kind") != "audio_summary_logistic/v1"
    ):
        raise ProjectError("Safe trained audio classifier gerekli.")
    spec = AudioSpec.from_dict(data["audio_spec"])
    _, rows, signals = samples(request, spec, control)
    model = data["model_weights"]
    values = []
    for r, (y, rate) in zip(rows, signals, strict=True):
        control.check()
        x = features(y, rate, spec)[0]
        z = (x - np.array(model["mean"])) / np.array(model["scale"])
        score = z @ np.array(model["coefficients"]).T + np.array(model["intercept"])
        cls = int(score[0] > 0) if len(model["labels"]) == 2 else int(np.argmax(score))
        values.append(
            dict(
                row_id=r["row_id"],
                source_record_id=r["source_record_id"],
                segment_id=r["segment_id"],
                recording_id=r["recording_id"],
                label=model["labels"][cls],
                status="model",
            )
        )
    return dict(
        schema="AudioPrediction/v1",
        fit=False,
        source_version=request["version_id"],
        model_run_id=data["run_id"],
        predictions=values,
    )
