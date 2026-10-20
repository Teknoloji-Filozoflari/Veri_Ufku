"""Safe append-only search checkpoints through the existing atomic ProjectStore/journal."""

import copy
import json
import tempfile
from dataclasses import replace

import numpy as np

from veri_ufku.modeling.search_contracts import SearchSpec
from veri_ufku.modeling.validation import ValidationSpec, development_folds
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import file_hash
from veri_ufku.storage.validation_store import prior_uses, transaction

STATUSES = {"running", "completed", "failed", "canceled", "budget_exhausted"}
TRIAL_STATUSES = {"running", "completed", "failed", "canceled", "pruned"}


def validate_record(record, versions):
    data = record["search"]
    if (
        data.get("schema") != "SearchRun/v1"
        or data.get("status") not in STATUSES
        or data["dataset_version"] not in versions
        or data["origin_version"] not in versions
    ):
        raise ProjectError("Search record source/schema/status geçersiz.")
    if set(record["dataset_version_ids"]) != {
        data["dataset_version"],
        data["origin_version"],
    }:
        raise ProjectError("Search kaynak sürüm bağları geçersiz.")
    search = SearchSpec.from_dict(data["search_spec"], require_backend=False)
    if (
        type(data["native_fit_reservations"]) is not int
        or not 0 <= data["native_fit_reservations"] <= 600
    ):
        raise ProjectError("Cumulative native fit bütçesi geçersiz.")
    if (
        data["source_snapshot_id"]
        != versions[data["dataset_version"]]["import_metadata"]["source_snapshot_id"]
    ):
        raise ProjectError("Search SourceSnapshotId bağı geçersiz.")
    if data.get("details_uri"):
        if (
            not isinstance(data["previous_checkpoint_id"], (str, type(None)))
            or type(data["checkpoint_index"]) is not int
            or data["checkpoint_index"] < 0
            or data["details_fingerprint"]["size"] > 32 * 1024**2
            or data["preparation_spec"]["source_version"] != data["dataset_version"]
        ):
            raise ProjectError("Search summary artifact/source bağı geçersiz.")
        search.candidates(data["preparation_spec"]["purpose"], require_backend=False)
        return
    protocol = ValidationSpec.from_dict(data["protocol"])
    method = protocol.resolved(data["preparation"])[0]
    pool = search.candidates(
        data["preparation"]["spec"]["purpose"], require_backend=False
    )
    if (
        data["plan"]["method"] != method
        or len(data["scope_plans"]) != protocol.folds + 1
        or data["elapsed_seconds"] < 0
        or len(data["trials"]) > search.attempts
    ):
        raise ProjectError("Search plan/budget/history geçersiz.")
    final = set(data["plan"]["membership"]["test"])
    dev = set(data["plan"]["membership"]["development"])
    if final & dev:
        raise ProjectError("Search final test geliştirmeye karışmış.")
    scopes = {s["name"]: s for s in data["scope_plans"]}
    if len(scopes) != len(data["scope_plans"]) or set(scopes) != {
        "development",
        *(f"outer:{i}" for i in range(protocol.folds)),
    }:
        raise ProjectError("Search scope plan kimlikleri geçersiz.")
    for name, s in scopes.items():
        train = set(s["train_row_ids"])
        evaluation = set(s["outer_evaluation_row_ids"])
        if (
            train & final
            or evaluation & final
            or train & evaluation
            or not train <= dev
            or not evaluation <= dev
            or s["inner_plan"]["method"] != method
        ):
            raise ProjectError("Search inner/outer/final üyelik sızıntısı.")
        expected = (
            data["plan"]["membership"]["development"]
            if name == "development"
            else data["plan"]["membership"]["folds"][int(name.split(":")[1])]["train"]
        )
        if train != set(expected):
            raise ProjectError("Search outer eğitim planı değişmiş.")
        if name != "development" and evaluation != set(
            data["plan"]["membership"]["folds"][int(name.split(":")[1])]["validation"]
        ):
            raise ProjectError("Search outer evaluation planı değişmiş.")
        if len(s["inner_plan"]["folds"]) != (
            protocol.folds if name == "development" else search.inner_folds
        ):
            raise ProjectError("Search inner fold sayısı değişmiş.")
        for fold in s["inner_plan"]["folds"]:
            a = set(fold["train"])
            b = set(fold["validation"])
            if a & b or not a | b <= train or min(len(a), len(b)) < 2:
                raise ProjectError("Search inner fold üyeliği geçersiz.")
    ids = set()
    terminal = set()
    for t in data["trials"]:
        if (
            t["id"] in ids
            or t["scope"] not in scopes
            or t["status"] not in TRIAL_STATUSES
            or type(t["candidate_index"]) is not int
            or not 0 <= t["candidate_index"] < len(pool)
            or t["parameters"] != pool[t["candidate_index"]]
        ):
            raise ProjectError("Trial kimlik/parameters/status geçersiz.")
        ids.add(t["id"])
        key = (t["scope"], t["candidate_index"])
        if t["status"] in ("completed", "failed", "pruned"):
            if key in terminal:
                raise ProjectError("Terminal trial tekrarlandı.")
            terminal.add(key)
        expected = scopes[t["scope"]]["inner_plan"]["folds"]
        if (
            len(t["folds"]) > len(expected)
            or t["status"] == "completed"
            and len(t["folds"]) != len(expected)
        ):
            raise ProjectError("Trial fold coverage geçersiz.")
        for f, planned in zip(t["folds"], expected):
            a = set(f["fit_row_ids"])
            b = set(f["evaluation_row_ids"])
            if (
                b != set(planned["validation"])
                or not a <= set(planned["train"])
                or a & b
                or (a | b) & final
            ):
                raise ProjectError("Trial fit/evaluation/final üyeliği geçersiz.")
            if not search.early_stopping and a != set(planned["train"]):
                raise ProjectError("Trial eğitim kayıtları sessiz düşürüldü.")
        if not set(t["prior_test_use_ids"]) <= set(data["prior_test_use_ids"]):
            raise ProjectError("Trial final kullanım defteri bağı eksik.")
    if data["status"] == "completed" and (
        data.get("recommended") is None
        or len(data["outer_evaluations"]) != protocol.folds
    ):
        raise ProjectError("Completed search nested evaluation/recommendation eksik.")
    if len(json.dumps(data, allow_nan=False).encode()) > 32 * 1024**2:
        raise ProjectError("Search safe JSON32MiB sınırını aşıyor.")


