"""Install the packaged launcher and icons for the current Linux user."""

import os
import shutil
import sys
from pathlib import Path

APP_ID = "org.veriufku.Veri_Ufku"
ASSETS = Path(__file__).parent / "assets/branding"


def install(data_home=None):
    target = Path(
        data_home or os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
    )
    if not target.is_absolute():
        raise ValueError("XDG_DATA_HOME must be an absolute path")
    executable = Path(sys.executable).parent / "veri-ufku"
    if not executable.is_file():
        raise FileNotFoundError("Install veri-ufku in this Python environment first")
    # Desktop entry string escaping follows Exec quoting, without invoking a shell.
    quoted = str(executable).replace("%", "%%")
    for character in ("\\", '"', "`", "$"):
        quoted = quoted.replace(character, "\\" + character)
    quoted = '"' + quoted.replace("\\", "\\\\") + '"'
    desktop = (ASSETS / f"{APP_ID}.desktop").read_text()
    desktop = desktop.replace("Exec=veri-ufku", f"Exec={quoted}")
    paths = []
    for size in (16, 24, 32, 48, 64, 128, 256, 512):
        path = target / f"icons/hicolor/{size}x{size}/apps/{APP_ID}.png"
        if path.is_symlink():
            raise ValueError("Refusing to overwrite a symbolic-link icon")
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ASSETS / f"icon-{size}.png", path)
        paths.append(path)
    launcher = target / f"applications/{APP_ID}.desktop"
    if launcher.is_symlink():
        raise ValueError("Refusing to overwrite a symbolic-link launcher")
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(desktop, encoding="utf-8")
    paths.append(launcher)
    return paths
