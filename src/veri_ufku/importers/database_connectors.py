"""Bound parameters and validated ordinary tables, inside read-only snapshots."""

import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

import polars as pl

from veri_ufku.importers.connector_contracts import identifier
from veri_ufku.storage.project_model import ProjectError


def quote(name, kind):
    identifier(name)
    char = "`" if kind in ("mysql", "mariadb") else '"'
    return char + name.replace(char, char * 2) + char


def query(spec, columns):
    selected = list(spec.columns or columns)
    if spec.key_column not in selected:
        selected.insert(0, spec.key_column)
    if not selected or any(c not in columns for c in selected):
        raise ProjectError(
            "Sorgu alanları ve benzersiz kaynak anahtarı tabloda olmalı."
        )
    params, where = [], []
    placeholder = "?" if spec.kind == "duckdb" else "%s"
    for item in spec.filters:
        if item["column"] not in columns:
            raise ProjectError("Sorgu filtresi tablo alanı değil.")
        where.append(
            quote(item["column"], spec.kind) + " " + item["op"] + " " + placeholder
        )
        params.append(item["value"])
    sql = "SELECT " + ",".join(quote(c, spec.kind) for c in selected)
    sql += " FROM " + quote(spec.schema, spec.kind) + "." + quote(spec.table, spec.kind)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY " + quote(spec.key_column, spec.kind) + " LIMIT " + placeholder
    params.append(spec.max_rows)
    return sql, params, selected


@contextmanager
def interrupt_on_cancel(control, callback):
    done = threading.Event()

    def watch():
        while not done.wait(0.05):
            if control.cancel and control.cancel.is_set():
                try:
                    callback()
                except Exception:
                    pass
                return

    thread = threading.Thread(target=watch, daemon=True)
    thread.start()
    try:
        yield
    finally:
        done.set()
        thread.join(timeout=1)


def physical_type(kind, name, precision=None, scale=None):
    name = name.lower()
    types = {
        "smallint": pl.Int16,
        "integer": pl.Int32,
        "int": pl.Int32,
        "bigint": pl.Int64,
        "tinyint": pl.Int8,
        "real": pl.Float32,
        "double precision": pl.Float64,
        "double": pl.Float64,
        "float": pl.Float64,
        "boolean": pl.Boolean,
        "bool": pl.Boolean,
        "varchar": pl.String,
        "character varying": pl.String,
        "character": pl.String,
        "char": pl.String,
        "text": pl.String,
        "longtext": pl.String,
        "mediumtext": pl.String,
        "tinytext": pl.String,
        "date": pl.Date,
        "uuid": pl.String,
        "timestamp without time zone": pl.Datetime("us"),
        "timestamp with time zone": pl.Datetime("us", "UTC"),
        "datetime": pl.Datetime("us"),
        "timestamp": pl.Datetime("us"),
    }
    if name in ("numeric", "decimal"):
        if (
            not precision
            or precision > 38
            or scale is None
            or not 0 <= scale <= precision
        ):
            raise ProjectError(
                "SQL decimal kesin precision≤38 ve scale beyanı gerekli."
            )
        return pl.Decimal(precision, scale)
    if name not in types:
        raise ProjectError(
            "SQL alan türü native destek sınırı dışında; kayıplı dönüşüm yok."
        )
    return types[name]


