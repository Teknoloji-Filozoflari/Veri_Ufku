"""Closed local replay recipe. Processing clock is data, never wall time."""

import math
from dataclasses import asdict, dataclass

from veri_ufku.storage.project_model import ProjectError


@dataclass(frozen=True)
class StreamSpec:
    event_id: str = ""
    event_time: str = ""
    processing_time: str = ""
    feedback_time: str = ""
    target: str = ""
    features: tuple = ()
    buffer: int = 64
    window: float = 60
    lateness: float = 0
    late_policy: str = "quarantine"
    clock: str = "event"
    retrain: str = "alarm_only"
    drift_threshold: float = 0.25
    checkpoint_every: int = 16
    seed: int = 62

    @classmethod
    def from_dict(cls, raw):
        try:
            s = cls(**{**raw, "features": tuple(raw.get("features", ()))})
        except (TypeError, ValueError):
            raise ProjectError("Stream kapalı tarif geçersiz.") from None
        cols = (
            s.event_id,
            s.event_time,
            s.processing_time,
            s.feedback_time,
            s.target,
            *s.features,
        )
        if (
            not 1 <= len(s.features) <= 16
            or any(not isinstance(c, str) or not c for c in cols)
            or len(set(cols)) != len(cols)
        ):
            raise ProjectError(
                "Stream ayrı ColumnId alanları ve1–16 feature gerektirir."
            )
        for k, lo, hi in (
            ("buffer", 2, 256),
            ("checkpoint_every", 1, 128),
            ("seed", 0, 2**32 - 1),
        ):
            if type(getattr(s, k)) is not int or not lo <= getattr(s, k) <= hi:
                raise ProjectError("Stream buffer/checkpoint/seed bütçesi geçersiz.")
        for k, lo, hi in (
            ("window", 0.001, 1e9),
            ("lateness", 0, 1e9),
            ("drift_threshold", 0, 1),
        ):
            v = getattr(s, k)
            if type(v) not in (int, float) or not math.isfinite(v) or not lo <= v <= hi:
                raise ProjectError("Stream window/lateness/drift geçersiz.")
        if (
            s.late_policy not in ("reject", "quarantine")
            or s.clock not in ("event", "processing")
            or s.retrain not in ("alarm_only", "reset")
        ):
            raise ProjectError("Stream açık late/clock/retrain policy gerektirir.")
        return s

    def data(self):
        return asdict(self)
