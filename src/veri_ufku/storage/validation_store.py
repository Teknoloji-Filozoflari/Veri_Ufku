"""Project-wide append-only test-use/choice journal, atomically committed before reveal."""

import copy
import json
from datetime import UTC, datetime

from veri_ufku.storage.project_model import ProjectError, decode, uid
from veri_ufku.storage.project_store import file_hash


def transaction(store, state, mutate, checkpoint=lambda point: None):
    store._guard()
    previous, pending, commit = store.state, dict(store.pending), store.commit_id
    try:
        draft = copy.deepcopy(state)
        # A caller cannot erase the journal by supplying an older project draft.
        journal = [
            r
            for r in store.state["results"]
            if "test_use" in r
            or "model_choice" in r
            or "baseline" in r
            or "time_series_test_use" in r
            or "time_series" in r
            or "experiment_event" in r
            or "monitoring" in r
            or "scenario" in r
            or "learning_lab" in r
            or "scientific_report" in r
            or "review_event" in r
            or "privacy_event" in r
            or "plugin_result" in r
            or "explanation" in r
            or "search" in r
            or "neural" in r
        ]
        existing = {r["id"]: r for r in draft["results"]}
        if any(existing.get(r["id"]) != r for r in journal):
            raise ProjectError(
                "Önceki model/test kullanım defteri silinemez; projeyi yeniden açın."
            )
        mutate(draft)
        store.state = draft
        store.save(checkpoint=checkpoint)
        return copy.deepcopy(store.state)
    except BaseException:
        if decode(store._read("ACTIVE", 4096))["commit_id"] != commit:
            store._load("ACTIVE")
            store.pending.clear()
        else:
            store.state, store.pending = previous, pending
        raise


def prior_uses(state):
    return [
        r["id"]
        for r in state["results"]
        if "test_use" in r or "time_series_test_use" in r
    ]


def choice(
    store,
    state,
    dataset_version,
    spec,
    pipeline_id,
    run_id,
    regression=None,
    classification=None,
    search_id=None,
):
    from veri_ufku.storage.experiment_store import capture

    captured = capture(
        dict(
            spec=spec,
            regression=regression,
            classification=classification,
            pipeline_id=pipeline_id,
        )
    )

    def add(draft):
        draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[dataset_version],
                seed=spec["seed"],
                capability_id="model.classification"
                if classification
                else "model.regression"
                if regression
                else "model.baseline",
                model_choice=dict(
                    schema="ModelChoice/v1",
                    experiment_capture=captured,
                    status="pending",
                    invalid_folds=[],
                    run_id=run_id,
                    pipeline_id=pipeline_id,
                    spec=spec,
                    regression=regression,
                    classification=classification,
                    chosen_at=datetime.now(UTC).isoformat(),
                    prior_test_use_ids=prior_uses(draft),
                    interpretation="Test görüldükten sonraki seçim keşifseldir; bağımsız değerlendirme gerekir."
                    if prior_uses(draft)
                    else "Henüz bu projede final test kullanımı kaydedilmedi; proje dışı kullanım bilinmez.",
                ),
            )
        )
        if search_id is not None:
            draft["results"][-1]["model_choice"]["search_id"] = search_id

    return transaction(store, state, add)