@contextmanager
def session(spec, secret, control):
    db = None
    empty_passfile = None
    try:
        if spec.kind == "postgresql":
            import psycopg

            empty_passfile = tempfile.NamedTemporaryFile(prefix="veri-ufku-pgpass-")
            db = psycopg.connect(
                host=spec.endpoint,
                port=spec.port or 5432,
                dbname=spec.database,
                user=spec.user,
                password=secret or "",
                passfile=empty_passfile.name,
                require_auth="password,md5,scram-sha-256,none",
                gssencmode="disable",
                sslcertmode="disable",
                sslmode="verify-full",
                sslrootcert=spec.ca_file or "system",
                connect_timeout=spec.timeout,
                autocommit=True,
            )
            role = db.execute(
                "SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user"
            ).fetchone()
            if not role or any(role):
                raise ProjectError(
                    "PostgreSQL için yetkisiz salt okunur rol gerekli; yönetici hesabı reddedildi."
                )
            db.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            db.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                (str(spec.timeout * 1000),),
            )
            db.execute("SELECT set_config('TimeZone', 'UTC', true)")
            token = str(db.execute("SELECT pg_current_snapshot()").fetchone()[0])
            tables = db.execute(
                "SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1,2"
            ).fetchall()
            metadata = dict(
                isolation="REPEATABLE READ READ ONLY",
                snapshot_token=token,
                consistency="single_transaction_snapshot",
                tls="verify-full",
                server=str(db.info.server_version),
            )
        elif spec.kind in ("mysql", "mariadb"):
            import pymysql

            db = pymysql.connect(
                host=spec.endpoint,
                port=spec.port or 3306,
                user=spec.user,
                password=secret,
                database=spec.database,
                connect_timeout=spec.timeout,
                read_timeout=spec.timeout,
                write_timeout=spec.timeout,
                ssl_ca=spec.ca_file or None,
                ssl_verify_cert=True,
                ssl_verify_identity=True,
                ssl_disabled=False,
                autocommit=True,
                charset="utf8mb4",
            )
            with db.cursor() as cursor:
                cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
                for (grant,) in cursor.fetchall():
                    if (
                        not grant.startswith("GRANT ")
                        or " TO " not in grant
                        or any(
                            priv.strip() not in ("SELECT", "USAGE")
                            for priv in grant.split(" ON ", 1)[0][6:].split(",")
                        )
                    ):
                        raise ProjectError(
                            "MySQL/MariaDB yalnız SELECT/USAGE grant'li hesap gerekli."
                        )
                cursor.execute("SELECT VERSION()")
                server = cursor.fetchone()[0]
                if ("mariadb" in server.lower()) != (spec.kind == "mariadb"):
                    raise ProjectError("Sunucu MySQL/MariaDB seçimiyle uyuşmuyor.")
                cursor.execute(
                    "SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ"
                )
                cursor.execute(
                    "SET SESSION max_statement_time=%s"
                    if spec.kind == "mariadb"
                    else "SET SESSION max_execution_time=%s",
                    (spec.timeout if spec.kind == "mariadb" else spec.timeout * 1000,),
                )
                cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
                cursor.execute("SHOW STATUS LIKE 'Ssl_cipher'")
                if not cursor.fetchone()[1]:
                    raise ProjectError("Veritabanı TLS doğrulaması gerekli.")
                cursor.execute(
                    "SELECT TABLE_SCHEMA,TABLE_NAME FROM information_schema.TABLES WHERE TABLE_TYPE='BASE TABLE' AND ENGINE='InnoDB' AND TABLE_SCHEMA NOT IN ('mysql','sys','performance_schema','information_schema') ORDER BY 1,2"
                )
                tables = cursor.fetchall()
            metadata = dict(
                isolation="REPEATABLE READ; WITH CONSISTENT SNAPSHOT; READ ONLY; InnoDB",
                consistency="single_transaction_snapshot",
                tls="certificate+hostname",
                server=server,
            )
        else:
            import duckdb

            path = Path(spec.endpoint).resolve(strict=True)
            if not path.is_file() or path.is_symlink():
                raise ProjectError("Yerel DuckDB dosyası gerekli.")
            db = duckdb.connect(
                str(path),
                read_only=True,
                config={
                    "enable_external_access": False,
                    "autoinstall_known_extensions": False,
                    "autoload_known_extensions": False,
                    "threads": control.budget.worker_threads,
                    "memory_limit": str(control.budget.ram_bytes // 2) + "B",
                },
            )
            db.execute("BEGIN TRANSACTION")
            tables = db.execute(
                "SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE' ORDER BY 1,2"
            ).fetchall()
            metadata = dict(
                isolation="file READ_ONLY; transaction",
                consistency="single_transaction_snapshot",
                external_access=False,
                server=duckdb.__version__,
            )
        yield db, [dict(schema=s, table=t) for s, t in tables], metadata
    except ImportError as error:
        raise ProjectError(
            "İsteğe bağlı connectors modülü kurulu değil; yerel temel uygulama kullanılabilir."
        ) from error
    except Exception as error:
        control.check()
        if isinstance(error, ProjectError):
            raise
        raise ProjectError(
            "Veritabanı bağlantısı/sorgusu tamamlanamadı; TLS, yetki veya timeout ayarını denetleyin. Secret ve sunucu hata metni gösterilmez."
        ) from error
    finally:
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
            try:
                db.close()
            except Exception:
                pass
        if empty_passfile is not None:
            empty_passfile.close()


def batches(spec, db, tables, metadata, control):
    if dict(schema=spec.schema, table=spec.table) not in tables:
        raise ProjectError("Doğrulanmış ordinary tablo/şemayı seçin.")
    if spec.kind == "duckdb":
        columns = [
            row[0]
            for row in db.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema=? AND table_name=? ORDER BY ordinal_position",
                [spec.schema, spec.table],
            ).fetchall()
        ]
        sql, params, selected = query(spec, columns)
        metadata.update(
            query=sql,
            parameters=list(params),
            key_column=spec.key_column,
            source_total_unknown=True,
            scope="bounded_ordered_query",
        )
        with interrupt_on_cancel(control, db.interrupt):
            reader = db.execute(sql, params).to_arrow_reader(1024)
            for batch in reader:
                control.check()
                yield pl.from_arrow(batch)
        return
    postgres = spec.kind == "postgresql"
    cursor = db.cursor()
    try:
        if postgres:
            relation = (
                quote(spec.schema, spec.kind) + "." + quote(spec.table, spec.kind)
            )
            cursor.execute(
                "SELECT has_table_privilege(%s, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'),has_schema_privilege(%s, 'CREATE')",
                (relation, spec.schema),
            )
            if any(cursor.fetchone()):
                raise ProjectError(
                    "Seçilen PostgreSQL kaynakta yazma/schema-create yetkisi var; salt okunur hesap gerekli."
                )
            cursor.execute(
                "SELECT column_name,data_type,numeric_precision,numeric_scale FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position",
                (spec.schema, spec.table),
            )
        else:
            cursor.execute(
                "SELECT COLUMN_NAME,DATA_TYPE,NUMERIC_PRECISION,NUMERIC_SCALE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION",
                (spec.schema, spec.table),
            )
        definitions = cursor.fetchall()
    finally:
        cursor.close()
    schema = {
        n: physical_type(spec.kind, dtype, precision, scale)
        for n, dtype, precision, scale in definitions
    }
    sql, params, selected = query(spec, schema)
    schema = {n: schema[n] for n in selected}
    metadata.update(
        query=sql,
        parameters=list(params),
        key_column=spec.key_column,
        source_total_unknown=True,
        scope="bounded_ordered_query",
    )
    cursor = (
        db.cursor(name="veri_ufku_read")
        if postgres
        else db.cursor(__import__("pymysql").cursors.SSCursor)
    )
    try:
        with interrupt_on_cancel(control, db.cancel if postgres else lambda: None):
            cursor.execute(sql, params)
            while rows := cursor.fetchmany(1024):
                control.check()
                converted = [
                    tuple(
                        str(v) if t == pl.String and v is not None else v
                        for v, t in zip(row, schema.values(), strict=True)
                    )
                    for row in rows
                ]
                yield pl.DataFrame(converted, schema=schema, orient="row", strict=True)
    finally:
        cursor.close()
