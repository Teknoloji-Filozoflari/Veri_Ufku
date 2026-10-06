"""Shared v1 job, capability, provenance and compute contracts; no Qt imports."""

import math
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class ExecutionKind(StrEnum):
    CPU = "cpu"
    IO = "io"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"

    @property
    def terminal(self):
        return self in {self.SUCCEEDED, self.FAILED, self.CANCELED}


@dataclass(frozen=True)
class ComputeBudget:
    ram_bytes: int = 2 * 1024**3
    temp_disk_bytes: int = 4 * 1024**3
    cpu_threads: int = 2
    max_wall_seconds: float = 600
    max_concurrent_cpu_jobs: int = 1
    max_concurrent_io_jobs: int = 2
    device: str = "cpu"
    sample_limit_rows: int = 10_000
    cancel_grace_ms: int = 2000
    reserve_disk_bytes: int = 1024**3

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            if name == "device":
                continue
            value = getattr(self, name)
            numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
            if not numeric or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid budget field: {name}")
            if name != "max_wall_seconds" and not isinstance(value, int):
                raise ValueError(f"Integer budget required: {name}")
        if self.device != "cpu":
            raise ValueError("Only CPU is supported")


@dataclass(frozen=True)
class Binding:
    dataset_version: str
    config_revision: int

    def __post_init__(self):
        if (
            not isinstance(self.dataset_version, str)
            or not self.dataset_version
            or type(self.config_revision) is not int
            or self.config_revision < 0
        ):
            raise ValueError("Invalid binding")


@dataclass(frozen=True)
class Capability:
    capability_id: str
    execution: ExecutionKind
    method: str
    version: int = 1
    kind: str = "infrastructure"
    maturity: str = "deneysel"
    semantic_version: int = 1
    input_schema: str = "DemoParameters/v1"
    output_type: str = "DemoResult/v1"
    supports: tuple[tuple[str, bool], ...] = (
        ("null", False),
        ("nan", False),
        ("inf", False),
        ("decimal", False),
        ("tz", False),
        ("sparse", False),
        ("weights", False),
        ("group", False),
        ("time", False),
        ("streaming", False),
        ("predict", False),
        ("proba", False),
        ("interval", False),
        ("safe_serialization", False),
        ("cancel", True),
    )
    limits: tuple[tuple[str, int], ...] = (("units", 1000), ("chunk_size", 1_000_000))
    parameter_schema: str = "DemoParameters/v1"
    backend: str = "python-stdlib"
    deterministic_policy: str = "exact integer result"
    requirement_ids: tuple[str, ...] = ("F01-S003", "F01-S006")
    help_links: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class DemoParameters:
    units: int = 100
    chunk_size: int = 100_000
    pause_seconds: float = 0.025

    def __post_init__(self):
        if (
            type(self.units) is not int
            or type(self.chunk_size) is not int
            or not 1 <= self.units <= 1000
            or not 1 <= self.chunk_size <= 1_000_000
        ):
            raise ValueError("Demo size exceeds supported limits")
        if (
            isinstance(self.pause_seconds, bool)
            or not isinstance(self.pause_seconds, (int, float))
            or not math.isfinite(self.pause_seconds)
            or not 0 <= self.pause_seconds <= 0.1
        ):
            raise ValueError("Invalid pacing interval")


@dataclass(frozen=True)
class JobSpec:
    capability_id: str
    binding: Binding
    parameters: DemoParameters = field(default_factory=DemoParameters)
    budget: ComputeBudget = field(default_factory=ComputeBudget)


@dataclass(frozen=True)
class Provenance:
    provenance_id: str
    dataset_versions: tuple[str, ...]
    config_revision: int
    capability_id: str
    parameters_hash: str
    environment: tuple[tuple[str, str], ...]
    created_at: str
    method_version: int = 1
    scope: str = "infrastructure_demo"
    seed: int | None = None
    seed_reason: str = "deterministic fixture; no sampling"
    source_snapshot_ids: tuple[str, ...] = ()
    row_lineage_ref: str | None = None
    column_lineage_ref: str | None = None
    filters: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    learning_content_version: str | None = None


@dataclass(frozen=True)
class Progress:
    phase: str
    done: int = 0
    total: int | None = None

    def __post_init__(self):
        if self.done < 0 or (
            self.total is not None and not 0 <= self.done <= self.total
        ):
            raise ValueError("Invalid progress")


@dataclass(frozen=True)
class AppError:
    code: str
    correlation_id: str
    exception_type: str = ""

    @classmethod
    def create(cls, code, exception_type=""):
        return cls(code, str(uuid4()), exception_type)


@dataclass(frozen=True)
class JobResult:
    result_id: str
    binding: Binding
    value: int
    provenance: Provenance
    result_type: str = "DemoResult/v1"


@dataclass(frozen=True)
class JobSnapshot:
    job_id: str
    spec: JobSpec
    state: JobState
    progress: Progress
    result: JobResult | None
    error: AppError | None
    provenance: Provenance
    submitted_at: float
    started_at: float | None
    ended_at: float | None
    cancel_requested_at: float | None
    worker_pid: int | None
    peak_rss_bytes: int
    peak_temp_bytes: int

    def result_for(self, current: Binding):
        if self.state == JobState.SUCCEEDED and self.spec.binding == current:
            return self.result
        return None