def validate_transition(previous, current):
    if (
        previous["compat_id"] != current["compat_id"]
        or len(current["trials"]) < len(previous["trials"])
        or current["elapsed_seconds"] < previous["elapsed_seconds"]
        or current["native_fit_reservations"] < previous["native_fit_reservations"]
    ):
        raise ProjectError("Search geçmişi/compatibility geriye alınamaz.")
    for a, b in zip(previous["trials"], current["trials"]):
        immutable = (
            "id",
            "scope",
            "candidate_index",
            "parameters",
            "prior_test_use_ids",
            "started_at",
        )
        if (
            any(a[k] != b[k] for k in immutable)
            or len(b["folds"]) < len(a["folds"])
            or b["folds"][: len(a["folds"])] != a["folds"]
        ):
            raise ProjectError("Trial geçmişi değiştirilemez veya silinemez.")
        if a["status"] != "running" and a != b:
            raise ProjectError("Terminal trial immutable; yeni attempt gerekir.")
    if (
        current["outer_evaluations"][: len(previous["outer_evaluations"])]
        != previous["outer_evaluations"]
        or current["curves"][: len(previous["curves"])] != previous["curves"]
    ):
        raise ProjectError("Outer/curve geçmişi geri alınamaz.")


def validate_source(data, frame, y, groups, times, spec, protocol, scopes):
    from veri_ufku.modeling.search import feasible, loss, score, training_subset

    names = frame["__vu_row_id"].to_list()
    index = {v: i for i, v in enumerate(names)}
    search = SearchSpec.from_dict(data["search_spec"], require_backend=False)
    method = protocol.resolved(data["preparation"])[0]
    metric = search.selected_metric(spec.purpose)
    scope_map = {s["name"]: s for s in scopes}

    def validate_fold(value, a, b):
        if set(value["evaluation_row_ids"]) != set(names[i] for i in b):
            raise ProjectError("Trial prediction RowId planı değişmiş.")
        evaluation = np.asarray([index[v] for v in value["evaluation_row_ids"]])
        expected = score(y[evaluation], np.asarray(value["predictions"]), spec.purpose)
        if expected != value["metrics"]:
            raise ProjectError("Trial metric kaynak prediction ile uyuşmuyor.")
        fit = a
        stop = None
        if search.early_stopping:
            _, parts = development_folds(
                [names[i] for i in a],
                y[a],
                groups[a] if groups is not None else None,
                times[a] if times is not None else None,
                replace(protocol, folds=2),
                method,
                spec.purpose == "classification",
            )
            x, z = parts[-1]
            fit = a[x]
            stop = a[z]
            if not value["early_stopping"]:
                raise ProjectError("External early stopping bölmesi eksik.")
            for stage in value["early_stopping"]:
                if set(stage["validation_row_ids"]) != set(names[i] for i in stop):
                    raise ProjectError("Stopping validation planı değişmiş.")
        if set(value["fit_row_ids"]) != set(names[i] for i in fit):
            raise ProjectError("Trial fit scope kaynak planıyla uyuşmuyor.")
        for child in value["child_fit_scopes"]:
            if not set(child) <= set(value["fit_row_ids"]):
                raise ProjectError("Resample/ensemble child fold dışına çıktı.")
        for fold in value["stacking_oof"]:
            a = set(fold["fit_row_ids"])
            b = set(fold["prediction_row_ids"])
            if a & b or a | b != set(value["fit_row_ids"]):
                raise ProjectError("Stacking OOF scope hatalı.")

    for trial in data["trials"]:
        scope = scope_map[trial["scope"]]
        for value, (a, b) in zip(trial["folds"], scope["folds"]):
            validate_fold(value, a, b)
        if trial["status"] == "completed":
            aggregate = {
                k: float(np.mean([f["metrics"][k] for f in trial["folds"]]))
                for k in trial["folds"][0]["metrics"]
            }
            if (
                aggregate != trial["metrics"]
                or trial["loss"] != loss(aggregate[metric], metric)
                or trial["feasible"] != feasible(aggregate, search.constraints)
            ):
                raise ProjectError("Trial aggregate/constraint uyuşmuyor.")
        if trial["status"] == "pruned" and (
            not search.prune_after_folds
            or len(trial["folds"]) >= len(scope["folds"])
            or trial["intermediate_loss"]
            != float(
                np.mean([loss(f["metrics"][metric], metric) for f in trial["folds"]])
            )
            or trial["intermediate_loss"] <= search.prune_loss_above
        ):
            raise ProjectError(
                "Pruning yalnız partial inner validation ile gerekçeli olmalı."
            )
    for e in data["outer_evaluations"]:
        scope = scope_map[e["scope"]]
        validate_fold(e, scope["train"], scope["evaluation"])
        candidates = [
            t
            for t in data["trials"]
            if t["scope"] == e["scope"] and t["status"] == "completed" and t["feasible"]
        ]
        winner = min(candidates, key=lambda t: (t["loss"], t["candidate_index"]))
        if e["winner_trial"] != winner["id"]:
            raise ProjectError("Outer winner inner CV yerine evaluation ile seçilmiş.")

    for curve in data["curves"]:
        if curve["kind"] not in ("learning", "validation") or len(
            curve["folds"]
        ) != len(scopes[-1]["folds"]):
            raise ProjectError("Search curve schema/fold sayısı geçersiz.")
        for value, (a, b) in zip(curve["folds"], scopes[-1]["folds"]):
            if curve["kind"] == "learning":
                a = training_subset(a, curve["x"], protocol, search, groups, times)
            if "metrics" in value:
                validate_fold(value, a, b)
        valid = [f for f in curve["folds"] if "metrics" in f]
        expected = (
            float(np.mean([f["metrics"][metric] for f in valid]))
            if len(valid) == len(curve["folds"])
            else None
        )
        if curve["value"] != expected:
            raise ProjectError("Curve aggregate kaynak fold skorlarıyla uyuşmuyor.")
    if data["recommended"] is not None:
        candidates = [
            t
            for t in data["trials"]
            if t["scope"] == "development"
            and t["status"] == "completed"
            and t["feasible"]
        ]
        winner = min(candidates, key=lambda t: (t["loss"], t["candidate_index"]))
        expected = copy.deepcopy(winner["parameters"])
        if search.early_stopping:
            expected["options"]["trees"] = min(
                f["selected_trees"] for f in winner["folds"]
            )
        if data["recommended"] != expected:
            raise ProjectError(
                "Recommendation full-development inner winner ile uyuşmuyor."
            )


