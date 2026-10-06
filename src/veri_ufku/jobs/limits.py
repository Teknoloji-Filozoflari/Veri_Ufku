"""Shared Linux process admission for import and dataset jobs."""

import os
import resource


def apply_process_limits(budget):
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[: budget.cpu_threads])
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
