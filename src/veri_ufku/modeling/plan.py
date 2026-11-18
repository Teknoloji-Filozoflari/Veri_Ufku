"""A serializable blueprint: names known structurally; category vocabulary deferred."""

import copy

import polars as pl

from veri_ufku.modeling.plans import strategy_of
from veri_ufku.operations.types import dtype_of
from veri_ufku.storage.project_model import ProjectError

TRAINING_DEPENDENCY = (
    "Requires a validated split/fold protocol in Phase16; no training performed"
)
MOD2_DEPENDENCY = "Mod 2 plan adımları yalnız eğitim katında öğrenilir; test/doğrulama verisine bilgi sıkmaz."
MOD2_REASON = (
    "Mod 2 planı: doldurma istatistiği yalnız eğitim katında öğrenilecek; "
    "test/doğrulama verisine bilgi sıkmaz."
)


def strip_mod2(plan):
    """Mod 2 türevli adım ve alanları çıkarır; kayıt sözleşmesi karşılaştırması için."""
    value = copy.deepcopy(plan)
    value["steps"] = [
        s
        for s in value.get("steps", [])
        if "mod2_plan_id" not in (s.get("parameters") or {})
    ]
    value.pop("mod2_plans", None)
    value.pop("mod2_notes", None)
    dependency = str(value.get("training_dependency", ""))
    value["training_dependency"] = (
        dependency.replace("; " + MOD2_DEPENDENCY, "")
        .replace(MOD2_DEPENDENCY, "")
        .strip()
    )
    return value


