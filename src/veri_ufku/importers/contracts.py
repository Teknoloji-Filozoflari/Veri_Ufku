"""Shared format adapter boundary; implemented adapters return artifact references."""

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

    def inspect(self, snapshot: dict, settings: object, control: object) -> dict: ...

    def preview(self, snapshot: dict, settings: object, control: object) -> dict: ...

    def import_data(
        self, snapshot: dict, settings: object, workspace: Path, control: object
    ) -> dict: ...
