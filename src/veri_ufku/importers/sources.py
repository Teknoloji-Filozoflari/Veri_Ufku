"""Bounded immutable directory/archive inputs; never extract archive paths."""

import gzip
import hashlib
import os
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from veri_ufku.importers.delimited import Control, capture, hash_artifact
from veri_ufku.storage.project_model import ProjectError, uid

MAX_FILES = 1024
MAX_EXPANDED = 512 * 1024**2
DATA_SUFFIXES = {
    ".parquet",
    ".arrow",
    ".ipc",
    ".feather",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".wav",
    ".flac",
    ".json",
}


def safe_member(name):
    if (
        not name
        or len(name) > 4096
        or "\\" in name
        or "\x00" in name
        or ":" in name
        or name.startswith("/")
        or any(p in ("", ".", "..") for p in name.rstrip("/").split("/"))
    ):
        raise ProjectError("Arşiv üye yolu güvenli değil; mutlak/üst yol reddedildi.")
    return PurePosixPath(name)


def directory_members(source):
    source = Path(source)
    entries = []
    zarr = (source / ".zgroup").is_file() or (source / "zarr.json").is_file()
    for parent, directories, files in os.walk(source, followlinks=False):
        for name in directories + files:
            path = Path(parent) / name
            if path.is_symlink():
                raise ProjectError("Dataset klasöründe symlink desteklenmez.")
        for name in files:
            path = Path(parent) / name
            if not path.is_file() or (
                not zarr and path.suffix.lower() not in DATA_SUFFIXES
            ):
                raise ProjectError(
                    "Dataset klasörü yalnız Parquet veya Arrow IPC parçaları içermeli."
                )
            member = path.relative_to(source).as_posix()
            safe_member(member)
            entries.append((member, path))
            if len(entries) > MAX_FILES:
                raise ProjectError("Dataset/arşiv parça sayısı1024 sınırını aştı.")
    if not entries:
        raise ProjectError("Dataset klasöründe veri parçası yok.")
    return sorted(entries)


