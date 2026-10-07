"""Ordinary SQLite tables only; query-only immutable captured file, no extensions."""

import sqlite3
from contextlib import closing
from pathlib import Path

from veri_ufku.importers.native import canonical
from veri_ufku.storage.project_model import ProjectError


def reject_live_companions(original):
    for suffix in ("-wal", "-journal"):
        companion = Path(str(original) + suffix)
        if companion.exists() and companion.stat().st_size:
            raise ProjectError(
                "SQLite WAL/journal etkin: önce kaynak uygulamada checkpoint/kapatma yapın; eksik snapshot alınmadı."
            )


def connect(snapshot):
    reject_live_companions(Path(snapshot.get("original", snapshot["path"])))
    path = Path(snapshot["path"]).resolve()
    with path.open("rb") as stream:
        if stream.read(16) != b"SQLite format 3\x00":
            raise ProjectError(
                "SQLite başlığı geçersiz veya şifreli kaynak desteklenmiyor."
            )
    db = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    db.enable_load_extension(False)
    db.execute("PRAGMA query_only=ON")
    db.execute("PRAGMA trusted_schema=OFF")
    return db


def tables(snapshot):
    with closing(connect(snapshot)) as db:
        return [
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' AND sql NOT LIKE 'CREATE VIRTUAL%' ORDER BY name"
            )
        ]


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def records(snapshot, settings, control):
    if settings.sheet not in tables(snapshot):
        raise ProjectError(
            "Salt okunur SQLite tablosunu seçin; view/virtual table desteklenmez."
        )
    try:
        with closing(connect(snapshot)) as db:
            # Stable capture order: rowid where available, declared primary-key order for WITHOUT ROWID.
            columns = db.execute(
                "PRAGMA table_info(" + quote(settings.sheet) + ")"
            ).fetchall()
            names = [r[1] for r in columns]
            if not 1 <= len(names) <= 256:
                raise ProjectError("SQLite tablo sütun sınırı1–256.")
            sql = db.execute(
                "SELECT sql FROM sqlite_schema WHERE name=?", (settings.sheet,)
            ).fetchone()[0]
            if "WITHOUT ROWID" in sql.upper():
                keys = [r[1] for r in sorted(columns, key=lambda r: r[5]) if r[5]]
            else:
                keys = [
                    next(
                        (
                            n
                            for n in ("rowid", "_rowid_", "oid")
                            if n.casefold() not in {name.casefold() for name in names}
                        ),
                        "",
                    )
                ]
                if not keys[0]:
                    raise ProjectError(
                        "SQLite gizli rowid isimlerinin tümü örtülmüş; açık sıralı dışa aktarım kullanın."
                    )
            cursor = db.execute(
                "SELECT "
                + ",".join(quote(n) for n in names)
                + " FROM "
                + quote(settings.sheet)
                + " ORDER BY "
                + ",".join(quote(n) for n in keys)
            )
            for i, row in enumerate(cursor, 1):
                control.check()
                if i > 10000000:
                    raise ProjectError("SQLite kayıt sınırı aşıldı.")
                if any(isinstance(v, bytes) for v in row):
                    raise ProjectError(
                        "SQLite BLOB desteklenmiyor; sessiz metne dönüşüm yok."
                    )
                values = dict(zip(names, row, strict=True))
                yield dict(
                    ordinal=i,
                    start=i,
                    end=i,
                    locator=f"sqlite:{settings.sheet}:capture-row:{i}",
                    values=values,
                    raw=canonical(values),
                    reason=None,
                    expansion="{}",
                    original_headers=names,
                )
    except sqlite3.Error as error:
        raise ProjectError(
            "SQLite salt okunur tablo okunamadı: " + str(error)
        ) from error
