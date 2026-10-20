"""Connector sources join the existing adapter/worker/native publication path."""

import copy
import json
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import polars as pl
import pyarrow.parquet as pq

from veri_ufku.importers.connector_contracts import ConnectorSpec
from veri_ufku.importers.delimited import Control, hash_artifact, verify_capture
from veri_ufku.importers.native import StructuredSettings, canonical
from veri_ufku.storage.project_model import ProjectError, uid


def metadata_valid(value):
    if not isinstance(value, dict) or set(value) != {
        "spec",
        "started_at",
        "finished_at",
        "details",
    }:
        raise ProjectError("Connector köken kaydı geçersiz.")
    ConnectorSpec.from_dict(value["spec"])
    for name in ("started_at", "finished_at"):
        datetime.fromisoformat(value[name])
    if (
        not isinstance(value["details"], dict)
        or len(json.dumps(value, ensure_ascii=False)) > 200000
    ):
        raise ProjectError("Connector köken boyutu geçersiz.")


def discover(spec, secret, control):
    if not spec.terms_acknowledged:
        raise ProjectError("Bağlantı ve servis kullanım koşullarını açıkça onaylayın.")
    from veri_ufku.importers.database_connectors import session

    if spec.kind not in ("postgresql", "mysql", "mariadb", "duckdb"):
        raise ProjectError("Tablo keşfi yalnız veritabanı için.")
    with session(spec, secret, control) as (_, tables, metadata):
        control.check()
        return dict(tables=tables, connection=metadata)


def capture(spec, secret, workspace, control):
    if not spec.terms_acknowledged:
        raise ProjectError(
            "Ağ/bağlantı eylemi ve servis koşulları açık onay gerektirir."
        )
    control.check()
    workspace = Path(workspace)
    started = datetime.now(UTC).isoformat()
    seen = sqlite3.connect(workspace / "connector-keys.sqlite")
    seen.execute("CREATE TABLE seen(key TEXT PRIMARY KEY)")

    def identity(value):
        if type(value) not in (str, int) or len(str(value)) > 4096:
            raise ProjectError(
                "Kaynak kayıt kimliği null olmayan String/Integer olmalı."
            )
        try:
            seen.execute("INSERT INTO seen VALUES (?)", (canonical(value),))
        except sqlite3.IntegrityError:
            raise ProjectError(
                "Kaynak kimliği tekrarlandı; retry/sayfalama kısmi yayın üretmedi."
            ) from None

    try:
        if spec.kind == "tile":
            from veri_ufku.geo.network import tile_capture

            source, adapter_id, details = tile_capture(spec, secret, workspace, control)
        elif spec.kind in ("http", "geocoding"):
            from veri_ufku.importers.http_connectors import rest_capture

            source, adapter_id, details = rest_capture(
                spec, secret, workspace, control, identity
            )
        elif spec.kind == "s3":
            from veri_ufku.importers.http_connectors import s3_capture

            source, adapter_id, details = s3_capture(spec, secret, workspace, control)
        else:
            from veri_ufku.importers.database_connectors import batches, session

            source, adapter_id = workspace / "query.parquet", "parquet"
            writer, count, decoded_bytes = None, 0, 0
            try:
                with session(spec, secret, control) as (db, tables, details):
                    for frame in batches(spec, db, tables, details, control):
                        control.check()
                        if frame.estimated_size() > min(
                            64 * 1024**2, control.budget.ram_bytes // 4
                        ):
                            raise ProjectError("Veritabanı batch bellek sınırı aşıldı.")
                        for value in frame[spec.key_column]:
                            identity(value)
                        arrow = frame.to_arrow()
                        decoded_bytes += arrow.nbytes
                        if decoded_bytes > spec.max_bytes:
                            raise ProjectError(
                                "Veritabanı decoded içerik sınırı aşıldı; kısmi yayın yok."
                            )
                        if writer is None:
                            writer = pq.ParquetWriter(
                                source, arrow.schema, compression="zstd"
                            )
                        writer.write_table(arrow)
                        count += frame.height
                        if count > spec.max_rows:
                            raise ProjectError("Veritabanı satır sınırı aşıldı.")
                        control.disk(workspace)
                        control.progress("Salt okunur sorgu snapshot'ı", count, None)
                    details["rows"] = count
                    details["duplicate_check"] = "unique non-null source keys"
            finally:
                if writer:
                    writer.close()
            if not count:
                raise ProjectError("Sorgu boş; yeni dataset yayımlanmadı.")
        control.check()
        fingerprint = hash_artifact(source, control)
        package = {
            "postgresql": "psycopg",
            "mysql": "pymysql",
            "mariadb": "pymysql",
            "duckdb": "duckdb",
            "s3": "boto3",
        }.get(spec.kind)
        if package:
            details["client_package"] = package
            details["client_version"] = version(package)
        connector = dict(
            spec=spec.data(),
            started_at=started,
            finished_at=datetime.now(UTC).isoformat(),
            details=details,
        )
        secret_values = [secret] if secret else []
        if spec.kind == "s3" and secret:
            auth = json.loads(secret)
            secret_values = [auth.get("secret_key"), auth.get("session_token")]
        encoded = json.dumps(connector, ensure_ascii=False)
        if any(value and value in encoded for value in secret_values):
            raise ProjectError(
                "Kaynak credential'ı metadata'da geri döndürdü; secret içeren kayıt yayımlanmadı."
            )
        metadata_valid(connector)
        snapshot = dict(
            path=str(source),
            original="/veri-ufku-connector-snapshots/" + uid(),
            fingerprint=fingerprint,
            captured_at=connector["finished_at"],
            adapter_id=spec.kind,
            payload_adapter=adapter_id,
            connector=connector,
        )
        from veri_ufku.importers.registry import default_settings

        settings = default_settings(adapter_id)
        if isinstance(settings, StructuredSettings):
            settings = replace(settings, format_metadata={"connector": connector})
        if adapter_id == "jsonl":
            settings = replace(settings, record_path="")
        return snapshot, settings
    finally:
        seen.close()


