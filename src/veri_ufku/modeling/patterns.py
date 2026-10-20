"""Immutable bounded basket/event mining, using the shared CPU artifact lifecycle."""

import copy
import json
import math
import time
from dataclasses import asdict
from datetime import UTC, datetime

import polars as pl

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.pattern_basket import mine
from veri_ufku.modeling.pattern_contracts import PatternSpec
from veri_ufku.modeling.pattern_events import cohort, funnel, process
from veri_ufku.modeling.recommendation_contracts import identity
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError


def read_rows(request, spec, control):
    checked(request, control)
    if not 1 <= request["row_count"] <= 5000:
        raise ProjectError(
            "Pattern önkontrolü:1..5000row,2000entity,64item/32activity."
        )
    names = {c["id"]: c["name"] for c in request["columns"]}
    basket = spec.task in ("apriori", "fp_growth")
    roles = [spec.entity, spec.activity] + (
        []
        if basket
        else [
            spec.time,
            *([spec.order] if spec.order else []),
            *([spec.complete] if spec.complete else []),
        ]
    )
    if any(c not in names for c in roles):
        raise ProjectError("Pattern ColumnId kaynak sürümünde yok.")
    f = pl.read_parquet(
        request["path"],
        columns=["__vu_row_id", "__vu_source_record_id", *[names[c] for c in roles]],
        n_rows=5001,
    )
    if len(f) != request["row_count"]:
        raise ProjectError("Pattern snapshot row count uyuşmuyor.")
    rows = []
    for raw in f.iter_rows(named=True):
        control.check()
        activity = raw[names[spec.activity]]
        row = dict(
            row_id=raw["__vu_row_id"],
            source_record_id=raw["__vu_source_record_id"],
            entity=identity(raw[names[spec.entity]]),
            activity=None if basket and activity is None else identity(activity),
        )
        if not basket:
            if not isinstance(activity, str):
                raise ProjectError("Event activity açık string etiket olmalı.")
            value = raw[names[spec.time]]
            if isinstance(value, str):
                try:
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        raise ValueError()
                    value = dt.timestamp()
                except (ValueError, OverflowError):
                    raise ProjectError(
                        "Event ISO timestamp offset içermeli; naif saat kabul edilmez."
                    ) from None
            elif isinstance(value, datetime):
                if value.tzinfo is None:
                    raise ProjectError("Event datetime timezone içermeli.")
                value = value.timestamp()
            if (
                type(value) not in (int, float)
                or not math.isfinite(value)
                or not spec.observation_start <= value < spec.observation_end
            ):
                raise ProjectError(
                    "Event timestamp finite Unix seconds/offset ISO ve [observation_start,end) içinde olmalı."
                )
            order = raw[names[spec.order]] if spec.order else None
            flag = raw[names[spec.complete]] if spec.complete else None
            if (
                order is not None
                and type(order) is not int
                or spec.order
                and order is None
            ):
                raise ProjectError("Event order nonnull integer kaynak sırası olmalı.")
            if spec.complete and type(flag) is not bool:
                raise ProjectError(
                    "Case complete açık bool olmalı; eksik durumda başarı çıkarılmaz."
                )
            row.update(activity_raw=activity, time=value, order=order, complete=flag)
        rows.append(row)
    if len({r["entity"] for r in rows}) > 2000 or len(
        {r["row_id"] for r in rows}
    ) != len(rows):
        raise ProjectError("Entity2000/unique RowId sınırı.")
    if not basket and len({r["activity"] for r in rows}) > 32:
        raise ProjectError("Event32activity önkontrol sınırı.")
    return rows


def baskets_for(rows, spec):
    groups = {}
    duplicates = 0
    for r in rows:
        groups.setdefault(r["entity"], []).append(r["activity"])
    baskets = []
    for values in groups.values():
        if None in values and (len(values) != 1):
            raise ProjectError(
                "Null item yalnız tek satırlı açık empty-basket işaretidir; eksik item sessiz düşmez."
            )
        extra = len(values) - len(set(values))
        if extra and spec.duplicates == "reject":
            raise ProjectError("Transaction/item duplicate; açık set seçimi gerekir.")
        duplicates += extra
        baskets.append(set(values) - {None})
    return baskets, duplicates


