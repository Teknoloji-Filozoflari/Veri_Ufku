"""Special target recipes bound to explicit development roles and source identities."""

import copy
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import polars as pl
import sklearn

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.special_targets import TargetSpec, evaluate
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError


@dataclass(frozen=True)
class TargetRecipe:
    task: str = "multilabel"
    features: tuple = ()
    targets: tuple = ()
    role: str = ""
    order: tuple = ()
    transductive: bool = False
    seed: int = 62

    @classmethod
    def from_dict(cls, raw):
        try:
            s = cls(
                **{
                    **raw,
                    **{
                        k: tuple(raw.get(k, ()))
                        for k in ("features", "targets", "order")
                    },
                }
            )
        except (TypeError, ValueError):
            raise ProjectError("Special recipe kapalı şema geçersiz.") from None
        TargetSpec(s.task, s.order, s.transductive).validate()
        cols = (*s.features, *s.targets, s.role)
        if (
            not 1 <= len(s.features) <= 16
            or not 1 <= len(s.targets) <= 8
            or any(not isinstance(c, str) or not c for c in cols)
            or len(set(cols)) != len(cols)
            or type(s.seed) is not int
            or not 0 <= s.seed <= 2**32 - 1
        ):
            raise ProjectError("Special recipe ColumnId/seed şeması geçersiz.")
        if (s.task in ("multilabel", "multioutput") and len(s.targets) < 2) or (
            s.task not in ("multilabel", "multioutput") and len(s.targets) != 1
        ):
            raise ProjectError("Target sayısı yöntemle uyuşmuyor.")
        return s

    def data(self):
        return asdict(self)


def validate(data):
    TargetRecipe.from_dict(data["target_recipe"])
    if (
        data.get("schema") != "SpecialTargetRun/v1"
        or data.get("status")
        not in ("running", "completed", "failed", "canceled", "budget_exhausted")
        or data["epoch"] != 0
        or data["curves"]
    ):
        raise ProjectError("SpecialTargetRun schema/status geçersiz.")
    if len(json.dumps(data, allow_nan=False).encode()) > 2 * 1024**2:
        raise ProjectError("Special JSON2MiB sınırı.")


def calculate(request, parameters, work, control=None, checkpoint=lambda value: None):
    control = control or Control()
    control.check()
    checked(request, control)
    start = time.monotonic()
    spec = TargetRecipe.from_dict(parameters)
    if not 3 <= request["row_count"] <= 640:
        raise ProjectError("Special target3–640row önkontrolü.")
    names = {c["id"]: c["name"] for c in request["columns"]}
    if any(c not in names for c in (*spec.features, *spec.targets, spec.role)):
        raise ProjectError("Special ColumnId sürümde yok.")
    frame = pl.read_parquet(request["path"], n_rows=641)
    roles = frame[names[spec.role]].to_list()
    if len(frame) != request["row_count"] or any(
        r not in ("train", "pool", "eval") for r in roles
    ):
        raise ProjectError(
            "Role yalnız train/pool/eval development; final test ayrı defter gerektirir."
        )
    groups = {
        role: frame.filter(pl.col(names[spec.role]) == role)
        for role in ("train", "pool", "eval")
    }
    if len(groups["pool"]) and any(
        v is not None and v != -1
        for c in spec.targets
        for v in groups["pool"][names[c]].to_list()
    ):
        raise ProjectError(
            "Pool hedefi null veya−1 olmalı; gerçek etiket sessiz göz ardı edilmez."
        )
    if len(groups["pool"]) and spec.task != "semisupervised":
        raise ProjectError("Pool yalnız semi-supervised için.")

    def lineage(f):
        return [
            dict(row_id=r["__vu_row_id"], source_record_id=r["__vu_source_record_id"])
            for r in f.iter_rows(named=True)
        ]

    now = datetime.now(UTC).isoformat()
    compat = digest(
        dict(
            source=request["fingerprint"],
            recipe=spec.data(),
            sklearn=sklearn.__version__,
        )
    )
    scope = "explicit development train/pool/eval; no final test; " + (
        "transductive eval features in graph"
        if spec.transductive
        else "eval features excluded from fit"
    )
    data = dict(
        schema="SpecialTargetRun/v1",
        run_id=request["run_id"],
        training_id=request["run_id"],
        dataset_version=request["version_id"],
        origin_version=request["origin_version"],
        source_snapshot_id=request["source_snapshot_id"],
        snapshot_fingerprint=request["fingerprint"],
        seed=spec.seed,
        spec={},
        target_recipe=spec.data(),
        epoch=0,
        curves=[],
        elapsed_seconds=0,
        created_at=now,
        data_access_at=now,
        prior_test_use_ids=request.get("prior_test_use_ids", []),
        plan=dict(
            split_id="special-development:" + compat,
            scope=scope,
            membership={k: lineage(f) for k, f in groups.items()},
        ),
        tensor_schema={},
        model_weights=None,
        runtime=None,
        compat_id=compat,
        metrics={},
        analysis={},
        mode="development_special_target",
        environment=dict(sklearn=sklearn.__version__, device="cpu"),
        experiment_capture=request.get("experiment_capture", {}),
        warnings=[
            "Explicit development roles, no final-test score. Group/time split integrity must be supplied upstream; random splitting not performed here.",
            "Safe result artifact only; new-data model prediction/persistence unavailable for these adapters.",
        ],
    )
    data["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + compat,
            dataset_versions=tuple(
                dict.fromkeys([request["version_id"], request["origin_version"]])
            ),
            config_revision=request.get("config_revision", 0),
            capability_id="model.special." + spec.task,
            parameters_hash=digest(spec.data()),
            environment=(("sklearn", sklearn.__version__),),
            created_at=now,
            scope=scope,
            seed=spec.seed,
            source_snapshot_ids=(request["source_snapshot_id"],),
            row_lineage_ref=data["plan"]["split_id"],
        )
    )

    def emit(status):
        data.update(status=status, elapsed_seconds=time.monotonic() - start)
        validate(data)
        checkpoint(copy.deepcopy(data))

    emit("running")

    def xy(role):
        f = groups[role]
        x = f.select([names[c] for c in spec.features]).to_numpy()
        y = f.select([names[c] for c in spec.targets]).to_numpy()
        return x, y if spec.task in ("multilabel", "multioutput") else y[:, 0]

    x, y = xy("train")
    ev, z = xy("eval")
    control.check()
    result = evaluate(
        TargetSpec(spec.task, spec.order, spec.transductive),
        x,
        y,
        ev,
        z,
        unlabeled=xy("pool")[0] if len(groups["pool"]) else None,
    )
    control.check()
    data.update(analysis=result, metrics=result["metrics"])
    data["warnings"] += result["warnings"]
    emit("completed")
    return data
