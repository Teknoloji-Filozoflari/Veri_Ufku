"""Bounded local PII candidates and human-policy export; never mutate input data."""

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from pathlib import Path

from veri_ufku.exports.privacy_contracts import LIMITATIONS, policy
from veri_ufku.exports.share_privacy import EMAIL, PHONE, SECRET_KEY, reason
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, encode, uid
from veri_ufku.storage.project_store import file_hash

MAX_ROWS = 10000
MAX_BYTES = 32 * 1024**2
HINT = re.compile(
    r"(?:^|[_\s])(ad|soyad|isim|name|surname|email|mail|phone|telefon|address|adres|kimlik|tc|birth|doğum)(?:$|[_\s])",
    re.I,
)


def verified(request, control):
    ref = request["source"]
    if (
        ref["row_count"] > MAX_ROWS
        or ref["fingerprint"]["size"] > MAX_BYTES
        or len(ref["columns"]) > 64
    ):
        raise ProjectError(
            "Privacy snapshot32MiB/10000row/64column sınırı; daha dar kaynak seçin."
        )
    if file_hash(Path(ref["path"])) != ref["fingerprint"]:
        raise ProjectError("Privacy kaynak hash değişmiş.")
    control.check()
    return ref


def pii_scan(request, control=None):
    import pyarrow.parquet as pq

    control = control or Control()
    ref = verified(request, control)
    counts = {
        c["id"]: dict(
            email=0,
            phone=0,
            secret=0,
            name_hint=bool(HINT.search(c["name"])),
            example_row_ids=[],
        )
        for c in ref["columns"]
    }
    names = {c["name"]: c["id"] for c in ref["columns"]}
    n = 0
    for batch in pq.ParquetFile(ref["path"]).iter_batches(
        batch_size=256, columns=[*names, "__vu_row_id"]
    ):
        control.check()
        for row in batch.to_pylist():
            n += 1
            for name, ident in names.items():
                v = row[name]
                stats = counts[ident]
                if isinstance(v, str):
                    flags = dict(
                        email=bool(EMAIL.search(v)),
                        phone=bool(PHONE.search(v)),
                        secret=reason(v) == "secret-pattern",
                    )
                    for k, found in flags.items():
                        stats[k] += int(found)
                    if any(flags.values()) and len(stats["example_row_ids"]) < 5:
                        stats["example_row_ids"].append(row["__vu_row_id"])
    verified(request, control)
    columns = [
        dict(
            id=c["id"],
            name=c["name"],
            type=c["type"],
            **counts[c["id"]],
            candidate=counts[c["id"]]["name_hint"]
            or any(counts[c["id"]][k] for k in ("email", "phone", "secret")),
        )
        for c in ref["columns"]
    ]
    result = dict(
        schema="PIICandidates/v1",
        version=ref["version_id"],
        fingerprint=ref["fingerprint"],
        rows_scanned=n,
        columns=columns,
        status="candidates-only; user confirmation required",
        limitations=LIMITATIONS,
    )
    result["scan_hash"] = digest(result)
    return result