def validate(data):
    PatternSpec.from_dict(data["pattern_spec"])
    if (
        data.get("schema") != "PatternRun/v1"
        or data.get("status")
        not in ("running", "completed", "canceled", "failed", "budget_exhausted")
        or data["epoch"] != 0
        or data["curves"]
    ):
        raise ProjectError("Pattern kapalı artifact schema/status hatası.")
    if data.get("details_uri"):
        if not data.get("lineage_hash") or not data.get("split_id"):
            raise ProjectError("Pattern lineage özeti eksik.")
        return
    ids = [r["row_id"] for r in data["rows"]]
    if (
        len(set(ids)) != len(ids)
        or ids != data["plan"]["membership"]["train"]
        or data["plan"]["membership"]["test"]
    ):
        raise ProjectError("Pattern kaynak RowId/plan bağı uyuşmuyor.")
    if len(json.dumps(data, allow_nan=False).encode()) > 16 * 1024**2:
        raise ProjectError("Pattern safe JSON16MiB sınırı.")


def calculate(request, parameters, work, control=None, checkpoint=lambda value: None):
    control = control or Control()
    start = time.monotonic()
    spec = PatternSpec.from_dict(parameters)
    rows = read_rows(request, spec, control)
    plan = dict(
        split_id="descriptive-pattern:"
        + digest(dict(source=request["fingerprint"], spec=spec.data())),
        membership=dict(train=[r["row_id"] for r in rows], validation=[], test=[]),
        scope="descriptive discovery only; not predictive evaluation or final test",
    )
    now = datetime.now(UTC).isoformat()
    compat = digest(dict(plan=plan, spec=spec.data()))
    data = dict(
        schema="PatternRun/v1",
        run_id=request["run_id"],
        training_id=request["run_id"],
        dataset_version=request["version_id"],
        origin_version=request["origin_version"],
        source_snapshot_id=request["source_snapshot_id"],
        snapshot_fingerprint=request["fingerprint"],
        seed=spec.seed,
        spec={},
        pattern_spec=spec.data(),
        plan=plan,
        epoch=0,
        curves=[],
        elapsed_seconds=0,
        created_at=now,
        data_access_at=now,
        prior_test_use_ids=request.get("prior_test_use_ids", []),
        rows=rows,
        analysis={},
        metrics={},
        model_weights=None,
        runtime=None,
        mode="descriptive_pattern_discovery",
        tensor_schema=dict(
            fit_row_ids=[],
            shape="no predictive fit; source event/transaction lineage preserved",
        ),
        compat_id=compat,
        experiment_capture=request.get("experiment_capture", {}),
        environment=dict(device="cpu", polars=pl.__version__),
        warnings=[
            "Exploratory multiple discovery: no controlled false discovery rate, p-value or causal claim.",
            "Rule and directly-follows graph are not causal DAGs; loops and partial traces permitted.",
            "Cohort NA denotes incomplete observation, not zero retention; first_observed is window-local, not true lifetime signup.",
            "Events are source rows; duplicate real-world events require an explicit upstream identity contract, never silently deduplicated.",
        ],
    )
    data["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + compat,
            dataset_versions=(request["version_id"],),
            config_revision=request.get("config_revision", 0),
            capability_id="model.pattern." + spec.task.replace("_", "-"),
            parameters_hash=digest(spec.data()),
            environment=(("device", "cpu"),),
            created_at=now,
            scope=plan["scope"],
            seed=spec.seed,
            source_snapshot_ids=(request["source_snapshot_id"],),
            row_lineage_ref=plan["split_id"],
        )
    )

    def emit(status):
        data.update(status=status, elapsed_seconds=time.monotonic() - start)
        validate(data)
        checkpoint(copy.deepcopy(data))

    emit("running")
    try:
        control.check()
        if spec.task in ("apriori", "fp_growth"):
            baskets, duplicates = baskets_for(rows, spec)
            data["analysis"] = mine(baskets, spec, control)
            data["analysis"].update(
                duplicate_rows=duplicates, duplicate_policy=spec.duplicates
            )
        else:
            data["analysis"] = (
                cohort
                if spec.task == "cohort"
                else funnel
                if spec.task == "funnel"
                else process
            )(rows, spec, control)
        control.check()
        emit("completed")
    except ProjectError as error:
        data["analysis"] = {}
        data["warnings"].append(str(error))
        emit("failed")
    except Canceled:
        data["analysis"] = {}
        emit("canceled")
    return data
