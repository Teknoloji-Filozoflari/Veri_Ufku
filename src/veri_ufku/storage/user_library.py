"""Local Verilerim index — not a second ProjectStore or provenance journal."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
INDEX_NAME = "library-index.json"


def _utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def library_root(data_home: Path) -> Path:
    return Path(data_home) / "library"


def index_path(data_home: Path) -> Path:
    return library_root(data_home) / INDEX_NAME


def empty_index():
    return {"schema_version": SCHEMA_VERSION, "entries": []}


def load_index(data_home: Path) -> dict:
    path = index_path(data_home)
    if not path.is_file():
        return empty_index()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Verilerim indeksi okunamadı veya sürüm uyumsuz.")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Verilerim indeksi bozuk.")
    return {"schema_version": SCHEMA_VERSION, "entries": list(entries)}


def save_index(data_home: Path, index: dict) -> None:
    root = library_root(data_home)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = index_path(data_home)
    tmp = path.with_suffix(".tmp")
    text = json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def fingerprint_file(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "size": size}


def add_file_entry(
    data_home: Path,
    source: Path,
    *,
    name: str,
    description: str = "",
    tags: list[str] | None = None,
    column_glossary: list[dict] | None = None,
) -> dict:
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError("Verilerim’e eklenecek dosya bulunamadı.")
    if source.stat().st_size > 512 * 1024 * 1024:
        raise ValueError("Verilerim kaydı 512 MiB üst sınırını aşıyor.")
    entry_id = "lib:" + uuid.uuid4().hex
    dest_dir = library_root(data_home) / entry_id.replace(":", "_")
    dest_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    dest = dest_dir / source.name
    shutil.copy2(source, dest)
    entry = {
        "id": entry_id,
        "name": (name or source.stem).strip()[:200],
        "description": (description or "").strip()[:2000],
        "tags": [str(tag).strip()[:64] for tag in (tags or []) if str(tag).strip()][
            :32
        ],
        "stored_path": str(dest),
        "original_name": source.name,
        "fingerprint": fingerprint_file(dest),
        "added_at": _utc_now(),
        "column_glossary": list(column_glossary or [])[:128],
        "pii_reminder": "Kişisel veya hassas veri içerebilir; paylaşmadan önce incele.",
    }
    index = load_index(data_home)
    index["entries"].append(entry)
    save_index(data_home, index)
    return entry


def remove_entry(data_home: Path, entry_id: str) -> bool:
    index = load_index(data_home)
    kept = []
    removed = None
    for entry in index["entries"]:
        if entry.get("id") == entry_id:
            removed = entry
        else:
            kept.append(entry)
    if removed is None:
        return False
    index["entries"] = kept
    save_index(data_home, index)
    stored = Path(removed.get("stored_path", ""))
    folder = stored.parent if stored.name else None
    if folder and folder.is_dir() and library_root(data_home) in folder.parents:
        shutil.rmtree(folder, ignore_errors=True)
    return True


def find_entry(data_home: Path, entry_id: str) -> dict | None:
    for entry in load_index(data_home)["entries"]:
        if entry.get("id") == entry_id:
            return entry
    return None


def disk_usage_bytes(data_home: Path) -> int:
    root = library_root(data_home)
    if not root.is_dir():
        return 0
    total = 0
    for path in root.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    return total