def project_policy(request, raw, key, control):
    import pyarrow as pa
    import pyarrow.parquet as pq

    from veri_ufku.exports.privacy_keys import pseudonym

    s = policy(raw)
    ref = verified(request, control)
    if s["version"] != ref["version_id"]:
        raise ProjectError("Privacy review başka dataset sürümüne ait.")
    cols = {c["id"]: c for c in ref["columns"]}
    if not {r["column"] for r in s["rules"]} <= set(cols):
        raise ProjectError("Privacy ColumnId mevcut değil.")
    pf = pq.ParquetFile(ref["path"])
    rules = [r for r in s["rules"] if r["strategy"] != "drop"]
    records = []
    schema = []
    for i, r in enumerate(rules):
        field = pf.schema_arrow.field(cols[r["column"]]["name"])
        if r["strategy"] == "keep" and not any(
            check(field.type)
            for check in (
                pa.types.is_boolean,
                pa.types.is_integer,
                pa.types.is_floating,
                pa.types.is_decimal,
                pa.types.is_string,
                pa.types.is_large_string,
                pa.types.is_date,
                pa.types.is_time,
                pa.types.is_timestamp,
                pa.types.is_duration,
            )
        ):
            raise ProjectError(
                "Keep yalnız taranabilir scalar kolonlar; nested/binary için mask/drop seçin."
            )
        schema.append(
            pa.field(
                "column_" + str(i + 1),
                field.type if r["strategy"] == "keep" else pa.string(),
            )
        )
    for batch in pf.iter_batches(
        batch_size=256, columns=[cols[r["column"]]["name"] for r in rules]
    ):
        control.check()
        for row in batch.to_pylist():
            output = {}
            for i, r in enumerate(rules):
                v = row[cols[r["column"]]["name"]]
                strategy = r["strategy"]
                if strategy == "keep":
                    if reason(v) == "secret-pattern" or SECRET_KEY.search(
                        cols[r["column"]]["name"]
                    ):
                        raise ProjectError(
                            "Secret deseni keep ile dışa aktarılamaz; mask/drop seçin."
                        )
                    output["column_" + str(i + 1)] = v
                elif strategy == "mask":
                    output["column_" + str(i + 1)] = None if v is None else "[redacted]"
                else:
                    if not key:
                        raise ProjectError(
                            "Pseudonym key yalnız keyring/worker memory üzerinden gerekli."
                        )
                    canonical = (
                        str(v) if isinstance(v, float) and not math.isfinite(v) else v
                    )
                    output["column_" + str(i + 1)] = (
                        None
                        if v is None
                        else pseudonym(
                            key, request["project_id"], r["column"], canonical
                        )
                    )
            records.append(output)
    verified(request, control)
    table = pa.Table.from_pylist(records, schema=pa.schema(schema))
    # Public output excludes source RowIds, raw column names, reviewer and freeform rationale.
    public_columns = [
        dict(
            alias="column_" + str(i + 1),
            column_id=r["column"],
            classification=r["classification"],
            strategy=r["strategy"],
        )
        for i, r in enumerate(rules)
    ]
    preview_rows = [
        {
            k: (
                "["
                + ("pseudonym" if rules[i]["strategy"] == "pseudonym" else "kept-value")
                + "]"
                if rules[i]["strategy"] != "mask" and v is not None
                else v
            )
            for i, (k, v) in enumerate(row.items())
        }
        for row in records[:10]
    ]
    preview = dict(
        schema="PrivacyExportPreview/v1",
        version=ref["version_id"],
        fingerprint=ref["fingerprint"],
        policy_hash=digest(s),
        review_id=request["review_id"],
        rows=table.num_rows,
        columns=public_columns,
        redacted_preview=preview_rows,
        plaintext_value_preview="kept/pseudonym values hidden; mask shown, original source remains in local dataset viewer",
        output_hash=digest(
            json.loads(
                json.dumps(
                    dict(
                        schema=str(table.schema),
                        rows=[
                            {
                                k: (
                                    str(v)
                                    if isinstance(v, float) and not math.isfinite(v)
                                    else v
                                )
                                for k, v in row.items()
                            }
                            for row in records
                        ],
                    ),
                    default=str,
                    allow_nan=False,
                )
            )
        ),
        key_ref=s["key_ref"]
        if any(r["strategy"] == "pseudonym" for r in rules)
        else None,
        limitations=LIMITATIONS,
    )
    preview["preview_hash"] = digest(preview)
    return table, preview


