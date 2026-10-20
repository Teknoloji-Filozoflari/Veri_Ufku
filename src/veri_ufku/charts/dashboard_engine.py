"""Bounded, version-bound dashboard evaluation; no Qt and no network access."""

import copy
import math
import os
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import polars as pl

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked, display, literal
from veri_ufku.charts.dashboard import DashboardSpec, DashboardWidget
from veri_ufku.charts.engine import calculate
from veri_ufku.charts.plot import render
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.storage.project_model import ProjectError, digest, encode, uid


def predicate(frame, columns, item):
    names = {c["id"]: c["name"] for c in columns}
    if item["column_id"] not in names:
        raise ProjectError("Filtrenin ColumnId bağı seçili sürümde yok.")
    name = names[item["column_id"]]
    col, dtype, op = pl.col(name), frame.schema[name], item["operator"]
    if op in ("is-null", "is_null"):
        return col.is_null()
    if op == "contains":
        if dtype != pl.String or not isinstance(item["value"], str):
            raise ProjectError("İçerir filtresi metin sütunu ve metin değer ister.")
        return col.str.contains(item["value"], literal=True).fill_null(False)
    values = item["value"] if op == "in" else [item["value"]]
    if not isinstance(values, list) or len(values) > 1000:
        raise ProjectError("IN filtresi en fazla1000 değer içermeli.")
    result = pl.lit(False)
    for value in values:
        if value is None:
            test = col.is_null()
        else:
            val = literal(str(value), dtype)
            functions = {
                "eq": col.eq,
                "gte": col.ge,
                "ge": col.ge,
                "lte": col.le,
                "le": col.le,
                "ne": col.ne,
                "gt": col.gt,
                "lt": col.lt,
                "in": col.eq,
            }
            if op not in functions:
                raise ProjectError("Dashboard filtre işlemi desteklenmiyor.")
            test = functions[op](val)
            if dtype.is_float():
                test = test & col.is_finite()
        result = result | test.fill_null(False)
    return result


def apply_filters(frame, columns, filters):
    for f in filters:
        frame = frame.filter(predicate(frame, columns, f))
    return frame


def mapping_for(spec, source, column, target):
    if source == target:
        return column
    for mapping in spec.filter_mappings.values():
        if (
            mapping.get("source_version"),
            mapping.get("source_column"),
            mapping["target_version"],
        ) == (source, column, target):
            return mapping["target_column"]
    return None


def selection_rows(spec, frames, target):
    if not spec.selection:
        return set(), False
    source = spec.selection["dataset_version"]
    source_frame = frames[source]
    selected = set(spec.selection["row_ids"])
    if not selected <= set(source_frame["__vu_row_id"].to_list()):
        raise ProjectError("Seçim RowId değerleri bağlı snapshot içinde yok.")
    if source == target:
        return selected, True
    matches = [
        m
        for m in spec.filter_mappings.values()
        if m.get("source_version") == source and m["target_version"] == target
    ]
    if not matches:
        return set(), False
    # A user may map multiple keys: all chosen key pairs are a conjunctive tuple.
    target_frame = frames[target]
    names = {}
    for version, frame in ((source, source_frame), (target, target_frame)):
        names[version] = {c["id"]: c["name"] for c in frames.columns[version]}
    source_keys = [names[source][m["source_column"]] for m in matches]
    target_keys = [names[target][m["target_column"]] for m in matches]
    if any(
        source_frame.schema[a] != target_frame.schema[b]
        for a, b in zip(source_keys, target_keys)
    ):
        raise ProjectError(
            "Seçim eşleme sütunlarının fiziksel türleri aynı olmalı; otomatik dönüşüm yok."
        )
    for frame, names_to_check in (
        (source_frame, source_keys),
        (target_frame, target_keys),
    ):
        for name in names_to_check:
            if frame.schema[name].is_nested() or frame.schema[name] == pl.Binary:
                raise ProjectError("Kaynak eşleme anahtarı skaler sütun olmalı.")
            if (
                frame.schema[name].is_float()
                and frame.filter(
                    pl.col(name).is_not_null() & ~pl.col(name).is_finite()
                ).height
            ):
                raise ProjectError("Kaynak eşleme anahtarı sonlu değerler içermeli.")
    keys = set(
        source_frame.filter(pl.col("__vu_row_id").is_in(sorted(selected)))
        .select(source_keys)
        .rows()
    )
    keys = {key for key in keys if all(v is not None for v in key)}
    return {
        row[0]
        for row in target_frame.select("__vu_row_id", *target_keys).rows()
        if tuple(row[1:]) in keys
    }, True


class Frames(dict):
    def __init__(self):
        super().__init__()
        self.columns = {}


