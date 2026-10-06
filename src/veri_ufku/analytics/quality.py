"""Read-only, deterministic quality scan with bounded examples and disk grouping."""

import json
import math
import sqlite3
import unicodedata
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, localcontext
from difflib import SequenceMatcher
from pathlib import Path

import polars as pl

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import (
    checked,
    display,
    filtered,
    literal,
    suggest_role,
    value_key,
)
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.storage.project_model import ProjectError, digest, encode, uid


def turkish_fold(value):
    return (
        unicodedata.normalize("NFC", value)
        .translate(str.maketrans({"I": "ı", "İ": "i"}))
        .lower()
        .strip()
    )


def key(value):
    if value is None:
        return ["null"]
    if isinstance(value, pl.Series):
        value = value.to_list()
    if isinstance(value, (list, dict)):
        return [type(value).__name__, repr(value)]
    return [type(value).__name__, value_key(value)]


def validate(parameters, columns):
    ids = {c["id"] for c in columns}
    if type(parameters.get("sample")) is not bool or parameters.get("target") not in (
        "dataset",
        "view",
    ):
        raise ProjectError("Kalite tarama kapsamı geçersiz.")
    if parameters.get("purpose") not in ("inspect", "clean", "model"):
        raise ProjectError("Tarama amacı geçersiz.")
    duplicates = parameters.get("duplicate_columns", [])
    rules = parameters.get("rules", [])
    if (
        not isinstance(duplicates, list)
        or not set(duplicates) <= ids
        or len(set(duplicates)) != len(duplicates)
    ):
        raise ProjectError("Tekrar sütunları geçersiz.")
    if not isinstance(rules, list) or len(rules) > 32:
        raise ProjectError("En fazla32 kalite kuralı girin.")
    for rule in rules:
        if (
            not isinstance(rule, dict)
            or set(rule) != {"column_id", "kind", "value", "upper"}
            or rule["column_id"] not in ids
        ):
            raise ProjectError("Kural sütunu/alanları geçersiz.")
        if rule["kind"] not in (
            "required",
            "unique",
            "range",
            "allowed",
            "number",
            "date",
            "convert",
        ) or any(
            not isinstance(rule[k], str) or len(rule[k]) > 1000
            for k in ("value", "upper")
        ):
            raise ProjectError("Kural türü/değeri geçersiz.")
        if rule["kind"] == "range":
            try:
                low, high = Decimal(rule["value"]), Decimal(rule["upper"])
                if not low.is_finite() or not high.is_finite() or low > high:
                    raise ValueError()
            except (ValueError, InvalidOperation) as error:
                raise ProjectError(
                    "Aralık alt/üst sınırları sonlu ve sıralı olmalı."
                ) from error
        if rule["kind"] == "date" and rule["value"] not in (
            "ISO",
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d/%m/%Y",
        ):
            raise ProjectError(
                "Tarih biçimi ISO veya listelenen açık biçimlerden biri olmalı."
            )
        if rule["kind"] == "convert" and rule["value"] not in (
            "int64",
            "float64",
            "boolean",
            "date",
        ):
            raise ProjectError(
                "Dönüşüm hedefi int64, float64, boolean veya date olmalı."
            )
        if rule["kind"] == "allowed" and not rule["value"]:
            raise ProjectError("İzin verilen değerleri | ile ayırın.")


def violates(value, rule):
    kind = rule["kind"]
    if kind == "required":
        return value is None or isinstance(value, str) and not value.strip()
    if value is None or kind == "unique":
        return False
    try:
        if kind == "convert":
            try:
                literal(
                    str(value),
                    {
                        "int64": pl.Int64,
                        "float64": pl.Float64,
                        "boolean": pl.Boolean,
                        "date": pl.Date,
                    }[rule["value"]],
                )
                return False
            except ProjectError:
                return True
        if kind in ("number", "range"):
            number = Decimal(str(value))
            return (
                not number.is_finite()
                or kind == "range"
                and not Decimal(rule["value"]) <= number <= Decimal(rule["upper"])
            )
        if kind == "allowed":
            return str(value) not in rule["value"].split("|")
        if kind == "date":
            if rule["value"] == "ISO":
                datetime.fromisoformat(str(value))
            else:
                datetime.strptime(str(value), rule["value"])
            return False
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        return True
    return False


