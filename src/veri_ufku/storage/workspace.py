"""Disposable per-job workspaces only. Project persistence belongs to Phase 04."""

import shutil
import tempfile
from pathlib import Path


def create_workspace(cache):
    jobs = Path(cache) / "jobs"
    jobs.mkdir(parents=True, exist_ok=True, mode=0o700)
    return Path(tempfile.mkdtemp(prefix="job-", dir=jobs))


def workspace_bytes(path):
    return sum(p.stat().st_size for p in path.glob("*") if p.is_file())


def remove_workspace(path):
    shutil.rmtree(path)