def kpi(frame, widget, names):
    values = (
        frame[names[widget.column_id]].to_list()
        if widget.column_id
        else [1] * frame.height
    )
    finite = [
        v
        for v in values
        if v is not None and (not isinstance(v, (float, Decimal)) or math.isfinite(v))
    ]
    if widget.aggregation != "count" and any(
        isinstance(v, bool) or not isinstance(v, (int, float, Decimal)) for v in finite
    ):
        raise ProjectError("KPI ölçümü sayısal sütun ister.")
    numerator = (
        len(finite)
        if widget.aggregation == "count"
        else sum(finite)
        if widget.aggregation == "sum"
        else sum(finite) / len(finite)
        if widget.aggregation == "mean" and finite
        else min(finite)
        if widget.aggregation == "min" and finite
        else max(finite)
        if widget.aggregation == "max" and finite
        else None
    )
    mode = widget.denominator_mode
    denominator = None
    if mode == "rows":
        denominator = frame.height
    elif mode == "non-null":
        denominator = len(finite)
    elif mode == "column-sum":
        vals = frame[names[widget.denominator_column]].to_list()
        if any(
            v is not None
            and (
                isinstance(v, bool)
                or not isinstance(v, (int, float, Decimal))
                or not math.isfinite(v)
            )
            for v in vals
        ):
            raise ProjectError("KPI paydası sonlu sayısal sütun olmalı.")
        denominator = sum(v for v in vals if v is not None)
    value = (
        numerator
        if mode == "none"
        else numerator / denominator
        if numerator is not None and denominator
        else None
    )
    return {
        "value": None if value is None else str(value),
        "numerator": None if numerator is None else str(numerator),
        "denominator_value": None if denominator is None else str(denominator),
        "denominator_mode": mode,
        "definition": f"{widget.aggregation} · payda: {widget.denominator} ({mode}) · önceki dönem: {widget.previous_period}",
        "included_n": frame.height,
        "finite_n": len(finite),
        "excluded_n": len(values) - len(finite),
        "warning": "Payda sıfır/boş; oran tanımsız."
        if mode != "none" and not denominator
        else "",
    }


