"""Read-only all-column inventory and explicit descriptive summaries."""

from collections import Counter

import polars as pl

from veri_ufku.analytics.contracts import ProfileSpec, ViewSpec
from veri_ufku.analytics.dataset import checked, profile
from veri_ufku.importers.delimited import Control, ImportSettings, TypeInference


def content_types(query, schema, request, control):
    """Inspect legacy text values without casting or rewriting the snapshot."""
    names = [c["name"] for c in request["columns"] if schema[c["name"]] == pl.String]
    if not names:
        return {}
    saved = request.get("import_settings", {})
    settings = ImportSettings(
        **{k: saved[k] for k in ("decimal", "thousands", "date_format") if k in saved}
    )
    candidates = {name: TypeInference(settings) for name in names}
    done = 0
    batches = query.select(names).collect_batches(
        chunk_size=4096, engine="streaming", lazy=True
    )
    for batch in batches:
        control.check()
        for name, candidate in candidates.items():
            if candidate.options:
                for value in batch[name]:
                    candidate.observe(value)
        done += batch.height
        control.progress("Sütun içerik türleri", done, request["row_count"])
    labels = {
        "int64": "Int64",
        "decimal": "Decimal(precision=38, scale=6)",
        "date": "Date",
        "boolean": "Boolean",
        "text": "String",
    }
    return {name: labels[candidate.resolve()] for name, candidate in candidates.items()}


def inspect(request, parameters, workspace, control=None):
    control = control or Control()
    checked(request, control)
    sample = parameters.get("sample", True)
    query = pl.scan_parquet(request["path"])
    schema = query.collect_schema()
    population = request["row_count"]
    used = min(population, control.budget.sample_limit_rows) if sample else population
    if sample:
        query = query.head(control.budget.sample_limit_rows)
    expressions = [pl.len().alias("rows")]
    for index, column in enumerate(request["columns"]):
        value = pl.col(column["name"])
        expressions.append(value.null_count().alias(f"null_{index}"))
        if schema[column["name"]].is_float():
            expressions.append(value.is_nan().sum().alias(f"nan_{index}"))
    counts = query.select(expressions).collect(engine="streaming").row(0, named=True)
    control.check()
    columns = []
    for index, column in enumerate(request["columns"]):
        control.check()
        dtype = schema[column["name"]]
        entry = dict(
            column,
            physical_type=str(dtype),
            content_type=str(dtype),
            non_null=used - counts[f"null_{index}"],
            null=counts[f"null_{index}"],
            nan=counts.get(f"nan_{index}", 0),
        )
        if parameters.get("describe") and dtype.is_numeric():
            result = profile(
                request,
                ProfileSpec(column["id"], sample, "dataset", 1, ViewSpec()),
                workspace,
                control,
            )
            entry["numeric"] = result["numeric"]
            entry["role"] = result["role"]
            entry["warnings"] = result["warnings"]
        columns.append(entry)
        control.progress("Sütun özeti", index + 1, len(request["columns"]))
    checked(request, control)
    return dict(
        dataset_version=request["version_id"],
        scope="sample" if used < population else "full",
        used_n=used,
        population_n=population,
        columns=columns,
        types=dict(Counter(c["content_type"] for c in columns)),
        stored_types=dict(Counter(c["physical_type"] for c in columns)),
        snapshot_bytes=request["fingerprint"]["size"],
        describe=bool(parameters.get("describe")),
        ddof=1,
        quantile_method="linear",
        excludes="numeric: null, NaN, +/-infinity; identifier/category summaries suppressed",
        filters=[],
    )
