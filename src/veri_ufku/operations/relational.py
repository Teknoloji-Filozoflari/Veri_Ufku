"""Bounded transformations, exact join estimates and immutable relation Parquet edges."""

import math
import sqlite3
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path

import polars as pl

from veri_ufku.importers.native import EXTRA, restore
from veri_ufku.operations.cleaning import batches, exact_value, key
from veri_ufku.operations.formula import evaluate, numeric
from veri_ufku.operations.relational_contracts import (
    GROUPED,
    MULTI,
    NEW_ROWS,
    input_versions,
)
from veri_ufku.operations.types import dtype_of
from veri_ufku.storage.project_model import ProjectError, decode, encode, uid

PREFIX = "__vu_phase11_"
LP = PREFIX + "lpos"
RP = PREFIX + "rpos"
LR = PREFIX + "lrow"
RR = PREFIX + "rrow"
LS = PREFIX + "lsr"
RS = PREFIX + "rsr"
SIDE = PREFIX + "side"
EDGE_SCHEMA = {
    "output_row_id": pl.String,
    "input_version_id": pl.String,
    "input_row_id": pl.String,
    "source_record_id": pl.String,
    "side": pl.String,
    "column_id": pl.String,
    "occurrence": pl.Int64,
}


def relation_row(out, version, parent, source, side, column=None, occurrence=0):
    return dict(
        output_row_id=out,
        input_version_id=version,
        input_row_id=parent,
        source_record_id=source,
        side=side,
        column_id=column,
        occurrence=occurrence,
    )


def safe_keys(query, names, schema):
    for n in names:
        if (
            schema[n].is_float()
            and query.select((pl.col(n).is_nan() | pl.col(n).is_infinite()).any())
            .collect(engine="streaming")
            .item()
        ):
            raise ProjectError(
                "Join/grup anahtarında NaN/inf var; null'dan ayrı tutulur. Önce açık temizleme seçin."
            )


def join_plan(request, spec):
    p = spec.parameters
    other = request["secondary"]
    left = pl.scan_parquet(request["path"])
    right = pl.scan_parquet(other["path"])
    lc = {c["id"]: c["name"] for c in request["columns"]}
    rc = {c["id"]: c["name"] for c in other["columns"]}
    lk = [lc[i] for i in p["left_keys"]]
    rk = [rc[i] for i in p["right_keys"]]
    safe_keys(left, lk, left.collect_schema())
    safe_keys(right, rk, right.collect_schema())
    counts_left = left.group_by(lk).len(name=LP)
    counts_right = (
        right.group_by(rk).len(name=RP).rename(dict(zip(rk, lk, strict=True)))
    )
    summary = counts_left.join(
        counts_right,
        on=lk,
        how="full",
        coalesce=True,
        nulls_equal=p["nulls_equal"],
        maintain_order="left_right",
    )
    s = (
        summary.select(
            (pl.col(LP).cast(pl.Int64) * pl.col(RP).cast(pl.Int64))
            .fill_null(0)
            .sum()
            .alias("matches"),
            pl.when(pl.col(RP).is_null())
            .then(pl.col(LP))
            .otherwise(0)
            .sum()
            .alias("left_unmatched"),
            pl.when(pl.col(LP).is_null())
            .then(pl.col(RP))
            .otherwise(0)
            .sum()
            .alias("right_unmatched"),
            (pl.col(LP).fill_null(0).max() > 1).alias("left_many"),
            (pl.col(RP).fill_null(0).max() > 1).alias("right_many"),
        )
        .collect(engine="streaming")
        .row(0, named=True)
    )
    count = (
        int(s["matches"] or 0)
        + (int(s["left_unmatched"] or 0) if p["how"] in ("left", "full") else 0)
        + (int(s["right_unmatched"] or 0) if p["how"] in ("right", "full") else 0)
    )
    relation = (
        ("n" if s["left_many"] else "1") + ":" + ("n" if s["right_many"] else "1")
    )
    right_names = {rc[i["column_id"]]: i["output"]["name"] for i in p["right_outputs"]}
    left = left.with_row_index(LP).with_columns(
        pl.col("__vu_row_id").alias(LR), pl.col("__vu_source_record_id").alias(LS)
    )
    right = right.with_row_index(RP).select(
        [pl.col(n).alias(right_names[n]) for n in rc.values()]
        + [
            pl.col(RP),
            pl.col("__vu_row_id").alias(RR),
            pl.col("__vu_source_record_id").alias(RS),
        ]
    )
    output = left.join(
        right,
        left_on=lk,
        right_on=[right_names[n] for n in rk],
        how=p["how"],
        nulls_equal=p["nulls_equal"],
        coalesce=False,
        maintain_order="left_right",
    )
    order = [RP, LP] if p["how"] == "right" else [LP, RP]
    output = output.sort(order, nulls_last=True, maintain_order=True)
    return output, dict(
        predicted_rows=count,
        relationship=relation,
        left_unmatched=int(s["left_unmatched"] or 0),
        right_unmatched=int(s["right_unmatched"] or 0),
        matched_pairs=int(s["matches"] or 0),
        nulls_equal=p["nulls_equal"],
        ordering="right_then_left_input"
        if p["how"] == "right"
        else "left_then_right_input",
    )