def blueprint(spec, columns, semantics, history, mod2_plans=()):
    steps = []
    lineage = []

    def step(kind, inputs, outputs, learned, reason, **parameters):
        steps.append(
            dict(
                kind=kind,
                input_column_ids=inputs,
                output_names=list(outputs),
                learned_scope="training_fold" if learned else "row_local",
                state="planned",
                parameters=parameters,
                reason=reason,
            )
        )

    for col in columns:
        if col["id"] not in spec.features:
            continue
        ident = col["id"]
        dtype = dtype_of(col["type"])
        role = semantics.get(ident, {}).get("role", "")
        prefix = "f_" + ident.removeprefix("col:").replace("-", "")
        outputs = []
        pending = False
        if spec.text is not None:
            if dtype not in (pl.String, pl.Null):
                raise ProjectError("TF-IDF metin alanı String/Null olmalı.")
            numeric = False
            pending = True
            outputs = [prefix + "__token_{training_index}"]
            step(
                "tfidf",
                [ident],
                outputs,
                True,
                "Token vocab ve IDF yalnız eğitim fold'unda öğrenilecek; inceleme vocab'ı kullanılmaz.",
                options=spec.text,
            )
        elif dtype.is_temporal():
            if not spec.date_features or not (
                dtype == pl.Date or isinstance(dtype, pl.Datetime)
            ):
                raise ProjectError(
                    "Tarih özellikleri için Date/Datetime alanı ve açık tarih seçimi gerekir."
                )
            outputs = [prefix + "__" + name for name in ("year", "month", "weekday")]
            step(
                "calendar",
                [ident],
                outputs,
                False,
                "Takvim bileşenleri satırdan üretilir; gelecek/hedef ufku kullanılmaz. Zaman ayırma yine gereklidir.",
                timezone="source_timezone; naive remains naive",
                components=["year", "month", "weekday"],
            )
            numeric = True
        elif dtype.is_numeric() and role not in ("category", "ordinal"):
            outputs = [prefix + "__numeric"]
            numeric = True
            step(
                "numeric",
                [ident],
                outputs,
                False,
                "Kimlik ölçüm değildir; Float64 kaybı gelecekte açık politika ile denetlenir.",
                precision=spec.precision,
                nonfinite=spec.invalid_numeric,
            )
        elif (
            dtype in (pl.String, pl.Boolean, pl.Categorical)
            or isinstance(dtype, pl.Enum)
            or dtype.is_numeric()
            and role in ("category", "ordinal")
        ):
            numeric = False
            if spec.categorical_imputation != "none":
                step(
                    "impute_category",
                    [ident],
                    [],
                    True,
                    "Kategori modunu yalnız eğitim katı öğrenir; eksik hedef doldurulmaz.",
                    strategy=spec.categorical_imputation,
                    all_missing="error",
                )
            if spec.encoding == "ordinal":
                order = semantics.get(ident, {}).get("ordinal_order", [])
                if role != "ordinal" or not order:
                    raise ProjectError(
                        "Ordinal encoding için Veri ekranında açık semantik sıra tanımlayın; nominal alanlara sıra uydurulmaz."
                    )
                outputs = [prefix + "__ordinal"]
                step(
                    "encode_ordinal",
                    [ident],
                    outputs,
                    False,
                    "Sıra kullanıcı tarafından verilmiştir; aralıkların eşitliği model varsayımıdır.",
                    order=order,
                    unknown="error",
                )
            else:
                outputs = [prefix + "__category_{training_index}"]
                pending = True
                step(
                    "encode_onehot",
                    [ident],
                    outputs,
                    True,
                    "Nominal kategorilere sıralama yüklenmez; kategori sözlüğü yalnız eğitim katında öğrenilir.",
                    categories="training_only",
                    unknown="ignore_with_warning",
                    sparse=True,
                    name_binding="training category index -> original ColumnId and category; deferred until fit",
                )
        elif dtype == pl.Null:
            numeric = False
            step(
                "unresolved_type",
                [ident],
                [],
                False,
                "Seçili alanın tamamı eksik; tür ve kullanılabilirlik belirlenmeden hazırlama uygulanamaz.",
            )
        else:
            raise ProjectError(
                "Metin kategorisi/skaler sayılar/Date/Datetime dışında bu model hazırlama planı desteklenmiyor."
            )
        if numeric:
            if spec.numeric_imputation != "none":
                step(
                    "impute_numeric",
                    [ident],
                    outputs,
                    True,
                    "Seçilen doldurma değeri yalnız eğitim katında öğrenilir; test/validation ortalaması kullanılmaz.",
                    strategy=spec.numeric_imputation,
                    all_missing="error",
                )
            scaling = (
                spec.scaling == "standard"
                or spec.scaling == "auto"
                and spec.family != "tree"
            )
            step(
                "standard_scale" if scaling else "no_scaling",
                [ident],
                outputs,
                scaling,
                "Uzaklıklar ve düzenlileştirilmiş doğrusal modeller ölçüm ölçeğine duyarlıdır; eğitim katında standardizasyon planlandı."
                if scaling
                else "Ağaç ailesine scaling otomatik önerilmez; açık none seçiminde diğer ailelerde ölçek duyarlılığını inceleyin.",
                explicit_override=spec.scaling == "standard" and spec.family == "tree",
            )
        lineage.append(
            dict(
                input_column_id=ident,
                source_name=col["name"],
                source_dtype=col["type"],
                output_names=list(outputs),
                names_status="template_training_bound"
                if pending
                else "structurally_known",
                category_map=None if pending else [],
                selected_after_fit="unknown"
                if spec.selection == "variance"
                else "all_planned",
            )
        )
    moved_columns = set()
    for f in history["findings"]:
        if f["resolution"] != "pending_fold_step":
            continue
        inputs = [c for c in f["column_ids"] if c in spec.features]
        if not inputs:
            continue
        for ident in inputs:
            key = (f["kind"], ident)
            if key in moved_columns:
                raise ProjectError(
                    "Aynı alandaki birden fazla geçmiş adım otomatik birleştirilemez; temiz kaynak yolunu seçip açık plan kurun."
                )
            moved_columns.add(key)
        if f["kind"] == "fill":
            for ident in inputs:
                if not any(
                    ident in s["input_column_ids"] and s["kind"].startswith("impute_")
                    for s in steps
                ):
                    line = next(
                        entry for entry in lineage if entry["input_column_id"] == ident
                    )
                    categorical = any(
                        s["kind"].startswith("encode_")
                        and ident in s["input_column_ids"]
                        for s in steps
                    )
                    if categorical and f["method"] != "mode":
                        raise ProjectError(
                            "Geçmiş sayısal doldurma kategorik encoding önüne otomatik taşınamaz; temiz kaynak planını seçin."
                        )
                    kind = "impute_category" if categorical else "impute_numeric"
                    step(
                        kind,
                        [ident],
                        line["output_names"],
                        True,
                        "Eski tüm-veri doldurması yerine eğitim katında yeniden öğrenilecek.",
                        strategy="most_frequent"
                        if f["method"] == "mode"
                        else f["method"],
                        all_missing="error",
                    )
                    inserted = steps.pop()
                    before = next(
                        (
                            i
                            for i, s in enumerate(steps)
                            if ident in s["input_column_ids"]
                            and (
                                s["kind"].startswith("encode_")
                                or s["kind"] in ("standard_scale", "no_scaling")
                            )
                        ),
                        len(steps),
                    )
                    steps.insert(before, inserted)
            for s in steps:
                if set(s["input_column_ids"]) & set(inputs) and s["kind"].startswith(
                    "impute_"
                ):
                    s["parameters"]["strategy"] = (
                        "most_frequent" if f["method"] == "mode" else f["method"]
                    )
                    s["parameters"]["relocated_from_operation_id"] = f["operation_id"]
        else:
            outputs = [
                "f_" + i.removeprefix("col:").replace("-", "") + "__outlier_iqr"
                for i in inputs
            ]
            step(
                "outlier_iqr_mark",
                inputs,
                outputs,
                True,
                "IQR eşiği eğitim katında öğrenilecek; eski tüm-veri eşikleri taşınmaz. Kayıt silinmez.",
                relocated_from_operation_id=f["operation_id"],
                thresholds=None,
                action="mark",
                quantile="linear",
                multiplier=f["policy_parameters"]["multiplier"],
            )
            for item, name in zip(inputs, outputs):
                step_line = next(
                    entry for entry in lineage if entry["input_column_id"] == item
                )
                step_line["output_names"].append(name)
    mod2_notes = []
    mod2_ids = []
    for entry in mod2_plans or ():
        plan = entry.get("plan") if isinstance(entry, dict) else None
        if not isinstance(plan, dict):
            continue
        mod2_ids.append(str(entry.get("id", "")))
        for operation in plan.get("operations", []):
            if operation.get("kind") != "fill" or operation.get("method") not in (
                "mean",
                "median",
                "mode",
            ):
                continue
            strategy = strategy_of(operation["method"])
            for ident in operation["column_ids"]:
                column = next((c for c in columns if c["id"] == ident), None)
                if column is None or ident not in spec.features:
                    mod2_notes.append(
                        f"{ident}: Mod 2 planı seçili olmayan bir kolonu hedefliyor; "
                        "plan bu koşuda uygulanmayacak."
                    )
                    continue
                if any(
                    ident in s["input_column_ids"] and s["kind"].startswith("impute_")
                    for s in steps
                ):
                    mod2_notes.append(
                        f"{column['name']}: kolon zaten spec'te dolduruluyor; "
                        "Mod 2 adımı eklenmedi"
                    )
                    continue
                role = semantics.get(ident, {}).get("role", "")
                categorical = (
                    role in ("category", "ordinal")
                    or not dtype_of(column["type"]).is_numeric()
                )
                line = next(
                    (item for item in lineage if item["input_column_id"] == ident),
                    None,
                )
                step(
                    "impute_category" if categorical else "impute_numeric",
                    [ident],
                    list(line["output_names"]) if line else [],
                    True,
                    MOD2_REASON,
                    strategy=strategy,
                    all_missing="error",
                    mod2_plan_id=str(entry.get("id", "")),
                )
                inserted = steps.pop()
                before = next(
                    (
                        i
                        for i, s in enumerate(steps)
                        if ident in s["input_column_ids"]
                        and (
                            s["kind"].startswith("encode_")
                            or s["kind"] in ("standard_scale", "no_scaling")
                        )
                    ),
                    len(steps),
                )
                steps.insert(before, inserted)
    if spec.selection == "variance":
        step(
            "select_variance",
            list(spec.features),
            [],
            True,
            "Sabit/az değişen özellik seçimi yalnız eğitim katında öğrenilir; hangi çıktıların kalacağı henüz bilinmez.",
            threshold=0,
            mask=None,
        )
    numeric_ids = [
        s["input_column_ids"][0] for s in steps if s["kind"] in ("numeric", "calendar")
    ]
    if spec.numeric_imputation in ("knn", "iterative"):
        if any(
            f["resolution"] == "pending_fold_step" and f["kind"] == "fill"
            for f in history["findings"]
        ):
            raise ProjectError(
                "Eski doldurma adımı KNN/iterative ile sessizce yeniden yorumlanmaz; temiz kaynak ve açık yeni plan seçin."
            )
        if not numeric_ids or spec.text is not None:
            raise ProjectError(
                "KNN/iterative en az bir sayısal özellik ister; TF-IDF için kullanılamaz."
            )
        first = [s for s in steps if s["kind"] in ("numeric", "calendar")]
        rest = [
            s
            for s in steps
            if s["kind"] not in ("numeric", "calendar", "impute_numeric")
        ]
        step(
            "impute_joint",
            numeric_ids,
            [],
            True,
            "Çok değişkenli tek doldurma yalnız eğitim katında fit edilir; MI değildir. KNN ham birim uzaklıkları kullanır, birimleri inceleyin.",
            strategy=spec.numeric_imputation,
            neighbors=spec.imputation_neighbors,
            iterations=spec.imputation_iterations,
            seed=spec.imputation_seed,
        )
        joint = steps.pop()
        steps = first + [joint] + rest
    if spec.missing_indicator:
        step(
            "missing_indicator",
            list(spec.features),
            [],
            False,
            "Eksik göstergesi özgün satırdan üretilir; validation eksikleri de işaretlenir, doldurma öncesi değer korunur.",
        )
        for line in lineage:
            line["output_names"].append(
                "f_"
                + line["input_column_id"].removeprefix("col:").replace("-", "")
                + "__missing"
            )
    return dict(
        schema="PreparationPlan/v1",
        fit_state="not_fitted",
        fitted_parameters={},
        estimator_family=spec.family,
        steps=steps,
        column_lineage=lineage,
        training_dependency=(
            TRAINING_DEPENDENCY + ("; " + MOD2_DEPENDENCY if mod2_ids else "")
        ),
        category_vocabulary=None,
        feature_selection_mask=None,
        mod2_plans=mod2_ids,
        mod2_notes=mod2_notes,
    )
