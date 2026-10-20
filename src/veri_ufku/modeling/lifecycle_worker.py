"""Disposable safe package parsing and inference; no project writes."""

import os
import shutil
import tempfile
from pathlib import Path

import polars as pl

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Progress
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import file_hash


def publish_file(source, destination, control):
    """No overwrite even in a race. Temporary sibling and link are on same filesystem."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ProjectError("Çıktı zaten var; üzerine yazılmaz. Yeni isim seçin.")
    if not destination.parent.is_dir():
        raise ProjectError("Çıktı klasörü mevcut olmalı.")
    with tempfile.TemporaryDirectory(
        prefix=".vu-model-", dir=destination.parent
    ) as tmp:
        staged = Path(tmp) / "output"
        shutil.copyfile(source, staged)
        with open(staged, "rb") as f:
            os.fsync(f.fileno())
        control.check()
        os.link(staged, destination)
        descriptor = os.open(destination.parent, os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return str(destination)


def calculate(request, action, workspace, control):
    from veri_ufku.modeling.lifecycle import (
        MAX_BYTES,
        load_package,
        predict,
        preview,
        raw_json,
        sha,
    )

    if action == "explain-export":
        import json

        from veri_ufku.modeling.explanation import redacted_export

        path = Path(workspace) / "explanation.json"
        path.write_text(
            json.dumps(
                redacted_export(request["explanation"]),
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
            )
        )
        return dict(
            card=request["explanation"]["card"],
            output=publish_file(path, request["destination"], control),
        )

    # Validate and use the same bounded bytes, including when exporting a package.
    # An external file can change after the dialog/open or while it is read.
    with open(request["package"], "rb") as source_package:
        raw = source_package.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ProjectError("Model paketi 128MiB sınırını aşıyor.")
    fingerprint = dict(size=len(raw), sha256=sha(raw))
    if (
        request.get("package_fingerprint")
        and fingerprint != request["package_fingerprint"]
    ):
        raise ProjectError("Model paketi değişmiş; yeniden açın.")
    package_snapshot = Path(workspace) / "input.vumodel"
    package_snapshot.write_bytes(raw)
    model, card = load_package(package_snapshot)
    if request.get("expected_card") is not None and request["expected_card"] != card:
        raise ProjectError("Kayıtlı model kartı paket kartıyla uyuşmuyor.")
    if action == "open":
        return dict(card=card, package_fingerprint=fingerprint)
    if action == "save":
        return dict(
            card=card,
            output=publish_file(package_snapshot, request["destination"], control),
        )
    if action == "explain":
        from veri_ufku.modeling.explanation import calculate as explain

        source = request["source"]
        background = request["background"]
        if (
            source["row_count"] > 5000
            or background.get("row_count", source["row_count"]) > 5000
        ):
            raise ProjectError(
                "Explanation source preflight5000rows; açık dataset daraltması gerekli."
            )
        checked(source, control)
        checked(background, control)
        result = explain(
            model,
            card,
            pl.read_parquet(source["path"]),
            pl.read_parquet(background["path"]),
            source,
            background,
            request["explain_spec"],
            control,
            fingerprint,
        )
        checked(source, control)
        checked(background, control)
        if file_hash(Path(request["package"])) != fingerprint:
            raise ProjectError("Açıklama sırasında model paketi değişti.")
        return dict(card=card, explanation=result, package_fingerprint=fingerprint)
    source = request["source"]
    checked(source, control)
    frame = pl.read_parquet(source["path"])
    report = preview(
        model,
        card,
        frame,
        source["columns"],
        request["mapping"],
        source.get("semantic_metadata"),
        control,
    )
    token = sha(
        raw_json(
            dict(
                package=fingerprint,
                source=source["fingerprint"],
                version=source["version_id"],
                preview=report,
                invalid=request["invalid"],
                batch=request["batch_size"],
            )
        )
    )
    if action == "preview":
        return dict(card=card, preview=report, token=token)
    if action != "predict" or token != request.get("preview_token"):
        raise ProjectError(
            "Güncel önizleme gerekli; veri/model/eşleme/politika değişmiş."
        )
    result, details = predict(
        model,
        card,
        frame,
        source["columns"],
        request["mapping"],
        source.get("semantic_metadata"),
        request["invalid"],
        request["batch_size"],
        control,
    )
    path = Path(workspace) / "prediction.parquet"
    result.write_parquet(path)
    checked(source, control)
    if file_hash(Path(request["package"])) != fingerprint:
        raise ProjectError("Tahmin sırasında paket değişti; çıktı yayımlanmadı.")
    control.disk(Path(workspace))
    output = publish_file(path, request["destination"], control)
    return dict(
        card=card,
        preview=report,
        token=token,
        details=details,
        output=output,
        dataset_version=source["version_id"],
        output_fingerprint=file_hash(Path(output)),
        examples=result.head(5).to_dicts(),
    )


def process_entry(request, action, workspace, cancel, connection, budget):
    try:
        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        value = calculate(request, action, workspace, control)
        value["worker_pid"] = os.getpid()
        connection.send(("result", value))
    except Canceled:
        connection.send(("canceled", None))
    except ProjectError as error:
        connection.send(("error", str(error)))
    except Exception as error:
        connection.send(
            (
                "error",
                resource_error_text(
                    error,
                    f"Model paketi/tahmin tamamlanamadı ({type(error).__name__}); kaynak korundu.",
                ),
            )
        )
    finally:
        connection.close()
