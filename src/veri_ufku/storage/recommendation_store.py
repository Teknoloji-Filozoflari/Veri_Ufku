"""Explicit new-file export only; model/run storage stays in neural_store/ProjectStore."""

import copy
import hashlib
import json
import os
from pathlib import Path

from veri_ufku.storage.project_model import ProjectError


def export_list(data, destination, include_ids=False):
    if data.get("schema") != "RecommendationList/v1" or type(include_ids) is not bool:
        raise ProjectError("Öneri listesi/onay şeması geçersiz.")
    path = Path(destination)
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ProjectError(
            "Yeni mutlak JSON dosyası seçin; mevcut dosya üzerine yazılmaz."
        )
    payload = copy.deepcopy(data)
    if not include_ids:
        salt = os.urandom(32)

        def mask(value):
            return (
                "masked:" + hashlib.sha256(salt + str(value).encode()).hexdigest()[:24]
            )

        payload["user"] = mask(payload["user"])
        payload["candidate_ids"] = [mask(i) for i in payload["candidate_ids"]]
        for r in payload["recommendations"]:
            r["item"] = mask(r["item"])
            r["source_records"] = [
                dict(
                    row_id=mask(s["row_id"]),
                    source_record_id=mask(s["source_record_id"]),
                )
                for s in r["source_records"]
            ]
    payload["export_identity_policy"] = (
        "source IDs explicitly included"
        if include_ids
        else "per-export salted pseudonyms; not a guarantee of anonymity"
    )
    raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2).encode()
    if len(raw) > 2 * 1024**2:
        raise ProjectError("Öneri export2MiB sınırı.")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
