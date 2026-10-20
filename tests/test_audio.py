"""Real WAV/FLAC, spectral references, immutable identities and speaker isolation."""

import io
import json
from contextlib import closing
from dataclasses import replace

import numpy as np
import pytest
import soundfile as sf

from veri_ufku.importers.audio import decode
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import detect, get_adapter
from veri_ufku.importers.sources import capture_source, unpack
from veri_ufku.modeling.audio import calculate, predict
from veri_ufku.modeling.audio_contracts import AudioSpec
from veri_ufku.modeling.audio_features import features, resample
from veri_ufku.modeling.audio_speech import errors, local_model
from veri_ufku.storage.neural_store import load, publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def recordings(folder, seed=58, n=16, human=True, prefix="bankA"):
    folder.mkdir(parents=True)
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        rate = 16000
        t = np.arange(rate) / rate
        y = 0.3 * np.sin(
            2 * np.pi * (1000 if i % 2 == 0 else 3000) * t + rng.uniform(-3, 3)
        )
        name = f"recording-{i}." + ("wav" if i % 2 == 0 else "flac")
        sf.write(folder / name, y, rate, subtype="PCM_16")
        rows.append(
            dict(
                id=prefix + str(i),
                file=name,
                label="low" if i % 2 == 0 else "high",
                label_status="human" if human else "model",
                speaker=prefix + "speaker" + str(i // 2),
                session=prefix + "session" + str(i // 2),
                source_recording=prefix + "source" + str(i),
                reference="Sensitive konuşma",
                reference_status="human",
                segments=[
                    dict(id="s0", start_frame=0, end_frame=8000),
                    dict(id="s1", start_frame=4000, end_frame=12000),
                ],
            )
        )
    manifest = dict(schema="AudioManifest/v1", classes=["low", "high"], recordings=rows)
    (folder / "audio.json").write_text(json.dumps(manifest, ensure_ascii=False))
    return manifest


def fixture(tmp_path):
    folder = tmp_path / "recordings"
    recordings(folder)
    work = tmp_path / "work"
    work.mkdir()
    c = Control()
    snapshot = unpack(capture_source(folder / "audio.json", work, c), work, c)
    assert detect(snapshot) == "audio_dataset"
    result = get_adapter("audio_dataset").import_data(
        snapshot, StructuredSettings(adapter_id="audio_dataset"), work, c
    )
    store = ProjectStore.create(tmp_path / "project")
    store.publish_import(result)
    d = store.state["datasets"][-1]
    s = store.state["sources"][-1]
    assert s["copy_uri"]
    request = dict(
        path=str(store.path(d["snapshot_uri"])),
        fingerprint=hash_artifact(store.path(d["snapshot_uri"]), c),
        columns=d["import_metadata"]["columns"],
        row_count=d["import_metadata"]["row_count"],
        version_id=d["version_id"],
        origin_version=d["version_id"],
        source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
        snapshot_uri=d["snapshot_uri"],
        config_revision=0,
        run_id="run:audio58",
        prior_test_use_ids=[],
        audio_bundle=str(store.path(s["copy_uri"])),
        audio_fingerprint=s["fingerprint"],
        audio_column=next(
            x["id"] for x in d["import_metadata"]["columns"] if x["name"] == "member"
        ),
    )
    return store, request, work, folder


@pytest.mark.parametrize("fmt", ["WAV", "FLAC"])
def test_real_formats_unchanged_signal_metadata(fmt):
    raw = io.BytesIO()
    y = 0.25 * np.sin(2 * np.pi * 1000 * np.arange(16000) / 16000)
    sf.write(raw, np.column_stack([y, y / 2]), 16000, format=fmt, subtype="PCM_16")
    decoded, info = decode(raw.getvalue())
    assert (
        info["sample_rate"] == 16000
        and info["channels"] == 2
        and info["duration_seconds"] == 1
    )
    np.testing.assert_allclose(decoded[:, 0], y, atol=1 / 32768)
    np.testing.assert_allclose(decoded[:, 1], y / 2, atol=1 / 32768)


def test_known_sine_psd_mfcc_resampling_and_quality():
    spec = AudioSpec(n_fft=256, hop=256)
    y = 0.4 * np.sin(2 * np.pi * 1000 * np.arange(4096) / 16000)
    summary, view = features(y, 16000, spec)
    psd = 10 ** (np.array(view["spectrogram_db"])[0] / 10)
    assert view["frequency_hz"][int(np.argmax(psd))] == 1000
    assert psd.sum() * (16000 / 256) == pytest.approx(0.4**2 / 2, abs=1e-8)
    # DCT-II orthonormal C0 = sum(log-mel)/sqrt(n_mels).
    assert view["mfcc_mean"][0] == pytest.approx(
        sum(view["logmel_mean"]) / np.sqrt(spec.n_mels)
    )
    assert len(summary) == 2 * (spec.n_mfcc + spec.n_mels)
    out, rate, recipe = resample(y, 16000, 8000)
    assert rate == 8000 and len(out) == 2048 and recipe["down"] == 2
    assert np.sqrt(np.mean(out[100:-100] ** 2)) == pytest.approx(
        0.4 / np.sqrt(2), abs=0.003
    )
    high = 0.4 * np.sin(2 * np.pi * 6000 * np.arange(4096) / 16000)
    rejected, _, _ = resample(high, 16000, 8000)
    assert np.sqrt(np.mean(rejected[100:-100] ** 2)) < 0.001
    _, q = features(np.zeros(512), 16000, spec)
    assert (
        q["quality"]["silence_window_fraction"] == 1
        and q["quality"]["clipped_sample_fraction"] == 0
    )
    _, q = features(np.ones(512), 16000, spec)
    assert q["quality"]["clipped_sample_fraction"] == 1
    with pytest.raises(ProjectError, match="Nyquist"):
        features(y, 16000, replace(spec, f_max=9000))


@pytest.mark.parametrize("task", ["features", "classification"])
def test_real_adapter_pipeline_safe_roundtrip_and_fit_ids(tmp_path, task):
    store, r, work, folder = fixture(tmp_path)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    with closing(store):
        value = calculate(
            r,
            AudioSpec(task=task, gain_db=-3 if task == "classification" else 0).data(),
            work,
        )
        assert value["status"] == "completed" and len(value["segments"]) == 32
        groups = {s["row_id"]: s["leakage_component"] for s in value["segments"]}
        p = value["plan"]["membership"]
        assert {groups[i] for i in p["train"]}.isdisjoint(
            {groups[i] for i in p["validation"] + p["test"]}
        )
        if task == "classification":
            assert set(value["tensor_schema"]["fit_row_ids"]) == set(p["train"])
            assert value["metrics"]["n"] == len(p["validation"])
            assert value["metrics"]["augmented_n"] == len(p["train"])
            assert sum(map(sum, value["metrics"]["confusion"])) == len(p["validation"])
        state = publish(store, store.state, value)
        saved = load(store, state["results"][-1])
        assert saved["metrics"] == value["metrics"]
        if task == "classification":
            result = predict(saved, r)
            assert result["fit"] is False and len(result["predictions"]) == 32
            assert {p["row_id"] for p in result["predictions"]} == set(groups)
        assert before == {p.name: p.read_bytes() for p in folder.iterdir()}


def test_fold_poison_isolation_and_overlap_same_component(tmp_path):
    store, r, work, _ = fixture(tmp_path)
    with closing(store):
        first = calculate(r, AudioSpec(task="classification").data(), work)
        # The persisted table is immutable; create a separate captured request copy solely for test poison.
        import polars as pl

        frame = pl.read_parquet(r["path"])
        held = set(
            first["plan"]["membership"]["validation"]
            + first["plan"]["membership"]["test"]
        )
        values = []
        for row in frame.iter_rows(named=True):
            m = json.loads(row["metadata"])
            if row["__vu_row_id"] in held:
                m["label"] = "high" if m["label"] == "low" else "low"
            values.append(json.dumps(m))
        poisoned = work / "poison.parquet"
        frame.with_columns(pl.Series("metadata", values)).write_parquet(poisoned)
        request = dict(
            r, path=str(poisoned), fingerprint=hash_artifact(poisoned, Control())
        )
        after = calculate(request, AudioSpec(task="classification").data(), work)
        assert first["model_weights"] == after["model_weights"]
        for recording_id in {s["recording_id"] for s in first["segments"]}:
            assert (
                len(
                    {
                        s["leakage_component"]
                        for s in first["segments"]
                        if s["recording_id"] == recording_id
                    }
                )
                == 1
            )


def test_controlled_bad_audio_segments_channel_and_model_unavailable(tmp_path):
    with pytest.raises(ProjectError):
        decode(b"broken private speech")
    raw = io.BytesIO()
    sf.write(raw, np.zeros(16), 16000, format="WAV", subtype="FLOAT")
    with pytest.raises(ProjectError):
        decode(b"")
    with pytest.raises(ProjectError):
        features(np.zeros(16), 16000, AudioSpec())
    with pytest.raises(ProjectError, match="unavailable"):
        local_model(str(tmp_path / "missing-model"), "tr")
    with pytest.raises(ProjectError, match="unavailable"):
        AudioSpec.from_dict(dict(task="transcribe"))
    store, r, work, _ = fixture(tmp_path)
    with closing(store):
        with pytest.raises(ProjectError, match="kanal"):
            calculate(r, AudioSpec(channel=1).data(), work)
        with pytest.raises(ProjectError, match="insan"):
            frame = __import__("polars").read_parquet(r["path"])
            modified = [
                json.dumps(dict(json.loads(m), label_status="model"))
                for m in frame["metadata"]
            ]
            path = work / "model-labels.parquet"
            frame.with_columns(
                __import__("polars").Series("metadata", modified)
            ).write_parquet(path)
            calculate(
                dict(r, path=str(path), fingerprint=hash_artifact(path, Control())),
                AudioSpec(task="classification").data(),
                work,
            )


def test_wer_cer_true_reference_and_no_invented_empty_score():
    assert errors("merhaba dünya", "merhaba")["wer"] == 0.5
    assert errors("abc", "adc")["cer"] == pytest.approx(1 / 3)
    assert errors("", "anything")["wer"] is None
    assert errors("a", "a a a")["wer"] == 2


def test_backend_output_fields_are_conditional_and_source_time_preserved():
    from veri_ufku.modeling.audio_speech import output

    # Adapter contract fixture; not a real Vosk recognition/model accuracy claim.
    a = output([dict(text="merhaba", result=[dict(word="merhaba")])], 10, 1, {})
    assert "start_seconds" not in a["words"][0] and "confidence" not in a["words"][0]
    b = output(
        [
            dict(
                text="merhaba",
                result=[dict(word="merhaba", start=0.1, end=0.5, conf=0.8)],
            )
        ],
        10,
        1,
        {},
    )
    assert (
        b["words"][0]["start_seconds"] == 10.1 and b["words"][0]["end_seconds"] == 10.5
    )
    assert b["confidence"] is None and b["words"][0]["confidence"] == 0.8
    with pytest.raises(ProjectError):
        output([dict(result=[dict(word="bad", start=0, end=2)])], 10, 1, {})


def test_single_wav_offline_snapshot_reopen_and_tamper(tmp_path, monkeypatch):
    import socket

    source = tmp_path / "single.wav"
    sf.write(
        source,
        0.2 * np.sin(2 * np.pi * 1000 * np.arange(16000) / 16000),
        16000,
        subtype="PCM_16",
    )
    work = tmp_path / "work"
    work.mkdir()
    c = Control()
    snapshot = unpack(capture_source(source, work, c), work, c)
    assert detect(snapshot) == "audio_dataset"
    result = get_adapter("audio_dataset").import_data(
        snapshot, StructuredSettings(adapter_id="audio_dataset"), work, c
    )
    with closing(ProjectStore.create(tmp_path / "project")) as store:
        store.publish_import(result)
        d = store.state["datasets"][-1]
        s = store.state["sources"][-1]
        assert s["copy_uri"]
        source.rename(tmp_path / "not-original.wav")

        def denied(*args, **kwargs):
            raise AssertionError("Offline audio path made a network request")

        monkeypatch.setattr(socket, "socket", denied)
        r = dict(
            path=str(store.path(d["snapshot_uri"])),
            fingerprint=hash_artifact(store.path(d["snapshot_uri"]), c),
            columns=d["import_metadata"]["columns"],
            row_count=1,
            version_id=d["version_id"],
            origin_version=d["version_id"],
            source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
            snapshot_uri=d["snapshot_uri"],
            config_revision=0,
            run_id="run:singleaudio",
            prior_test_use_ids=[],
            audio_bundle=str(store.path(s["copy_uri"])),
            audio_fingerprint=s["fingerprint"],
            audio_column=next(
                x["id"]
                for x in d["import_metadata"]["columns"]
                if x["name"] == "member"
            ),
        )
        value = calculate(r, AudioSpec().data(), work)
        assert (
            value["status"] == "completed"
            and value["segments"][0]["duration_seconds"] == 1
        )
        state = publish(store, store.state, value)
        record = state["results"][-1]
        assert (
            load(store, record)["segments"][0]["source_record_id"]
            == value["segments"][0]["source_record_id"]
        )
        artifact = store.path(record["neural"]["details_uri"])
        artifact.chmod(0o600)
        artifact.write_bytes(b"{}")
        with pytest.raises(ProjectError, match="hash"):
            load(store, record)
