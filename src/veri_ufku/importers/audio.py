"""Bounded immutable WAV/FLAC recordings, explicit segments and leakage components."""

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import polars as pl

from veri_ufku.importers.delimited import Control
from veri_ufku.importers.images import ImageAdapter, json_data
from veri_ufku.importers.sources import safe_member
from veri_ufku.packaging.optional import LazyModule
from veri_ufku.storage.project_model import ProjectError

sf = LazyModule("soundfile", "audio")

SUFFIXES = {".wav", ".flac"}


def decode(raw):
    if not 1 <= len(raw) <= 16 * 1024**2:
        raise ProjectError("Ses dosyası16MiB sınırı.")
    try:
        with sf.SoundFile(io.BytesIO(raw)) as f:
            if (
                f.format not in ("WAV", "FLAC")
                or f.subtype not in ("PCM_16", "PCM_24", "PCM_32", "FLOAT")
                or f.channels not in (1, 2)
                or not 8000 <= f.samplerate <= 96000
                or not 1 <= f.frames <= 2_000_000
                or f.frames / f.samplerate > 60
            ):
                raise ProjectError(
                    "WAV/FLAC PCM16/24/32 veya WAV float;1–2kanal,8–96kHz,60s/2Mframe/16MiB sınırı."
                )
            y = f.read(dtype="float64", always_2d=True)
            if len(y) != f.frames or not np.isfinite(y).all():
                raise ProjectError("Ses truncated/nonfinite; kaynak düzeltilmez.")
            rate, channels, subtype, fmt = f.samplerate, f.channels, f.subtype, f.format
        return y, dict(
            sample_rate=rate,
            channels=channels,
            frames=len(y),
            duration_seconds=len(y) / rate,
            format=fmt,
            subtype=subtype,
            amplitude_reference="digital full-scale1; PCM decoded without peak normalization",
            decoded_sha256=hashlib.sha256(str(rate).encode() + y.tobytes()).hexdigest(),
        )
    except ProjectError:
        raise
    except (sf.SoundFileError, ValueError, OSError):
        raise ProjectError(
            "Ses decode başarısız; dosya/konuşma loglanmadı, kaynak korunur."
        ) from None


def groups(rows):
    parents = list(range(len(rows)))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for i, a in enumerate(rows):
        for j, b in enumerate(rows[:i]):
            if any(
                a[k] and a[k] == b[k]
                for k in (
                    "recording_id",
                    "source_recording",
                    "speaker",
                    "session",
                    "decoded_sha256",
                )
            ):
                parents[root(i)] = root(j)
    for i, row in enumerate(rows):
        row["leakage_component"] = "audio-group:" + str(root(i))


