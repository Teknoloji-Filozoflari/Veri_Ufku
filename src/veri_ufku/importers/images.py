"""Bounded local image snapshots; explicit annotation schema and duplicate components."""

import hashlib
import io
import json
import warnings
from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
from PIL import Image, ImageOps, UnidentifiedImageError

from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.importers.native import describe
from veri_ufku.importers.sources import safe_member, verify_sources
from veri_ufku.storage.project_model import ProjectError, uid

SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_PIXELS = 4_000_000
MAX_IMAGES = 256


def json_data(raw):
    if len(raw) > 2 * 1024**2:
        raise ProjectError("Görüntü manifesti2MiB sınırını aşıyor.")

    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError()
            out[k] = v
        return out

    try:
        return json.loads(
            raw,
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (ValueError, UnicodeError, RecursionError):
        raise ProjectError("Görüntü manifest JSON geçersiz.") from None


def decode(raw):
    if not 1 <= len(raw) <= 16 * 1024**2:
        raise ProjectError("Görüntü dosyası16MiB sınırında olmalı.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as im:
                if (
                    im.width * im.height > MAX_PIXELS
                    or getattr(im, "n_frames", 1) != 1
                    or im.format not in ("PNG", "JPEG", "WEBP")
                    or im.mode not in ("RGB", "L")
                ):
                    raise ProjectError(
                        "Görüntü pixel/kanal/format sınırı:4M pixel, tek frame RGB/L PNG/JPEG/WebP; alpha/CMYK sessiz dönüştürülmez."
                    )
                size, mode = list(im.size), im.mode
                im.verify()
            with Image.open(io.BytesIO(raw)) as im:
                orientation = int(im.getexif().get(274, 1))
                if not 1 <= orientation <= 8:
                    raise ProjectError("EXIF orientation geçersiz.")
                oriented = ImageOps.exif_transpose(im)
                pixels = np.asarray(oriented.convert("RGB"), dtype=np.uint8).copy()
        return pixels, dict(
            original_size=size,
            size=[pixels.shape[1], pixels.shape[0]],
            channels=1 if mode == "L" else 3,
            mode=mode,
            orientation=orientation,
            decoded_sha256=hashlib.sha256(pixels.tobytes()).hexdigest(),
        )
    except ProjectError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise ProjectError(
            "Görüntü bozuk veya güvenli decode sınırını aşıyor; kaynak değiştirilmedi."
        ) from None


def decode_mask(raw, size, mask_labels):
    if not 1 <= len(raw) <= 16 * 1024**2:
        raise ProjectError("Mask dosyası16MiB sınırı.")
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if (
                im.format != "PNG"
                or im.mode != "L"
                or list(im.size) != size
                or im.width * im.height > MAX_PIXELS
                or getattr(im, "n_frames", 1) != 1
            ):
                raise ProjectError(
                    "Mask oriented boyutla eşleşen tek-frame uint8 L PNG olmalı."
                )
            im.verify()
        with Image.open(io.BytesIO(raw)) as im:
            values = np.asarray(im, dtype=np.uint8).copy()
        if values.max() >= len(mask_labels):
            raise ProjectError("Mask class index schema dışında.")
        return values
    except ProjectError:
        raise
    except (OSError, ValueError, UnidentifiedImageError):
        raise ProjectError("Mask bozuk; kaynak değiştirilmedi.") from None


def signature(pixels):
    small = np.asarray(
        Image.fromarray(pixels).resize((9, 8), Image.Resampling.BILINEAR), dtype=float
    )
    gray = small.mean(2)
    return dict(
        dhash=[int(v) for v in (gray[:, 1:] > gray[:, :-1]).ravel()],
        color=pixels.mean(axis=(0, 1)).tolist(),
    )


def near(a, b):
    return a["decoded_sha256"] == b["decoded_sha256"] or (
        sum(
            x != y
            for x, y in zip(
                a["signature"]["dhash"], b["signature"]["dhash"], strict=True
            )
        )
        <= 4
        and np.linalg.norm(
            np.asarray(a["signature"]["color"]) - b["signature"]["color"]
        )
        <= 8
    )


def components(records):
    parent = list(range(len(records)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    pairs = []
    for i, a in enumerate(records):
        for j in range(i):
            b = records[j]
            duplicate = near(a, b)
            grouped = any(
                a.get(k) and a[k] == b.get(k)
                for k in ("group", "subject", "video_source")
            )
            if duplicate or grouped:
                parent[root(i)] = root(j)
            if duplicate:
                pairs.append(
                    dict(
                        left=a["image_id"],
                        right=b["image_id"],
                        exact=a["decoded_sha256"] == b["decoded_sha256"],
                    )
                )
    for i, r in enumerate(records):
        r["leakage_component"] = "image-group:" + str(root(i))
    return pairs


def annotation(value, size, classes, mask_labels):
    if not isinstance(value, dict) or set(value) - {
        "label",
        "boxes",
        "mask",
        "status",
        "reviewer",
        "reviewed_at",
    }:
        raise ProjectError(
            "Annotation şeması: label/boxes/mask/status/reviewer/reviewed_at."
        )
    a = dict(
        label=value.get("label", ""),
        boxes=value.get("boxes", []),
        mask=value.get("mask", ""),
        status=value.get("status", "proposed"),
        reviewer=value.get("reviewer", ""),
        reviewed_at=value.get("reviewed_at", ""),
    )
    if (
        a["status"] not in ("human", "proposed", "model")
        or any(
            not isinstance(a[k], str) or len(a[k]) > 1000
            for k in ("label", "mask", "reviewer", "reviewed_at")
        )
        or a["label"]
        and a["label"] not in classes
        or a["status"] == "human"
        and not a["reviewer"].strip()
    ):
        raise ProjectError(
            "İnsan/model önerisi ayrımı, sınıf şeması ve reviewer gerekli."
        )
    if not isinstance(a["boxes"], list) or len(a["boxes"]) > 50:
        raise ProjectError("BBox sayısı en fazla50.")
    ids = set()
    for b in a["boxes"]:
        if (
            not isinstance(b, dict)
            or set(b) != {"id", "label", "xyxy"}
            or not isinstance(b["id"], str)
            or not b["id"]
            or b["id"] in ids
            or b["label"] not in mask_labels[1:]
            or not isinstance(b["xyxy"], list)
            or len(b["xyxy"]) != 4
        ):
            raise ProjectError(
                "BBox: unique id/label/half-open XYXY, oriented pixel koordinatları."
            )
        ids.add(b["id"])
        x1, y1, x2, y2 = b["xyxy"]
        if any(
            type(v) not in (int, float) or not np.isfinite(v) for v in b["xyxy"]
        ) or not (0 <= x1 < x2 <= size[0] and 0 <= y1 < y2 <= size[1]):
            raise ProjectError("BBox boyutu/koordinatı geçersiz; otomatik onarım yok.")
    if a["mask"]:
        safe_member(a["mask"])
    return a


def scan(snapshot, control=None):
    control = control or Control()
    members = {m["name"]: m for m in snapshot.get("members", [])}
    if not members:
        raise ProjectError(
            "Görüntü klasörü veya images.json içeren captured bundle seçin."
        )
    if "images.json" in members:
        manifest = json_data(Path(members["images.json"]["path"]).read_bytes())
        if (
            not isinstance(manifest, dict)
            or set(manifest) != {"schema", "classes", "mask_labels", "images"}
            or manifest["schema"] != "VisionManifest/v1"
        ):
            raise ProjectError(
                "images.json VisionManifest/v1 classes/mask_labels/images ister."
            )
        rows, classes, mask_labels = (
            manifest["images"],
            manifest["classes"],
            manifest["mask_labels"],
        )
    else:
        rows = [
            dict(
                id=n,
                file=n,
                annotation=dict(
                    label=Path(n).parts[0] if len(Path(n).parts) > 1 else "",
                    status="proposed",
                ),
            )
            for n in sorted(members)
            if Path(n).suffix.lower() in SUFFIXES
        ]
        classes = sorted(
            {r["annotation"]["label"] for r in rows if r["annotation"]["label"]}
        )
        mask_labels = ["background", "object"]
    if (
        not isinstance(rows, list)
        or not 1 <= len(rows) <= MAX_IMAGES
        or any(
            not isinstance(v, list)
            or len(v) > 16
            or any(not isinstance(x, str) or not 1 <= len(x) <= 100 for x in v)
            or len(set(v)) != len(v)
            for v in (classes, mask_labels)
        )
        or not mask_labels
        or mask_labels[0] != "background"
    ):
        raise ProjectError("Görüntü256/sınıf16/schema sınırı; mask0 background olmalı.")
    records, ids, filenames = [], set(), set()
    for item in rows:
        control.check()
        if (
            not isinstance(item, dict)
            or set(item)
            - {
                "id",
                "file",
                "annotation",
                "group",
                "subject",
                "video_source",
                "sequence",
                "frame_index",
                "time_seconds",
            }
            or not isinstance(item.get("id"), str)
            or not 1 <= len(item["id"]) <= 200
            or item["id"] in ids
        ):
            raise ProjectError("Manifest görüntü kimliği unique/metin olmalı.")
        name = item.get("file", "")
        safe_member(name)
        if name not in members or name in filenames:
            raise ProjectError(
                "Görüntü/etiket eşlemesi eksik veya aynı dosya iki kayıtla sayılıyor."
            )
        ids.add(item["id"])
        filenames.add(name)
        raw = Path(members[name]["path"]).read_bytes()
        pixels, info = decode(raw)
        a = annotation(item.get("annotation", {}), info["size"], classes, mask_labels)
        if a["mask"]:
            if a["mask"] not in members:
                raise ProjectError("Mask dosyası bulunamadı.")
            decode_mask(
                Path(members[a["mask"]]["path"]).read_bytes(), info["size"], mask_labels
            )
        frame = {
            k: item.get(k, "") for k in ("group", "subject", "video_source", "sequence")
        }
        if any(not isinstance(v, str) or len(v) > 200 for v in frame.values()):
            raise ProjectError("Group/subject/video/sequence kimlikleri metin olmalı.")
        index, seconds = item.get("frame_index", -1), item.get("time_seconds", -1.0)
        if (
            type(index) is not int
            or index < -1
            or type(seconds) not in (int, float)
            or not np.isfinite(seconds)
            or seconds < -1
            or frame["video_source"]
            and (not frame["sequence"] or index < 0 or seconds < 0)
        ):
            raise ProjectError(
                "Extracted video frame kaynak/sequence/index/time kimliği gerekli; video decoder değil."
            )
        records.append(
            dict(
                image_id=item["id"],
                member=name,
                sha256=hashlib.sha256(raw).hexdigest(),
                **info,
                signature=signature(pixels),
                annotation=a,
                **frame,
                frame_index=index,
                time_seconds=float(seconds),
            )
        )
        control.progress(
            "Görüntü güvenli decode/etiket eşlemesi", len(records), len(rows)
        )
    video_ids = [
        (r["video_source"], r["sequence"], r["frame_index"])
        for r in records
        if r["video_source"]
    ]
    if len(set(video_ids)) != len(video_ids):
        raise ProjectError("Video frame sequence/index yineleniyor.")
    pairs = components(records)
    return dict(
        schema="VisionCatalog/v1",
        classes=classes,
        mask_labels=mask_labels,
        images=records,
        duplicates=pairs,
        near_policy="RGB mean distance≤8 and dHash Hamming≤4; conservative grouping, not exhaustive semantic duplicate detection",
        annotation_coordinates="EXIF-oriented XYXY half-open pixels; masks already oriented; no silent repair",
        video_scope="pre-extracted frames only; no video decoding/full-video analysis",
    )


class ImageAdapter:
    record_id_column = "image_id"
    locator_prefix = "image:"
    adapter_id = "image_dataset"

    def validate_source(self, request, control=None):
        if request.adapter_id != self.adapter_id or not request.path.is_file():
            raise ProjectError("Görüntü captured bundle bulunamadı.")

    def inspect(self, snapshot, settings, control):
        catalog = scan(snapshot, control)
        return dict(
            formula_behavior=f"{len(catalog['images'])} görüntü; {len(catalog['duplicates'])} exact/near çift. {catalog['annotation_coordinates']}; bozuk/aşırı büyük resimde durur. Görüntüler daima immutable kopyaya alınır."
        )

    def frame(self, snapshot, control):
        catalog = scan(snapshot, control)
        rows = [
            dict(
                image_id=r["image_id"],
                member=r["member"],
                label=r["annotation"]["label"] or None,
                leakage_component=r["leakage_component"],
                metadata=json.dumps(r, ensure_ascii=False),
            )
            for r in catalog["images"]
        ]
        return pl.DataFrame(rows), catalog

    def preview(self, snapshot, settings, control=None):
        control = control or Control()
        f, catalog = self.frame(snapshot, control)
        return dict(
            schema=dict(
                names=f.columns,
                original_headers=f.columns,
                types=[str(t) for t in f.dtypes],
                warnings=[
                    catalog["near_policy"],
                    "Folder labels proposed; human review is required before fit.",
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
            diagnostics=dict(scope="full", format_metadata=catalog),
            importable=True,
        )

    def import_data(self, snapshot, settings, workspace, control):
        f, catalog = self.frame(snapshot, control)
        schema = f.schema
        names = f.columns
        f = (
            f.with_row_index("__vu_start_line", offset=1)
            .with_columns(pl.col("__vu_start_line").cast(pl.Int64))
            .with_columns(
                pl.Series("__vu_row_id", ["row:" + uid() for _ in range(f.height)]),
                pl.Series(
                    "__vu_source_record_id", ["sr:" + uid() for _ in range(f.height)]
                ),
                pl.col("__vu_start_line").alias("__vu_end_line"),
                pl.concat_str(
                    pl.lit(self.locator_prefix), pl.col(self.record_id_column)
                ).alias("__vu_source_locator"),
                pl.lit([], dtype=pl.List(pl.String)).alias("__vu_missing_fields"),
                pl.lit("{}").alias("__vu_expansion_index"),
            )
        )
        output = Path(workspace) / (uid() + ".dataset.parquet")
        f.write_parquet(output)
        saved = replace(
            settings,
            native_schema={n: describe(t) for n, t in f.schema.items()},
            format_metadata=catalog,
        )
        verify_sources(snapshot, control)
        control.disk(workspace, force=True)
        return dict(
            path=str(output),
            quarantine=None,
            artifact_fingerprint=hash_artifact(output, control),
            quarantine_fingerprint=None,
            schema=dict(
                names=names,
                original_headers=names,
                types=[str(schema[n]) for n in names],
                warnings=[
                    catalog["near_policy"],
                    "Images copied immutably; human annotations distinguished from model/proposed.",
                ],
            ),
            accepted=f.height,
            bad_count=0,
            examined=f.height,
            source_snapshot_id="snapshot:" + uid(),
            settings=saved.data(),
            capture=snapshot,
            adapter_id=self.adapter_id,
            diagnostics=dict(
                scope="full",
                source_records=f.height,
                output_rows=f.height,
                format_metadata=catalog,
            ),
            backend="Pillow12.3.0/read-only image manifest",
        )
