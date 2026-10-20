"""Explicit allocation/transfer admission. Never converts sparse implicitly."""

import math
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from veri_ufku.storage.project_model import ProjectError


def dense_bytes(shape, itemsize=8, copies=2):
    if any(type(n) is not int or n < 0 for n in shape) or itemsize < 1 or copies < 1:
        raise ValueError("Invalid allocation shape")
    return math.prod(shape) * itemsize * copies


def checked_dense(matrix, budget, *, explicit=False):
    if hasattr(matrix, "toarray"):
        if not explicit:
            raise ProjectError("Sparse → dense dönüşümü açık seçim gerektirir.")
        required = dense_bytes(matrix.shape, matrix.dtype.itemsize)
        import os

        from veri_ufku.jobs.resources import rss_bytes

        if required + rss_bytes(os.getpid()) > budget.ram_bytes:
            raise ProjectError(
                "Dense dönüşüm RAM bütçesini aşar; sparse yöntemi seçin."
            )
        return matrix.toarray()
    return matrix


def device_plan(budget, *, supports_gpu=False, transfer_bytes=0, available_bytes=0):
    if budget.device == "cpu":
        return dict(device="cpu", transfer_bytes=0, fallback=False)
    if not supports_gpu or available_bytes <= 0:
        raise ProjectError(
            "GPU yöntemi/device doğrulanmadı; otomatik CPU fallback yok."
        )
    if transfer_bytes < 0 or transfer_bytes > min(
        budget.transfer_bytes, budget.device_memory_bytes, available_bytes
    ):
        raise ProjectError("GPU transfer/VRAM bütçesi aşıldı.")
    return dict(device=budget.device, transfer_bytes=transfer_bytes, fallback=False)


@contextmanager
def spill_directory(parent, control):
    """Exclusive job-owned spill only; cleanup on success, failure and cancellation."""
    with TemporaryDirectory(prefix="spill-", dir=parent) as directory:
        path = Path(directory)
        control.disk(path, force=True)
        yield path
        control.disk(path, force=True)