def scan(snapshot, control=None):
    control = control or Control()
    members = {m["name"]: m["path"] for m in snapshot.get("members", [])}
    if not members:
        members = {Path(snapshot["original"]).name: snapshot["path"]}
    if "audio.json" in members:
        manifest = json_data(Path(members["audio.json"]).read_bytes())
        if (
            not isinstance(manifest, dict)
            or set(manifest) != {"schema", "classes", "recordings"}
            or manifest["schema"] != "AudioManifest/v1"
        ):
            raise ProjectError("audio.json AudioManifest/v1 classes/recordings ister.")
        entries, classes = manifest["recordings"], manifest["classes"]
    else:
        entries = [
            dict(
                id=n,
                file=n,
                label=Path(n).parts[0] if len(Path(n).parts) > 1 else "",
                label_status="proposed",
            )
            for n in sorted(members)
        ]
        classes = sorted({r["label"] for r in entries if r["label"]})
    if (
        not isinstance(entries, list)
        or not 1 <= len(entries) <= 64
        or not isinstance(classes, list)
        or len(classes) > 16
        or any(not isinstance(c, str) or not 1 <= len(c) <= 100 for c in classes)
        or len(set(classes)) != len(classes)
    ):
        raise ProjectError("Audio schema64recording/16classes sınırı.")
    rows, ids, files = [], set(), set()
    for entry in entries:
        control.check()
        if not isinstance(entry, dict) or set(entry) - {
            "id",
            "file",
            "label",
            "label_status",
            "speaker",
            "session",
            "source_recording",
            "segments",
            "reference",
            "reference_status",
        }:
            raise ProjectError("Recording schema alanı geçersiz.")
        for key in (
            "id",
            "file",
            "label",
            "speaker",
            "session",
            "source_recording",
            "reference",
            "label_status",
            "reference_status",
        ):
            if not isinstance(entry.get(key, ""), str) or len(entry.get(key, "")) > (
                8000 if key == "reference" else 200
            ):
                raise ProjectError("Audio kimlik/etiket/referans metin sınırı.")
        rid, name = entry.get("id", ""), entry.get("file", "")
        safe_member(name)
        if (
            not rid
            or rid in ids
            or name in files
            or name not in members
            or Path(name).suffix.lower() not in SUFFIXES
        ):
            raise ProjectError("Recording/file eşlemesi unique ve WAV/FLAC olmalı.")
        label = entry.get("label", "")
        status = entry.get("label_status", "proposed")
        if (
            label
            and label not in classes
            or status not in ("human", "proposed", "model")
            or entry.get("reference_status", "proposed")
            not in ("human", "proposed", "model")
        ):
            raise ProjectError("İnsan/model etiketi ve referans şeması geçersiz.")
        ids.add(rid)
        files.add(name)
        raw = Path(members[name]).read_bytes()
        y, info = decode(raw)
        segments = entry.get(
            "segments", [dict(id="whole", start_frame=0, end_frame=len(y))]
        )
        if not isinstance(segments, list) or not 1 <= len(segments) <= 32:
            raise ProjectError("Recording1..32 açık segment ister.")
        seen = set()
        for segment in segments:
            if (
                not isinstance(segment, dict)
                or set(segment) != {"id", "start_frame", "end_frame"}
                or not isinstance(segment["id"], str)
                or not 1 <= len(segment["id"]) <= 100
                or segment["id"] in seen
                or type(segment["start_frame"]) is not int
                or type(segment["end_frame"]) is not int
                or not 0 <= segment["start_frame"] < segment["end_frame"] <= len(y)
            ):
                raise ProjectError(
                    "Segment unique id ve bounded half-open kaynak frame aralığı ister."
                )
            seen.add(segment["id"])
            rows.append(
                dict(
                    recording_id=rid,
                    member=name,
                    segment_id=rid + ":" + segment["id"],
                    start_frame=segment["start_frame"],
                    end_frame=segment["end_frame"],
                    sha256=hashlib.sha256(raw).hexdigest(),
                    label=label,
                    label_status=status,
                    speaker=entry.get("speaker", ""),
                    session=entry.get("session", ""),
                    source_recording=entry.get("source_recording", rid),
                    reference=entry.get("reference", ""),
                    reference_status=entry.get("reference_status", "proposed"),
                    reference_scope="whole_recording",
                    **info,
                )
            )
            if len(rows) > 256:
                raise ProjectError("256segment sınırı.")
    groups(rows)
    return dict(
        schema="AudioCatalog/v1",
        classes=classes,
        segments=rows,
        near_policy="All segments of source recording, equal decoded PCM, declared speaker/session remain one split component. Unknown speaker identity cannot be inferred.",
    )


class AudioAdapter(ImageAdapter):
    adapter_id = "audio_dataset"
    record_id_column = "segment_id"
    locator_prefix = "audio:"

    def inspect(self, snapshot, settings, control):
        c = scan(snapshot, control)
        return dict(
            formula_behavior=f"{len(c['segments'])} segment; {c['near_policy']}; ses kopyası daima proje içinde. Mikrofon/diarization/event detection yok."
        )

    def frame(self, snapshot, control):
        c = scan(snapshot, control)
        return pl.DataFrame(
            [
                dict(
                    recording_id=r["recording_id"],
                    member=r["member"],
                    segment_id=r["segment_id"],
                    label=r["label"] or None,
                    leakage_component=r["leakage_component"],
                    metadata=json.dumps(r, ensure_ascii=False),
                )
                for r in c["segments"]
            ]
        ), c

    def preview(self, snapshot, settings, control=None):
        control = control or Control()
        f, c = self.frame(snapshot, control)
        return dict(
            schema=dict(
                names=f.columns,
                original_headers=f.columns,
                types=[str(t) for t in f.dtypes],
                warnings=[
                    c["near_policy"],
                    "Folder class labels proposed; human label required before fit",
                ],
            ),
            rows=[
                [str(v) if v is not None else "∅" for v in row]
                for row in f.head(20).iter_rows()
            ],
            bad=[],
            examined=f.height,
            limited=False,
            suggestions=[str(t) for t in f.dtypes],
            settings=settings.data(),
            capture=snapshot,
            diagnostics=dict(scope="full", format_metadata=c),
            importable=True,
        )
