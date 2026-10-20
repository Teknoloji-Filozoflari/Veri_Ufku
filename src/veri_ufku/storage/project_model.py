"""Bounded, data-only project schema, independent of application releases."""

import hashlib
import json
import re
import uuid
from pathlib import PurePosixPath

SCHEMA_VERSION = 7
MAX_MANIFEST = 4 * 1024 * 1024
MAX_ARTIFACT = 4 * 1024**3


class ProjectError(ValueError):
    pass


def uid():
    return str(uuid.uuid4())


def encode(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, allow_nan=False
    ).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    if len(raw) > MAX_MANIFEST:
        raise ProjectError("Proje metadata boyutu sınırı aşıldı.")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ProjectError("Metadata alanı tekrarlanmış.")
            result[key] = value
        return result

    try:
        return json.loads(
            raw,
            object_pairs_hook=unique,
            parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)),
        )
    except (ValueError, RecursionError, UnicodeError) as error:
        raise ProjectError("Proje metadata biçimi geçersiz.") from error


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9:_-]{1,100}", value):
        raise ProjectError("Proje kimliği geçersiz.")


def entity_id(value, namespace):
    identifier(value)
    try:
        prefix, raw = value.split(":", 1)
        parsed = uuid.UUID(raw)
        if prefix != namespace or parsed.version != 4 or str(parsed) != raw:
            raise ValueError
    except ValueError as error:
        raise ProjectError("Kalıcı kimlik isim alanlı UUIDv4 olmalı.") from error


def relative(value):
    if not isinstance(value, str) or len(value) > 300 or "\\" in value:
        raise ProjectError("Artifact yolu geçersiz.")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or any(p in {"..", "."} for p in path.parts)
    ):
        raise ProjectError("Artifact yolu proje dışına çıkamaz.")
    if len(path.parts) != 2 or path.parts[0] not in {"snapshots", "sources"}:
        raise ProjectError("Artifact konumu geçersiz.")
    identifier(path.stem)
    return value