def internals(frame):
    expr = []
    for n, t in EXTRA.items():
        if n not in frame.columns:
            expr.append(pl.lit(None, dtype=t).alias(n))
    return frame.with_columns(expr)


def synthetic(frame, spec, ids):
    return frame.with_columns(
        pl.Series("__vu_row_id", ids, dtype=pl.String),
        pl.lit(None, dtype=pl.String).alias("__vu_source_record_id"),
        pl.lit(None, dtype=pl.Int64).alias("__vu_start_line"),
        pl.lit(None, dtype=pl.Int64).alias("__vu_end_line"),
        pl.lit("lineage:" + spec.id).alias("__vu_source_locator"),
        pl.lit([], dtype=pl.List(pl.String)).alias("__vu_missing_fields"),
        pl.lit("{}").alias("__vu_expansion_index"),
    )


def bounded_sum_value(number, dt, diagnostics):
    if dt.is_float():
        value = float(number)
        if not math.isfinite(value) or value == 0 and number != 0:
            raise ProjectError(
                "Float toplulaştırma taşma/underflow üretiyor; işlem uygulanmadı."
            )
        diagnostics["rounded_values"] += Decimal.from_float(value) != number
        return value
    return exact_value(number, dt)


def metric_update(state, value, method):
    state["count"] += 1
    if value is None:
        return
    state["valid"] += 1
    if method in ("sum", "mean"):
        state["sum"] = str(Decimal(state["sum"]) + numeric(value))
    elif method in ("min", "max", "reject"):
        decimal = isinstance(value, Decimal)
        low = (
            Decimal(state["min"])
            if decimal and state["min"] is not None
            else state["min"]
        )
        high = (
            Decimal(state["max"])
            if decimal and state["max"] is not None
            else state["max"]
        )
        if low is None or value < low:
            state["min"] = str(value) if decimal else value
        if high is None or value > high:
            state["max"] = str(value) if decimal else value


def metric_result(state, method, dt, source_dt, diagnostics):
    if state is None:
        return 0 if method == "count" else None
    if method == "count":
        return state["count"]
    if method == "count_valid":
        return state["valid"]
    if not state["valid"]:
        return None
    if method in ("sum", "mean"):
        number = Decimal(state["sum"])
        if method == "mean":
            number /= state["valid"]
        return bounded_sum_value(number, dt, diagnostics)
    value = state["min" if method in ("min", "reject") else "max"]
    return Decimal(value) if isinstance(source_dt, pl.Decimal) else value


def empty_state():
    return dict(count=0, valid=0, sum="0", min=None, max=None)


