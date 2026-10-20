"""Immutable quality reports and bounded candidates; similarity is never identity."""

import hashlib
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import polars as pl

from veri_ufku.analytics.dataset import checked, literal
from veri_ufku.operations.data_contracts import RULES, contract_validate, require
from veri_ufku.storage.project_model import uid


def normalize(value):
    return unicodedata.normalize("NFKC", value).casefold().strip()


def candidates(request, p, control):
    require(
        request["row_count"] <= 20000,
        "Aday üretimi en fazla20.000 kayıt; açık filtreyle ayrı sürüm oluşturun.",
    )
    names = {c["id"]: c["name"] for c in request["columns"]}
    query = pl.scan_parquet(request["path"])
    rows = (
        query.select(
            "__vu_row_id",
            "__vu_source_record_id",
            names[p["name_column"]],
            names[p["block_column"]],
        )
        .collect()
        .to_dicts()
    )
    blocks = {}
    for row in rows:
        control.check()
        key = row[names[p["block_column"]]]
        name = row[names[p["name_column"]]]
        if key is None or name is None or not key.strip() or not name.strip():
            continue
        require(
            len(name) <= 256 and len(key) <= 256,
            "Aday metinleri en fazla256 karakter olmalı.",
        )
        blocks.setdefault(normalize(key), []).append(row)
    require(
        sum(len(b) * (len(b) - 1) // 2 for b in blocks.values()) <= 20000,
        "Blocking çok geniş: en fazla20.000 karşılaştırma; daha seçici anahtar kullanın.",
    )
    result = []
    for group in blocks.values():
        group.sort(key=lambda r: r["__vu_row_id"])
        for i, left in enumerate(group):
            for right in group[i + 1 :]:
                control.check()
                a, b = left[names[p["name_column"]]], right[names[p["name_column"]]]
                score = SequenceMatcher(
                    None, normalize(a), normalize(b), autojunk=False
                ).ratio()
                if score >= p["threshold"]:
                    result.append(
                        dict(
                            left=left["__vu_row_id"],
                            right=right["__vu_row_id"],
                            left_source=left["__vu_source_record_id"],
                            right_source=right["__vu_source_record_id"],
                            left_name=a,
                            right_name=b,
                            score=score,
                            blocking=left[names[p["block_column"]]],
                            decision="unreviewed",
                        )
                    )
    result.sort(key=lambda r: (-r["score"], r["left"], r["right"]))
    require(
        len(result) <= 200,
        "En fazla200 aday; eşiği/blocking seçiciliğini artırın. Sonuç sessizce kırpılmadı.",
    )
    return result


def evaluate(request, contract, workspace, control):
    contract = contract_validate(contract, request["columns"])
    names = {c["id"]: c["name"] for c in request["columns"]}
    schema = pl.read_parquet_schema(request["path"])
    query = pl.scan_parquet(request["path"])
    reports = []
    masks = []
    unquarantinable = False
    for index, r in enumerate(contract["rules"]):
        control.progress("Veri sözleşmesini kontrol et", index, len(contract["rules"]))
        kind, p = r["kind"], r["parameters"]
        name = names.get(r["column_id"])
        col = pl.col(name) if name else None
        mask = None
        reason = ""
        global_bad = False
        if kind == "range":
            tests = []
            for bound, op in [("minimum", "lt"), ("maximum", "gt")]:
                if p[bound] is not None:
                    value = literal(p[bound], schema[name])
                    tests.append(getattr(col, op)(value))
            mask = pl.any_horizontal(tests).fill_null(False)
            if schema[name].is_float():
                mask = mask | (col.is_not_null() & ~col.is_finite())
        elif kind == "nullable":
            mask = col.is_null() if not p["allowed"] else pl.lit(False)
        elif kind == "unique":
            mask = col.is_duplicated()
            if not p["nulls_equal"]:
                mask = mask & col.is_not_null()
        elif kind == "ordinal":
            require(
                schema[name] == pl.String,
                "Ordinal değer kuralı String fiziksel tür gerektirir.",
            )
            mask = col.is_not_null() & ~col.is_in(p["order"])
            stored = (
                request.get("semantic_metadata", {})
                .get(r["column_id"], {})
                .get("ordinal_order")
            )
            if stored != p["order"]:
                global_bad = True
                reason = "Kayıtlı ordinal sıra sözleşmeyle uyuşmuyor."
        elif kind == "type":
            from veri_ufku.operations.types import dtype_of

            global_bad = schema[name] != dtype_of(p["expected"])
            reason = "Fiziksel tür: " + str(schema[name])
        elif kind == "unit":
            actual = (
                request.get("semantic_metadata", {}).get(r["column_id"], {}).get("unit")
            )
            global_bad = actual != p["expected"]
            reason = (
                "Kayıtlı birim: "
                + (actual if actual is not None else "bilinmiyor")
                + "; değerlerden birim çıkarılmaz."
            )
        elif kind == "row_count":
            global_bad = not p["minimum"] <= request["row_count"] <= p["maximum"]
            reason = "Tablo kayıt sayısı: " + str(request["row_count"])
        else:
            other = request["secondary"]
            checked(other, control)
            other_name = next(
                c["name"] for c in other["columns"] if c["id"] == p["column_id"]
            )
            other_schema = pl.read_parquet_schema(other["path"])
            keys = (
                pl.scan_parquet(other["path"])
                .select(pl.col(other_name).alias("__key"))
                .filter(pl.col("__key").is_not_null())
            )
            duplicates = (
                keys.select(pl.col("__key").is_duplicated().any()).collect().item()
            )
            if schema[name] != other_schema[other_name]:
                global_bad = True
                reason = (
                    "Foreign-key fiziksel türleri eşleşmiyor; sessiz cast yapılmadı."
                )
            elif duplicates:
                global_bad = True
                reason = "Referans key benzersiz değil; tüm referans bağı geçersiz."
            else:
                base = query.filter(col.is_not_null()) if p["nullable"] else query
                missing = base.join(
                    keys.unique(),
                    left_on=name,
                    right_on="__key",
                    how="anti",
                    nulls_equal=False,
                ).select("__vu_row_id")
                # Semi join keeps membership on disk; no Python identity set.
                mask_name = "__vu_contract_" + str(index)
                query = query.join(
                    missing.with_columns(pl.lit(True).alias(mask_name)),
                    on="__vu_row_id",
                    how="left",
                    maintain_order="left",
                )
                mask = pl.col(mask_name).fill_null(False)
        if mask is None:
            mask = pl.lit(global_bad)
        flag = "__vu_rule_" + str(index)
        query = query.with_columns(mask.alias(flag))
        bad = query.filter(pl.col(flag))
        count = bad.select(pl.len()).collect(engine="streaming").item()
        display = ["__vu_row_id", "__vu_source_record_id"] + ([name] if name else [])
        examples = bad.select(display).head(10).collect().to_dicts()
        examples = [
            {k: None if v is None else str(v)[:256] for k, v in row.items()}
            for row in examples
        ]
        if global_bad:
            count = max(1, count)
        reports.append(
            dict(
                rule_id=r["id"],
                kind=kind,
                level=RULES[kind],
                severity=r["severity"],
                violations=count,
                examples=examples,
                reason=reason,
                definition=r,
            )
        )
        if r["severity"] == "error":
            masks.append(pl.col(flag))
            unquarantinable |= global_bad
    error_mask = pl.any_horizontal(masks) if masks else pl.lit(False)
    errors = sum(r["violations"] for r in reports if r["severity"] == "error")
    warnings = sum(r["violations"] for r in reports if r["severity"] == "warning")
    return (
        query,
        error_mask,
        dict(
            dataset_version=request["version_id"],
            contract=contract,
            rules=reports,
            error_violations=errors,
            warning_violations=warnings,
            unquarantinable=unquarantinable,
            silent_corrections=0,
        ),
    )


def execute(request, spec, workspace, control):
    kind, p = spec.kind, spec.parameters
    query = pl.scan_parquet(request["path"])
    names = {c["id"]: c["name"] for c in request["columns"]}
    diagnostics = {}
    relation = None
    if kind == "contract_check":
        query, mask, report = evaluate(request, p["contract"], workspace, control)
        blocked = bool(
            report["error_violations"]
            and (
                p["policy"] == "stop"
                or p["policy"] == "quarantine"
                and report["unquarantinable"]
            )
        )
        diagnostics.update(
            contract_report=report, policy=p["policy"], publication_allowed=not blocked
        )
        if p["policy"] == "quarantine" and report["error_violations"] and not blocked:
            relation = Path(workspace) / ("quarantine-" + uid() + ".parquet")
            query.filter(mask).select(
                pl.all().exclude("^__vu_rule_.*$", "^__vu_contract_.*$")
            ).sink_parquet(relation, maintain_order=True, engine="streaming")
            diagnostics.update(
                relation_rows=pl.scan_parquet(relation)
                .select(pl.len())
                .collect()
                .item(),
                quarantine_kind="contract_error_rows",
                warnings=[
                    "Karantina hata kayıtlarını ayrı saklar; uyarılar veride kalır. Kaynak değiştirilmedi."
                ],
            )
            query = query.filter(~mask)
        query = query.select(pl.all().exclude("^__vu_rule_.*$", "^__vu_contract_.*$"))
    elif kind == "category_candidates":
        name = names[spec.column_ids[0]]
        values = (
            query.select(pl.col(name).drop_nulls().unique().sort())
            .head(201)
            .collect()
            .to_series()
            .to_list()
        )
        require(
            len(values) <= 200 and all(len(v) <= 256 for v in values),
            "Fuzzy kategori en fazla200 benzersiz değer /256 karakter; açık filtre kullanın.",
        )
        found = []
        for i, a in enumerate(values):
            for b in values[i + 1 :]:
                control.check()
                score = SequenceMatcher(
                    None, normalize(a), normalize(b), autojunk=False
                ).ratio()
                if score >= p["threshold"]:
                    found.append(
                        dict(
                            left_value=a,
                            right_value=b,
                            score=score,
                            decision="unreviewed",
                        )
                    )
        require(len(found) <= 200, "En fazla200 kategori adayı; eşiği artırın.")
        diagnostics.update(
            category_candidates=sorted(found, key=lambda c: -c["score"]),
            publication_allowed=False,
            warnings=[
                "Benzer kategoriler otomatik eşlenmez; onay kaynak değeri hedef değere açıkça eşler."
            ],
        )
    elif kind == "entity_candidates":
        diagnostics.update(
            candidates=candidates(request, p, control),
            publication_allowed=False,
            warnings=[
                "Skor aynı kişi olma olasılığı değildir. Blocking dışında aday yok; benzer ad kimlik kanıtı değildir."
            ],
        )
    elif kind == "category_map":
        name = names[spec.column_ids[0]]
        query = query.with_columns(pl.col(name).replace(p["mapping"]).alias(name))
        changed = (
            pl.scan_parquet(request["path"])
            .select(
                pl.col(name)
                .is_in([k for k, v in p["mapping"].items() if k != v])
                .fill_null(False)
                .sum()
            )
            .collect()
            .item()
        )
        diagnostics.update(
            modified_rows=changed,
            changed_cells=changed,
            changed_columns=1,
            approval=p["approval"],
            mapping=p["mapping"],
            warnings=["Yalnız açıkça onaylanan kategori değerleri eşlendi."],
        )
    elif kind == "entity_merge":
        found = candidates(
            request,
            {k: p[k] for k in ("name_column", "block_column", "threshold")},
            control,
        )
        approved = {tuple(sorted(pair)) for pair in p["pairs"]}
        eligible = {tuple(sorted((c["left"], c["right"]))) for c in found}
        require(
            approved <= eligible,
            "Onaylanan çift güncel blocking/skor adayı değil; tekrar önizleyin.",
        )
        canonical = next(
            c["name"] for c in spec.output_schema if c["id"] == p["canonical_column"]
        )
        rows = (
            query.select(
                "__vu_row_id",
                "__vu_source_record_id",
                *([canonical] if p["canonical_column"] in names else []),
            )
            .collect()
            .to_dicts()
        )
        require(len(rows) <= 20000)
        # Every previous group participates, so overlapping approvals never split a group.
        parent = {r["__vu_row_id"]: r["__vu_row_id"] for r in rows}

        def root(row):
            while parent[row] != row:
                parent[row] = parent[parent[row]]
                row = parent[row]
            return row

        def union(a, b):
            a, b = root(a), root(b)
            if a != b:
                parent[max(a, b)] = min(a, b)

        groups = {}
        for r in rows:
            old = r.get(canonical)
            if old:
                if old in groups:
                    union(groups[old], r["__vu_row_id"])
                else:
                    groups[old] = r["__vu_row_id"]
        for a, b in approved:
            union(a, b)
        ids = {}
        for r in rows:
            key = root(r["__vu_row_id"])
            ids.setdefault(key, []).append(r)
        mapping = {}
        for members in ids.values():
            old_ids = sorted({r[canonical] for r in members if r.get(canonical)})
            ident = (
                old_ids[0]
                if old_ids
                else "canonical:"
                + hashlib.sha256(
                    (
                        request["version_id"] + min(r["__vu_row_id"] for r in members)
                    ).encode()
                ).hexdigest()[:32]
            )
            for r in members:
                mapping[r["__vu_row_id"]] = ident
        query = query.with_columns(
            pl.col("__vu_row_id")
            .replace_strict(mapping, return_dtype=pl.String)
            .alias(canonical)
        )
        relation = Path(workspace) / ("identity-" + uid() + ".parquet")
        pl.DataFrame(
            {
                "input_version_id": [request["version_id"]] * len(rows),
                "row_id": [r["__vu_row_id"] for r in rows],
                "source_record_id": [r["__vu_source_record_id"] for r in rows],
                "previous_canonical_id": [r.get(canonical) for r in rows],
                "canonical_id": [mapping[r["__vu_row_id"]] for r in rows],
            },
            schema={
                "input_version_id": pl.String,
                "row_id": pl.String,
                "source_record_id": pl.String,
                "previous_canonical_id": pl.String,
                "canonical_id": pl.String,
            },
        ).write_parquet(relation)
        diagnostics.update(
            modified_rows=sum(
                r.get(canonical) != mapping[r["__vu_row_id"]] for r in rows
            ),
            changed_cells=sum(
                r.get(canonical) != mapping[r["__vu_row_id"]] for r in rows
            ),
            changed_columns=1,
            relation_rows=len(rows),
            relation_kind="canonical_identity_inverse",
            approval=p["approval"],
            decisions=[
                c for c in found if tuple(sorted((c["left"], c["right"]))) in approved
            ],
            canonical_column=p["canonical_column"],
            identity_policy="all rows and SourceRecordIds preserved; canonical groups only; immutable parent is complete inverse",
            warnings=[
                "Canonical atama kayıt silmez. İnsan onayı doğruluk garantisi değildir. Bağlı sonuçlar giriş sürümüne bağlı kalır."
            ],
        )
    output = Path(workspace) / (uid() + ".parquet")
    control.check()
    query.sink_parquet(output, maintain_order=True, engine="streaming")
    control.disk(workspace)
    control.check()
    return spec, output, diagnostics, relation
