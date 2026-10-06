"""Source adapter boundary; no file formats are implemented in Phase 01."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SourceRequest:
    path: Path
    adapter_id: str


class SourceAdapter(Protocol):
    adapter_id: str

    def validate_source(self, request: SourceRequest) -> None: ...