def grouped(request, spec, workspace, control, diagnostics):
    p = spec.parameters
    cols = {c["id"]: c["name"] for c in request["columns"]}
    schema = pl.read_parquet_schema(request["path"])
    groups = [cols[i] for i in p["group_columns"]]
    query = pl.scan_parquet(request["path"])
    safe_keys(query, groups, schema)
    if spec.kind == "pivot":
        header = cols[p["header_column"]]
        if (
            query.select(pl.col(header).is_null().any())
            .collect(engine="streaming")
            .item()
        ):
            raise ProjectError(
                "Pivot başlığı null olamaz; önce açık eşleme/doldurma seçin."
            )
        categories = (
            query.select(header)
            .unique(maintain_order=True)
            .head(257)
            .collect(engine="streaming")[header]
            .to_list()
        )
        if len(categories) > 256 - len(groups):
            raise ProjectError(
                "Pivot256 sütun sınırını aşıyor; kategori kapsamını azaltın."
            )
        if not categories:
            raise ProjectError("Boş veride pivot başlıkları yok.")
        resolved = []
        used = set(groups)
        for value in categories:
            name = "Pivot_" + str(value)
            if name in used:
                raise ProjectError(
                    "Pivot başlık adı grup sütunuyla çakışıyor; grup adını değiştirin."
                )
            used.add(name)
            resolved.append(
                dict(
                    value=str(value),
                    output=dict(
                        id="col:" + uid(),
                        name=name,
                        original_name=str(value),
                        type=str(restore(p["target"])),
                    ),
                )
            )
        params = dict(p, resolved_headers=resolved)
        from veri_ufku.operations.contracts import build

        rebuilt = build(request, spec.kind, spec.column_ids, params, spec.destination)
        spec = replace(spec, parameters=params, output_schema=rebuilt.output_schema)
        p = spec.parameters
        metrics = [
            dict(
                column_id=p["value_column"],
                method=p["aggregation"],
                target=p["target"],
                output=h["output"],
                category=h["value"],
            )
            for h in resolved
        ]
    else:
        metrics = p["metrics"]
    group_db = sqlite3.connect(Path(workspace) / "groups.sqlite")
    parts = []
    edge_parts = []
    output = Path(workspace) / (uid() + ".parquet")
    relation = Path(workspace) / (uid() + "-lineage.parquet")
    group_db.execute(
        "CREATE TABLE g(k TEXT PRIMARY KEY, id TEXT, anchor TEXT, position INTEGER, state TEXT)"
    )
    temporal = {
        n
        for n in groups
        + [cols[m["column_id"]] for m in metrics if m["column_id"] is not None]
        if schema[n].is_temporal()
    }
    position = 0
    group_count = 0
    collisions = 0
    try:
        with localcontext() as ctx:
            ctx.prec = 1200
            for frame in batches(query, control, workspace):
                physical = {n: frame[n].cast(pl.Int64).to_list() for n in temporal}
                edges = []
                for index, row in enumerate(frame.iter_rows(named=True)):
                    control.check()
                    gkey = encode(
                        [
                            key(physical[n][index] if n in physical else row[n])
                            for n in groups
                        ]
                    ).decode()
                    found = group_db.execute(
                        "SELECT id,anchor,position,state FROM g WHERE k=?", (gkey,)
                    ).fetchone()
                    if found:
                        rid, anchor, first, state = found
                        state = decode(state.encode())
                    else:
                        rid, anchor, first, state = (
                            "row:" + uid(),
                            row["__vu_row_id"],
                            position,
                            {},
                        )
                        group_count += 1
                        if group_count > p["max_output_rows"]:
                            raise ProjectError(
                                "Toplulaştırma çıktı satır bütçesini aşıyor."
                            )
                    column_out = None
                    for m in metrics:
                        if (
                            spec.kind == "pivot"
                            and str(row[cols[p["header_column"]]]) != m["category"]
                        ):
                            continue
                        mi = m["output"]["id"]
                        accumulator = state.setdefault(mi, empty_state())
                        if spec.kind == "pivot" and accumulator["count"]:
                            collisions += 1
                            if p["aggregation"] == "reject":
                                raise ProjectError(
                                    "Pivot hücresinde birden çok kayıt var; sum/mean/min/max/count agregasyonunu açıkça seçin."
                                )
                        n = cols.get(m["column_id"])
                        value = (
                            physical[n][index]
                            if n in physical
                            else row[n]
                            if n
                            else None
                        )
                        if isinstance(value, float) and not math.isfinite(value):
                            raise ProjectError(
                                "Toplulaştırma NaN/inf ölçümünü sessiz null saymaz; önce açık temizleme seçin."
                            )
                        metric_update(accumulator, value, m["method"])
                        column_out = mi if spec.kind == "pivot" else None
                    group_db.execute(
                        "INSERT OR REPLACE INTO g VALUES (?,?,?,?,?)",
                        (gkey, rid, anchor, first, encode(state).decode()),
                    )
                    edges.append(
                        relation_row(
                            rid,
                            request["version_id"],
                            row["__vu_row_id"],
                            row["__vu_source_record_id"],
                            "member",
                            column_out,
                        )
                    )
                    position += 1
                group_db.commit()
                edge = Path(workspace) / (uid() + "-edge.parquet")
                pl.DataFrame(edges, schema=EDGE_SCHEMA).write_parquet(edge)
                edge_parts.append(edge)
                control.disk(workspace)
                control.progress(
                    "Gruplar ve tam üyelik", position, request["row_count"]
                )
            if not group_count and not groups and spec.kind == "aggregate":
                group_db.execute(
                    "INSERT INTO g VALUES (?,?,?,?,?)",
                    ("[]", "row:" + uid(), None, 0, encode({}).decode()),
                )
                group_count = 1
            cursor = group_db.execute("SELECT id,anchor,state FROM g ORDER BY position")
            while records := cursor.fetchmany(4096):
                control.check()
                states = [decode(r[2].encode()) for r in records]
                values = {}
                for m in metrics:
                    n = cols.get(m["column_id"])
                    dt = restore(m["target"])
                    src = schema[n] if n else pl.Int64
                    v = [
                        metric_result(
                            s.get(m["output"]["id"]), m["method"], dt, src, diagnostics
                        )
                        for s in states
                    ]
                    series = pl.Series(
                        m["output"]["name"],
                        v,
                        dtype=pl.Int64 if dt.is_temporal() else dt,
                        strict=True,
                    )
                    values[series.name] = (
                        series.cast(dt) if dt.is_temporal() else series
                    )
                frame = pl.DataFrame(values).with_columns(
                    pl.Series("__vu_row_id", [r[0] for r in records]),
                    pl.Series(LR, [r[1] for r in records], dtype=pl.String),
                )
                part = Path(workspace) / (uid() + "-metrics.parquet")
                frame.write_parquet(part)
                parts.append(part)
        if not parts:
            types = {m["output"]["name"]: restore(m["target"]) for m in metrics}
            types.update(__vu_row_id=pl.String)
            types[LR] = pl.String
            part = Path(workspace) / (uid() + "-metrics.parquet")
            pl.DataFrame(schema=types).write_parquet(part)
            parts.append(part)
        metrics_query = pl.scan_parquet(parts)
        if groups:
            anchors = query.select(
                [pl.col("__vu_row_id").alias(LR)] + [pl.col(n) for n in groups]
            )
            metrics_query = metrics_query.join(
                anchors, on=LR, how="left", maintain_order="left"
            )
        frame_schema = {c["name"]: dtype_of(c["type"]) for c in spec.output_schema}
        final = metrics_query.select(list(frame_schema) + ["__vu_row_id"])
        final = final.with_columns(
            pl.lit(None, dtype=pl.String).alias("__vu_source_record_id"),
            pl.lit(None, dtype=pl.Int64).alias("__vu_start_line"),
            pl.lit(None, dtype=pl.Int64).alias("__vu_end_line"),
            pl.lit("lineage:" + spec.id).alias("__vu_source_locator"),
            pl.lit([], dtype=pl.List(pl.String)).alias("__vu_missing_fields"),
            pl.lit("{}").alias("__vu_expansion_index"),
        )
        final.sink_parquet(output, maintain_order=True, engine="streaming")
        if edge_parts:
            pl.scan_parquet(edge_parts).sink_parquet(
                relation, maintain_order=True, engine="streaming"
            )
        else:
            pl.DataFrame(schema=EDGE_SCHEMA).write_parquet(relation)
        diagnostics["new_nulls"] = (
            pl.scan_parquet(output)
            .select(
                pl.sum_horizontal(
                    [pl.col(m["output"]["name"]).null_count() for m in metrics]
                )
            )
            .collect()
            .item()
        )
        diagnostics.update(
            predicted_rows=group_count,
            group_count=group_count,
            pivot_collisions=collisions,
            relation_rows=position,
        )
        if any(restore(m["target"]).is_float() for m in metrics):
            diagnostics["warnings"].append(
                "Float64 toplulaştırma yaklaşık binary aritmetik çıktısıdır; yuvarlanan sonuç sayısı raporlanır. Kesin ondalık için Decimal seçin."
            )
        return spec, output, relation
    finally:
        group_db.close()
        (Path(workspace) / "groups.sqlite").unlink(missing_ok=True)
        for part in parts + edge_parts:
            part.unlink(missing_ok=True)


