"""Verify bundled development wheel content and lock entry, without importing it."""

import base64
import csv
import hashlib
import io
import json
import tomllib
import zipfile
from pathlib import Path


def verify(root):
    directory = root / "tools/wheels"
    manifest = json.loads((directory / "manifest.json").read_text())
    wheel = directory / manifest["artifact"]
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    if digest != manifest["sha256"]:
        raise ValueError("Development artifact integrity mismatch")
    lock = tomllib.loads((root / "uv.lock").read_text())
    package = next(p for p in lock["package"] if p["name"] == "ruff")
    if package["wheels"][0]["hash"] != "sha256:" + digest:
        raise ValueError("Development artifact differs from lock")
    with zipfile.ZipFile(wheel) as archive:
        rows = csv.reader(
            io.StringIO(archive.read("ruff-0.16.10.dist-info/RECORD").decode())
        )
        for name, checksum, _ in rows:
            if checksum:
                expected = "sha256=" + base64.urlsafe_b64encode(
                    hashlib.sha256(archive.read(name)).digest()
                ).decode().rstrip("=")
                if checksum != expected:
                    raise ValueError("Wheel RECORD mismatch")
    return digest


if __name__ == "__main__":
    print(
        "PASS: development wheel and lock integrity",
        verify(Path(__file__).resolve().parents[1]),
    )
