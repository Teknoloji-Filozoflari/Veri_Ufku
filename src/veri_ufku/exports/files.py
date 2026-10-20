"""Exclusive artifact publication outside the project; never replace a source."""

import hashlib
import os
from pathlib import Path

from veri_ufku.importers.delimited import Control
from veri_ufku.storage.project_model import ProjectError, uid


def publish(source, destination, project_root, control=None):
    control = control or Control()
    path = Path(destination).absolute()
    if (
        path.parent.resolve() != path.parent
        or path.exists()
        or path.is_symlink()
        or path.is_relative_to(Path(project_root).resolve())
    ):
        raise ProjectError(
            "Yeni, proje dışında ve symlink olmayan bir çıktı dosyası seçin. Mevcut kaynak/dosya korunur."
        )
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = "." + uid() + ".export"
    try:
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        digest = hashlib.sha256()
        size = 0
        with os.fdopen(fd, "wb") as out, Path(source).open("rb") as inp:
            while chunk := inp.read(1024**2):
                control.check()
                out.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            out.flush()
            os.fsync(out.fileno())
        control.check()
        os.link(
            temporary,
            path.name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
            follow_symlinks=False,
        )
        os.fsync(directory)
        return dict(path=str(path), size=size, sha256=digest.hexdigest())
    finally:
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass
        os.close(directory)
