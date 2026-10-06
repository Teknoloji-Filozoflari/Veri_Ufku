"""Minimal shared registry. No import/stat/model capability exists yet."""

from veri_ufku.domain.contracts import Capability, ExecutionKind

CAPABILITIES = {
    "demo.cpu": Capability(
        "demo.cpu", ExecutionKind.CPU, "integer_sum", help_links=("tasks",)
    ),
    "demo.io": Capability(
        "demo.io", ExecutionKind.IO, "bounded_file_write", help_links=("tasks",)
    ),
    "demo.unknown": Capability(
        "demo.unknown", ExecutionKind.IO, "unknown_total", help_links=("tasks",)
    ),
    "demo.failure": Capability(
        "demo.failure", ExecutionKind.IO, "controlled_failure", help_links=("tasks",)
    ),
}


def get_capability(capability_id):
    try:
        return CAPABILITIES[capability_id]
    except KeyError:
        raise ValueError("Unsupported capability") from None
