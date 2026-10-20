"""Descriptive full-snapshot change reports and explicit keyed delayed-target scoring."""

import math
from decimal import Decimal, localcontext

import polars as pl

from veri_ufku.analytics.dataset import checked
from veri_ufku.importers.delimited import Control
from veri_ufku.storage.project_model import ProjectError

NOTE = "Tam snapshot betimlemesi; test/p-değeri/eşik kullanılmaz. Örneklem büyüklüğü ve veri toplama farkları dağılımı etkileyebilir. Dağılım değişimi otomatik model başarısızlığı değildir; hedef olmadan başarı metriği hesaplanmaz."


def summary(series):
    n = len(series)
    result = dict(
        n=n,
        missing=series.null_count(),
        missing_rate=series.null_count() / n if n else None,
        dtype=str(series.dtype),
    )
    if series.dtype.is_numeric():
        if isinstance(series.dtype, pl.Decimal) or series.dtype.is_integer():
            values = sorted(Decimal(v) for v in series.drop_nulls())
            result.update(
                valid_n=len(values),
                nonfinite=0,
                precision="exact Decimal80; numeric summaries serialized as decimal text",
            )

            def quantile(q):
                h = Decimal(len(values) - 1) * q
                lower = int(h)
                return values[lower] + (
                    values[min(lower + 1, len(values) - 1)] - values[lower]
                ) * (h - lower)

            with localcontext() as context:
                context.prec = 80
                stats = (
                    dict(
                        min=values[0],
                        max=values[-1],
                        mean=sum(values) / len(values),
                        q25=quantile(Decimal(".25")),
                        median=quantile(Decimal(".5")),
                        q75=quantile(Decimal(".75")),
                    )
                    if values
                    else dict.fromkeys(("min", "max", "mean", "q25", "median", "q75"))
                )
                result.update(
                    {k: str(v) if v is not None else None for k, v in stats.items()}
                )
            return result
        values = [float(v) for v in series.drop_nulls() if math.isfinite(float(v))]
        result.update(
            valid_n=len(values), nonfinite=n - series.null_count() - len(values)
        )
        if values:
            s = pl.Series(values)
            result.update(
                min=min(values),
                max=max(values),
                mean=math.fsum(v / len(values) for v in values),
                q25=s.quantile(0.25, interpolation="linear"),
                median=s.median(),
                q75=s.quantile(0.75, interpolation="linear"),
            )
        else:
            result.update(
                min=None, max=None, mean=None, q25=None, median=None, q75=None
            )
    elif series.dtype in (pl.String, pl.Boolean, pl.Categorical, pl.Enum):
        counts = series.drop_nulls().cast(pl.String).value_counts(sort=True)
        counts = counts.sort(["count", counts.columns[0]], descending=[True, False])
        result["categories"] = [
            dict(value=r[0], count=r[1], rate=r[1] / n if n else None)
            for r in counts.head(30).rows()
        ]
        result["distinct"] = counts.height
        result["other_count"] = counts["count"].slice(30).sum()
        result["category_limit"] = 30
    else:
        result["distribution"] = "Bu fiziksel tür için dağılım özeti desteklenmiyor."
    return result


def compare(old, new, mapping, control=None):
    control = control or Control()
    for request in (old, new):
        checked(request, control)
        if request["row_count"] > 100000:
            raise ProjectError(
                "Dağılım karşılaştırması tam snapshot için 100000 kayıtla sınırlı."
            )
    a, b = pl.read_parquet(old["path"]), pl.read_parquet(new["path"])
    reports = []
    used = set()
    for c in old["columns"]:
        control.check()
        target = next(
            (d for d in new["columns"] if d["id"] == mapping.get(c["id"])), None
        )
        if not target:
            reports.append(
                dict(
                    name=c["name"],
                    schema_change="removed/unmapped",
                    before=summary(a[c["name"]]),
                    after=None,
                )
            )
            continue
        used.add(target["id"])
        reports.append(
            dict(
                name=c["name"],
                new_name=target["name"],
                schema_change="type_changed"
                if c["type"] != target["type"]
                else "renamed"
                if c["name"] != target["name"]
                else "same",
                before=summary(a[c["name"]]),
                after=summary(b[target["name"]]),
                role_before=old.get("semantic_metadata", {}).get(c["id"], {}),
                role_after=new.get("semantic_metadata", {}).get(target["id"], {}),
            )
        )
    for c in new["columns"]:
        if c["id"] not in used:
            reports.append(
                dict(
                    name=c["name"],
                    schema_change="added/unmapped",
                    before=None,
                    after=summary(b[c["name"]]),
                )
            )
    return dict(
        schema="DatasetChange/v1",
        old_version=old["version_id"],
        new_version=new["version_id"],
        old_fingerprint=old["fingerprint"],
        new_fingerprint=new["fingerprint"],
        scope="full",
        columns=reports,
        method="descriptive-null-category-quantiles/v1",
        note=NOTE,
        metrics=None,
    )


