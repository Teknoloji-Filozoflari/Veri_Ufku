"""Local immutable commits. ACTIVE alone publishes SQLite + manifest + artifacts."""

import copy
import ctypes
import errno
import fcntl
import os
import platform
import shutil
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from veri_ufku.domain.contracts import Provenance
from veri_ufku.storage.project_model import (
    MAX_ARTIFACT,
    MAX_MANIFEST,
    SCHEMA_VERSION,
    ProjectError,
    decode,
    digest,
    encode,
    identifier,
    new_state,
    relative,
    uid,
    validate_manifest,
    validate_state,
)

CRASH_POINTS = (
    "artifact_written",
    "artifact_fsynced",
    "artifact_promoted",
    "artifact_directory_synced",
    "metadata_inserted",
    "metadata_committed",
    "manifest_written",
    "manifest_fsynced",
    "manifest_promoted",
    "commit_directory_synced",
    "pointer_written",
    "pointer_fsynced",
    "pointer_replaced",
    "root_synced",
)


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def file_hash(path):
    h = __import__("hashlib").sha256()
    size = 0
    with open(path, "rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_ARTIFACT:
                raise ProjectError("Dosya boyutu sınırı aşıldı (4 GiB).")
            h.update(chunk)
    return {"sha256": h.hexdigest(), "size": size}


def source_fingerprint(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ProjectError("Kaynak normal bir dosya olmalı.")
    before = path.stat()
    first, second = file_hash(path), file_hash(path)
    after = path.stat()
    if first != second or (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise ProjectError(
            "Kaynak okuma sırasında değişti. Yazmayı durdurup tekrar seçin."
        )
    return first


def filesystem(path):
    """Longest matching mount, including sandbox bind mounts. Unknown is not supported."""
    resolved = str(Path(path).resolve())
    matches = []
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        left, right = line.split(" - ", 1)
        mount = left.split()[4].replace("\\040", " ")
        if resolved == mount or resolved.startswith(mount.rstrip("/") + "/"):
            matches.append((len(mount), right.split()[0]))
    return max(matches, default=(0, "unknown"))[1]


def require_local(path):
    fs = filesystem(path)
    if fs not in {"ext4", "btrfs", "tmpfs"}:
        raise ProjectError(
            f"Bu dosya sisteminde yazma doğrulanmadı ({fs}). Yerel Btrfs/ext4 dizini seçin."
        )
    # tmpfs permits tests and temporary projects, with no power-loss durability claim.
    return fs


def validate_destination(root):
    root = Path(root)
    if root.is_symlink() or root.exists():
        raise ProjectError(
            "Hedef zaten var. Yeni bir proje dizini seçin; mevcut hedef ezilmedi."
        )
    if not root.parent.exists():
        raise ProjectError(
            "Projenin üst klasörü mevcut değil. Klasör seç düğmesiyle var olan bir konum seçin ve sonuna yeni proje klasörünün adını ekleyin."
        )
    if not root.parent.is_dir():
        raise ProjectError(
            "Projenin üst yolu bir dosya. Klasör seç düğmesiyle bir dizin seçin."
        )
    require_local(root.parent)


class CheckedWriter:
    def __init__(self, stream, checkpoint):
        self.stream, self.checkpoint = stream, checkpoint

    def write(self, raw):
        size = self.stream.write(raw)
        self.checkpoint("parquet_chunk_written")
        return size

    def flush(self):
        self.stream.flush()

    def seek(self, *args):
        return self.stream.seek(*args)

    def tell(self):
        return self.stream.tell()


def publish_directory(parent, temporary, destination):
    """Linux renameat2 NOREPLACE: an intervening target is never overwritten."""
    fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        rename = libc.renameat2
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        if rename(fd, os.fsencode(temporary), fd, os.fsencode(destination), 1) != 0:
            error = ctypes.get_errno()
            if error in {errno.EEXIST, errno.ENOTEMPTY}:
                raise ProjectError(
                    "Farklı kaydet hedefi bu sırada oluşturulmuş; mevcut hedef korunuyor."
                )
            raise OSError(error, "Directory publication failed")
        os.fsync(fd)
    finally:
        os.close(fd)


class ProjectStore:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        self.base = Path(f"/proc/self/fd/{self.root_fd}")
        self.identity = (self.root.stat().st_dev, self.root.stat().st_ino)
        self.directory_fds = {}
        self.lock_fd = None
        self.read_only = True
        self.stale_lock = False
        self.notice = ""
        self.commit_id = None
        self.manifest = None
        self.state = None
        self.pending = {}
        self.closed = False

    def path(self, uri):
        # Pin internal parents via O_NOFOLLOW openat. A replaced/symlinked directory
        # cannot redirect SQLite, artifacts or ACTIVE to an external destination.
        parts = Path(uri).parts
        if (
            not parts
            or Path(uri).is_absolute()
            or "\\" in uri
            or any(p in {"..", "."} for p in parts)
        ):
            raise ProjectError("Proje yolu geçersiz.")
        parent_fd = self.root_fd
        key_parts = []
        for part in parts[:-1]:
            key_parts.append(part)
            key = "/".join(key_parts)
            try:
                stat = os.stat(part, dir_fd=parent_fd, follow_symlinks=False)
                if key in self.directory_fds:
                    fd = self.directory_fds[key]
                    held = os.fstat(fd)
                    if (stat.st_dev, stat.st_ino) != (held.st_dev, held.st_ino):
                        raise ProjectError(
                            "Proje alt dizini değişti; işlem durduruldu."
                        )
                else:
                    fd = os.open(
                        part,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=parent_fd,
                    )
                    self.directory_fds[key] = fd
                parent_fd = fd
            except OSError as error:
                raise ProjectError(
                    "Proje alt dizini eksik veya sembolik bağlantı; işlem durduruldu."
                ) from error
        result = Path(f"/proc/self/fd/{parent_fd}") / parts[-1]
        if result.is_symlink():
            raise ProjectError("Proje içindeki sembolik bağlantılar desteklenmiyor.")
        return result

    def _guard(self):
        if self.closed or self.lock_fd is None or self.read_only:
            raise ProjectError(
                "Proje salt okunur; kayıt için ayrı bir yerel kopya oluşturun."
            )
        stat = self.root.stat()
        if (stat.st_dev, stat.st_ino) != self.identity:
            raise ProjectError("Proje dizini değişti; yazma durduruldu.")
        lock_stat = self.path(".writer.lock").stat()
        held_stat = os.fstat(self.lock_fd)
        if (lock_stat.st_dev, lock_stat.st_ino) != (held_stat.st_dev, held_stat.st_ino):
            raise ProjectError("Proje kilit dosyası değişti; yazma durduruldu.")

    def _acquire(self, recover_lock=False):
        require_local(self.root)
        fd = os.open(
            self.path(".writer.lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            self.notice = "Başka bir uygulama bu projeyi yazıyor. Salt okunur açıldı."
            return
        marker = os.read(fd, 4096)
        self.stale_lock = bool(marker)
        if marker and not recover_lock:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            self.notice = "Önceki yazıcı temiz kapanmamış. Salt okunur açıldı; kilidi kontrollü kurtarabilirsiniz."
            return
        self.lock_fd = fd
        self.read_only = False
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(
            fd,
            encode(
                {
                    "pid": os.getpid(),
                    "boot_id": Path("/proc/sys/kernel/random/boot_id")
                    .read_text()
                    .strip(),
                }
            ),
        )
        os.fsync(fd)
        sync_dir(self.base)
        if marker:
            self.notice = (
                "Eski kilit kernel kilidi edinilerek kurtarıldı. Önceki kayıt korundu."
            )

    @contextmanager
    def _db(self, write=False):
        path = self.path("metadata.sqlite")
        if path.exists() and (
            not path.is_file() or path.stat().st_size > 256 * 1024**2
        ):
            raise ProjectError("SQLite metadata boyutu sınır dışında (256 MiB).")
        for suffix in ("-journal", "-wal", "-shm"):
            self.path("metadata.sqlite" + suffix)
        if write:
            self._guard()
            db = sqlite3.connect(path, timeout=1)
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
        else:
            db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_MANIFEST)
        db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 16384)
        deadline = time.monotonic() + 5
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
        db.execute("PRAGMA trusted_schema=OFF")
        try:
            with db:
                yield db
        finally:
            db.close()

    @classmethod
    def create(cls, root, name="Adsız proje"):
        root = Path(root)
        validate_destination(root)
        root.mkdir(mode=0o700)
        sync_dir(root.parent)
        store = cls(root)
        try:
            store._acquire()
            for directory in (
                "staging",
                "commits",
                "snapshots",
                "sources",
                "quarantine",
            ):
                store.path(directory).mkdir(mode=0o700)
            with store._db(True) as db:
                db.execute(
                    "CREATE TABLE commits (commit_id TEXT PRIMARY KEY, manifest_hash TEXT NOT NULL, payload BLOB NOT NULL)"
                )
            store.state = new_state(name)
            store.save()
            return store
        except BaseException:
            store.close()
            raise

    @classmethod
    def open(cls, root, *, writable=True, recover_lock=False):
        store = cls(root)
        try:
            # Reject future/malformed manifests before touching a lock or SQLite.
            preview = decode(store._read("ACTIVE", 4096))
            if not isinstance(preview, dict) or set(preview) != {
                "commit_id",
                "manifest_sha256",
                "format_version",
            }:
                raise ProjectError(
                    "Aktif kayıt işaretçisi geçersiz; proje değiştirilmedi."
                )
            identifier(preview["commit_id"])
            if type(preview["format_version"]) is not int or preview[
                "format_version"
            ] not in (0, 1, 2, 3, SCHEMA_VERSION):
                raise ProjectError(
                    "Bilinmeyen gelecek proje şema sürümü; proje değiştirilmedi."
                )
            validate_manifest(
                decode(store._read(f"commits/{preview['commit_id']}/manifest.json"))
            )
            if writable:
                try:
                    store._acquire(recover_lock)
                except ProjectError as error:
                    store.notice = str(error) + " Salt okunur açıldı."
            if not store.read_only:
                # Writable connection rolls back a hot SQLite journal before reading ACTIVE.
                with store._db(True) as db:
                    db.execute("SELECT 1 FROM commits LIMIT 1").fetchall()
            store._load("ACTIVE")
            if store.manifest["format_version"] in (1, 2, 3):
                store.notice += f" Şema {store.manifest['format_version']} açıldı; sonraki açık kayıt şema {SCHEMA_VERSION} olarak yayımlanır, eski commit korunur."
            if store.manifest["format_version"] == 0:
                store.read_only = True
                store.notice = "Eski şema 0 salt okunur açıldı. Farklı kaydet ile yeni kopyaya geçin."
            if not store.read_only:
                store.quarantine_staging()
            return store
        except (OSError, sqlite3.Error, ProjectError) as error:
            store.close()
            if isinstance(error, ProjectError):
                raise
            raise ProjectError(
                "Proje açılamadı. İzinleri ve kayıt bütünlüğünü kontrol edin. Yarım SQLite işlemi için Önceki kilidi kurtararak aç seçeneğini kullanın; mevcut dosyalar korundu."
            ) from error

    def _read(self, uri, limit=MAX_MANIFEST):
        path = self.path(uri)
        if not path.is_file() or path.stat().st_size > limit:
            raise ProjectError("Proje dosyası eksik veya boyutu sınır dışında.")
        with open(path, "rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ProjectError("Proje dosyası boyutu sınır dışında.")
        return raw

    def _load(self, pointer):
        p = decode(self._read(pointer, 4096))
        if not isinstance(p, dict) or set(p) != {
            "commit_id",
            "manifest_sha256",
            "format_version",
        }:
            raise ProjectError(
                "Aktif kayıt işaretçisi bozuk. Sağlam kayıt seçilmeden proje değiştirilmeyecek."
            )
        identifier(p["commit_id"])
        if type(p["format_version"]) is not int or p["format_version"] not in (
            0,
            1,
            2,
            3,
            SCHEMA_VERSION,
        ):
            raise ProjectError(
                "Bilinmeyen gelecek proje şema sürümü; proje değiştirilmedi."
            )
        raw = self._read(f"commits/{p['commit_id']}/manifest.json")
        if digest(raw) != p["manifest_sha256"]:
            raise ProjectError("Manifest bütünlüğü bozuk; proje değiştirilmedi.")
        manifest = decode(raw)
        state = validate_manifest(manifest)
        if (
            manifest["commit_id"] != p["commit_id"]
            or manifest["format_version"] != p["format_version"]
        ):
            raise ProjectError("Manifest ve aktif kayıt uyuşmuyor.")
        with self._db() as db:
            record = db.execute(
                "SELECT manifest_hash, payload FROM commits WHERE commit_id=?",
                (p["commit_id"],),
            ).fetchone()
        if record != (digest(raw), raw):
            raise ProjectError("SQLite ve manifest kaydı uyuşmuyor.")
        for uri, info in manifest["artifacts"].items():
            path = self.path(uri)
            if (
                not path.is_file()
                or path.stat().st_size != info["size"]
                or file_hash(path)["sha256"] != info["sha256"]
            ):
                raise ProjectError(
                    "Bağlı veri kopyası eksik veya değişmiş; proje değiştirilmedi."
                )
        for uri, info in manifest["artifacts"].items():
            if info["kind"] == "parquet":
                import polars as pl

                path = self.path(uri)
                try:
                    schema = {
                        k: str(v) for k, v in pl.read_parquet_schema(path).items()
                    }
                    rows = pl.scan_parquet(path).select(pl.len()).collect().item()
                except pl.exceptions.PolarsError as error:
                    raise ProjectError("Parquet metadata okunamadı.") from error
                if schema != info["schema"] or rows != info["rows"]:
                    raise ProjectError(
                        "Parquet şema/satır bilgisi manifest ile uyuşmuyor."
                    )
        self.manifest, self.state, self.commit_id = (
            manifest,
            copy.deepcopy(state),
            manifest["commit_id"],
        )

    def quarantine_staging(self):
        self._guard()
        for path in self.path("staging").iterdir():
            if path.is_symlink():
                continue
            destination = self.path("quarantine") / uid()
            os.rename(path, destination)
        sync_dir(self.path("staging"))
        sync_dir(self.path("quarantine"))
        # No committed or orphan artifact deletion; history and recovery remain intact.

    def stage_source(self, source, portable=False, *, checkpoint=lambda point: None):
        self._guard()
        source = Path(source).resolve(strict=True)
        if source.is_relative_to(self.root):
            raise ProjectError(
                "Proje içindeki dosya harici kaynak olarak kullanılamaz."
            )
        fp = source_fingerprint(source)
        ref = dict(
            id="source:" + uid(), path=str(source), fingerprint=fp, copy_uri=None
        )
        if portable:
            tx = self.path("staging") / uid()
            tx.mkdir(mode=0o700)
            dest = tx / "source.bin"
            if shutil.disk_usage(self.base).free < fp["size"] + max(
                64 * 1024**2, fp["size"] // 10
            ):
                raise ProjectError("Kaynak kopyası için yeterli disk alanı yok.")
            with open(source, "rb") as original, open(dest, "xb") as output:
                while chunk := original.read(1024 * 1024):
                    output.write(chunk)
                    checkpoint("source_chunk_written")
            if file_hash(dest) != fp or source_fingerprint(source) != fp:
                raise ProjectError("Kaynak kopyalama sırasında değişti. Tekrar seçin.")
            uri = f"sources/{uid()}.bin"
            self.pending[uri] = (
                dest,
                dict(**fp, kind="source", rows=None, schema=None),
            )
            ref["copy_uri"] = uri
        self.state["sources"].append(ref)
        return ref

    def stage_parquet(self, frame, *, checkpoint=lambda point: None):
        self._guard()
        import polars as pl

        tx = self.path("staging") / uid()
        tx.mkdir(mode=0o700)
        path = tx / "snapshot.parquet"
        estimate = frame.estimated_size() * 2 + MAX_MANIFEST
        if shutil.disk_usage(self.base).free < estimate + max(
            64 * 1024**2, estimate // 10
        ):
            raise ProjectError("Parquet snapshot için yeterli disk alanı yok.")
        with open(path, "xb") as output:
            frame.write_parquet(CheckedWriter(output, checkpoint))
        loaded = pl.read_parquet(path)
        if not loaded.equals(frame):
            raise ProjectError("Parquet yazım doğrulaması başarısız.")
        uri = f"snapshots/{uid()}.parquet"
        info = dict(
            **file_hash(path),
            kind="parquet",
            rows=frame.height,
            schema={k: str(v) for k, v in frame.schema.items()},
        )
        self.pending[uri] = (path, info)
        return uri

    def publish_import(self, result, *, portable=False, checkpoint=lambda point: None):
        """Publish only a completed immutable import; retain prior state on failure."""
        self._guard()
        import polars as pl

        previous, pending = copy.deepcopy(self.state), dict(self.pending)
        source = result["capture"]
        if Path(source["original"]).is_relative_to(self.root):
            raise ProjectError("Proje dosyası kaynak olarak kullanılamaz.")

        def adopt(path, kind, expected=None):
            checkpoint("import_copy_begin")
            path = Path(path)
            size = path.stat().st_size
            if (
                size > MAX_ARTIFACT
                or shutil.disk_usage(self.base).free < size * 2 + 64 * 1024**2
            ):
                raise ProjectError(
                    "İçe aktarma artifact boyutu veya boş disk alanı yetersiz."
                )
            tx = self.path("staging") / uid()
            tx.mkdir(mode=0o700)
            dest = tx / "import.bin"
            with open(path, "rb") as stream, open(dest, "xb") as out:
                while block := stream.read(1024 * 1024):
                    out.write(block)
                    checkpoint("import_copy_chunk")
            fp = file_hash(dest)
            if expected is not None and fp != expected:
                raise ProjectError(
                    "İçe aktarma kopyası değişmiş; dataset yayımlanmadı."
                )
            rows, schema = None, None
            if kind == "parquet":
                schema = {k: str(v) for k, v in pl.read_parquet_schema(dest).items()}
                rows = (
                    pl.scan_parquet(dest)
                    .select(pl.len())
                    .collect(engine="streaming")
                    .item()
                )
            uri = (
                ("snapshots/" if kind == "parquet" else "sources/")
                + uid()
                + (".parquet" if kind == "parquet" else ".bin")
            )
            self.pending[uri] = (dest, dict(**fp, kind=kind, rows=rows, schema=schema))
            return uri, rows

        try:
            snapshot_uri, count = adopt(
                result["path"], "parquet", result["artifact_fingerprint"]
            )
            if count != result["accepted"]:
                raise ProjectError("Dataset kayıt sayısı doğrulanamadı.")
            quarantine_uri = None
            if result["quarantine"]:
                quarantine_uri, count = adopt(
                    result["quarantine"], "parquet", result["quarantine_fingerprint"]
                )
                if count != result["bad_count"]:
                    raise ProjectError("Karantina kayıt sayısı doğrulanamadı.")
            copy_uri = (
                adopt(source["path"], "source", source["fingerprint"])[0]
                if portable
                else None
            )
            ref = dict(
                id="source:" + uid(),
                path=source["original"],
                fingerprint=source["fingerprint"],
                copy_uri=copy_uri,
            )
            schema = result["schema"]
            metadata = dict(
                columns=[
                    dict(id="col:" + uid(), name=n, original_name=o, type=t)
                    for n, o, t in zip(
                        schema["names"],
                        schema["original_headers"],
                        schema["types"],
                        strict=True,
                    )
                ],
                row_count=result["accepted"],
                bad_count=result["bad_count"],
                source_snapshot_id=result["source_snapshot_id"],
                captured_at=source["captured_at"],
                settings=result["settings"],
            )
            dataset = dict(
                dataset_id="dataset:" + uid(),
                version_id="dv:" + uid(),
                source_id=ref["id"],
                snapshot_uri=snapshot_uri,
                quarantine_uri=quarantine_uri,
                import_metadata=metadata,
            )
            self.state["sources"].append(ref)
            self.state["datasets"].append(dataset)
            self.state["import_settings"][dataset["dataset_id"]] = result["settings"]
            provenance = Provenance(
                provenance_id="prov:" + uid(),
                dataset_versions=(dataset["version_id"],),
                config_revision=result.get("config_revision", 0),
                capability_id="import."
                + result.get(
                    "adapter_id",
                    "tsv" if source["original"].lower().endswith(".tsv") else "csv",
                ),
                parameters_hash=digest(encode(result["settings"])),
                environment=(
                    ("python", platform.python_version()),
                    ("polars", pl.__version__),
                ),
                created_at=datetime.now(UTC).isoformat(),
                scope="full",
                seed=self.state["seed"],
                seed_reason="Kaynak snapshot tam okunur; örnekleme yok",
                source_snapshot_ids=(result["source_snapshot_id"],),
                row_lineage_ref=snapshot_uri,
                column_lineage_ref=dataset["dataset_id"],
                exclusions=(quarantine_uri,) if quarantine_uri else (),
                learning_content_version="5",
            )
            self.state["operations"].append(
                dict(
                    id="op:" + uid(),
                    dataset_version_ids=[dataset["version_id"]],
                    seed=self.state["seed"],
                    capability_id=provenance.capability_id,
                    settings=result["settings"],
                    source_fingerprint=source["fingerprint"],
                    source_snapshot_id=result["source_snapshot_id"],
                    scope="full",
                    backend=result.get("backend", "python-csv/polars"),
                    diagnostics=result.get("diagnostics", {}),
                    backend_version=pl.__version__,
                    provenance=decode(encode(asdict(provenance))),
                )
            )
            self.save(checkpoint=checkpoint)
            return dataset
        except BaseException:
            # ACTIVE may already have changed on a durability error: reconcile before
            # reporting failure; never overwrite the published commit with old state.
            pointer = decode(self._read("ACTIVE", 4096))
            if pointer["commit_id"] != self.commit_id:
                self._load("ACTIVE")
                self.pending.clear()
            else:
                self.state, self.pending = previous, pending
            raise

    def source_statuses(self):
        statuses = {}
        for source in self.state["sources"]:
            try:
                statuses[source["id"]] = (
                    "unchanged"
                    if source_fingerprint(source["path"]) == source["fingerprint"]
                    else "changed"
                )
            except FileNotFoundError:
                statuses[source["id"]] = "missing"
            except (OSError, ProjectError):
                statuses[source["id"]] = "unavailable"
        return statuses

    def relink(self, source_id, path):
        self._guard()
        fp = source_fingerprint(path)
        source = next((s for s in self.state["sources"] if s["id"] == source_id), None)
        if source is None or fp != source["fingerprint"]:
            raise ProjectError(
                "Seçilen dosya kayıtlı veri sürümüyle aynı değil. Eski sonuçlar korunur; yeni veri için ayrı içe aktarma gerekir."
            )
        source["path"] = str(Path(path).resolve(strict=True))

    def results_status(self):
        statuses = self.source_statuses()
        versions = {d["version_id"]: d for d in self.state["datasets"]}
        latest = {d["dataset_id"]: d["version_id"] for d in self.state["datasets"]}
        return [
            dict(
                result,
                current=all(
                    statuses[versions[v]["source_id"]] == "unchanged"
                    and latest[versions[v]["dataset_id"]] == v
                    for v in result["dataset_version_ids"]
                ),
            )
            for result in self.state["results"]
        ]

    def save(self, *, autosave=False, checkpoint=lambda point: None):
        self._guard()
        validate_state(self.state)
        pointer = "AUTOSAVE" if autosave else "ACTIVE"
        if (
            self.commit_id
            and decode(self._read("ACTIVE", 4096))["commit_id"] != self.commit_id
        ):
            raise ProjectError("Aktif proje sürümü değişmiş; kayıt durduruldu.")
        estimate = sum(info["size"] for _, info in self.pending.values()) + MAX_MANIFEST
        if shutil.disk_usage(self.base).free < estimate + max(
            64 * 1024**2, estimate // 10
        ):
            raise ProjectError("Kayıt için yeterli geçici disk alanı yok.")
        commit = uid()
        tx = self.path("staging") / uid()
        tx.mkdir(mode=0o700)
        artifacts = copy.deepcopy(self.manifest["artifacts"] if self.manifest else {})
        for uri, (path, info) in self.pending.items():
            relative(uri)
            checkpoint("artifact_written")
            if file_hash(path) != {k: info[k] for k in ("sha256", "size")}:
                raise ProjectError("Geçici artifact değişmiş.")
            with open(path, "rb") as stream:
                os.fsync(stream.fileno())
            checkpoint("artifact_fsynced")
            final = self.path(uri)
            # A retry after a failed promotion must verify, never overwrite.
            if final.exists():
                if file_hash(final) != {k: info[k] for k in ("sha256", "size")}:
                    raise ProjectError("Artifact hedef çakışması.")
            else:
                os.link(path, final, follow_symlinks=False)
            checkpoint("artifact_promoted")
            sync_dir(final.parent)
            checkpoint("artifact_directory_synced")
            artifacts[uri] = info
        migration = copy.deepcopy(self.manifest["migration"] if self.manifest else [])
        if self.manifest and self.manifest["format_version"] < SCHEMA_VERSION:
            migration.append(
                dict(
                    from_version=self.manifest["format_version"],
                    to_version=SCHEMA_VERSION,
                    original_commit=self.commit_id,
                )
            )
        manifest = dict(
            format_version=SCHEMA_VERSION,
            project_id=self.manifest["project_id"] if self.manifest else uid(),
            commit_id=commit,
            parent_commit=self.commit_id,
            state=copy.deepcopy(self.state),
            artifacts=artifacts,
            created_at=datetime.now(UTC).isoformat(),
            environment={"application": "0.1.0", "python": platform.python_version()},
            migration=migration,
        )
        validate_manifest(manifest)
        raw = encode(manifest)
        if len(raw) > MAX_MANIFEST:
            raise ProjectError("Manifest boyutu sınır dışında.")
        with self._db(True) as db:
            db.execute("INSERT INTO commits VALUES (?,?,?)", (commit, digest(raw), raw))
            checkpoint("metadata_inserted")
        checkpoint("metadata_committed")
        path = tx / "manifest.json"
        with open(path, "xb") as stream:
            stream.write(raw)
            stream.flush()
            checkpoint("manifest_written")
            os.fsync(stream.fileno())
        checkpoint("manifest_fsynced")
        sync_dir(tx)
        dest = self.path(f"commits/{commit}")
        os.rename(tx, dest)
        checkpoint("manifest_promoted")
        sync_dir(self.path("commits"))
        checkpoint("commit_directory_synced")
        temporary = self.path("staging") / (uid() + ".pointer")
        with open(temporary, "xb") as stream:
            stream.write(
                encode(
                    dict(
                        commit_id=commit,
                        manifest_sha256=digest(raw),
                        format_version=SCHEMA_VERSION,
                    )
                )
            )
            stream.flush()
            checkpoint("pointer_written")
            os.fsync(stream.fileno())
        checkpoint("pointer_fsynced")
        self._guard()
        os.replace(temporary, self.path(pointer))
        checkpoint("pointer_replaced")
        try:
            sync_dir(self.base)
        except OSError as error:
            raise ProjectError(
                "Kayıt işaretçisi değişti, dayanıklılık doğrulanamadı. Yeniden açıp kaydı kontrol edin; iki kayıt da korundu."
            ) from error
        checkpoint("root_synced")
        if not autosave:
            self.manifest, self.commit_id = manifest, commit
            self.pending.clear()
        # Autosave keeps pending refs for later manual save. It cannot change ACTIVE.
        return commit

    def restore_autosave(self):
        self._guard()
        active, original, original_state = self.commit_id, self.manifest, self.state
        try:
            self._load("AUTOSAVE")
            recovered, recovered_manifest = self.state, self.manifest
            if recovered_manifest["parent_commit"] != active:
                raise ProjectError(
                    "Otomatik kayıt başka bir temel sürüme ait; otomatik uygulanmadı."
                )
        except BaseException:
            self.state, self.manifest, self.commit_id = original_state, original, active
            raise
        self.state, self.manifest, self.commit_id = (
            recovered,
            dict(original, artifacts=recovered_manifest["artifacts"]),
            active,
        )

    def save_as(self, target):
        target = Path(target)
        resolved = target.resolve()
        if (
            resolved == self.root
            or resolved.is_relative_to(self.root)
            or self.root.is_relative_to(resolved)
            or target.is_symlink()
            or target.exists()
        ):
            raise ProjectError(
                "Farklı kaydet hedefi aynı proje, sembolik bağlantı veya mevcut hedef olamaz. Yeni bir dizin seçin."
            )
        for source in self.state["sources"]:
            if resolved == Path(source["path"]).resolve():
                raise ProjectError("Hedef kaynak dosyayla aynı; kaynak korundu.")
        validate_destination(target)
        parent = target.parent.resolve(strict=True)
        temporary_name = ".veri-ufku-saveas-" + uid()
        temporary_root = parent / temporary_name
        candidate = ProjectStore.create(temporary_root, self.state["name"])
        try:
            candidate.state = copy.deepcopy(self.state)
            candidate.manifest["project_id"] = self.manifest["project_id"]
            candidate.manifest["migration"] = copy.deepcopy(self.manifest["migration"])
            if self.manifest["format_version"] < SCHEMA_VERSION:
                candidate.manifest["migration"].append(
                    {
                        "from_version": self.manifest["format_version"],
                        "to_version": SCHEMA_VERSION,
                        "original_commit": self.commit_id,
                    }
                )
            artifacts = dict(self.manifest["artifacts"])
            artifacts.update({uri: info for uri, (_, info) in self.pending.items()})
            for uri, info in artifacts.items():
                path = self.pending[uri][0] if uri in self.pending else self.path(uri)
                tx = candidate.path("staging") / uid()
                tx.mkdir()
                dest = tx / "artifact"
                shutil.copyfile(path, dest)
                candidate.pending[uri] = (dest, info)
            candidate.save()
            # Verify the completed copy before making its directory visible.
            candidate._load("ACTIVE")
            publish_directory(parent, temporary_name, target.name)
            candidate.root = parent / target.name
            return candidate
        except BaseException:
            candidate.close()
            raise

    def close(self):
        if self.closed:
            return
        if self.lock_fd is not None:
            os.ftruncate(self.lock_fd, 0)
            os.fsync(self.lock_fd)
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            os.close(self.lock_fd)
        for fd in self.directory_fds.values():
            os.close(fd)
        os.close(self.root_fd)
        self.closed = True
