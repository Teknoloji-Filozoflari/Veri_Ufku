"""Exclusive atomic export: an existing file, source or project artifact is never replaced."""

import os
from pathlib import Path

from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.storage.project_model import ProjectError, uid


def export(result, destination, fmt, project_root, control=None):
    control = control or Control()
    path = Path(destination).absolute()
    if fmt not in ("png", "svg", "pdf") or path.suffix.lower() != "." + fmt:
        raise ProjectError("PNG/SVG/PDF için aynı uzantılı yeni hedef seçin.")
    if (
        path.parent.resolve() != path.parent
        or path.is_symlink()
        or path.exists()
        or path.is_relative_to(Path(project_root).resolve())
    ):
        raise ProjectError(
            "Yeni ve proje dışındaki bir çıktı seçin; mevcut dosya/kaynak/symlink korunur."
        )
    source = Path(result["paths"][fmt])
    if hash_artifact(source, control) != result["fingerprints"][fmt]:
        raise ProjectError("Çizim artifact değişmiş; yeniden oluşturun.")
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temp = "." + uid() + ".export"
    try:
        fd = os.open(
            temp,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        with os.fdopen(fd, "wb") as out, source.open("rb") as inp:
            while chunk := inp.read(1024**2):
                control.check()
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        control.check()
        os.link(
            temp,
            path.name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
            follow_symlinks=False,
        )
        os.fsync(directory)
        return dict(
            exported=str(path), format=fmt, dataset_version=result["dataset_version"]
        )
    finally:
        try:
            os.unlink(temp, dir_fd=directory)
        except FileNotFoundError:
            pass
        os.close(directory)