def evaluate(
    predictions,
    targets,
    prediction_key,
    target_key,
    prediction_column,
    target_column,
    purpose,
):
    """No positional join, duplicate keys or inferred target. Report unmatched and invalid."""
    if purpose not in ("regression", "classification"):
        raise ProjectError(
            "Performans yalnız etiketli regression/classification için hesaplanır."
        )
    if (
        prediction_column not in predictions.columns
        or target_column not in targets.columns
    ):
        raise ProjectError(
            "Tahmin veya gerçek hedef kolonu bulunamadı; başarı metriği hesaplanmadı."
        )
    for frame, key in ((predictions, prediction_key), (targets, target_key)):
        if (
            key not in frame.columns
            or frame[key].null_count()
            or frame[key].n_unique() != frame.height
        ):
            raise ProjectError(
                "Eşleme anahtarı boş/tekrarlı; satır sırası ile eşleme yapılmaz."
            )
    if predictions[prediction_key].dtype != targets[target_key].dtype:
        raise ProjectError("Kimlik türleri uyuşmuyor.")
    joined = predictions.select(
        pl.col(prediction_key).alias("key"),
        pl.col(prediction_column).alias("prediction"),
    ).join(
        targets.select(
            pl.col(target_key).alias("key"), pl.col(target_column).alias("target")
        ),
        on="key",
        how="inner",
    )
    valid = joined.drop_nulls(["prediction", "target"])
    for name in ("prediction", "target"):
        if valid[name].dtype.is_float():
            valid = valid.filter(pl.col(name).is_finite())
    if purpose == "regression":
        if (
            not valid["prediction"].dtype.is_numeric()
            or not valid["target"].dtype.is_numeric()
        ):
            raise ProjectError("Sayısal performans için sayısal hedef/tahmin gerekir.")
        # Refuse silent precision loss for large integer/decimal targets.
        if any(
            isinstance(valid[k].dtype, pl.Decimal) for k in ("prediction", "target")
        ) or any(
            abs(float(v)) > 2**53 for k in ("prediction", "target") for v in valid[k]
        ):
            raise ProjectError("Float64 hassasiyet sınırı; performans hesaplanmadı.")
        valid = valid.filter(
            pl.col("prediction").is_finite() & pl.col("target").is_finite()
        )
        errors = [float(p) - float(t) for _, p, t in valid.rows()]
        metrics = (
            dict(
                mae=sum(abs(e) for e in errors) / len(errors),
                rmse=math.sqrt(sum(e * e for e in errors) / len(errors)),
            )
            if errors
            else None
        )
    else:
        if valid["prediction"].dtype != valid["target"].dtype:
            raise ProjectError("Tahmin/hedef sınıf türleri uyuşmuyor.")
        metrics = (
            dict(accuracy=sum(p == t for _, p, t in valid.rows()) / valid.height)
            if valid.height
            else None
        )
    return dict(
        schema="DelayedPerformance/v1",
        purpose=purpose,
        matched=joined.height,
        scored=valid.height,
        invalid=joined.height - valid.height,
        unmatched_predictions=predictions.height - joined.height,
        unmatched_targets=targets.height - joined.height,
        metrics=metrics,
        note="Sonradan gelen gerçek hedef; kimlik ile eşlenmiş keşifsel yeni performans. Eğitim/final test metriği değildir.",
    )
