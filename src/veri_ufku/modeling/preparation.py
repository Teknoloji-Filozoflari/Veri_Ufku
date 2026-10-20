"""Observational suitability scan and unfitted plan; no estimator or transform fit."""

import hashlib
import json
import re
from pathlib import Path

import polars as pl

from veri_ufku.analytics.dataset import checked
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.contracts import PreparationSpec, identifier
from veri_ufku.modeling.history import ancestors, audit
from veri_ufku.modeling.plan import blueprint
from veri_ufku.storage.project_model import ProjectError, uid

MAX_ROWS = 100000
MAX_COLUMNS = 100


def finite(name, dtype):
    value = pl.col(name)
    return value.is_not_null() & (
        value.is_finite() if dtype.is_float() else pl.lit(True)
    )


def mentions(value, ident):
    if isinstance(value, dict):
        return any(mentions(v, ident) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(mentions(v, ident) for v in value)
    return value == ident


def calculate(request, parameters, workspace, control=None):
    control = control or Control()
    spec = (
        parameters
        if isinstance(parameters, PreparationSpec)
        else PreparationSpec.from_dict(parameters)
    )
    spec.validate(request["columns"])
    checked(request, control)
    if (
        not 0 < request["row_count"] <= MAX_ROWS
        or len(request["columns"]) > MAX_COLUMNS
        or request["row_count"] * (128 + 16 * len(request["columns"]))
        > control.budget.ram_bytes // 2
    ):
        raise ProjectError(
            "Model hazırlığı kapsamı boş veya bütçeyi aşıyor:100000 kayıt/100 sütun. Sessiz örnekleme yapılmaz."
        )
    if spec.source_version != request["version_id"]:
        raise ProjectError("Hazırlık kaynağı veri sürümüyle uyuşmuyor.")
    history = audit(
        request["history_state"],
        request["origin_version"],
        request["version_id"],
        spec.history_action,
    )
    if (
        spec.history_action in ("raw", "relocate")
        and history["unresolved_source_operations"]
    ):
        raise ProjectError(
            "Bu kaynak sürümünde geçmiş riski hâlâ var; riskli işlemlerden önceki temiz sürümü seçin."
        )
    if (
        spec.history_action in ("raw", "relocate")
        and request["version_id"] == request["origin_version"]
        and history["findings"]
    ):
        raise ProjectError(
            "Geçmiş riski için gerçekten önceki temiz kaynak seçilmeli; yalnız yeni pipeline kurmak yeterli değil."
        )
    columns = request["columns"]
    semantics = request.get("semantic_metadata", {})
    versions = {d["version_id"]: d for d in request["history_state"]["datasets"]}
    source_ancestors = ancestors(request["history_state"], request["version_id"])
    query = pl.scan_parquet(request["path"])
    schema = query.collect_schema()
    metrics = []
    for i, c in enumerate(columns):
        name = c["name"]
        dt = schema[name]
        if dt.is_nested() or dt == pl.Binary or isinstance(dt, pl.Object):
            # Unsupported selected types are rejected by blueprint; other columns remain visible.
            metrics.extend(
                [
                    pl.col(name).null_count().alias(f"{i}_null"),
                    pl.lit(None, dtype=pl.UInt64).alias(f"{i}_unique"),
                    pl.lit(0).alias(f"{i}_nonfinite"),
                ]
            )
            continue
        metrics.extend(
            [
                pl.col(name).null_count().alias(f"{i}_null"),
                pl.col(name).filter(finite(name, dt)).n_unique().alias(f"{i}_unique"),
                (pl.col(name).is_not_null() & ~pl.col(name).is_finite())
                .sum()
                .alias(f"{i}_nonfinite")
                if dt.is_float()
                else pl.lit(0).alias(f"{i}_nonfinite"),
            ]
        )
    control.progress("Amaç/hedef ve özellik uygunluğu taranıyor", 0, len(columns))
    row = query.select(metrics).collect(engine="streaming").row(0, named=True)
    rows = request["row_count"]
    profiles = []
    risks = []
    blockers = []

    def risk(code, message, column_id="", blocking=False):
        item = dict(
            code=code,
            reason=message,
            column_id=column_id,
            severity="blocker" if blocking else "review",
            certainty="candidate"
            if code
            in ("suspect_target_derivative", "identifier_candidate", "history_decision")
            else "observation",
        )
        risks.append(item)
        if blocking:
            blockers.append(code + (":" + column_id if column_id else ""))

    for i, c in enumerate(columns):
        control.check()
        dt = schema[c["name"]]
        null = int(row[f"{i}_null"])
        bad = int(row[f"{i}_nonfinite"])
        unique = row[f"{i}_unique"]
        valid = rows - null - bad
        role = semantics.get(c["id"], {}).get("role", "")
        p = dict(
            column_id=c["id"],
            name=c["name"],
            dtype=str(dt),
            role=role,
            null_count=null,
            nonfinite_count=bad,
            valid_count=valid,
            unique_count=unique,
            selected=c["id"] in spec.features,
            identifier_candidate=identifier(c, semantics),
        )
        profiles.append(p)
        if p["identifier_candidate"]:
            risk(
                "identifier_candidate",
                "Kimlik rolü veya id/uuid/kimlik adı gözlendi; kimlikler ölçüm değildir. İsme dayalı aday kesin tespit değildir.",
                c["id"],
                blocking=p["selected"] and not spec.allow_identifiers,
            )
        if (
            unique is not None
            and unique >= 20
            and unique / max(valid, 1) > 0.5
            and (dt == pl.String or role in ("category", "ordinal"))
        ):
            risk(
                "high_cardinality",
                f"{unique}/{valid} farklı kategori; one-hot boyutu/bellek ve yeni kategoriler incelenmeli. Sözlük henüz öğrenilmedi.",
                c["id"],
            )
        if c["id"] in spec.features and unique in (0, 1):
            risk(
                "constant_feature",
                "Seçili özellik boş/sabit; eğitim katında kullanılabilirliği yeniden kontrol edilecek.",
                c["id"],
                blocking=valid == 0,
            )
        if p["selected"] and bad and spec.invalid_numeric == "reject":
            risk(
                "nonfinite_feature",
                "Seçili ölçüm NaN/inf içeriyor; reddetme politikası seçili. Açık eksik sayma politikası veya kaynak düzeltmesi gerekir.",
                c["id"],
                True,
            )
        if (
            p["selected"]
            and (null or bad and spec.invalid_numeric == "as_missing")
            and spec.numeric_imputation == "none"
            and (
                (dt.is_numeric() and role not in ("category", "ordinal"))
                or dt.is_temporal()
            )
        ):
            risk(
                "missing_feature",
                "Eksik sayısal özellik var ve imputasyon kapalı; seçili hazırlama yolu bu eksikliği ele almıyor.",
                c["id"],
                True,
            )
        if (
            p["selected"]
            and (null or bad and spec.invalid_numeric == "as_missing")
            and spec.text is None
            and spec.categorical_imputation == "none"
            and (dt == pl.String or dt == pl.Boolean or role in ("category", "ordinal"))
        ):
            risk(
                "missing_feature",
                "Eksik kategori var ve imputasyon kapalı; hazırlama planını düzenleyin.",
                c["id"],
                True,
            )
        if dt.is_temporal():
            risk(
                "temporal_structure",
                "Tarih/zaman alanı var. Tahmin anında bilinen bilgi ve gelecek hedef ufkunu inceleyin; bu rapor geçerli zaman ayırma protokolü kurmaz.",
                c["id"],
            )
    target_info = None
    eligible = rows
    if spec.target:
        c = next(c for c in columns if c["id"] == spec.target)
        dt = schema[c["name"]]
        if dt.is_nested() or dt.is_temporal() or dt == pl.Binary:
            raise ProjectError(
                "Hedef skaler sayısal veya kategori olmalı; tarih/nested/binary hedef desteklenmiyor."
            )
        target_info = dict(next(p for p in profiles if p["column_id"] == spec.target))
        eligible = target_info["valid_count"]
        if rows - eligible:
            risk(
                "missing_target",
                f"{rows - eligible} eksik/sonlu olmayan hedef; hedef doldurulmaz. Gelecekte eğitim kapsamından çıkarma açık kayıt gerektirir.",
                spec.target,
            )
        if target_info["unique_count"] < 2:
            risk(
                "constant_target",
                "Hedef boş veya sabit; bu hedefle tahmin problemi kurulamaz.",
                spec.target,
                True,
            )
        if spec.purpose == "regression" and not dt.is_numeric():
            risk(
                "target_type",
                "Sayısal tahmin için fiziksel sayısal hedef gerekir.",
                spec.target,
                True,
            )
        if spec.purpose == "classification":
            distribution = (
                query.filter(finite(c["name"], dt))
                .group_by(c["name"])
                .len()
                .sort(["len", c["name"]], descending=[True, False])
                .head(20)
                .collect(engine="streaming")
            )
            target_info["class_distribution"] = [
                dict(
                    label=str(v)[:256] + ("…" if len(str(v)) > 256 else ""),
                    count=int(n),
                    **(
                        dict(
                            label_truncated=True,
                            label_sha256=hashlib.sha256(str(v).encode()).hexdigest(),
                        )
                        if len(str(v)) > 256
                        else {}
                    ),
                )
                for v, n in distribution.iter_rows()
            ]
            target_info["distribution_limit"] = 20
            target_info["distribution_truncated"] = target_info["unique_count"] > 20
            minimum = (
                query.filter(finite(c["name"], dt))
                .group_by(c["name"])
                .len()
                .select(pl.col("len").min())
                .collect()
                .item()
            )
            target_info["min_class_count"] = int(minimum or 0)
            if minimum is not None and minimum < 2:
                risk(
                    "rare_class",
                    "En az bir sınıfta2 kayıt yok; eğitim/değerlendirme bölmesi için yeterli temsil olmayabilir.",
                    spec.target,
                    True,
                )
            maximum = max(
                (x["count"] for x in target_info["class_distribution"]), default=0
            )
            if maximum / max(eligible, 1) > 0.8:
                risk(
                    "class_imbalance",
                    "En büyük sınıf geçerli hedeflerin %80inden fazla; yalnız doğruluk yanıltıcı olabilir.",
                    spec.target,
                )
        for feature in spec.features:
            fc = next(c for c in columns if c["id"] == feature)
            name_hint = c["name"].casefold() in fc["name"].casefold() or bool(
                re.search(
                    r"(target|label|hedef|sonuc|sonuç|prediction|tahmin)",
                    fc["name"],
                    re.I,
                )
            )
            dependent = any(
                mentions(op.get("spec", {}).get("parameters", {}), spec.target)
                and feature
                in {
                    co["id"]
                    for co in op.get("spec", {}).get("output_schema", [])
                    if co["id"]
                    not in {
                        c["id"]
                        for c in versions[op["spec"]["input_version_id"]][
                            "import_metadata"
                        ]["columns"]
                    }
                }
                for op in request["history_state"]["operations"]
                if op.get("output_version_id") in source_ancestors
            )
            equal = False
            if dt == schema[fc["name"]] and eligible:
                count = (
                    query.filter(finite(c["name"], dt))
                    .select(
                        (pl.col(fc["name"]) == pl.col(c["name"])).fill_null(False).sum()
                    )
                    .collect()
                    .item()
                )
                equal = count == eligible
            if name_hint or dependent or equal:
                risk(
                    "suspect_target_derivative",
                    "Hedefle ad/işlem bağı veya tüm geçerli hedeflerde aynı değer gözlendi. Tahmin anında mevcut olup olmadığını inceleyin; bu kesin sızıntı tespiti değildir.",
                    feature,
                )
    if eligible < 20:
        risk(
            "sample_size",
            f"{eligible} kullanılabilir hedef/gözlem; örnek miktarı küçük. Bu sayı güç veya genelleme garantisi değildir.",
            blocking=eligible < 2,
        )
    group_info = None
    if spec.group:
        gc = next(c for c in columns if c["id"] == spec.group)
        if schema[gc["name"]].is_nested() or schema[gc["name"]] == pl.Binary:
            raise ProjectError(
                "Grup anahtarı skaler olmalı; nested/binary grup desteklenmiyor."
            )
        p = next(p for p in profiles if p["column_id"] == spec.group)
        group_info = dict(
            p,
            repeat_rows=rows
            - p["null_count"]
            - p["nonfinite_count"]
            - (p["unique_count"] or 0),
        )
        risk(
            "group_structure",
            "Aynı grup/kişinin tekrarları birlikte ayrılmalı; grup ve zaman birlikte gerekebilir. Split bu fazda henüz yapılmaz.",
            spec.group,
        )
        if p["null_count"] or p["nonfinite_count"]:
            risk(
                "missing_group",
                "Grup anahtarında eksik/geçersiz kayıt var; gelecekteki ayırma için çözülmeli.",
                spec.group,
            )
    for f in history["findings"]:
        if not f["removed_from_source"]:
            risk(
                "history_learned"
                if f["risk"] == "dataset_learned"
                else "history_decision",
                f["reason"],
                blocking=True,
            )
    if history["relocation_unavailable"]:
        risk(
            "relocation_unavailable",
            "Seçim/filtre/dedup/sıralı doldurma gibi bazı geçmiş adımlar otomatik fold adımına taşınmıyor. Temiz kaynaktan yeni plan kurun veya kararları ayrıca inceleyin.",
            blocking=True,
        )
    if spec.family == "tree" and spec.scaling == "standard":
        risk(
            "unnecessary_scaling",
            "Ağaç ailesinde standardizasyon genellikle gerekli değildir; açık kullanıcı seçimi kaydedildi.",
        )
    if spec.family != "tree" and spec.scaling == "none":
        risk(
            "scale_sensitive",
            "Seçilen model ailesi ölçeğe duyarlıdır; scaling kapalı seçim açıkça kaydedildi.",
        )
    if (
        spec.time
        and not schema[
            next(c["name"] for c in columns if c["id"] == spec.time)
        ].is_temporal()
    ):
        risk(
            "time_type",
            "Zaman anahtarının fiziksel türü Date/Datetime değil; gelecekte zaman protokolü kurulmadan türü inceleyin.",
            spec.time,
            True,
        )
    if not spec.prediction_context.strip():
        risk(
            "prediction_context",
            "Tahmin anında hangi bilgilerin mevcut olduğu belirtilmedi; hedef türevleri ve zaman yapısını bağlamıyla inceleyin.",
        )
    plan = blueprint(spec, columns, semantics, history)
    plan["version_id"] = "ml-pipeline:" + uid()
    selected = set(spec.features) | {
        v for v in (spec.target, spec.group, spec.time) if v
    }
    width = sum(
        max(1, (p["unique_count"] or 0) + 1)
        if schema[p["name"]] == pl.String and spec.encoding == "onehot"
        else 3
        if schema[p["name"]].is_temporal()
        else 1
        for p in profiles
        if p["column_id"] in spec.features
    )
    cost = dict(
        selected_columns=len(selected),
        selected_features=len(spec.features),
        rows=rows,
        projected_input_bytes=rows * (192 + 80 * len(selected)),
        possible_dense_columns=width,
        possible_dense_bytes=rows * width * 8,
        ram_budget_bytes=control.budget.ram_bytes,
        streaming_fit=False,
        estimate=True,
        caveat="Yaklaşık öngörü; uzun metin, fold kopyaları, sparse/dense dönüşümü ve yöntem ek bellek gerektirebilir. Kategori üst sınırı tam kaynakta gözlenir; eğitim sözlüğü yalnız eğitimde öğrenilir.",
        action="Özellik seçimini daraltın. Gerekirse açık filtreyle daha küçük veri sürümü oluşturun; ilk-N örneklem temsili garanti etmez. Sessiz örnekleme yapılmaz.",
    )
    result = dict(
        schema="PreparationReport/v1",
        spec=spec.data(),
        origin_version=request["origin_version"],
        dataset_version=request["version_id"],
        fitted=False,
        resource_forecast=cost,
        scope="full",
        dataset_n=rows,
        eligible_n=eligible,
        excluded_target_n=rows - eligible,
        columns=profiles,
        target=target_info,
        group=group_info,
        history=history,
        plan=plan,
        risks=risks,
        blockers=blockers,
        status="blocked" if blockers else "review_required",
        leakage_certified=False,
        config_revision=request.get("config_revision", 0),
        provenance=dict(
            snapshot_fingerprint=request["fingerprint"],
            snapshot_uri=request["snapshot_uri"],
            source_snapshot_id=request["source_snapshot_id"],
            backend="polars",
            backend_version=pl.__version__,
            fit_scope=None,
            seed=None,
            seed_reason="Deterministic observational scan and unfitted blueprint; no random training",
            help_content_version=33,
        ),
    )
    checked(request, control)
    Path(workspace, "preparation-report.json").write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    control.disk(Path(workspace))
    control.check()
    return result
