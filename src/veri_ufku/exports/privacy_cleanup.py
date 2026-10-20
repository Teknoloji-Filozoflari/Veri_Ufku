"""Preview/revalidate only owned flat orphan scratch; never walk project artifacts."""

import os
import stat
from datetime import UTC, datetime
from pathlib import Path

from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, decode
from veri_ufku.storage.project_store import file_hash

FILES = {"marker.json", "payload.zip", "sealed.vupseal"}


def preview(cache, project_root, days=1, control=None):
    control = control or Control()
    if type(days) is not int or not 1 <= days <= 3650:
        raise ProjectError("Cleanup retention1..3650gün gerekli.")
    root = Path(cache)
    project = Path(project_root).resolve()
    if (
        root.is_symlink()
        or root.resolve().is_relative_to(project)
        or project.is_relative_to(root.resolve())
    ):
        raise ProjectError(
            "Privacy cache proje kökünden ayrı olmalı; symlink kabul edilmez."
        )
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    rs = root.stat()
    cutoff = datetime.now(UTC).timestamp() - days * 86400
    candidates = []
    protected = []
    children = list(root.iterdir())
    if len(children) > 128:
        raise ProjectError("Cleanup128scratch dizini sınırı.")
    total = 0
    for d in children:
        control.check()
        try:
            if d.is_symlink() or not d.is_dir():
                raise ValueError()
            ds = d.stat()
            entries = list(d.iterdir())
            if (
                not entries
                or len(entries) > 3
                or not {p.name for p in entries} <= FILES
            ):
                raise ValueError()
            for p in entries:
                st = p.lstat()
                if (
                    not stat.S_ISREG(st.st_mode)
                    or st.st_nlink != 1
                    or st.st_size > 48 * 1024**2
                    or st.st_mtime > cutoff
                ):
                    raise ValueError()
            total += sum(p.stat().st_size for p in entries)
            if total > 32 * 1024**2:
                raise ProjectError(
                    "Cleanup toplam32MiB sınırı; daha küçük cache için manuel yönetim gerekli."
                )
            marker = d / "marker.json"
            if marker.stat().st_size > 1024:
                raise ValueError()
            mark = decode(marker.read_bytes())
            if (
                not isinstance(mark, dict)
                or set(mark) != {"schema", "owner", "pid"}
                or mark["schema"] != "PrivacyScratch/v1"
                or mark["owner"] != "Veri_Ufku.privacy"
                or type(mark["pid"]) is not int
                or not 1 <= mark["pid"] <= 2147483647
            ):
                raise ValueError()
            try:
                os.kill(mark["pid"], 0)
            except ProcessLookupError:
                pass
            except PermissionError:
                raise ValueError() from None
            else:
                raise ValueError()  # Live or recycled PID: conservatively protect.
            candidates.append(
                dict(
                    directory=d.name,
                    device=ds.st_dev,
                    inode=ds.st_ino,
                    files=[
                        dict(
                            name=p.name,
                            device=p.stat().st_dev,
                            inode=p.stat().st_ino,
                            fingerprint=file_hash(p),
                        )
                        for p in sorted(entries)
                    ],
                )
            )
        except (OSError, ValueError, TypeError, KeyError):
            protected.append(d.name)
    plan = dict(
        schema="PrivacyCleanup/v1",
        root=str(root),
        device=rs.st_dev,
        inode=rs.st_ino,
        days=days,
        candidates=candidates,
        protected=sorted(protected),
        scope="only owned idle scratch; all project/history/source/model/report and external exports protected",
        bytes=sum(f["fingerprint"]["size"] for c in candidates for f in c["files"]),
    )
    plan["preview_hash"] = digest(plan)
    return plan


def apply(cache, project_root, plan, confirmed, control=None):
    control = control or Control()
    if confirmed is not True or plan.get("preview_hash") != digest(
        {k: v for k, v in plan.items() if k != "preview_hash"}
    ):
        raise ProjectError("Cleanup için aynı scope/hash açık onayı gerekli.")
    fresh = preview(cache, project_root, plan["days"], control)
    if fresh != plan:
        raise ProjectError("Cleanup cache değişmiş; yeni önizleme gerekli.")
    removed = []
    # All candidates validated before unlink. Same-user hostile races are outside this local cleanup contract.
    for item in plan["candidates"]:
        control.check()
        d = Path(cache) / item["directory"]
        fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            st = os.fstat(fd)
            if (st.st_dev, st.st_ino) != (item["device"], item["inode"]):
                raise ProjectError("Cleanup dizin kimliği değişmiş.")
            for f in item["files"]:
                st = os.stat(f["name"], dir_fd=fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(st.st_mode)
                    or st.st_nlink != 1
                    or (st.st_dev, st.st_ino) != (f["device"], f["inode"])
                ):
                    raise ProjectError("Cleanup dosya kimliği değişmiş.")
            for f in item["files"]:
                os.unlink(f["name"], dir_fd=fd)
        finally:
            os.close(fd)
        d.rmdir()
        removed.append(item["directory"])
    return dict(
        action="cleanup",
        status="completed",
        removed=removed,
        bytes=plan["bytes"],
        preview_hash=plan["preview_hash"],
        scope=plan["scope"],
    )