def rule_description(rule):
    if not rule:
        return "kullanıcı kuralı yok"
    labels = {
        "required": "Değer gerekli",
        "unique": "Null hariç benzersiz",
        "range": "Sayısal aralık",
        "allowed": "İzin verilen etiketler",
        "number": "Sonlu sayıya dönüşebilir",
        "date": "Geçerli tarih",
        "convert": "Hedef türe kayıpsız dönüşebilir",
    }
    return (
        labels[rule["kind"]]
        + ": "
        + rule["value"]
        + (" … " + rule["upper"] if rule["upper"] else "")
    )


def scan(request, parameters, workspace, control=None):
    control = control or Control()
    checked(request, control)
    columns = request["columns"]
    validate(parameters, columns)
    view = ViewSpec.from_dict(parameters["view"])
    view.validate(columns)
    effective = (
        ViewSpec(filters=view.filters) if parameters["target"] == "view" else ViewSpec()
    )
    query, schema, _ = filtered(request, effective)
    population = query.select(pl.len()).collect(engine="streaming").item()
    limit = (
        min(population, control.budget.sample_limit_rows)
        if parameters["sample"]
        else population
    )
    source = query.head(limit)
    scope = (
        "sample" if limit < population else "filtered" if effective.filters else "full"
    )
    roles = {}
    advisory = source.head(200).collect(engine="streaming")
    for c in columns:
        proposed, _ = suggest_role(
            c["name"], schema[c["name"]], advisory[c["name"]].to_list()
        )
        roles[c["id"]] = (
            request.get("semantic_metadata", {}).get(c["id"], {}).get("role", proposed)
        )
    findings = {}
    warnings = (
        [
            "Örneklem ilk N kayıttır; tüm veriyi temsil ettiği ve bulunmayan sorunların olmadığı söylenemez."
        ]
        if scope == "sample"
        else []
    )
    path = Path(workspace) / "quality.sqlite"
    db = sqlite3.connect(path)
    db.execute("PRAGMA cache_size=-8192")
    db.execute("PRAGMA temp_store=FILE")
    db.execute(
        "CREATE TABLE records (ord INTEGER PRIMARY KEY, rid TEXT, sid TEXT, fullkey TEXT, selectedkey TEXT)"
    )
    db.execute(
        "CREATE TABLE cells (col TEXT, ord INTEGER, k TEXT, text TEXT, normalized TEXT, number TEXT)"
    )
    db.create_collation(
        "exact_number",
        lambda a, b: (Decimal(a) > Decimal(b)) - (Decimal(a) < Decimal(b)),
    )
    names = {c["id"]: c["name"] for c in columns}

    def hit(code, cid, reason, kind, learning, ordinals, rule=None):
        ident = code + ":" + cid + (":" + digest(encode(rule))[:12] if rule else "")
        if ident not in findings:
            findings[ident] = dict(
                id=ident,
                code=code,
                column_id=cid,
                column=names.get(cid, "Tüm sütunlar"),
                reason=reason,
                classification=kind,
                learning_id=learning,
                count=0,
                examples=[],
                rule=rule,
            )
        finding = findings[ident]
        for ordinal in ordinals:
            control.check()
            finding["count"] += 1
            if len(finding["examples"]) < 5:
                rid, sid = db.execute(
                    "SELECT rid,sid FROM records WHERE ord=?", (ordinal,)
                ).fetchone()
                values = db.execute(
                    "SELECT col,text FROM cells WHERE ord=?", (ordinal,)
                ).fetchall()
                finding["examples"].append(
                    dict(
                        row_id=rid,
                        source_record_id=sid,
                        values="; ".join(
                            names[col] + "=" + text
                            for col, text in values
                            if not cid or col == cid
                        )[:1024],
                    )
                )

    try:
        used = 0
        exprs = [
            pl.col(c["name"]).cast(pl.String)
            if schema[c["name"]].is_temporal()
            else pl.col(c["name"])
            for c in columns
        ]
        for batch in source.select(
            exprs + [pl.col("__vu_row_id"), pl.col("__vu_source_record_id")]
        ).collect_batches(chunk_size=4096, maintain_order=True, engine="streaming"):
            control.check()
            for row in batch.iter_rows(named=True):
                ordinal = used
                used += 1
                if used % 256 == 0:
                    control.check()
                keys = {c["id"]: key(row[c["name"]]) for c in columns}
                db.execute(
                    "INSERT INTO records VALUES (?,?,?,?,?)",
                    (
                        ordinal,
                        row["__vu_row_id"],
                        row["__vu_source_record_id"],
                        json.dumps(list(keys.values()), ensure_ascii=False),
                        json.dumps(
                            [keys[c] for c in parameters["duplicate_columns"]],
                            ensure_ascii=False,
                        ),
                    ),
                )
                for c in columns:
                    cid, value = c["id"], row[c["name"]]
                    numeric = (
                        schema[c["name"]].is_numeric()
                        and value is not None
                        and (not isinstance(value, float) or math.isfinite(value))
                    )
                    number = (
                        str(
                            Decimal.from_float(value)
                            if isinstance(value, float)
                            else Decimal(value)
                        )
                        if numeric
                        else None
                    )
                    db.execute(
                        "INSERT INTO cells VALUES (?,?,?,?,?,?)",
                        (
                            cid,
                            ordinal,
                            json.dumps(keys[cid], ensure_ascii=False),
                            repr(value)[:256]
                            if isinstance(value, str)
                            else display(value),
                            turkish_fold(value) if isinstance(value, str) else None,
                            number,
                        ),
                    )
                for c in columns:
                    cid, value = c["id"], row[c["name"]]
                    if value is None:
                        hit(
                            "missing",
                            cid,
                            "Fiziksel null; eksiklik nedeni bu taramayla belirlenemez.",
                            "observation",
                            "missing-mechanism",
                            [ordinal],
                        )
                    if isinstance(value, float) and not math.isfinite(value):
                        hit(
                            "nonfinite",
                            cid,
                            "NaN/sonsuz null değildir; sayısal işlemler için inceleyin.",
                            "candidate",
                            "quality",
                            [ordinal],
                        )
                    if isinstance(value, str) and (
                        not value.strip()
                        or value != value.strip()
                        or "  " in value
                        or any(ch in value for ch in "\t\n\r")
                    ):
                        hit(
                            "whitespace",
                            cid,
                            "Boş metin veya baş/son/çoklu boşluk; anlamlı biçim olabilir.",
                            "candidate",
                            "quality",
                            [ordinal],
                        )
                    for rule in parameters["rules"]:
                        if rule["column_id"] == cid and violates(value, rule):
                            hit(
                                "invalid_date"
                                if rule["kind"] == "date"
                                else "conversion"
                                if rule["kind"] in ("number", "convert")
                                else "rule",
                                cid,
                                "Kullanıcının açık kuralına uymuyor: "
                                + rule_description(rule),
                                "violation",
                                "quality",
                                [ordinal],
                                rule,
                            )
            db.commit()
            control.disk(workspace)
            control.progress("Kalite taraması", used, limit)
        db.execute("CREATE INDEX cells_col_key ON cells(col,k)")
        db.execute("CREATE INDEX cells_col_ord ON cells(col,ord)")
        db.execute("CREATE INDEX full_groups ON records(fullkey)")
        db.execute("CREATE INDEX selected_groups ON records(selectedkey)")
        for field, code in (
            ("fullkey", "duplicates_full"),
            ("selectedkey", "duplicates_selected"),
        ):
            if field == "selectedkey" and not parameters["duplicate_columns"]:
                continue
            hits = db.execute(
                f"SELECT ord FROM records WHERE {field} IN (SELECT {field} FROM records GROUP BY {field} HAVING COUNT(*)>1) ORDER BY ord"
            )
            hit(
                code,
                "",
                "Aynı değerleri taşıyan grubun tüm üyeleri sayılır; meşru tekrarlı olay olabilir. Seçili sütunlar: "
                + ", ".join(names[c] for c in parameters["duplicate_columns"]),
                "candidate",
                "duplicates",
                (r[0] for r in hits),
            )
        for c in columns:
            control.check()
            cid = c["id"]
            distinct = db.execute(
                "SELECT COUNT(DISTINCT k) FROM cells WHERE col=? AND k!=?",
                (cid, json.dumps(["null"])),
            ).fetchone()[0]
            if distinct == 1:
                hit(
                    "constant",
                    cid,
                    "Tarama kapsamında tek non-null değer; kaldırmak zorunlu değildir.",
                    "observation",
                    "quality",
                    (
                        r[0]
                        for r in db.execute(
                            "SELECT ord FROM cells WHERE col=? AND k!=? ORDER BY ord",
                            (cid, json.dumps(["null"])),
                        )
                    ),
                )
            for rule in parameters["rules"]:
                if rule["column_id"] == cid and rule["kind"] == "unique":
                    hit(
                        "uniqueness",
                        cid,
                        "Açık benzersizlik kuralı; null hariç tekrar grubunun tüm üyeleri.",
                        "violation",
                        "duplicates",
                        (
                            r[0]
                            for r in db.execute(
                                "SELECT ord FROM cells WHERE col=? AND k!=? AND k IN (SELECT k FROM cells WHERE col=? GROUP BY k HAVING COUNT(*)>1) ORDER BY ord",
                                (cid, json.dumps(["null"]), cid),
                            )
                        ),
                        rule,
                    )
            if roles[cid] in ("category", "ordinal") and schema[c["name"]] == pl.String:
                variants = db.execute(
                    "SELECT k,text,normalized FROM cells WHERE col=? GROUP BY k ORDER BY MIN(ord) LIMIT 201",
                    (cid,),
                ).fetchall()
                if len(variants) > 200:
                    warnings.append(
                        names[cid]
                        + ": benzer kategori taraması ilk200 farklı etiketle sınırlı; eksiksiz aday listesi değildir."
                    )
                if any(v[2] and len(v[2]) > 256 for v in variants):
                    warnings.append(
                        names[cid]
                        + ": 256 karakterden uzun etiketler benzer yazım karşılaştırmasına alınmadı."
                    )
                variants = [v for v in variants if not v[2] or len(v[2]) <= 256]
                suspect = set()
                for i, (ka, a, na) in enumerate(variants[:200]):
                    for kb, b, nb in variants[:i]:
                        if (
                            na
                            and nb
                            and (
                                na == nb
                                or min(len(na), len(nb)) >= 4
                                and SequenceMatcher(
                                    None, na, nb, autojunk=False
                                ).ratio()
                                >= 0.85
                            )
                        ):
                            suspect.update((ka, kb))
                if suspect:
                    placeholders = ",".join("?" for _ in suspect)
                    hit(
                        "category_similarity",
                        cid,
                        "Türkçe I/ı, İ/i ve NFC ile karşılaştırılan benzer etiket adayları; anlamları aynı olmayabilir. Birleştirme yapılmaz.",
                        "candidate",
                        "quality",
                        (
                            r[0]
                            for r in db.execute(
                                f"SELECT ord FROM cells WHERE col=? AND k IN ({placeholders}) ORDER BY ord",
                                (cid, *sorted(suspect)),
                            )
                        ),
                    )
            if roles[cid] == "measurement" and schema[c["name"]].is_numeric():
                n = db.execute(
                    "SELECT COUNT(*) FROM cells WHERE col=? AND number IS NOT NULL",
                    (cid,),
                ).fetchone()[0]
                if n >= 4:

                    def quantile(q):
                        with localcontext() as ctx:
                            ctx.prec = 80
                            pos = Decimal(n - 1) * q
                            lo = int(pos)
                            values = [
                                Decimal(r[0])
                                for r in db.execute(
                                    "SELECT number FROM cells WHERE col=? AND number IS NOT NULL ORDER BY number COLLATE exact_number LIMIT 2 OFFSET ?",
                                    (cid, lo),
                                )
                            ]
                            return values[0] + (values[-1] - values[0]) * (pos - lo)

                    with localcontext() as ctx:
                        ctx.prec = 80
                        q1, q3 = quantile(Decimal(".25")), quantile(Decimal(".75"))
                        low, high = (
                            q1 - Decimal("1.5") * (q3 - q1),
                            q3 + Decimal("1.5") * (q3 - q1),
                        )
                    hit(
                        "outlier",
                        cid,
                        f"Sonlu ölçümlerde 1.5×IQR adayı; linear quantile; n={n}; sınırlar {low}…{high}. Hata veya silme kararı değildir.",
                        "candidate",
                        "outliers",
                        (
                            ord
                            for ord, num in db.execute(
                                "SELECT ord,number FROM cells WHERE col=? AND number IS NOT NULL ORDER BY ord",
                                (cid,),
                            )
                            if Decimal(num) < low or Decimal(num) > high
                        ),
                    )
        control.disk(workspace)
        checked(request, control)
        result = []
        for finding in findings.values():
            if not finding["count"]:
                continue
            cid = finding["column_id"]
            role = roles.get(cid, "record")
            physical = str(schema[names[cid]]) if cid else "row"
            purpose_label = {
                "inspect": "veriyi incelemek",
                "clean": "temizliğe hazırlanmak",
                "model": "modellemeye hazırlanmak",
            }[parameters["purpose"]]
            role_label = {
                "identifier": "kimlik",
                "category": "kategori",
                "measurement": "ölçüm",
                "time": "tarih",
                "text": "serbest metin",
                "ordinal": "sıralı kategori",
                "ignored": "dışlanan",
                "record": "kayıt",
            }[role]
            reason = f"{finding['reason']} Amaç: {purpose_label}; rol: {role_label}; tür: {physical}; kullanılan {used}/{population}; {rule_description(finding['rule'])}."
            finding.update(
                ratio=finding["count"] / used if used else 0,
                scope=scope,
                denominator=used,
                options=[
                    "Kaynak ve kayıt anlamını incele",
                    "Kuralı/rolü gözden geçir",
                    "Tüm veriyle yeniden tara",
                ],
            )
            options = list(finding["options"])
            if role == "identifier":
                options.append(
                    "Kimliğin analiz birimine göre benzersiz olması gerekip gerekmediğini doğrula"
                )
            if parameters["purpose"] == "model":
                options.append(
                    "Eksik doldurma/kodlama kararını eğitim katında öğren; sızıntıyı incele"
                )
            if scope == "sample":
                options.append("Aday kararını örneklemden tüm veriye genelleme")
            finding["options"] = options
            finding["recommendation"] = dict(
                id="recommendation:"
                + digest(encode([request["version_id"], finding["id"], parameters]))[
                    :24
                ],
                reason=reason,
                precondition="Kapsamı ve kayıt anlamını doğrulayın; değişiklik öncesi önizleme gerekir.",
                impact=f"{finding['count']}/{used} kayıt incelenmeli; tarama veri değiştirmez.",
                operation_id={
                    "missing": "transform.fill_missing",
                    "duplicates_full": "transform.deduplicate",
                    "duplicates_selected": "transform.deduplicate",
                    "whitespace": "transform.trim",
                    "category_similarity": "transform.map_categories",
                    "conversion": "transform.convert_type",
                    "invalid_date": "transform.parse_date",
                }.get(finding["code"], "quality.review." + finding["code"]),
                learning_id=finding["learning_id"],
                available=False,
            )
            result.append(finding)
        return dict(
            dataset_version=request["version_id"],
            scope=scope,
            used_n=used,
            population_n=population,
            dataset_n=request["row_count"],
            import_exclusions=dict(
                count=request.get("import_bad_count", 0),
                scope="source import; outside active dataset",
                reason="İçe aktarmada karantinaya alınan kayıtlar bu taramanın satırlarına/oranına dahil değildir; import kaydını inceleyin.",
            ),
            findings=result,
            warnings=warnings,
            parameters=parameters,
            snapshot_fingerprint=request["fingerprint"],
            roles=roles,
            methods=dict(
                version="quality/v1",
                sample_method="firstN immutable input order"
                if scope == "sample"
                else "all scope records",
                quantile="linear h=(n-1)q; Decimal80",
                outlier="1.5 IQR; measurement only; finite n>=4",
                category="Turkish NFC lower/strip; SequenceMatcher>=.85; first200 variants<=256 chars",
            ),
            provenance=json.loads(
                encode(
                    asdict(
                        Provenance(
                            provenance_id="prov:" + uid(),
                            dataset_versions=(request["version_id"],),
                            config_revision=request.get("config_revision", 0),
                            capability_id="dataset.quality",
                            parameters_hash=digest(encode(parameters)),
                            environment=(
                                ("polars", pl.__version__),
                                ("method", "quality/v1"),
                            ),
                            created_at=datetime.now(UTC).isoformat(),
                            scope=scope,
                            seed=None,
                            seed_reason="Deterministik ilkN; rastgele örnekleme yok"
                            if scope == "sample"
                            else "Tam kapsam; örnekleme yok",
                            source_snapshot_ids=(request["source_snapshot_id"],),
                            row_lineage_ref=request["snapshot_uri"],
                            filters=tuple(
                                encode(f).decode("utf8") for f in effective.filters
                            ),
                            exclusions=("Karantina kayıtları dataset dışında",)
                            if request.get("import_bad_count", 0)
                            else (),
                            learning_content_version="7",
                        )
                    )
                )
            ),
        )
    finally:
        db.close()
        path.unlink(missing_ok=True)