def reserve_test(store, state, baseline, run_id):
    from veri_ufku.storage.experiment_store import capture

    if baseline["mode"] != "development":
        raise ProjectError("Final test için kayıtlı geliştirme koşusu seçin.")
    ident = "result:" + uid()

    def add(draft):
        if not any(
            r.get("baseline", {}).get("run_id") == baseline["run_id"]
            for r in draft["results"]
        ):
            raise ProjectError("Geliştirme koşusu bu projede kayıtlı değil.")
        draft["results"].append(
            dict(
                id=ident,
                dataset_version_ids=list(
                    dict.fromkeys(
                        [baseline["origin_version"], baseline["dataset_version"]]
                    )
                ),
                seed=baseline["seed"],
                capability_id="model.classification"
                if baseline.get("classification")
                else "model.regression"
                if baseline.get("regression")
                else "model.baseline",
                test_use=dict(
                    schema="FinalTestUse/v1",
                    experiment_capture=capture(
                        dict(
                            pipeline_id=baseline["pipeline_id"],
                            spec=baseline["spec"],
                            regression=baseline.get("regression"),
                            classification=baseline.get("classification"),
                        )
                    ),
                    dataset_version=baseline["dataset_version"],
                    source_snapshot_id=baseline["source_snapshot_id"],
                    snapshot_fingerprint=baseline["snapshot_fingerprint"],
                    split_id=baseline["plan"]["split_id"],
                    protocol_id=baseline["plan"]["protocol_id"],
                    pipeline_id=baseline["pipeline_id"],
                    run_id=run_id,
                    development_run_id=baseline["run_id"],
                    selected_model=baseline.get("selected_model"),
                    regression=baseline.get("regression"),
                    classification=baseline.get("classification"),
                    decision=decision_summary(baseline.get("decision")),
                    requested_at=datetime.now(UTC).isoformat(),
                    evaluated_at=None,
                    status="pending",
                    prior_test_use_ids=prior_uses(draft),
                    note="Değerlendirme başlamadan kayıt açıldı. Pending kayıt kesilmiş veya sonucu kaydedilememiş kullanımı da görünür tutar; proje dışı kullanım bilinmez.",
                ),
            )
        )

    return transaction(store, state, add), ident


def complete(
    store,
    state,
    result=None,
    test_use_id=None,
    status="completed",
    invalid_folds=None,
    checkpoint=lambda point: None,
    run_id=None,
):
    def update(draft):
        if result:
            from veri_ufku.modeling.baseline import validate_saved

            versions = {d["version_id"]: d for d in draft["datasets"]}
            record = dict(
                id="result:" + uid(),
                dataset_version_ids=list(
                    dict.fromkeys([result["origin_version"], result["dataset_version"]])
                ),
                seed=result["seed"],
                capability_id="model.classification"
                if result.get("classification")
                else "model.regression"
                if result.get("regression")
                else "model.baseline",
                baseline={
                    k: v
                    for k, v in result.items()
                    if k not in ("worker_pid", "project_root", "model_package")
                },
            )
            from veri_ufku.storage.model_store import adopt

            if result.get("model_package"):
                adopt(store, record["baseline"], result["model_package"])
            validate_saved(record, versions)
            if result.get("uncertainty"):
                from veri_ufku.modeling.uncertainty import validate_source

                validate_source(store, result)
            from veri_ufku.modeling.history import audit

            if result["history"] != audit(
                draft,
                result["origin_version"],
                result["dataset_version"],
                result["preparation_spec"]["history_action"],
            ):
                raise ProjectError("Baseline geçmişi kayıtlı işlemlerle uyuşmuyor.")
            d = versions[result["dataset_version"]]
            if (
                file_hash(store.path(d["snapshot_uri"]))
                != result["snapshot_fingerprint"]
            ):
                raise ProjectError("Baseline kaynak fingerprint değişti.")
            if (result["mode"] == "final") != bool(test_use_id):
                raise ProjectError("Final test kullanım kaydı zorunlu.")
            raw = json.dumps(
                record["baseline"], ensure_ascii=False, sort_keys=True, allow_nan=False
            ).encode()
            if len(raw) > 256 * 1024:
                if len(raw) > 256 * 1024**2:
                    raise ProjectError("Baseline ayrıntı kaydı 256MiB sınırını aşıyor.")
                target = store.path("staging") / uid()
                target.mkdir(mode=0o700)
                path = target / "baseline.bin"
                path.write_bytes(raw)
                fp = file_hash(path)
                uri = "sources/" + uid() + ".bin"
                store.pending[uri] = (
                    path,
                    dict(**fp, kind="source", rows=None, schema=None),
                )
                record["baseline"] = summarize(record["baseline"], uri, fp)
            draft["results"].append(record)
        if run_id:
            for record in draft["results"]:
                if record.get("model_choice", {}).get("run_id") == run_id:
                    record["model_choice"].update(
                        status=status,
                        invalid_folds=invalid_folds or [],
                        finished_at=datetime.now(UTC).isoformat(),
                    )
        if test_use_id:
            entry = next(
                r["test_use"] for r in draft["results"] if r["id"] == test_use_id
            )
            if entry["status"] != "pending":
                raise ProjectError("Test kullanım kaydı tekrar tamamlanamaz.")
            if (
                result
                and any(
                    entry[k] != result["plan"][k] for k in ("split_id", "protocol_id")
                )
                or result
                and entry["run_id"] != result["run_id"]
            ):
                raise ProjectError("Test kullanımı run/split bağı uyuşmuyor.")
            if result and (
                entry.get("selected_model") != result.get("selected_model")
                or entry.get("regression") != result.get("regression")
                or entry.get("classification") != result.get("classification")
                or entry.get("decision") != decision_summary(result.get("decision"))
            ):
                raise ProjectError(
                    "Final model geliştirme seçiminden farklı; test değerlendirmesi reddedildi."
                )
            if result and result.get("uncertainty"):
                development = next(
                    r["baseline"]
                    for r in draft["results"]
                    if r.get("baseline", {}).get("run_id")
                    == entry["development_run_id"]
                )
                if (
                    development.get("uncertainty") != result["uncertainty"]
                    or result["fit_count"] != 0
                ):
                    raise ProjectError(
                        "Final test calibration/threshold/q frozen kalmalı; refit reddedildi."
                    )
            entry.update(
                status=status,
                evaluated_at=result["evaluated_at"] if result else None,
                finished_at=datetime.now(UTC).isoformat(),
                invalid_folds=invalid_folds or [],
            )

    return transaction(store, state, update, checkpoint)