def fingerprint(value):
    if not isinstance(value, dict) or set(value) != {"sha256", "size"}:
        raise ProjectError("Kaynak fingerprint alanları geçersiz.")
    if not isinstance(value["sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", value["sha256"]
    ):
        raise ProjectError("Artifact hash değeri geçersiz.")
    if type(value["size"]) is not int or not 0 <= value["size"] <= MAX_ARTIFACT:
        raise ProjectError("Artifact boyutu sınır dışında.")


def new_state(name="Adsız proje"):
    return dict(
        name=name,
        sources=[],
        import_settings={},
        datasets=[],
        operations=[],
        results=[],
        help_preferences={"depth": 0},
        seed=None,
    )


def validate_state(state):
    if not isinstance(state, dict) or set(state) - {"workflow"} != set(new_state()):
        raise ProjectError("Proje durum alanları eksik veya bilinmiyor.")
    if not isinstance(state["name"], str) or not 1 <= len(state["name"]) <= 200:
        raise ProjectError("Proje adı 1–200 karakter olmalı.")
    if state["seed"] is not None and (
        type(state["seed"]) is not int or not 0 <= state["seed"] < 2**32
    ):
        raise ProjectError("Seed 0–4294967295 aralığında olmalı.")
    for key in ("import_settings", "help_preferences"):
        if not isinstance(state[key], dict):
            raise ProjectError("Proje ayarları geçersiz.")
    for key in ("sources", "datasets", "operations", "results"):
        if not isinstance(state[key], list) or len(state[key]) > 10000:
            raise ProjectError("Proje kayıt sayısı geçersiz.")
    seen = set()
    for source in state["sources"]:
        if not isinstance(source, dict) or set(source) - {"connector"} != {
            "id",
            "path",
            "fingerprint",
            "copy_uri",
        }:
            raise ProjectError("Kaynak alanları geçersiz.")
        if "connector" in source:
            from veri_ufku.importers.connector_contracts import ConnectorSpec

            metadata = source["connector"]
            if not isinstance(metadata, dict) or set(metadata) != {
                "spec",
                "details",
                "started_at",
                "finished_at",
            }:
                raise ProjectError("Connector kaynak kökeni geçersiz.")
            ConnectorSpec.from_dict(metadata["spec"])
            if source["copy_uri"] is None:
                raise ProjectError("Connector değişmez kaynak kopyası gerekli.")
        entity_id(source["id"], "source")
        if source["id"] in seen:
            raise ProjectError("Kaynak kimliği tekrarlandı.")
        seen.add(source["id"])
        if (
            not isinstance(source["path"], str)
            or not source["path"].startswith("/")
            or len(source["path"]) > 4096
            or "\x00" in source["path"]
        ):
            raise ProjectError("Kaynak yolu geçersiz.")
        fingerprint(source["fingerprint"])
        if source["copy_uri"] is not None:
            relative(source["copy_uri"])
    versions = set()
    for dataset in state["datasets"]:
        if (
            not isinstance(dataset, dict)
            or not {
                "dataset_id",
                "version_id",
                "source_id",
                "snapshot_uri",
            }
            <= set(dataset)
            or set(dataset)
            - {
                "dataset_id",
                "version_id",
                "source_id",
                "snapshot_uri",
                "import_metadata",
                "quarantine_uri",
                "semantic_metadata",
                "analysis_unit",
                "parent_version_ids",
                "input_version_ids",
                "operation_id",
                "output_schema",
                "lineage_uri",
                "forked_from_version_id",
                "derived_analysis",
                "schema_contract",
                "entity_resolution",
            }
        ):
            raise ProjectError("Dataset alanları geçersiz.")
        entity_id(dataset["dataset_id"], "dataset")
        entity_id(dataset["version_id"], "dv")
        if dataset["version_id"] in versions or dataset["source_id"] not in seen:
            raise ProjectError("Dataset sürümü veya kaynak bağı geçersiz.")
        if "input_version_ids" in dataset:
            inputs = dataset["input_version_ids"]
            if (
                not isinstance(inputs, list)
                or not 1 <= len(inputs) <= 2
                or any(v not in versions for v in inputs)
                or not dataset.get("operation_id")
            ):
                raise ProjectError(
                    "Dataset girdileri önceki değişmez sürümlere bağlı olmalı."
                )
        versions.add(dataset["version_id"])
        if dataset["snapshot_uri"] is not None:
            relative(dataset["snapshot_uri"])
        if dataset.get("quarantine_uri"):
            relative(dataset["quarantine_uri"])
        if dataset.get("lineage_uri"):
            relative(dataset["lineage_uri"])
        if "import_metadata" in dataset:
            m = dataset["import_metadata"]
            if not isinstance(m, dict) or set(m) != {
                "columns",
                "row_count",
                "bad_count",
                "source_snapshot_id",
                "captured_at",
                "settings",
            }:
                raise ProjectError("İçe aktarma metadata alanları geçersiz.")
            entity_id(m["source_snapshot_id"], "snapshot")
            if any(
                type(m[k]) is not int or m[k] < 0 for k in ("row_count", "bad_count")
            ):
                raise ProjectError("İçe aktarma kayıt sayısı geçersiz.")
            if not isinstance(m["captured_at"], str) or len(m["captured_at"]) > 100:
                raise ProjectError("Kopya zamanı geçersiz.")
            from veri_ufku.importers.registry import settings_from_dict

            settings_from_dict(m["settings"])
            if not isinstance(m["columns"], list) or not 1 <= len(m["columns"]) <= 256:
                raise ProjectError("Sütun metadata sınırı geçersiz.")
            column_ids, column_names = set(), set()
            for c in m["columns"]:
                if not isinstance(c, dict) or set(c) != {
                    "id",
                    "name",
                    "original_name",
                    "type",
                }:
                    raise ProjectError("Sütun alanları geçersiz.")
                entity_id(c["id"], "col")
                if (
                    c["id"] in column_ids
                    or c["name"] in column_names
                    or any(
                        not isinstance(c[k], str) or len(c[k]) > 1048576
                        for k in ("name", "original_name", "type")
                    )
                ):
                    raise ProjectError("Sütun kimliği/adı geçersiz.")
                column_ids.add(c["id"])
                column_names.add(c["name"])
    from veri_ufku.analytics.contracts import validate_semantics

    previous = {}
    for dataset in state["datasets"]:
        validate_semantics(dataset)
        for parent in dataset.get("parent_version_ids", []):
            old = previous.get(parent)
            if (
                not old
                or old["dataset_id"] != dataset["dataset_id"]
                or (
                    not dataset.get("operation_id")
                    and any(
                        old.get(k) != dataset.get(k)
                        for k in (
                            "dataset_id",
                            "source_id",
                            "snapshot_uri",
                            "import_metadata",
                        )
                    )
                )
            ):
                raise ProjectError(
                    "Metadata parent önceki aynı dataset ve fiziksel snapshot sürümü olmalı."
                )
        if dataset.get("forked_from_version_id"):
            source = previous.get(dataset["forked_from_version_id"])
            if (
                not source
                or dataset.get("parent_version_ids")
                or dataset.get("operation_id")
                or source["dataset_id"] == dataset["dataset_id"]
                or any(
                    dataset.get(k) != source.get(k)
                    for k in (
                        "snapshot_uri",
                        "source_id",
                        "import_metadata",
                        "semantic_metadata",
                        "analysis_unit",
                    )
                )
            ):
                raise ProjectError(
                    "Kopya dataset kökü değişmez giriş sürümünü tam korumalı."
                )
        previous[dataset["version_id"]] = dataset
    from veri_ufku.operations.contracts import OperationSpec, validate_workflow

    validate_workflow(state)
    for d in state["datasets"]:
        if d.get("operation_id"):
            entity_id(d["operation_id"], "op")
            if not isinstance(d.get("output_schema"), dict):
                raise ProjectError("İşlem çıktı şeması eksik.")
    for key in ("operations", "results"):
        ids = set()
        for record in state[key]:
            if not isinstance(record, dict) or not {
                "id",
                "dataset_version_ids",
                "seed",
            } <= set(record):
                raise ProjectError("İşlem/sonuç sürüm bağı veya seed eksik.")
            entity_id(record["id"], "op" if key == "operations" else "result")
            if record["id"] in ids:
                raise ProjectError("İşlem/sonuç kimliği tekrarlandı.")
            ids.add(record["id"])
            if "spec" in record:
                spec = OperationSpec.from_dict(record["spec"])
                if spec.id != record["id"] or spec.input_version_id not in versions:
                    raise ProjectError("İşlem tarifi sürüm bağı geçersiz.")
            if (
                not isinstance(record["dataset_version_ids"], list)
                or not set(record["dataset_version_ids"]) <= versions
            ):
                raise ProjectError("İşlem/sonuç bilinmeyen veri sürümüne bağlı.")
            if record["seed"] is not None and (
                type(record["seed"]) is not int or not 0 <= record["seed"] < 2**32
            ):
                raise ProjectError("İşlem/sonuç seed geçersiz.")
    from veri_ufku.operations.contracts import validate

    by_version = {d["version_id"]: d for d in state["datasets"]}
    from veri_ufku.storage.unsupervised_store import validate_derived, validate_record

    for record in state["results"]:
        if "unsupervised" in record:
            validate_record(record, by_version)
    from veri_ufku.storage.time_series_store import (
        validate_journal as validate_series_journal,
    )

    validate_series_journal(state)
    for record in state["results"]:
        if "text_analysis" in record:
            from veri_ufku.storage.text_store import (
                validate_record as validate_text_record,
            )

            validate_text_record(record, by_version)
        if "time_series" in record:
            from veri_ufku.storage.time_series_store import (
                validate_record as validate_series_record,
            )

            validate_series_record(record, by_version)
    from veri_ufku.operations.data_contracts import contract_validate

    for dataset in state["datasets"]:
        if "schema_contract" in dataset:
            value = dataset["schema_contract"]
            if (
                not isinstance(value, dict)
                or set(value) - {"report_operation"}
                != {"dataset_version", "definition_version", "definition", "status"}
                or value["dataset_version"] != dataset["version_id"]
                or value["definition_version"] not in by_version
                or value["status"]
                not in ("requires_validation", "checked", "inapplicable")
            ):
                raise ProjectError("Sürüm bağlı şema sözleşmesi geçersiz.")
            contract_validate(
                value["definition"],
                by_version[value["definition_version"]]["import_metadata"]["columns"],
            )
            if "report_operation" in value:
                record = next(
                    (
                        o
                        for o in state["operations"]
                        if o["id"] == value["report_operation"]
                    ),
                    None,
                )
                if (
                    not record
                    or record.get("spec", {}).get("kind") != "contract_check"
                    or record["spec"]["parameters"]["contract"] != value["definition"]
                    or value["status"] == "checked"
                    and record["output_version_id"] != dataset["version_id"]
                ):
                    raise ProjectError(
                        "Kalite sözleşmesinin kayıtlı kontrol/provenance bağı geçersiz."
                    )
            elif value["status"] == "checked":
                raise ProjectError("Kontrol edilmiş sözleşmenin sonuç kaydı gerekli.")
            for rule in value["definition"]["rules"]:
                if rule["kind"] == "foreign_key":
                    p = rule["parameters"]
                    other = by_version.get(p["version_id"])
                    if not other or p["column_id"] not in {
                        c["id"] for c in other["import_metadata"]["columns"]
                    }:
                        raise ProjectError(
                            "Sözleşmenin foreign-key referans sürümü/sütunu projede yok."
                        )
        if "entity_resolution" in dataset:
            value = dataset["entity_resolution"]
            if (
                not isinstance(value, dict)
                or set(value)
                != {"canonical_column", "decision_operation", "input_version"}
                or value["canonical_column"]
                not in {c["id"] for c in dataset["import_metadata"]["columns"]}
                or value["input_version"] not in by_version
            ):
                raise ProjectError("Canonical kimlik bağı geçersiz.")
            decision = next(
                (
                    o
                    for o in state["operations"]
                    if o["id"] == value["decision_operation"]
                ),
                None,
            )
            if (
                not decision
                or decision.get("spec", {}).get("kind") != "entity_merge"
                or decision["spec"]["parameters"]["canonical_column"]
                != value["canonical_column"]
                or decision["spec"]["input_version_id"] != value["input_version"]
            ):
                raise ProjectError("Canonical insan kararının provenance bağı eksik.")
        if "derived_analysis" in dataset:
            validate_derived(dataset, by_version, state["results"])
    from veri_ufku.charts.contracts import validate_saved

    for record in state["results"]:
        if "dashboard" in record:
            from veri_ufku.charts.dashboard import DashboardSpec

            dashboard = record["dashboard"]
            spec = DashboardSpec(
                **{
                    **dashboard,
                    "widgets": tuple(dashboard.get("widgets", ())),
                    "global_filters": tuple(dashboard.get("global_filters", ())),
                }
            )
            spec.validate(by_version)
            bound = spec.bound_versions()
            if bound != set(record["dataset_version_ids"]):
                raise ProjectError("Dashboard sonuç sürüm bağı kayıtla uyuşmuyor.")
        if "chart" in record:
            validate_saved(record, by_version)
        if "analysis" in record:
            from veri_ufku.statistics.contracts import (
                validate_saved as validate_analysis,
            )

            validate_analysis(record, by_version)
    by_operation = {o["id"]: o for o in state["operations"]}
    for d in state["datasets"]:
        if d.get("operation_id"):
            op = by_operation.get(d["operation_id"])
            parents = d.get("parent_version_ids", [])
            if (
                not op
                or len(parents) != 1
                or op.get("output_version_id") != d["version_id"]
            ):
                raise ProjectError("İşlem çıktısının kalıcı tarif bağı eksik.")
            parent = by_version[parents[0]]
            binding_parent = parent
            if op.get("spec", {}).get("destination") == "copy":
                if (
                    parent.get("forked_from_version_id")
                    != op["spec"]["input_version_id"]
                ):
                    raise ProjectError("Kopya işlem giriş bağı geçersiz.")
                binding_parent = by_version[parent["forked_from_version_id"]]
            spec = validate(
                op.get("spec", {}),
                dict(
                    columns=binding_parent["import_metadata"]["columns"],
                    settings=binding_parent["import_metadata"]["settings"],
                    version_id=binding_parent["version_id"],
                    entity_resolution=binding_parent.get("entity_resolution", {}),
                    **(
                        {
                            "secondary": {
                                "version_id": other["version_id"],
                                "columns": other["import_metadata"]["columns"],
                                "settings": other["import_metadata"]["settings"],
                            }
                        }
                        if (
                            other := by_version.get(
                                op.get("spec", {})
                                .get("parameters", {})
                                .get("secondary_version_id")
                                or (
                                    op.get("spec", {}).get(
                                        "input_version_ids", [None, None]
                                    )[1]
                                    if op.get("spec", {}).get("kind")
                                    == "contract_check"
                                    and len(
                                        op.get("spec", {}).get("input_version_ids", [])
                                    )
                                    == 2
                                    else None
                                )
                            )
                        )
                        else {}
                    ),
                ),
            )
            if list(spec.input_version_ids) != d.get("input_version_ids", []):
                raise ProjectError("Dataset giriş sürümü ilişkileri uyuşmuyor.")
            if (
                list(spec.output_schema) != d["import_metadata"]["columns"]
                or d["source_id"] != parent["source_id"]
            ):
                raise ProjectError("İşlem çıktı kolon/kaynak bağı uyuşmuyor.")
    from veri_ufku.storage.validation_store import validate_journal

    for record in state["results"]:
        if "baseline" in record:
            from veri_ufku.modeling.baseline import validate_saved as validate_baseline

            validate_baseline(record, by_version)
            from veri_ufku.modeling.history import audit

            run = record["baseline"]
            if run["history"] != audit(
                state,
                run["origin_version"],
                run["dataset_version"],
                run["preparation_spec"]["history_action"],
            ):
                raise ProjectError("Baseline geçmişi kayıtlı işlemlerle uyuşmuyor.")
    validate_journal(state)
    from veri_ufku.storage.experiment_store import validate as validate_experiments

    validate_experiments(state)
    from veri_ufku.storage.monitor_store import validate_records as validate_monitors

    validate_monitors(state, by_version)
    from veri_ufku.storage.learning_lab_store import validate_records as validate_labs

    validate_labs(state)
    from veri_ufku.storage.review_store import validate_records as validate_reviews

    validate_reviews(state)
    from veri_ufku.storage.privacy_store import validate_records as validate_privacy

    validate_privacy(state)
    from veri_ufku.storage.plugin_store import validate_records as validate_plugins

    validate_plugins(state)
    from veri_ufku.storage.report_builder_store import (
        validate_records as validate_reports,
    )

    validate_reports(state, by_version)
    from veri_ufku.storage.scenario_store import validate_records as validate_scenarios

    validate_scenarios(state, by_version)
    from veri_ufku.storage.explanation_store import validate_records

    validate_records(state, by_version)
    from veri_ufku.storage.search_store import (
        validate_journal as validate_search_journal,
    )

    validate_search_journal(state, by_version)
    from veri_ufku.storage.neural_store import (
        validate_journal as validate_neural_journal,
    )

    validate_neural_journal(state, by_version)
    from veri_ufku.modeling.contracts import validate_saved as validate_preparation
    from veri_ufku.modeling.history import audit as audit_preparation

    for record in state["results"]:
        if "preparation" in record:
            validate_preparation(record, by_version)
            result = record["preparation"]
            if result["history"] != audit_preparation(
                state,
                result["origin_version"],
                result["dataset_version"],
                result["spec"]["history_action"],
            ):
                raise ProjectError(
                    "Model hazırlığı kayıtlı işlem geçmişiyle uyuşmuyor."
                )
    if len(encode(state)) > MAX_MANIFEST // 2:
        raise ProjectError("Proje durum boyutu sınırı aşıldı.")


def _validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ProjectError("Manifest nesne olmalı.")
    version = manifest.get("format_version")
    if type(version) is not int or version not in (0, 1, 2, 3, 4, 5, 6, SCHEMA_VERSION):
        raise ProjectError(
            "Bilinmeyen proje şema sürümü. Uyumlu bir Veri_Ufku sürümüyle açın; proje değiştirilmedi."
        )
    fields = {
        "format_version",
        "project_id",
        "commit_id",
        "parent_commit",
        "state",
        "artifacts",
        "created_at",
        "environment",
        "migration",
    }
    if set(manifest) != fields:
        raise ProjectError("Manifest alanları eksik veya bilinmiyor.")
    for key in ("project_id", "commit_id"):
        identifier(manifest[key])
    if manifest["parent_commit"] is not None:
        identifier(manifest["parent_commit"])
    if (
        not isinstance(manifest["created_at"], str)
        or len(manifest["created_at"]) > 80
        or not isinstance(manifest["environment"], dict)
        or not isinstance(manifest["migration"], list)
    ):
        raise ProjectError("Manifest ortam/tarih/migrasyon kaydı geçersiz.")
    state = manifest["state"]
    if version == 0:
        state = dict(state, help_preferences={"depth": 0}, seed=None)
    validate_state(state)
    if version < 2 and any(
        set(d) - {"dataset_id", "version_id", "source_id", "snapshot_uri"}
        for d in state["datasets"]
    ):
        raise ProjectError("Eski şemada yeni dataset alanları olamaz.")
    if version < 4 and any(
        set(d) & {"semantic_metadata", "analysis_unit", "parent_version_ids"}
        for d in state["datasets"]
    ):
        raise ProjectError("Sütun rolü metadata şema4 gerektirir.")
    if version < 5 and (
        "workflow" in state or any("operation_id" in d for d in state["datasets"])
    ):
        raise ProjectError("İşlem geçmişi proje şema5 gerektirir.")
    if version < 6 and any(
        d.get("lineage_uri") or d.get("forked_from_version_id")
        for d in state["datasets"]
    ):
        raise ProjectError("Kopya dataset/köken ilişkisi şema6 gerektirir.")
    if version < 7 and (
        any(d.get("input_version_ids") for d in state["datasets"])
        or any(
            d.get("import_metadata", {}).get("settings", {}).get("adapter_id")
            in ("ods", "sqlite", "ipc", "ipc_stream")
            for d in state["datasets"]
        )
    ):
        raise ProjectError("Çoklu girdi/yeni adaptör proje şema7 gerektirir.")
    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, dict) or len(artifacts) > 10000:
        raise ProjectError("Artifact listesi geçersiz.")
    for uri, info in artifacts.items():
        relative(uri)
        if not isinstance(info, dict) or set(info) != {
            "sha256",
            "size",
            "kind",
            "rows",
            "schema",
        }:
            raise ProjectError("Artifact alanları geçersiz.")
        fingerprint({k: info[k] for k in ("sha256", "size")})
        if info["kind"] not in {"source", "parquet"}:
            raise ProjectError("Artifact türü desteklenmiyor.")
        if info["kind"] == "parquet" and (
            type(info["rows"]) is not int
            or info["rows"] < 0
            or not isinstance(info["schema"], dict)
        ):
            raise ProjectError("Parquet satır/şema bilgisi geçersiz.")
    refs = [s["copy_uri"] for s in state["sources"]] + [
        uri
        for d in state["datasets"]
        for uri in (d["snapshot_uri"], d.get("quarantine_uri"), d.get("lineage_uri"))
    ]
    refs += [
        uri
        for record in state["results"]
        if "analysis" in record
        for uri in record["analysis"]["artifact_uris"].values()
    ]
    refs += [
        uri
        for record in state["results"]
        if "chart" in record
        for uri in record["chart"]["artifact_uris"].values()
    ]
    refs += [
        r["baseline"]["details_uri"]
        for r in state["results"]
        if r.get("baseline", {}).get("details_uri")
    ]
    refs += [
        r["explanation"]["details_uri"] for r in state["results"] if "explanation" in r
    ]
    refs += [
        r["search"]["details_uri"]
        for r in state["results"]
        if r.get("search", {}).get("details_uri")
    ]
    refs += [
        r["unsupervised"]["assignments_uri"]
        for r in state["results"]
        if "unsupervised" in r
    ]
    refs += [
        r[k]["model_package_uri"]
        for r in state["results"]
        for k in ("baseline", "unsupervised")
        if r.get(k, {}).get("model_package_uri")
    ]
    refs += [
        r["time_series"]["details_uri"] for r in state["results"] if "time_series" in r
    ]
    refs += [
        r["monitoring"]["details_uri"] for r in state["results"] if "monitoring" in r
    ]
    refs += [
        a["uri"]
        for r in state["results"]
        if "scientific_report" in r
        for a in r["scientific_report"]["file_refs"].values()
    ]
    refs += [r["scenario"]["details_uri"] for r in state["results"] if "scenario" in r]
    refs += [
        r["learning_lab"]["details_uri"]
        for r in state["results"]
        if "learning_lab" in r
    ]
    refs += [
        r["plugin_result"]["details_uri"]
        for r in state["results"]
        if "plugin_result" in r
    ]
    refs += [r["neural"]["details_uri"] for r in state["results"] if "neural" in r]
    from veri_ufku.storage.model_store import validate_links

    validate_links(state, artifacts)
    if any(uri and uri not in artifacts for uri in refs):
        raise ProjectError("Bağlı artifact bulunamadı.")
    for source in state["sources"]:
        uri = source["copy_uri"]
        if uri and (
            artifacts[uri]["kind"] != "source"
            or {k: artifacts[uri][k] for k in ("sha256", "size")}
            != source["fingerprint"]
        ):
            raise ProjectError("Taşınabilir kaynak kopyası fingerprint ile uyuşmuyor.")
    for dataset in state["datasets"]:
        uri = dataset["snapshot_uri"]
        if (
            dataset.get("quarantine_uri")
            and artifacts[dataset["quarantine_uri"]]["kind"] != "parquet"
        ):
            raise ProjectError("Karantina türü Parquet olmalı.")
        if uri and artifacts[uri]["kind"] != "parquet":
            raise ProjectError("Dataset snapshot türü Parquet olmalı.")
        if (
            dataset.get("lineage_uri")
            and artifacts[dataset["lineage_uri"]]["kind"] != "parquet"
        ):
            raise ProjectError("Satır kökeni artifact türü Parquet olmalı.")
        if "import_metadata" in dataset:
            m = dataset["import_metadata"]
            q = dataset.get("quarantine_uri")
            if (
                not uri
                or artifacts[uri]["rows"] != m["row_count"]
                or (artifacts[q]["rows"] if q else 0) != m["bad_count"]
            ):
                raise ProjectError(
                    "Dataset/karantina kayıt sayıları metadata ile uyuşmuyor."
                )
            if dataset.get("forked_from_version_id"):
                source = next(
                    d
                    for d in state["datasets"]
                    if d["version_id"] == dataset["forked_from_version_id"]
                )
                if artifacts[uri] != artifacts[source["snapshot_uri"]]:
                    raise ProjectError(
                        "Kopya dataset snapshotı kaynak sürümle aynı olmalı."
                    )
                continue
            if dataset.get("derived_analysis"):
                from veri_ufku.operations.types import dtype_of

                source = next(
                    d
                    for d in state["datasets"]
                    if d["version_id"] == dataset["derived_analysis"]["source_version"]
                )
                expected_schema = dict(artifacts[source["snapshot_uri"]]["schema"])
                for column in m["columns"][len(source["import_metadata"]["columns"]) :]:
                    expected_schema[column["name"]] = str(dtype_of(column["type"]))
                if expected_schema != artifacts[uri]["schema"]:
                    raise ProjectError(
                        "İşaretli dataset şeması kaynak ve analiz kolonlarıyla uyuşmuyor."
                    )
                continue
            if dataset.get("operation_id"):
                if dataset["output_schema"] != artifacts[uri]["schema"]:
                    raise ProjectError("İşlem çıktı şeması artifact ile uyuşmuyor.")
                parents = dataset.get("parent_version_ids", [])
                operation = next(
                    (
                        o
                        for o in state["operations"]
                        if o["id"] == dataset["operation_id"]
                    ),
                    None,
                )
                if (
                    not operation
                    or (
                        operation.get("spec", {}).get("input_version_id") not in parents
                        and not any(
                            d["version_id"] in parents
                            and d.get("forked_from_version_id")
                            == operation.get("spec", {}).get("input_version_id")
                            for d in state["datasets"]
                        )
                    )
                    or operation.get("output_version_id") != dataset["version_id"]
                ):
                    raise ProjectError("İşlem çıktı/giriş sürüm bağı geçersiz.")
                continue
            from veri_ufku.importers.delimited import (
                INTERNAL,
                TYPES,
                ImportSettings,
                dtype,
            )

            if "adapter_id" in m["settings"]:
                from veri_ufku.importers.registry import validate_native_metadata

                if version < 3:
                    raise ProjectError("Native import metadata şema 3 gerektirir.")
                validate_native_metadata(m, artifacts[uri])
                continue
            settings = ImportSettings.from_dict(m["settings"])
            kinds = tuple(c["type"] for c in m["columns"])
            if any(k not in TYPES for k in kinds) or (
                settings.types and settings.types != kinds
            ):
                raise ProjectError("Dataset sütun türleri ayarlarla uyuşmuyor.")
            schema = {c["name"]: str(dtype(c["type"], settings)) for c in m["columns"]}
            schema.update(
                {n: "String" if i < 2 else "Int64" for i, n in enumerate(INTERNAL)}
            )
            if schema != artifacts[uri]["schema"]:
                raise ProjectError("Dataset sütun şeması metadata ile uyuşmuyor.")
    return state


def validate_manifest(manifest):
    try:
        return _validate_manifest(manifest)
    except (TypeError, KeyError, OverflowError, RecursionError) as error:
        raise ProjectError("Manifest alan türleri geçersiz.") from error