def publish(store, state, data):
    from veri_ufku.modeling.search import context

    data = copy.deepcopy(data)
    choices = {
        r["model_choice"]["run_id"]: r["model_choice"]
        for r in state["results"]
        if "model_choice" in r
    }
    if any(
        run not in choices or choices[run].get("search_id") != data["search_id"]
        for run in data["session_run_ids"]
    ):
        raise ProjectError("Search session kalıcı model-choice journal bağı eksik.")
    versions = {d["version_id"]: d for d in state["datasets"]}
    record = dict(
        id="result:" + uid(),
        dataset_version_ids=list(
            dict.fromkeys([data["origin_version"], data["dataset_version"]])
        ),
        seed=data["search_spec"]["seed"],
        capability_id="model.search." + data["search_spec"]["method"],
        search=data,
    )
    validate_record(record, versions)
    d = versions[data["dataset_version"]]
    if file_hash(store.path(d["snapshot_uri"])) != data["snapshot_fingerprint"]:
        raise ProjectError("Search source fingerprint değişti.")
    request = dict(
        path=str(store.path(d["snapshot_uri"])),
        fingerprint=data["snapshot_fingerprint"],
        version_id=d["version_id"],
        origin_version=data["origin_version"],
        source_snapshot_id=data["source_snapshot_id"],
        snapshot_uri=d["snapshot_uri"],
        config_revision=0,
        columns=d["import_metadata"]["columns"],
        semantic_metadata=d.get("semantic_metadata", {}),
        row_count=d["import_metadata"]["row_count"],
        history_state=state,
        preparation=data["preparation"],
    )
    from veri_ufku.domain.contracts import ComputeBudget
    from veri_ufku.importers.delimited import Control

    with tempfile.TemporaryDirectory(prefix="search-parent-") as work:
        values = context(
            request,
            ValidationSpec.from_dict(data["protocol"]),
            SearchSpec.from_dict(data["search_spec"]),
            work,
            Control(
                budget=ComputeBudget(cpu_threads=data["environment"]["cpu_threads"])
            ),
        )
    frame, y, groups, times, spec, _, plan, scopes, scope_plans, _, _, compat = values
    if (
        compat != data["compat_id"]
        or plan != data["plan"]
        or scope_plans != data["scope_plans"]
    ):
        raise ProjectError("Search frozen joint validation/provenance uyuşmuyor.")
    validate_source(
        data,
        frame,
        y,
        groups,
        times,
        spec,
        ValidationSpec.from_dict(data["protocol"]),
        scopes,
    )

    def add(draft):
        if data["prior_test_use_ids"] != prior_uses(draft):
            raise ProjectError("Search final test geçmişi güncel değil; sıfırlanamaz.")
        old_record = next(
            (
                r
                for r in reversed(draft["results"])
                if r.get("search", {}).get("search_id") == data["search_id"]
            ),
            None,
        )
        old = load_search(store, old_record) if old_record else None
        if old:
            validate_transition(old, data)
        raw = json.dumps(
            data, ensure_ascii=False, sort_keys=True, allow_nan=False
        ).encode()
        staging = store.path("staging") / uid()
        staging.mkdir(mode=0o700)
        path = staging / "search.bin"
        path.write_bytes(raw)
        fp = file_hash(path)
        uri = "sources/" + uid() + ".bin"
        store.pending[uri] = (path, dict(**fp, kind="source", rows=None, schema=None))
        sequence = (
            old_record["search"].get("checkpoint_index", 0) + 1 if old_record else 0
        )
        record["search"] = summarize(
            data, uri, fp, sequence, old_record["id"] if old_record else None
        )
        draft["results"].append(record)

    return transaction(store, state, add)


