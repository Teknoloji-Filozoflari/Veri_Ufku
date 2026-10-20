"""Canonical data-only JSON, shared without importing model backends."""

import hashlib
import json

from veri_ufku.storage.project_model import ProjectError


def raw_json(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False
    ).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ProjectError("Yinelenen paket JSON alanı.")
            result[key] = value
        return result

    try:
        return json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)),
        )
    except (ValueError, RecursionError, UnicodeError) as error:
        raise ProjectError("Model paketi JSON sözleşmesi geçersiz.") from error