def execute(request, spec, workspace, control):
    if any(
        c["name"].startswith(PREFIX)
        for r in [request] + ([request["secondary"]] if "secondary" in request else [])
        for c in r["columns"]
    ):
        raise ProjectError(
            "Girdi geçici işlem ad alanıyla çakışıyor; önce sütunu yeniden adlandırın."
        )
    p = spec.parameters
    cols = {c["id"]: c["name"] for c in request["columns"]}
    query = pl.scan_parquet(request["path"])
    d = dict(
        warnings=[],
        new_nulls=0,
        changed_cells=0,
        modified_rows=0,
        zero_divisions=0,
        rounded_values=0,
        examples=[],
        parse_errors=0,
        relation_rows=0,
    )
    versions = input_versions(request, spec.kind, p)
    relation = None
    if spec.kind in GROUPED:
        spec, output, relation = grouped(request, spec, workspace, control, d)
    else:
        if spec.kind == "join":
            query, stats = join_plan(request, spec)
            d.update(stats)
            d["warnings"].append(
                f"Join {stats['relationship']}: tam anahtar sayımlarından {stats['predicted_rows']} çıktı; sol eşleşmeyen {stats['left_unmatched']}, sağ eşleşmeyen {stats['right_unmatched']}. İki kaynağa bağlı yeni satırlar; tek SourceRecordId yok."
            )
        elif spec.kind == "append":
            queries = []
            for side, r in enumerate([request, request["secondary"]]):
                names = {c["id"]: c["name"] for c in r["columns"]}
                key_id = "left_column" if side == 0 else "right_column"
                expr = [
                    pl.col(names[m[key_id]]).alias(m["output"]["name"])
                    if m[key_id] is not None
                    else pl.lit(None, dtype=dtype_of(m["output"]["type"])).alias(
                        m["output"]["name"]
                    )
                    for m in p["mapping"]
                ]
                src = pl.scan_parquet(r["path"])
                expr += [
                    pl.col("__vu_row_id").alias(LR),
                    pl.col("__vu_source_record_id").alias(LS),
                    pl.lit(side).cast(pl.Int64).alias(SIDE),
                ]
                queries.append(src.select(expr))
            query = pl.concat(queries)
            d["predicted_rows"] = sum(
                r["row_count"] for r in [request, request["secondary"]]
            )
            d["warnings"].append(
                "Append açık eşlemeyle sol kayıtlar ardından sağ kayıtları ekler. Eksik taraf yalnız seçilen null alanlarla tamamlanır; tür dönüşümü veya sütun düşürme yok."
            )
        elif spec.kind == "unpivot":
            idx = [cols[i] for i in p["index_columns"]]
            val = [cols[i] for i in p["value_columns"]]
            query = (
                query.with_row_index(LP)
                .with_columns(
                    pl.col("__vu_row_id").alias(LR),
                    pl.col("__vu_source_record_id").alias(LS),
                )
                .unpivot(
                    on=val,
                    index=idx
                    + [
                        LP,
                        LR,
                        LS,
                        "__vu_row_id",
                        "__vu_source_record_id",
                        "__vu_start_line",
                        "__vu_end_line",
                    ],
                    variable_name=p["variable_output"]["name"],
                    value_name=p["value_output"]["name"],
                )
            )
            rank = p["variable_output"]["name"]
            query = query.with_columns(
                pl.col(rank)
                .replace_strict(
                    {n: i for i, n in enumerate(val)}, return_dtype=pl.Int64
                )
                .alias(RP)
            ).sort([LP, RP], maintain_order=True)
            d["predicted_rows"] = request["row_count"] * len(val)
        elif spec.kind == "date_parts":
            value = pl.col(cols[spec.column_ids[0]])
            if p["timezone"] != "preserve":
                value = value.dt.convert_time_zone(p["timezone"])
            query = query.with_columns(
                [
                    getattr(value.dt, item["part"])()
                    .cast(pl.Int64)
                    .alias(item["output"]["name"])
                    for item in p["parts"]
                ]
            )
            d["warnings"].append(
                "Tarih parçaları seçili timezone'da hesaplanır; naive zaman UTC sayılmaz. ISO hafta günü Pazartesi1–Pazar7. Kaynak an/tür değişmez."
            )
        if spec.kind in ("join", "append", "unpivot"):
            if d["predicted_rows"] > p["max_output_rows"]:
                raise ProjectError(
                    f"Tam çıktı tahmini {d['predicted_rows']} satır; seçilen {p['max_output_rows']} sınırını aşıyor. Yayın yok."
                )
            if d["predicted_rows"] > request["row_count"]:
                d["warnings"].append(
                    "Satır sayısı artıyor; bu etki örneklemden tahmin edilmedi, tam veri anahtar/alan sayımıdır."
                )
        parts = []
        edges = []
        output = Path(workspace) / (uid() + ".parquet")
        total = 0
        if spec.kind in ("join", "append", "unpivot"):
            relation = Path(workspace) / (uid() + "-lineage.parquet")
        try:
            for frame in batches(query, control, workspace):
                outids = []
                edge = []
                if spec.kind in ("computed", "text_split", "text_combine"):
                    out_names = (
                        [i["name"] for i in p["outputs"]]
                        if spec.kind == "text_split"
                        else [p["output"]["name"]]
                    )
                    values = {n: [] for n in out_names}
                    for row in frame.iter_rows(named=True):
                        control.check()
                        if spec.kind == "computed":
                            before = d["zero_divisions"]
                            value = evaluate(
                                p["tree"],
                                {i: row[cols[i]] for i in spec.column_ids},
                                p["zero_policy"],
                                d,
                            )
                            value = exact_value(value, restore(p["target"]))
                            d["new_nulls"] += value is None
                            if d["zero_divisions"] > before and len(d["examples"]) < 5:
                                d["examples"].append(
                                    dict(
                                        row_id=row["__vu_row_id"],
                                        column_id=p["output"]["id"],
                                        reason="Sıfıra bölme → açık null",
                                    )
                                )
                            values[out_names[0]].append(value)
                        elif spec.kind == "text_split":
                            value = row[cols[spec.column_ids[0]]]
                            pieces = (
                                value.split(p["delimiter"], len(out_names) - 1)
                                if value is not None
                                else []
                            )
                            for i, n in enumerate(out_names):
                                value = pieces[i] if i < len(pieces) else None
                                values[n].append(value)
                                d["new_nulls"] += value is None
                        else:
                            v = [row[cols[i]] for i in spec.column_ids]
                            value = (
                                None
                                if p["null_policy"] == "propagate" and None in v
                                else p["separator"].join(x for x in v if x is not None)
                            )
                            values[out_names[0]].append(value)
                            d["new_nulls"] += value is None
                    dt = restore(p["target"]) if spec.kind == "computed" else pl.String
                    frame = frame.with_columns(
                        [
                            pl.Series(n, v, dtype=dt, strict=True)
                            for n, v in values.items()
                        ]
                    )
                if spec.kind == "date_parts":
                    d["new_nulls"] += sum(
                        frame[item["output"]["name"]].null_count()
                        for item in p["parts"]
                    )
                if relation:
                    for i, row in enumerate(frame.iter_rows(named=True)):
                        control.check()
                        out = "row:" + uid()
                        outids.append(out)
                        if spec.kind == "join":
                            if row[LR] is None:
                                d["new_nulls"] += len(request["columns"])
                            if row[RR] is None:
                                d["new_nulls"] += len(request["secondary"]["columns"])
                            for v, ri, si, side in [
                                (versions[0], LR, LS, "left"),
                                (versions[1], RR, RS, "right"),
                            ]:
                                if row[ri] is not None:
                                    edge.append(
                                        relation_row(
                                            out,
                                            v,
                                            row[ri],
                                            row[si],
                                            side,
                                            occurrence=total + i,
                                        )
                                    )
                        else:
                            side = row[SIDE] if spec.kind == "append" else 0
                            if spec.kind == "append":
                                d["new_nulls"] += sum(
                                    m["left_column" if side == 0 else "right_column"]
                                    is None
                                    for m in p["mapping"]
                                )
                            column = (
                                next(
                                    (
                                        cid
                                        for cid in p.get("value_columns", [])
                                        if cols[cid]
                                        == row[p["variable_output"]["name"]]
                                    ),
                                    None,
                                )
                                if spec.kind == "unpivot"
                                else None
                            )
                            edge.append(
                                relation_row(
                                    out,
                                    versions[side],
                                    row[LR],
                                    row[LS],
                                    "left" if side == 0 else "right",
                                    column,
                                    occurrence=total + i,
                                )
                            )
                    if spec.kind == "join":
                        frame = synthetic(frame, spec, outids)
                    elif spec.kind == "append":
                        frame = synthetic(frame, spec, outids).with_columns(
                            pl.col(LS).alias("__vu_source_record_id")
                        )
                    else:
                        frame = internals(
                            frame.with_columns(pl.Series("__vu_row_id", outids))
                        )
                    ep = Path(workspace) / (uid() + "-edge.parquet")
                    pl.DataFrame(edge, schema=EDGE_SCHEMA).write_parquet(ep)
                    edges.append(ep)
                    d["relation_rows"] += len(edge)
                total += frame.height
                frame = frame.select(
                    [c["name"] for c in spec.output_schema]
                    + [
                        n
                        for n in frame.columns
                        if n
                        in (
                            "__vu_row_id",
                            "__vu_source_record_id",
                            "__vu_start_line",
                            "__vu_end_line",
                            *EXTRA,
                        )
                    ]
                )
                part = Path(workspace) / (uid() + "-part.parquet")
                frame.write_parquet(part)
                parts.append(part)
                control.disk(workspace)
                control.progress(
                    "Dönüşüm tam veri",
                    total,
                    d.get("predicted_rows", request["row_count"]),
                )
            if not parts:
                schema = {c["name"]: dtype_of(c["type"]) for c in spec.output_schema}
                schema.update(
                    __vu_row_id=pl.String,
                    __vu_source_record_id=pl.String,
                    __vu_start_line=pl.Int64,
                    __vu_end_line=pl.Int64,
                )
                schema.update(EXTRA)
                part = Path(workspace) / (uid() + "-part.parquet")
                pl.DataFrame(schema=schema).write_parquet(part)
                parts.append(part)
            pl.scan_parquet(parts).sink_parquet(
                output, maintain_order=True, engine="streaming"
            )
            if relation:
                if edges:
                    pl.scan_parquet(edges).sink_parquet(
                        relation, maintain_order=True, engine="streaming"
                    )
                else:
                    pl.DataFrame(schema=EDGE_SCHEMA).write_parquet(relation)
        finally:
            for part in parts + edges:
                part.unlink(missing_ok=True)
    source_ids = {c["id"] for c in request["columns"]}
    output_ids = {c["id"] for c in spec.output_schema}
    d["changed_columns"] = len(source_ids ^ output_ids)
    if spec.kind not in NEW_ROWS:
        d["modified_rows"] = request["row_count"]
    d["new_row_ids"] = spec.kind in GROUPED | MULTI | {"unpivot"}
    if spec.kind == "computed":
        d["warnings"].append(
            "Formül izinli AST ile yorumlanır; null yayılır, coalesce/ifelse açık istisnadır. Bölme reject/null politikasındadır. Exact hedefe uymayan kesir/Decimal/Float64 reddedilir; round() açık half-even seçimi ve sayımıdır."
        )
    control.disk(workspace)
    return spec, output, d, relation