class ConnectorAdapter:
    def __init__(self, kind):
        self.adapter_id = kind

    def validate_source(self, request, control=None):
        if not request.path.is_file():
            raise ProjectError("Connector yerel snapshot'ı yok.")

    def delegate(self, snapshot, settings):
        from veri_ufku.importers.registry import get_adapter

        return get_adapter(snapshot["payload_adapter"])

    def inspect(self, snapshot, settings, control):
        metadata_valid(snapshot["connector"])
        verify_capture(snapshot, control)
        return dict(
            connector=snapshot["connector"],
            **self.delegate(snapshot, settings).inspect(snapshot, settings, control),
        )

    def preview(self, snapshot, settings, control=None):
        result = self.delegate(snapshot, settings).preview(snapshot, settings, control)
        connector = copy.deepcopy(snapshot["connector"])
        if isinstance(settings, StructuredSettings):
            result["settings"]["format_metadata"] = dict(
                result["settings"].get("format_metadata", {}), connector=connector
            )
        result["schema"]["warnings"].append(
            "Bağlantı kopyası: "
            + connector["details"]["consistency"]
            + ". Kaynak tazeliği otomatik denetlenmez; yeniden bağlantı açık eylemdir."
        )
        if connector["spec"]["kind"] not in ("http", "s3", "tile", "geocoding"):
            result["schema"]["warnings"].append(
                "Sorgu sıralı ve limitli; tüm kaynak tablo büyüklüğü bilinmiyor."
            )
        return result

    def import_data(self, snapshot, settings, workspace, control):
        spec = ConnectorSpec.from_dict(snapshot["connector"]["spec"])

        def bounded_progress(phase, done, total):
            if done > spec.max_rows:
                raise ProjectError(
                    "Connector kaynak kayıt sınırı aşıldı; kısmi yayın yok."
                )
            control.progress(phase, done, total)

        bounded = Control(control.cancel, bounded_progress, control.budget)
        bounded.started = control.started
        result = self.delegate(snapshot, settings).import_data(
            snapshot, settings, workspace, bounded
        )
        connector = copy.deepcopy(snapshot["connector"])
        if isinstance(settings, StructuredSettings):
            result["settings"]["format_metadata"] = dict(
                result["settings"].get("format_metadata", {}), connector=connector
            )
        result["adapter_id"] = self.adapter_id
        details = connector["details"]
        if details.get("client_package"):
            result["environment"] = tuple(result.get("environment", ())) + (
                (details["client_package"], details["client_version"]),
            )
        result.setdefault("diagnostics", {})["connector"] = connector
        if result["examined"] > spec.max_rows:
            raise ProjectError("Connector kayıt sınırı aşıldı; kısmi yayın yok.")
        if spec.kind not in ("s3", "tile"):
            key = spec.field_mapping.get(spec.key_column, spec.key_column)
            if key not in result["schema"]["original_headers"]:
                raise ProjectError("Kaynak kayıt kimliği eşleme sırasında kayboldu.")
            key = result["schema"]["names"][
                result["schema"]["original_headers"].index(key)
            ]
            source = pl.scan_parquet(result["path"])
            schema = source.collect_schema()

            def locators(frame):
                control.check()
                return frame.with_columns(
                    pl.Series(
                        "__vu_source_locator",
                        [
                            canonical(dict(connector=spec.kind, source_key=v))
                            for v in frame[key]
                        ],
                        dtype=pl.String,
                    )
                )

            rewritten = Path(workspace) / (uid() + ".connector.parquet")
            source.map_batches(
                locators,
                schema=schema,
                streamable=True,
                predicate_pushdown=False,
                projection_pushdown=False,
                slice_pushdown=False,
            ).sink_parquet(rewritten, engine="streaming")
            result["path"] = str(rewritten)
            result["artifact_fingerprint"] = hash_artifact(rewritten, control)
        return result
