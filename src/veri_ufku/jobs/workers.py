"""Registered deterministic infrastructure fixtures, never file-supplied code."""

import os
import resource
from pathlib import Path

from veri_ufku.domain.contracts import Progress


class Canceled(Exception):
    pass


class BudgetExceeded(Exception):
    pass


def run_fixture(capability_id, parameters, budget, workspace, cancel, report):
    value = 0
    if capability_id == "demo.failure":
        raise RuntimeError("Sensitive sample value must never reach logs or UI")
    for unit in range(parameters.units):
        if cancel.is_set():
            raise Canceled
        if capability_id == "demo.cpu":
            start = unit * parameters.chunk_size
            # Actual CPU work; cancellation at bounded chunk boundaries.
            for number in range(start, start + parameters.chunk_size):
                value += number
        else:
            size = (unit + 1) * 4096
            if size > budget.temp_disk_bytes:
                raise BudgetExceeded
            with (Path(workspace) / "fixture.bin").open("ab") as file:
                file.write(b"\x00" * 4096)
            value = size
        report(
            Progress(
                "work",
                unit + 1,
                None if capability_id == "demo.unknown" else parameters.units,
            )
        )
        if cancel.wait(parameters.pause_seconds):
            raise Canceled
    return value


def process_entry(spec, workspace, cancel, connection):
    try:
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            os.environ[name] = str(spec.budget.cpu_threads)
        available_cpus = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, available_cpus[: spec.budget.cpu_threads])
        resource.setrlimit(
            resource.RLIMIT_AS, (spec.budget.ram_bytes, spec.budget.ram_bytes)
        )
        value = run_fixture(
            spec.capability_id,
            spec.parameters,
            spec.budget,
            workspace,
            cancel,
            lambda progress: connection.send(("progress", progress)),
        )
        connection.send(("result", value))
    except Canceled:
        connection.send(("canceled", None))
    except (BudgetExceeded, MemoryError) as error:
        connection.send(("error", ("budget", type(error).__name__)))
    except Exception as error:
        connection.send(("error", ("worker", type(error).__name__)))
    finally:
        connection.close()