def validate_journal(state):
    entries = {r["id"]: r for r in state["results"]}
    seen = set()
    runs = {
        r["baseline"]["run_id"]: r["baseline"]
        for r in state["results"]
        if "baseline" in r
    }
    if len(runs) != sum("baseline" in r for r in state["results"]):
        raise ProjectError(
            "Baseline run kimliği tekrarlandı; yeni koşu kimliği gerekir."
        )
    for r in state["results"]:
        if "time_series_test_use" in r:
            seen.add(r["id"])
        for key in ("test_use", "model_choice"):
            if key not in r:
                continue
            value = r[key]
            if set(value["prior_test_use_ids"]) != seen:
                raise ProjectError(
                    "Test kullanım/seçim geçmişi önceki kayıtlara bağlı olmalı."
                )
            if key == "model_choice" and value.get("classification"):
                from veri_ufku.modeling.classification import settings

                settings(value["classification"])
                run = runs.get(value["run_id"])
                if run and (
                    run.get("classification") != value["classification"]
                    or run["spec"] != value["spec"]
                    or run["pipeline_id"] != value["pipeline_id"]
                ):
                    raise ProjectError(
                        "Kategori sınıf/eşik/model ayar geçmişi koşuyla uyuşmuyor."
                    )
            if key == "test_use":
                if (
                    value["schema"] != "FinalTestUse/v1"
                    or value["status"]
                    not in ("pending", "completed", "canceled", "failed", "stale")
                    or value["development_run_id"] not in runs
                ):
                    raise ProjectError("Test defteri durum/geliştirme koşusu geçersiz.")
                if value["status"] == "completed":
                    run = runs.get(value["run_id"])
                    if (
                        not run
                        or run["mode"] != "final"
                        or value["evaluated_at"] != run["evaluated_at"]
                        or value.get("selected_model") != run.get("selected_model")
                        or value.get("regression") != run.get("regression")
                        or value.get("classification") != run.get("classification")
                        or value.get("decision")
                        != decision_summary(run.get("decision"))
                        or value["prior_test_use_ids"] != run["prior_test_use_ids"]
                        or any(
                            value[k] != run["plan"][k]
                            for k in ("split_id", "protocol_id")
                        )
                    ):
                        raise ProjectError(
                            "Tamamlanan final test kaydı/sonucu uyuşmuyor."
                        )
                development = runs[value["development_run_id"]]
                final_run = runs.get(value["run_id"])
                if (
                    value["status"] == "completed"
                    and development.get("uncertainty")
                    and (
                        development["uncertainty"] != final_run.get("uncertainty")
                        or final_run["fit_count"] != 0
                    )
                ):
                    raise ProjectError("Final calibration frozen geçmişi uyuşmuyor.")
                if any(
                    value[k] != development[k]
                    for k in (
                        "dataset_version",
                        "source_snapshot_id",
                        "snapshot_fingerprint",
                        "pipeline_id",
                    )
                ) or any(
                    value[k] != development["plan"][k]
                    for k in ("split_id", "protocol_id")
                ):
                    raise ProjectError(
                        "Test defteri dondurulmuş geliştirme protokolüyle uyuşmuyor."
                    )
                seen.add(r["id"])
                if (
                    value.get("selected_model") != development.get("selected_model")
                    or value.get("regression") != development.get("regression")
                    or value.get("classification") != development.get("classification")
                    or value.get("decision")
                    != decision_summary(development.get("decision"))
                ):
                    raise ProjectError(
                        "Final aday defterdeki geliştirme seçimine bağlı olmalı."
                    )
    for run in runs.values():
        if (
            not set(run["prior_test_use_ids"])
            <= {
                i
                for i, r in entries.items()
                if "test_use" in r or "time_series_test_use" in r
            }
            or run["mode"] == "final"
            and not any(
                r.get("test_use", {}).get("run_id") == run["run_id"]
                and r["test_use"]["status"] == "completed"
                for r in entries.values()
            )
        ):
            raise ProjectError("Baseline final test defteri bağı eksik.")