def validate_journal(state, versions):
    searches = {}
    seen = []
    for record in state["results"]:
        if "test_use" in record or "time_series_test_use" in record:
            seen.append(record["id"])
        if "search" not in record:
            continue
        validate_record(record, versions)
        data = record["search"]
        if data["prior_test_use_ids"] != seen:
            raise ProjectError("Search kalıcı final kullanım defteri bağı silinmiş.")
        previous = searches.get(data["search_id"])
        if data.get("details_uri"):
            if (
                data["previous_checkpoint_id"] != (previous["id"] if previous else None)
                or data["checkpoint_index"]
                != (
                    previous["search"].get("checkpoint_index", 0) + 1 if previous else 0
                )
                or previous
                and (
                    previous["search"]["compat_id"] != data["compat_id"]
                    or previous["search"]["elapsed_seconds"] > data["elapsed_seconds"]
                )
            ):
                raise ProjectError(
                    "Search checkpoint zinciri/compatibility geriye alınmış."
                )
        elif previous:
            validate_transition(previous["search"], data)
        searches[data["search_id"]] = record


def summarize(data, uri, fingerprint, sequence, previous):
    fields = (
        "schema",
        "search_id",
        "status",
        "dataset_version",
        "origin_version",
        "source_snapshot_id",
        "snapshot_fingerprint",
        "protocol",
        "search_spec",
        "environment",
        "compat_id",
        "prior_test_use_ids",
        "interpretation",
        "elapsed_seconds",
        "created_at",
        "estimated_cost",
        "recommended",
        "native_fit_reservations",
        "session_run_ids",
    )
    result = {k: copy.deepcopy(data[k]) for k in fields}
    result.update(
        preparation_spec=copy.deepcopy(data["preparation"]["spec"]),
        trial_counts={
            k: sum(t["status"] == k for t in data["trials"]) for k in TRIAL_STATUSES
        },
        details_uri=uri,
        details_fingerprint=fingerprint,
        checkpoint_index=sequence,
        previous_checkpoint_id=previous,
    )
    return result


