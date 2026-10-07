"""Bounded, data-only project schema, independent of application releases."""

import hashlib
import json
import re
import uuid
from pathlib import PurePosixPath

SCHEMA_VERSION = 5
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
        if not isinstance(source, dict) or set(source) != {
            "id",
            "path",
            "fingerprint",
            "copy_uri",
        }:
            raise ProjectError("Kaynak alanları geçersiz.")
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
                "operation_id",
                "output_schema",
            }
        ):
            raise ProjectError("Dataset alanları geçersiz.")
        entity_id(dataset["dataset_id"], "dataset")
        entity_id(dataset["version_id"], "dv")
        if dataset["version_id"] in versions or dataset["source_id"] not in seen:
            raise ProjectError("Dataset sürümü veya kaynak bağı geçersiz.")
        versions.add(dataset["version_id"])
        if dataset["snapshot_uri"] is not None:
            relative(dataset["snapshot_uri"])
        if dataset.get("quarantine_uri"):
            relative(dataset["quarantine_uri"])
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
            spec = validate(
                op.get("spec", {}),
                dict(
                    columns=parent["import_metadata"]["columns"],
                    version_id=parent["version_id"],
                ),
            )
            if (
                list(spec.output_schema) != d["import_metadata"]["columns"]
                or d["source_id"] != parent["source_id"]
            ):
                raise ProjectError("İşlem çıktı kolon/kaynak bağı uyuşmuyor.")
    if len(encode(state)) > MAX_MANIFEST // 2:
        raise ProjectError("Proje durum boyutu sınırı aşıldı.")


def _validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ProjectError("Manifest nesne olmalı.")
    version = manifest.get("format_version")
    if type(version) is not int or version not in (0, 1, 2, 3, 4, SCHEMA_VERSION):
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
        for uri in (d["snapshot_uri"], d.get("quarantine_uri"))
    ]
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
                    or operation.get("spec", {}).get("input_version_id") not in parents
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
