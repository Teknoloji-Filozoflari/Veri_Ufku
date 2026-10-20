"""Atomic safe JSON forecast runs and persistent final-test reveal journal."""

import copy
import json
from datetime import UTC, datetime

from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import file_hash
from veri_ufku.storage.validation_store import transaction


def check_history(state, version):
    from veri_ufku.modeling.history import audit

    history = audit(state, version, version, "raw")
    if any(
        f["risk"] == "dataset_learned" or f["kind"] == "ordered_fill"
        for f in history["findings"]
    ):
        raise ProjectError(
            "Kaynak geçmişinde tüm veriden öğrenme veya sıralı doldurma var; geleceğin etkisi dışlanamaz. Veri ekranından önceki ham/temiz kaynak sürümünü seçin. Bu yol geçmişi otomatik değiştirmez."
        )


def validate_record(record, versions):
    from veri_ufku.modeling.time_series import TimeSeriesSpec

    value = record["time_series"]
    dataset = versions.get(value["dataset_version"])
    if (
        not dataset
        or record["dataset_version_ids"] != [dataset["version_id"]]
        or record["seed"] is not None
    ):
        raise ProjectError("Zaman serisi sürüm bağı geçersiz.")
    TimeSeriesSpec.from_dict(value["spec"]).validate(
        dataset["import_metadata"]["columns"]
    )
    if value["schema"] != "TimeSeriesRun/v1" or not value["details_uri"].startswith(
        "sources/"
    ):
        raise ProjectError("Zaman serisi artifact bağı geçersiz.")


def load(store, record):
    from veri_ufku.modeling.time_series import validate_run

    summary = record["time_series"]
    path = store.path(summary["details_uri"])
    if file_hash(path) != summary["details_fingerprint"]:
        raise ProjectError("Zaman serisi ayrıntı hash'i değişmiş.")
    if path.stat().st_size > 64 * 1024**2:
        raise ProjectError("Seri ayrıntısı 64 MiB sınırını aşıyor.")

    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ProjectError("Seri ayrıntısında yinelenen JSON alanı.")
            result[key] = item
        return result

    try:
        value = json.loads(
            path.read_bytes(),
            object_pairs_hook=unique,
            parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)),
        )
    except (ValueError, RecursionError, UnicodeError) as error:
        raise ProjectError("Seri ayrıntı JSON biçimi geçersiz.") from error
    if (
        summarize(value, summary["details_uri"], summary["details_fingerprint"])
        != summary
    ):
        raise ProjectError("Zaman serisi özet/ayrıntı uyuşmuyor.")
    dataset = next(
        d
        for d in store.state["datasets"]
        if d["version_id"] == value["dataset_version"]
    )
    validate_run(value, dataset)
    info = store.manifest["artifacts"][dataset["snapshot_uri"]]
    if value["snapshot_fingerprint"] != {k: info[k] for k in ("sha256", "size")}:
        raise ProjectError("Zaman serisi kaynak fingerprint bağı değişmiş.")
    from itertools import chain

    import polars as pl

    from veri_ufku.modeling.time_series import TimeSeriesSpec, normalize

    spec = TimeSeriesSpec.from_dict(value["spec"])
    columns = dataset["import_metadata"]["columns"]
    names = [
        c["name"]
        for c in columns
        if c["id"] in (spec.date, spec.measurement, spec.group)
    ]
    if value.get("advanced", {}).get("schema") == "SignalRun/v1":
        from veri_ufku.modeling.signals import validate_source

        validate_source(
            value, pl.read_parquet(store.path(dataset["snapshot_uri"])), columns
        )
        return value
    normalized = normalize(
        pl.read_parquet(
            store.path(dataset["snapshot_uri"]), columns=["__vu_row_id"] + names
        ),
        columns,
        spec,
        dataset.get("semantic_metadata"),
    )
    for source, saved in zip(normalized, value["groups"], strict=True):
        cutoff = len(source["series"]) - spec.test_periods
        if (
            (source["group"], source["group_type"])
            != (saved["group"], saved["group_type"])
            or saved["train_row_ids"]
            != list(chain.from_iterable(source["members"][:cutoff]))
            or saved["test_row_ids"]
            != list(chain.from_iterable(source["members"][cutoff:]))
        ):
            raise ProjectError(
                "Kayıtlı zaman/grup üyelikleri gerçek kaynakla uyuşmuyor."
            )
    if value.get("advanced"):
        from veri_ufku.modeling.temporal import validate_source

        all_frame = pl.read_parquet(store.path(dataset["snapshot_uri"]))
        validate_source(value, all_frame, columns)
    return value


def frozen(value):
    return (
        value["dataset_version"],
        value["snapshot_fingerprint"],
        value["spec"],
        [
            (
                g["group"],
                g["group_type"],
                g["chosen"],
                g["train_end"],
                g["test_start"],
                g["test_end"],
            )
            for g in value["groups"]
        ],
    )


def summarize(value, uri, fp):
    summary = copy.deepcopy(value)
    summary["groups"] = [
        dict(g, train_row_ids=[], test_row_ids=[], folds=[], history=[])
        for g in value["groups"]
    ]
    if value.get("advanced", {}).get("schema") == "SignalRun/v1":
        summary["advanced"]["recordings"] = []
        summary["advanced"]["windows"] = []
        summary["advanced"]["classifier"] = None
    elif value.get("advanced"):
        for g in summary["groups"]:
            g["diagnostics"] = {
                key: {
                    k: v
                    for k, v in d.items()
                    if k not in ("trend", "seasonal", "residual", "values", "lags")
                }
                for key, d in g["diagnostics"].items()
            }
        summary["advanced"]["series_task"] = None
        summary["advanced"]["reconciliation"] = []
    summary.update(details_uri=uri, details_fingerprint=fp)
    return summary


