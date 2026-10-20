"""Optional explicit local Vosk; no model download, no code import, no audio logging."""

import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np

from veri_ufku.importers.images import json_data
from veri_ufku.storage.project_model import ProjectError


def local_model(folder, language):
    try:
        if importlib.metadata.version("vosk") != "0.3.45":
            raise ProjectError(
                "Vosk sürümü doğrulanmış adapterle uyuşmuyor: unavailable."
            )
    except importlib.metadata.PackageNotFoundError:
        raise ProjectError(
            "Optional yerel Vosk backend yok: unavailable; otomatik install/download yok."
        ) from None
    root = Path(folder)
    metadata = root / "audio-model.json"
    if (
        not root.is_dir()
        or root.is_symlink()
        or not metadata.is_file()
        or metadata.is_symlink()
    ):
        raise ProjectError(
            "Yerel speech model/audio-model.json yok: unavailable; internet gerekmez."
        )
    m = json_data(metadata.read_bytes())
    if (
        not isinstance(m, dict)
        or set(m) != {"schema", "language", "license", "training_dataset", "files"}
        or m["schema"] != "LocalVosk/v1"
        or m["language"] != language
        or any(
            not isinstance(m[k], str) or not 1 <= len(m[k]) <= 1000
            for k in ("language", "license", "training_dataset")
        )
        or not isinstance(m["files"], dict)
        or not 1 <= len(m["files"]) <= 128
    ):
        raise ProjectError(
            "STT dil/lisans/dataset/hash beyanı uyumsuz; model adı kalite garantisi değildir."
        )
    files = [p for p in root.rglob("*") if p.is_file() and p.name != "audio-model.json"]
    if (
        any(p.is_symlink() for p in root.rglob("*"))
        or {p.relative_to(root).as_posix() for p in files} != set(m["files"])
        or sum(p.stat().st_size for p in files) > 512 * 1024**2
    ):
        raise ProjectError("Speech model safe file/hash/512MiB sınırı.")
    for p in files:
        if (
            hashlib.sha256(p.read_bytes()).hexdigest()
            != m["files"][p.relative_to(root).as_posix()]
        ):
            raise ProjectError("Speech model file hash değişti.")
    for name in ("am/final.mdl", "conf/model.conf"):
        if name not in m["files"]:
            raise ProjectError("Yerel Vosk model eksik: unavailable.")
    return root, m


def transcribe(y, rate, spec, control, origin):
    root, m = local_model(spec.stt_folder, spec.language)
    if rate != 16000:
        raise ProjectError(
            "Bu STT adapteri açık16kHz resampling ister; içerik rate'i yeniden etiketlenmez."
        )
    if np.max(np.abs(y)) > 1:
        raise ProjectError(
            "STT PCM16 dönüşümü için full-scale dışı ses; sessiz clip yok."
        )
    from vosk import KaldiRecognizer, Model, SetLogLevel

    SetLogLevel(-1)
    model = Model(model_path=str(root))
    rec = KaldiRecognizer(model, rate)
    rec.SetWords(True)
    pcm = np.rint(y * 32767).astype("<i2").tobytes()
    results = []
    for i in range(0, len(pcm), 8000):
        control.check()
        if rec.AcceptWaveform(pcm[i : i + 8000]):
            results.append(json.loads(rec.Result()))
    results.append(json.loads(rec.FinalResult()))
    return output(results, origin, len(y) / rate, m)


def output(results, origin, duration, metadata):
    if (
        not isinstance(results, list)
        or len(results) > 1024
        or any(
            not isinstance(r, dict) or not isinstance(r.get("text", ""), str)
            for r in results
        )
    ):
        raise ProjectError("Speech backend response şeması geçersiz.")
    text = " ".join(r.get("text", "") for r in results).strip()
    if len(text) > 8000:
        raise ProjectError("Speech transcript8000 karakter sınırı.")
    words = []
    for r in results:
        for word in r.get("result", []):
            if not isinstance(word, dict) or not isinstance(word.get("word"), str):
                raise ProjectError("Speech word şeması geçersiz.")
            v = dict(word=word["word"])
            if "start" in word and "end" in word:
                if (
                    any(
                        type(word[k]) not in (int, float) or not np.isfinite(word[k])
                        for k in ("start", "end")
                    )
                    or not 0 <= word["start"] <= word["end"] <= duration + 0.001
                ):
                    raise ProjectError(
                        "Backend timestamp seçili segment sınırında değil."
                    )
                v.update(
                    start_seconds=origin + word["start"],
                    end_seconds=origin + word["end"],
                )
            if "conf" in word:
                if type(word["conf"]) not in (int, float) or not 0 <= word["conf"] <= 1:
                    raise ProjectError("Backend confidence şeması geçersiz.")
                v["confidence"] = word["conf"]
            words.append(v)
            if len(words) > 4096:
                raise ProjectError("Speech word4096 bütçesi.")
    return dict(
        text=text,
        words=words,
        confidence=None,
        backend="vosk0.3.45",
        model_metadata=metadata,
        scope="local transcription, no diarization/event detection; backend word confidence not calibrated correctness",
    )


def edit_distance(a, b):
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(
                min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (x != y))
            )
        previous = current
    return previous[-1]


def errors(reference, hypothesis):
    if not reference.strip():
        return dict(
            wer=None,
            cer=None,
            reason="Empty reference denominator; no quality score invented",
        )
    words = reference.split()
    return dict(
        wer=edit_distance(words, hypothesis.split()) / len(words),
        cer=edit_distance(reference, hypothesis) / len(reference),
        normalization="Exact case/punctuation/Unicode; whitespace split for WER; all characters incl spaces for CER; no silent correction",
    )
