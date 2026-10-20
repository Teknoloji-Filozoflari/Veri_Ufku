"""Prepare desktop sizes from the user-selected logo without changing the source."""

import hashlib
import json
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "output/branding/v2/02-veri-baglari.png"
    target = ROOT / "src/veri_ufku/assets/branding"
    target.mkdir(parents=True, exist_ok=True)
    image = QImage(str(source))
    if image.isNull() or not image.hasAlphaChannel():
        raise ValueError("Selected logo must be a transparent PNG")
    shutil.copyfile(source, target / "logo.png")
    for size in (16, 24, 32, 48, 64, 128, 256, 512):
        scaled = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if not scaled.save(str(target / f"icon-{size}.png")):
            raise OSError("Could not save application icon")
    (target / "source.json").write_text(
        json.dumps(
            {
                "name": "Veri Bağları",
                "source": "output/branding/v2/02-veri-baglari.png",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "selected_by": "user",
                "date": "2026-10-08",
                "preparation": "Qt smooth scaling; original image preserved",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