def export(request, params, workspace, control, key=None, seal_key=None):
    import pyarrow.parquet as pq

    from veri_ufku.exports.files import publish
    from veri_ufku.exports.privacy_keys import encrypt

    table, preview = project_policy(request, request["policy"], key, control)
    if (
        params["reviewed"] is not True
        or params["preview_hash"] != preview["preview_hash"]
    ):
        raise ProjectError(
            "Privacy export için aynı review/source/key önizlemesini açıkça inceleyin."
        )
    fmt = params["format"]
    if fmt not in ("zip", "sealed"):
        raise ProjectError(
            "Privacy format zip/sealed; raw export burada desteklenmiyor."
        )
    dest = Path(params["destination"])
    if dest.suffix.lower() != (".vupseal" if fmt == "sealed" else ".zip"):
        raise ProjectError("Privacy çıktı uzantısı formatla uyumlu olmalı.")
    out = io.BytesIO()
    pq.write_table(table, out)
    pq.read_table(io.BytesIO(out.getvalue()))
    data = io.StringIO(newline="")
    writer = csv.writer(data)
    writer.writerow(table.column_names)
    for row in table.to_pylist():
        writer.writerow(
            [
                (
                    "'" + v
                    if isinstance(v, str)
                    and v.lstrip().startswith(("=", "+", "-", "@"))
                    else v
                )
                for v in row.values()
            ]
        )
    manifest = dict(
        schema="PrivacyExport/v1",
        export_id="export:" + uid(),
        source_reference=dict(
            version=preview["version"], fingerprint=preview["fingerprint"]
        ),
        review_id=request["review_id"],
        policy_hash=preview["policy_hash"],
        columns=preview["columns"],
        rows=preview["rows"],
        key_ref=preview["key_ref"],
        limitations=LIMITATIONS,
        csv_policy="null empty; formula prefixes escaped; Parquet authoritative null/type",
        encrypted=fmt == "sealed",
        encryption_key_ref=params.get("encryption_key_ref")
        if fmt == "sealed"
        else None,
    )
    manifest["members"] = {
        "data.parquet": hashlib.sha256(out.getvalue()).hexdigest(),
        "data.csv": hashlib.sha256(data.getvalue().encode("utf-8-sig")).hexdigest(),
    }
    members = {
        "data.parquet": out.getvalue(),
        "data.csv": data.getvalue().encode("utf-8-sig"),
        "manifest.json": encode(manifest),
    }
    if sum(map(len, members.values())) > MAX_BYTES:
        raise ProjectError("Privacy expanded export32MiB sınırı.")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for n, raw in members.items():
            z.writestr(n, raw)
    raw = buffer.getvalue()
    if len(raw) > MAX_BYTES:
        raise ProjectError("Privacy export32MiB sınırı.")
    if fmt == "sealed":
        if not seal_key:
            raise ProjectError("Fernet key yok; plaintext fallback yapılmadı.")
        raw = encrypt(raw, seal_key)
    path = Path(workspace) / ("sealed.vupseal" if fmt == "sealed" else "payload.zip")
    path.write_bytes(raw)
    control.disk(workspace, force=True)
    receipt = publish(path, dest, request["project_root"], control)
    return dict(
        action="export",
        status="published",
        receipt=receipt,
        preview=preview,
        limitations=LIMITATIONS,
    )


def inspect_sealed(path, key, control=None):
    from veri_ufku.exports.privacy_keys import decrypt

    control = control or Control()
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > 48 * 1024**2:
        raise ProjectError("Encrypted export48MiB/symlink sınırı.")
    control.check()
    raw = decrypt(path.read_bytes(), key)
    if len(raw) > MAX_BYTES:
        raise ProjectError("Decrypted export32MiB sınırı.")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if (
                len(z.infolist()) != 3
                or set(z.namelist()) != {"manifest.json", "data.parquet", "data.csv"}
                or sum(i.file_size for i in z.infolist()) > MAX_BYTES
            ):
                raise ProjectError("Encrypted export closed members/sizes uyuşmuyor.")
            from veri_ufku.storage.project_model import decode

            manifest = decode(z.read("manifest.json"))
            if (
                not isinstance(manifest, dict)
                or set(manifest)
                != {
                    "schema",
                    "export_id",
                    "source_reference",
                    "review_id",
                    "policy_hash",
                    "columns",
                    "rows",
                    "key_ref",
                    "limitations",
                    "csv_policy",
                    "encrypted",
                    "encryption_key_ref",
                    "members",
                }
                or manifest["schema"] != "PrivacyExport/v1"
            ):
                raise ProjectError("Encrypted export şema desteklenmiyor.")
            from veri_ufku.exports.privacy_contracts import reference

            for k in ("key_ref", "encryption_key_ref"):
                if manifest[k] is not None:
                    reference(manifest[k])
            if (
                type(manifest["rows"]) is not int
                or not 0 <= manifest["rows"] <= MAX_ROWS
                or manifest["encrypted"] is not True
                or manifest["limitations"] != LIMITATIONS
            ):
                raise ProjectError("Encrypted export metadata sınırı geçersiz.")
            if set(manifest["members"]) != {"data.parquet", "data.csv"} or any(
                hashlib.sha256(z.read(n)).hexdigest() != h
                for n, h in manifest["members"].items()
            ):
                raise ProjectError("Encrypted export member hash bozuk.")
            import pyarrow.parquet as pq

            if (
                pq.ParquetFile(io.BytesIO(z.read("data.parquet"))).metadata.num_rows
                != manifest["rows"]
            ):
                raise ProjectError("Encrypted export row count bozuk.")
        return dict(
            action="sealed-inspection",
            status="authenticated; not extracted or executed",
            manifest=manifest,
            limitations=LIMITATIONS,
        )
    except (KeyError, zipfile.BadZipFile, ValueError, TypeError):
        raise ProjectError("Şifreli export safe içerik doğrulanamadı.") from None