def reserve(store, state, development):
    ident = "result:" + uid()

    def add(draft):
        if not any(
            r.get("time_series", {}).get("run_id") == development["run_id"]
            and r["time_series"]["mode"] == "development"
            and frozen(r["time_series"]) == frozen(development)
            for r in draft["results"]
        ):
            raise ProjectError("Kayıtlı geliştirme koşusu gerekli.")
        draft["results"].append(
            dict(
                id=ident,
                dataset_version_ids=[development["dataset_version"]],
                seed=None,
                capability_id="model.time-series",
                time_series_test_use=dict(
                    status="pending",
                    development_run_id=development["run_id"],
                    created_at=datetime.now(UTC).isoformat(),
                    prior_use_ids=[
                        r["id"]
                        for r in draft["results"]
                        if "time_series_test_use" in r or "test_use" in r
                    ],
                ),
            )
        )

    return transaction(store, state, add), ident


def finish(
    store,
    state,
    result=None,
    test_use_id=None,
    status="completed",
    checkpoint=lambda point: None,
):
    from veri_ufku.modeling.time_series import validate_run

    item = None

    def add(draft):
        nonlocal item
        if result is not None:
            value = {
                k: copy.deepcopy(v) for k, v in result.items() if k != "worker_pid"
            }
            dataset = next(
                d
                for d in draft["datasets"]
                if d["version_id"] == value["dataset_version"]
            )
            check_history(draft, value["dataset_version"])
            validate_run(value, dataset)
            if value.get("advanced"):
                import polars as pl

                if value["advanced"].get("schema") == "SignalRun/v1":
                    from veri_ufku.modeling.signals import validate_source
                else:
                    from veri_ufku.modeling.temporal import validate_source

                validate_source(
                    value,
                    pl.read_parquet(store.path(dataset["snapshot_uri"])),
                    dataset["import_metadata"]["columns"],
                )
            if (
                file_hash(store.path(dataset["snapshot_uri"]))
                != value["snapshot_fingerprint"]
            ):
                raise ProjectError("Kaynak snapshot değişmiş.")
            if (value["mode"] == "final") != bool(test_use_id):
                raise ProjectError(
                    "Final test açılmadan kullanım defteri kaydedilmeli."
                )
            previous = [
                r["id"]
                for r in draft["results"]
                if ("time_series_test_use" in r or "test_use" in r)
                and r["id"] != test_use_id
            ]
            value["prior_test_use_ids"] = previous
            value["interpretation"] = (
                "Önceki final test kullanımı var; yeniden seçim keşifseldir, bağımsız değerlendirme gerekir."
                if previous
                else "Bu projede önceki final test kullanımı yok; proje dışı kullanım bilinmez."
            )
            raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
            if len(raw) > 64 * 1024**2:
                raise ProjectError("Seri ayrıntısı 64 MiB sınırını aşıyor.")
            target = store.path("staging") / uid()
            target.mkdir(mode=0o700)
            path = target / "time-series.bin"
            path.write_bytes(raw)
            fp = file_hash(path)
            uri = "sources/" + uid() + ".bin"
            store.pending[uri] = (
                path,
                dict(**fp, kind="source", rows=None, schema=None),
            )
            item = dict(
                id="result:" + uid(),
                dataset_version_ids=[dataset["version_id"]],
                seed=None,
                capability_id=value.get("advanced", {})
                .get("provenance", {})
                .get("capability_id", "model.time-series"),
                time_series=summarize(value, uri, fp),
            )
            draft["results"].append(item)
        if test_use_id:
            use = next(
                r["time_series_test_use"]
                for r in draft["results"]
                if r["id"] == test_use_id
            )
            if (
                use["status"] != "pending"
                or result
                and use["development_run_id"] != result["development_run_id"]
            ):
                raise ProjectError(
                    "Final test defteri dondurulmuş geliştirme koşusuyla uyuşmuyor."
                )
            use.update(
                status=status,
                finished_at=datetime.now(UTC).isoformat(),
                result_id=item["id"] if item else None,
            )

    new_state = transaction(store, state, add, checkpoint)
    return new_state, item


def validate_journal(state):
    seen = []
    runs = {
        r["time_series"]["run_id"]: r for r in state["results"] if "time_series" in r
    }
    if len(runs) != sum("time_series" in r for r in state["results"]):
        raise ProjectError("Seri koşu kimliği yinelenemez.")
    for r in state["results"]:
        if "time_series_test_use" in r:
            use = r["time_series_test_use"]
            dev = runs.get(use["development_run_id"])
            if (
                not dev
                or dev["time_series"]["mode"] != "development"
                or use["prior_use_ids"] != seen
                or use["status"]
                not in ("pending", "completed", "failed", "canceled", "stale")
            ):
                raise ProjectError("Seri final test kullanım kaydı geçersiz.")
            if use["status"] == "completed":
                final = next(
                    (p for p in runs.values() if p["id"] == use["result_id"]), None
                )
                if (
                    not final
                    or final["time_series"]["mode"] != "final"
                    or final["time_series"]["development_run_id"]
                    != use["development_run_id"]
                    or frozen(final["time_series"]) != frozen(dev["time_series"])
                ):
                    raise ProjectError("Tamamlanan seri final test sonucu eksik.")
            seen.append(r["id"])
        elif "test_use" in r:
            seen.append(r["id"])