def summarize(value, uri, fp):
    summary = copy.deepcopy(value)
    summary["plan"]["membership"] = None
    summary["excluded_target_row_ids"] = None
    for e in summary["evaluations"]:
        e["fit_row_ids"] = None
        e["fitted_parameters"] = None
        if summary.get("classification"):
            e["curves"] = None
        if "predictions" in e:
            e["predictions"] = None
    for c in summary.get("comparison", []):
        c["evaluations"] = None
    if summary.get("classification"):
        summary["decision"]["validation_row_ids"] = None
        summary["decision_validation"] = None
    summary.update(details_uri=uri, details_fingerprint=fp)
    return summary


def load_run(store, record):
    from veri_ufku.modeling.baseline import validate_saved

    summary = record["baseline"]
    if not summary.get("details_uri"):
        return copy.deepcopy(summary)
    path = store.path(summary["details_uri"])
    if (
        path.stat().st_size > 256 * 1024**2
        or file_hash(path) != summary["details_fingerprint"]
    ):
        raise ProjectError("Baseline ayrıntı artifactı bozuk/boyut sınırını aşıyor.")
    full = json.loads(path.read_bytes())
    if (
        summarize(full, summary["details_uri"], summary["details_fingerprint"])
        != summary
    ):
        raise ProjectError("Baseline ayrıntısı kayıt özetiyle uyuşmuyor.")
    validate_saved(
        dict(record, baseline=full),
        {d["version_id"]: d for d in store.state["datasets"]},
    )
    return full


def decision_summary(value):
    if value is None:
        return None
    return {k: v for k, v in value.items() if k != "validation_row_ids"}