def zarr_root(snapshot):
    """Reconstruct only validated captured members, never open the live source."""
    members = snapshot.get("members", [])
    if not members or not any(m["name"] in (".zgroup", "zarr.json") for m in members):
        raise ProjectError("Zarr kök metadata bulunamadı.")
    root = Path(snapshot["path"]).with_suffix(".zarr-capture")
    root.mkdir(exist_ok=True, mode=0o700)
    for member in members:
        target = root / str(safe_member(member["name"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            os.link(member["path"], target)
        elif target.is_symlink() or not os.path.samefile(member["path"], target):
            raise ProjectError("Zarr kopya bağı değişti.")
    return root


class DigestWriter:
    """Non-seekable ZIP gives identical bytes for capture and source hashing."""

    def __init__(self, output=None):
        self.output, self.digest, self.size = output, hashlib.sha256(), 0

    def write(self, raw):
        if self.output:
            self.output.write(raw)
        self.digest.update(raw)
        self.size += len(raw)
        return len(raw)

    def tell(self):
        return self.size

    def flush(self):
        if self.output:
            self.output.flush()


def bundle_directory(source, control, output=None):
    entries = directory_members(source)
    maximum = min(MAX_EXPANDED, control.budget.temp_disk_bytes // 4)
    if sum(p.stat().st_size for _, p in entries) > maximum:
        raise ProjectError("Çok parçalı kaynak toplam boyut bütçesini aştı.")
    sink = DigestWriter(output)
    with zipfile.ZipFile(sink, "w", compression=zipfile.ZIP_STORED) as archive:
        for member, path in entries:
            control.check()
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            with path.open("rb") as source_stream, archive.open(info, "w") as target:
                while raw := source_stream.read(65536):
                    control.check()
                    target.write(raw)
                    if sink.size > maximum + 1024**2:
                        raise ProjectError(
                            "Dataset kopyası büyüdü; kaynak değişmiş olabilir."
                        )
            control.progress("Dataset parçası kopyası", sink.size, None)
    if directory_members(source) != entries:
        raise ProjectError("Dataset parçaları okuma sırasında değişti.")
    return dict(sha256=sink.digest.hexdigest(), size=sink.size)


def directory_fingerprint(source, control=None):
    control = control or Control()
    first = bundle_directory(source, control)
    if first != bundle_directory(source, control):
        raise ProjectError("Dataset klasörü okuma sırasında değişti.")
    return first


def capture_source(source, workspace, control):
    if Path(source).suffix.lower() == ".gpkg" and any(
        Path(str(source) + suffix).exists() for suffix in ("-wal", "-journal", "-shm")
    ):
        raise ProjectError(
            "GeoPackage active WAL/journal; checkpoint edilmiş dosya seçin."
        )
    if Path(source).suffix.lower() == ".shp":
        return capture_shape(source, workspace, control)
    if Path(source).suffix.lower() in (".tif", ".tiff") and any(
        Path(str(source) + s).exists() for s in (".msk", ".aux.xml", ".ovr")
    ):
        raise ProjectError(
            "GeoTIFF dış sidecar içeriyor; self-contained export kullanın."
        )
    path = Path(source)
    if path.name in ("images.json", "audio.json") and path.is_file():
        path = path.parent
    if not path.is_dir():
        return capture(path, workspace, control, any_format=True)
    if path.is_symlink():
        raise ProjectError("Dataset kökü symlink olamaz.")
    path = path.resolve(strict=True)
    target = Path(workspace) / (uid() + ".source")
    with target.open("xb") as stream:
        fingerprint = bundle_directory(path, control, stream)
    if fingerprint != directory_fingerprint(path, control):
        raise ProjectError("Dataset kopyalama sırasında değişti; yeniden seçin.")
    return dict(
        path=str(target),
        original=str(path),
        fingerprint=fingerprint,
        captured_at=datetime.now(UTC).isoformat(),
        capture_id=uid(),
        directory=True,
        strict_source=True,
    )


def unpack(snapshot, workspace, control):
    """One gzip member or validated ZIP. XLSX/ODS retain their own adapter."""
    if snapshot.get("members"):
        return snapshot
    source = Path(snapshot["path"])
    with source.open("rb") as stream:
        magic = stream.read(4)
    members = []
    maximum = min(MAX_EXPANDED, control.budget.temp_disk_bytes // 4)
    total = 0

    def copy(stream, name):
        nonlocal total
        target = Path(workspace) / (uid() + ".input")
        digest, size = hashlib.sha256(), 0
        with target.open("xb") as output:
            while raw := stream.read(65536):
                control.check()
                size += len(raw)
                total += len(raw)
                if total > maximum:
                    raise ProjectError(
                        "Açılmış arşiv/gzip boyutu512MiB veya disk bütçesini aştı."
                    )
                output.write(raw)
                digest.update(raw)
                control.disk(workspace)
        members.append(
            dict(
                name=name,
                path=str(target),
                fingerprint=dict(sha256=digest.hexdigest(), size=size),
            )
        )

    if magic[:2] == b"\x1f\x8b":
        name = Path(snapshot["original"]).name.removesuffix(".gz")
        safe_member(name)
        with gzip.open(source, "rb") as stream:
            copy(stream, name)
    elif magic[:2] == b"PK":
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            if not snapshot.get("directory") and (
                "[Content_Types].xml" in names or "mimetype" in names
            ):
                return snapshot
            seen = set()
            infos = archive.infolist()
            if len(infos) > MAX_FILES:
                raise ProjectError("Arşiv1024 üye sınırını aştı.")
            for info in infos:
                safe_member(info.filename)
                kind = stat.S_IFMT(info.external_attr >> 16)
                if (
                    info.filename in seen
                    or kind not in (0, stat.S_IFREG, stat.S_IFDIR)
                    or info.flag_bits & 1
                ):
                    raise ProjectError(
                        "Arşiv yinelenen/encrypted/link/özel üye içeriyor."
                    )
                seen.add(info.filename)
                if (
                    info.file_size > maximum
                    or info.file_size > max(1, info.compress_size) * 1000
                ):
                    raise ProjectError("Arşiv açılma boyutu/oranı sınırı aşıldı.")
            if sum(i.file_size for i in infos) > maximum:
                raise ProjectError("Arşiv toplam açılma boyutu sınırı aşıldı.")
            for info in sorted(infos, key=lambda i: i.filename):
                if not info.is_dir():
                    with archive.open(info) as stream:
                        copy(stream, info.filename)
    else:
        return snapshot
    if not members:
        raise ProjectError("Arşivde veri dosyası yok.")
    return dict(snapshot, members=members, strict_source=True)


def input_snapshot(snapshot):
    members = snapshot.get("members", [])
    if len(members) == 1 and not snapshot.get("directory"):
        member = members[0]
        return dict(
            snapshot,
            path=member["path"],
            original=member["name"],
            fingerprint=member["fingerprint"],
        )
    return snapshot


def verify_sources(snapshot, control):
    for member in snapshot.get("shape_sources", []):
        if hash_artifact(member["original"], control) != member["fingerprint"]:
            raise ProjectError("Shapefile kaynak bileşeni değişti.")
    for member in snapshot.get("members", []):
        if hash_artifact(member["path"], control) != member["fingerprint"]:
            raise ProjectError("Açılmış kaynak parçası değişti; yeniden seçin.")
    if snapshot.get("strict_source"):
        path = Path(snapshot["original"])
        current = (
            directory_fingerprint(path, control)
            if snapshot.get("directory")
            else hash_artifact(path, control)
        )
        if current != snapshot["fingerprint"]:
            raise ProjectError("Kaynak dosya/parçaları değişti; yeniden önizleyin.")


def capture_shape(source, workspace, control):
    if Path(source).is_symlink():
        raise ProjectError("Shapefile symlink kaynak desteklenmez.")
    source = Path(source).resolve(strict=True)
    components = [
        source.with_suffix(s)
        for s in (".shp", ".shx", ".dbf", ".prj", ".cpg")
        if source.with_suffix(s).exists()
    ]
    if not {".shp", ".shx", ".dbf"} <= {p.suffix.lower() for p in components}:
        raise ProjectError("Shapefile .shp/.shx/.dbf bileşenleri eksik.")
    members = []
    originals = []
    for p in components:
        if p.is_symlink():
            raise ProjectError("Shapefile symlink bileşen desteklenmez.")
        snap = capture(p, workspace, control, any_format=True)
        members.append(
            dict(name=p.name, path=snap["path"], fingerprint=snap["fingerprint"])
        )
        originals.append(dict(original=str(p), fingerprint=snap["fingerprint"]))
    base = next(m for m in members if m["name"] == source.name)
    return dict(
        path=base["path"],
        original=str(source),
        fingerprint=base["fingerprint"],
        captured_at=datetime.now(UTC).isoformat(),
        capture_id=uid(),
        members=members,
        shape_sources=originals,
        strict_source=True,
    )
