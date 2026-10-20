"""Shared Linux process admission for import and dataset jobs."""

import os
import resource

THREAD_VARIABLES = (
    "POLARS_MAX_THREADS",
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def configure_threads(count):
    """Set BEFORE native libraries are imported; inherited by spawned workers."""
    for name in THREAD_VARIABLES:
        os.environ[name] = str(count)


def resource_error_text(error, fallback):
    import errno
    import sqlite3

    sqlite_code = getattr(error, "sqlite_errorcode", 0)

    if (
        sqlite_code == sqlite3.SQLITE_NOMEM
        or isinstance(error, MemoryError)
        or (isinstance(error, OSError) and error.errno == errno.ENOMEM)
    ):
        return "Bellek yetersiz. Özellikleri azaltın veya açıkça daha küçük bir veri sürümü seçin; önceki proje korundu."
    if sqlite_code == sqlite3.SQLITE_FULL or (
        isinstance(error, OSError) and error.errno in (errno.ENOSPC, errno.EDQUOT)
    ):
        return "Disk alanı veya kotası yetersiz. Alan açıp yeniden deneyin; önceki proje korundu."
    return fallback


def apply_process_limits(budget):
    if budget.device != "cpu":
        raise ValueError("CPU worker cannot execute GPU budget; no implicit fallback")
    configure_threads(budget.worker_threads)
    # Libraries can already be imported by spawn's module initialization.
    from threadpoolctl import threadpool_limits

    threadpool_limits(limits=budget.worker_threads)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[: budget.worker_threads])
    with open("/proc/self/status") as status:
        baseline = next(
            int(line.split()[1]) * 1024 for line in status if line.startswith("VmSize:")
        )
    resource.setrlimit(
        resource.RLIMIT_AS, (baseline + budget.ram_bytes, baseline + budget.ram_bytes)
    )
    resource.setrlimit(
        resource.RLIMIT_CPU,
        (int(budget.max_wall_seconds) + 1, int(budget.max_wall_seconds) + 2),
    )
