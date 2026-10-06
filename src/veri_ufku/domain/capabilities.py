"""Minimal shared registry. No import/stat/model capability exists yet."""

from veri_ufku.domain.contracts import Capability, ExecutionKind

CAPABILITIES = {
    "demo.cpu": Capability("demo.cpu", ExecutionKind.CPU, "integer_sum"),
    "demo.io": Capability("demo.io", ExecutionKind.IO, "bounded_file_write"),
    "demo.unknown": Capability("demo.unknown", ExecutionKind.IO, "unknown_total"),
    "demo.failure": Capability("demo.failure", ExecutionKind.IO, "controlled_failure"),
}


def get_capability(capability_id):
    try:
        return CAPABILITIES[capability_id]
    except KeyError:
        raise ValueError("Unsupported capability") from None