def load_search(store, record):
    if record is None:
        raise ProjectError("Kayıtlı arama bulunamadı.")
    summary = record["search"]
    if not summary.get("details_uri"):
        return copy.deepcopy(summary)
    path = store.path(summary["details_uri"])
    if (
        path.stat().st_size > 32 * 1024**2
        or file_hash(path) != summary["details_fingerprint"]
    ):
        raise ProjectError("Search safe JSON artifact bozuk/boyut sınırında.")
    data = json.loads(path.read_bytes())
    if (
        summarize(
            data,
            summary["details_uri"],
            summary["details_fingerprint"],
            summary["checkpoint_index"],
            summary["previous_checkpoint_id"],
        )
        != summary
    ):
        raise ProjectError("Search artifact/özet uyuşmuyor.")
    validate_record(
        dict(record, search=data), {d["version_id"]: d for d in store.state["datasets"]}
    )
    return data


def export_history(data, target):
    """Create a new safe JSON file atomically; existing paths/sources are never replaced."""
    import os
    from pathlib import Path

    path = Path(target)
    if (
        not path.is_absolute()
        or not path.parent.is_dir()
        or path.exists()
        or path.is_symlink()
    ):
        raise ProjectError(
            "History export yeni mutlak dosya yolu ister; mevcut dosya/source üzerine yazılmaz."
        )
    raw = json.dumps(
        data, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2
    ).encode()
    if len(raw) > 32 * 1024**2:
        raise ProjectError("History JSON32MiB sınırını aşıyor.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".search-export-", dir=path.parent, delete=False
        ) as f:
            temporary = Path(f.name)
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.link(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return str(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
