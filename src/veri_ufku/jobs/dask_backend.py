"""Optional bounded local Dask chunk reduction; never connects on import/open.

Remote execution is deliberately unavailable until mutually authenticated executor
and cluster-wide quotas have real acceptance evidence. A remote plan is a preview,
not a connection or authorization to upload.
"""

import importlib.util
import math
from dataclasses import dataclass
from importlib.metadata import version
from urllib.parse import urlsplit

from veri_ufku.storage.project_model import ProjectError


def available():
    return (
        importlib.util.find_spec("dask") is not None and version("dask") == "2026.8.0"
    )


@dataclass(frozen=True)
class RemotePlan:
    endpoint: str
    location: str
    credential_ref: str
    transfer_bytes: int

    def preview(self, budget):
        url = urlsplit(self.endpoint)
        if (
            url.scheme != "tls"
            or not url.hostname
            or not url.port
            or url.username
            or url.password
            or url.path
            or url.query
            or url.fragment
        ):
            raise ProjectError(
                "Remote plan yalnız credentials içermeyen tls://host:port kabul eder."
            )
        if (
            not self.location
            or not self.credential_ref
            or not 0 <= self.transfer_bytes <= budget.transfer_bytes
        ):
            raise ProjectError("Konum, keyring referansı ve transfer bütçesi gerekli.")
        return dict(
            endpoint=self.endpoint,
            location=self.location,
            transfer_bytes=self.transfer_bytes,
            auth="mutual TLS; system keyring reference",
            available=False,
            warning="Remote runtime/cluster-wide quota doğrulanmadı; bağlantı ve veri transferi kapalı. Retry/resume exactly-once garantisi değildir.",
        )


def chunk_summary(values):
    finite = [float(v) for v in values if v is not None and math.isfinite(v)]
    return dict(
        n=len(finite), excluded=len(values) - len(finite), total=math.fsum(finite)
    )


def parquet_summary(path, column, control, *, chunk_rows=4096):
    """One explicit numeric column; streaming read, bounded task waves, no upload."""
    if not available():
        raise ProjectError("Optional Dask kurulu değil; yerel çekirdek kullanılabilir.")
    if control.budget.device != "cpu":
        raise ProjectError("Dask chunk summary CPU-only; implicit GPU fallback yok.")
    if type(chunk_rows) is not int or not 1 <= chunk_rows <= min(
        4096, control.budget.sample_limit_rows
    ):
        raise ProjectError("Chunk boyutu erken örnek/bellek sınırını aşamaz.")
    import dask
    import pyarrow as pa
    import pyarrow.parquet as pq

    from veri_ufku.importers.delimited import hash_artifact

    fingerprint = hash_artifact(path, control)
    source = pq.ParquetFile(path)
    field = source.schema_arrow.field(column)
    if not (pa.types.is_integer(field.type) or pa.types.is_floating(field.type)):
        raise ProjectError("Chunk summary yalnız integer/float kolon destekler.")
    # Python scalar/list and Arrow buffers coexist. Conservative preflight, RSS
    # supervisor still owns the hard runtime guard; this is not an exact estimate.
    wave = min(control.budget.max_tasks, 8)
    if chunk_rows * wave * 128 > control.budget.ram_bytes // 4:
        raise ProjectError("Chunk/task dalgası RAM önkontrolünü aşıyor.")
    n = excluded = tasks = 0
    total, pending = 0.0, []

    def drain():
        nonlocal n, excluded, total
        control.check()
        results = dask.compute(
            *pending, scheduler="threads", num_workers=control.budget.worker_threads
        )
        for result in results:
            n += result["n"]
            excluded += result["excluded"]
            total = math.fsum((total, result["total"]))
        pending.clear()
        control.check()

    for batch in source.iter_batches(
        batch_size=chunk_rows, columns=[column], use_threads=False
    ):
        control.check()
        tasks += 1
        pending.append(
            dask.delayed(chunk_summary, pure=True)(batch.column(0).to_pylist())
        )
        if len(pending) >= wave:
            drain()
    if pending:
        drain()
    if hash_artifact(path, control) != fingerprint:
        raise ProjectError("Kaynak hesap sırasında değişti; sonuç yayınlanmadı.")
    return dict(
        source_fingerprint=fingerprint,
        method="compute.dask-summary/v1",
        n=n,
        excluded=excluded,
        total=total,
        chunks=tasks,
        chunk_rows=chunk_rows,
        max_pending_tasks=wave,
        backend="dask/local-threads",
        consistency="immutable local snapshot required by caller",
        transfer_bytes=0,
        exactly_once=False,
        numeric="Float64 chunk sums; rounding depends on chunk order",
    )