def evaluate(request, workspace, control=None):
    control = control or Control()
    spec = DashboardSpec(**request["spec"])
    spec.validate(request["datasets"])
    frames = Frames()
    size = 0
    for version, info in request["datasets"].items():
        r = info["request"]
        checked(r, control)
        if r["row_count"] > 10000:
            raise ProjectError(
                "Dashboard tam snapshot sınırı10000 satır; açık daha küçük veri sürümü seçin. Sessiz örnekleme yok."
            )
        frame = pl.read_parquet(r["path"])
        if (
            "__vu_row_id" not in frame
            or frame["__vu_row_id"].n_unique() != frame.height
        ):
            raise ProjectError("Dashboard snapshot RowId kimlikleri geçersiz.")
        size += frame.estimated_size() * 8
        if size > control.budget.ram_bytes // 3:
            raise ProjectError(
                "Dashboard veri kaynakları ortak bellek bütçesini aşıyor."
            )
        frames[version] = frame
        frames.columns[version] = r["columns"]
    output = []
    for index, raw in enumerate(spec.widgets):
        control.check()
        w = raw if isinstance(raw, DashboardWidget) else DashboardWidget(**raw)
        info = request["datasets"][w.dataset_version]
        r = info["request"]
        columns = r["columns"]
        names = {c["id"]: c["name"] for c in columns}
        filters, unmapped = [], []
        for f in spec.global_filters:
            f = f if isinstance(f, dict) else asdict(f)
            source = f.get("dataset_version")
            if source not in frames:
                raise ProjectError(
                    "Global filtre açık kaynak veri sürümüne bağlanmalı."
                )
            target = mapping_for(spec, source, f["column_id"], w.dataset_version)
            if target is None:
                unmapped.append(f["column_id"])
            else:
                filters.append({**f, "column_id": target})
        chart_spec = None
        if w.kind == "chart":
            saved = request["charts"].get(w.chart_result_id)
            if not saved or saved["dataset_version"] != w.dataset_version:
                raise ProjectError(
                    "Dashboard grafik sonucu widget veri sürümüyle uyuşmuyor."
                )
            chart_spec = copy.deepcopy(saved["spec"])
            filters.extend(chart_spec.get("view", {}).get("filters", []))
        base = apply_filters(frames[w.dataset_version], columns, filters)
        current = apply_filters(base, columns, w.filters)
        selected, mapped = selection_rows(spec, frames, w.dataset_version)
        if spec.drill_down and spec.selection and mapped:
            current = current.filter(pl.col("__vu_row_id").is_in(sorted(selected)))
        active_ids = set(current["__vu_row_id"].to_list())
        linked = sorted(active_ids & selected)
        status = (
            "current"
            if w.dataset_version in request["active_versions"]
            and info.get("source_current", True)
            else "stale"
        )
        item = {
            "id": w.id,
            "kind": w.kind,
            "title": w.title,
            "grid": list(w.grid),
            "dataset_version": w.dataset_version,
            "freshness": status,
            "status_text": "Güncel snapshot"
            if status == "current"
            else "Eski sürüm / kaynak değişmiş · güncel veri değildir",
            "row_ids": sorted(active_ids),
            "n": current.height,
            "linked_count": len(linked),
            "selected_row_ids": linked,
            "filter_contract": {
                "global": filters,
                "local": list(w.filters),
                "unmapped": unmapped,
                "selection_mapped": mapped,
                "drill_down": spec.drill_down,
            },
            "mapping_notice": f"{len(unmapped)} global filtre bu kaynakta eşlenmedi."
            if unmapped
            else "",
        }
        if w.kind == "note":
            item["text"] = w.text
        elif w.kind == "kpi":
            item["kpi"] = kpi(current, w, names)
            if w.previous_period != "none":
                previous = apply_filters(base, columns, w.previous_filters)
                if spec.drill_down and mapped:
                    previous = previous.filter(
                        pl.col("__vu_row_id").is_in(sorted(selected))
                    )
                item["kpi"]["previous"] = kpi(previous, w, names)
                a, b = item["kpi"]["value"], item["kpi"]["previous"]["value"]
                item["kpi"]["difference"] = (
                    str(Decimal(a) - Decimal(b))
                    if a is not None and b is not None
                    else None
                )
        elif w.kind == "table":
            chosen = list(w.columns) or list(names)[:12]
            item["columns"] = [{"id": c, "name": names[c]} for c in chosen]
            item["rows"] = [
                {
                    "row_id": row["__vu_row_id"],
                    "cells": [display(row[names[c]]) for c in chosen],
                    "selected": row["__vu_row_id"] in selected,
                }
                for row in current.head(200).iter_rows(named=True)
            ]
            item["page_notice"] = (
                f"İlk{min(200, current.height)}/{current.height} kayıt; seçim yalnız görünür RowId ile."
            )
        elif current.height == 0:
            item["empty"] = "Seçili filtre kapsamı boş; grafik üretilmedi."
        else:
            job = Path(workspace) / ("widget-" + str(index))
            job.mkdir()
            snapshot = job / "view.parquet"
            current.write_parquet(snapshot)
            cr = {
                **r,
                "path": str(snapshot),
                "fingerprint": hash_artifact(snapshot, control),
                "row_count": current.height,
            }
            chart_spec.update(
                view=ViewSpec().data(),
                scope="sample" if chart_spec.get("scope") == "sample" else "full",
                bounds=[],
            )
            result = calculate(cr, chart_spec, job, control)
            result["filters"] = filters + list(w.filters)
            members = pl.read_parquet(result["paths"]["members"])
            selected_points = sorted(
                members.filter(pl.col("row_id").is_in(linked))["point_id"]
                .unique()
                .to_list()
            )
            result = render(result, job, highlight=selected_points, control=control)
            result["dashboard_context"] = {
                "original_snapshot": r["fingerprint"],
                "filter_contract": item["filter_contract"],
                "freshness": status,
            }
            item["chart"] = result
            item["image_path"] = result["paths"]["png"]
            item["memberships"] = {
                str(row["point_id"]): row["row_id"]
                for row in members.group_by("point_id")
                .agg("row_id")
                .iter_rows(named=True)
            }
        output.append(item)
    provenance = Provenance(
        "prov:" + uid(),
        tuple(sorted(frames)),
        request["revision"],
        "dashboard.canvas",
        digest(encode(spec.data())),
        (("adapter", "local-polars-matplotlib"),),
        datetime.now(UTC).isoformat(),
        scope="dashboard-full-snapshot",
        filters=(digest(encode(spec.data()["global_filters"])),),
    )
    control.disk(workspace, force=True)
    mapping_keys = {}
    for mapping in spec.filter_mappings.values():
        for side in ("source", "target"):
            version, column = mapping[side + "_version"], mapping[side + "_column"]
            names = {c["id"]: c["name"] for c in frames.columns[version]}
            frame = frames[version]
            dtype = frame.schema[names[column]]
            if dtype.is_nested() or dtype == pl.Binary:
                raise ProjectError("Kaynak eşleme anahtarı skaler sütun olmalı.")
            if (
                dtype.is_float()
                and frame.filter(
                    pl.col(names[column]).is_not_null()
                    & ~pl.col(names[column]).is_finite()
                ).height
            ):
                raise ProjectError("Kaynak eşleme anahtarı sonlu değerler içermeli.")
            mapping_keys.setdefault(version, {})[column] = {
                row[0]: str(dtype) + ":" + str(row[1]) if row[1] is not None else None
                for row in frame.select("__vu_row_id", names[column]).rows()
            }
    return {
        "widgets": output,
        "spec": spec.data(),
        "provenance": asdict(provenance),
        "worker_pid": os.getpid(),
        "revision": request["revision"],
        "mapping_keys": mapping_keys,
    }
