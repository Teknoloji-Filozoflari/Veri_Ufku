"""Closed basket/cohort/funnel/process recipes; timezone and observation bounds explicit."""

import math
from dataclasses import asdict, dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from veri_ufku.storage.project_model import ProjectError


@dataclass(frozen=True)
class PatternSpec:
    task: str = "apriori"
    entity: str = ""
    activity: str = ""
    time: str = ""
    order: str = ""
    complete: str = ""
    duplicates: str = "reject"
    min_support: float = 0.2
    min_confidence: float = 0.5
    max_length: int = 4
    candidate_budget: int = 5000
    rule_budget: int = 1000
    timezone: str = "UTC"
    period: str = "month"
    cohort_start: str = "first_observed"
    start_activity: str = "signup"
    unit: str = "person"
    observation_start: float = 0
    observation_end: float = 1
    stages: tuple = ("view", "buy")
    window_seconds: float = 86400
    ties: str = "reject"
    conformance: dict | None = None
    seed: int = 60

    @classmethod
    def from_dict(cls, raw):
        try:
            s = cls(**{**raw, "stages": tuple(raw.get("stages", ("view", "buy")))})
        except (ValueError, TypeError):
            raise ProjectError("Pattern kapalı tarif şeması geçersiz.") from None
        if (
            s.task
            not in (
                "apriori",
                "fp_growth",
                "cohort",
                "funnel",
                "process",
                "conformance",
            )
            or not all(
                isinstance(getattr(s, k), str)
                for k in (
                    "entity",
                    "activity",
                    "time",
                    "order",
                    "complete",
                    "timezone",
                    "start_activity",
                )
            )
            or not s.entity
            or not s.activity
            or s.entity == s.activity
        ):
            raise ProjectError("Task/entity/activity ColumnId şeması geçersiz.")
        if (
            s.duplicates not in ("reject", "set")
            or s.period not in ("day", "week", "month")
            or s.cohort_start not in ("first_observed", "activity")
            or s.unit not in ("person", "event")
            or s.ties not in ("reject", "order")
        ):
            raise ProjectError("Duplicate/period/cohort/unit/tie seçimi geçersiz.")
        for key, lo, hi in (
            ("max_length", 1, 5),
            ("candidate_budget", 1, 20000),
            ("rule_budget", 1, 2000),
            ("seed", 0, 2**32 - 1),
        ):
            v = getattr(s, key)
            if type(v) is not int or not lo <= v <= hi:
                raise ProjectError(
                    "Pattern length/candidate/rule/seed bütçesi geçersiz."
                )
        for key, lo, hi in (
            ("min_support", 0.0001, 1),
            ("min_confidence", 0, 1),
            ("observation_start", -1e10, 1e10),
            ("observation_end", -1e10, 1e10),
            ("window_seconds", 1, 366 * 86400),
        ):
            v = getattr(s, key)
            if type(v) not in (int, float) or not math.isfinite(v) or not lo <= v <= hi:
                raise ProjectError(
                    "Pattern support/confidence/time parametresi geçersiz."
                )
        try:
            ZoneInfo(s.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ProjectError(
                "IANA timezone bulunamadı; sessiz UTC dönüşümü yok."
            ) from None
        if s.task not in ("apriori", "fp_growth"):
            roles = [
                s.entity,
                s.activity,
                s.time,
                *([s.order] if s.order else []),
                *([s.complete] if s.complete else []),
            ]
            if (
                not s.time
                or len(set(roles)) != len(roles)
                or s.observation_end <= s.observation_start
            ):
                raise ProjectError(
                    "Ayrı event rolleri ve start<end gözlem aralığı gerekli."
                )
        if (
            not 2 <= len(s.stages) <= 10
            or any(not isinstance(x, str) or not 1 <= len(x) <= 128 for x in s.stages)
            or len(set(s.stages)) != len(s.stages)
        ):
            raise ProjectError("Funnel2..10 unique sıralı activity ister.")
        if s.ties == "order" and not s.order:
            raise ProjectError("Eşit timestamp için kaynak sıra kolonu seçin.")
        if s.task == "conformance":
            m = s.conformance
            if (
                not isinstance(m, dict)
                or set(m) != {"schema", "starts", "ends", "edges"}
                or m["schema"] != "ActivityTransitionModel/v1"
            ):
                raise ProjectError(
                    "Conformance ActivityTransitionModel/v1 starts/ends/edges ister; Petri alignment değildir."
                )
            if any(not isinstance(m[k], list) for k in ("starts", "ends", "edges")):
                raise ProjectError("Conformance starts/ends/edges liste olmalı.")
            labels = [*m["starts"], *m["ends"]]
            if (
                not m["starts"]
                or not m["ends"]
                or len(m["edges"]) > 256
                or any(
                    not isinstance(pair, list) or len(pair) != 2 for pair in m["edges"]
                )
            ):
                raise ProjectError("Conformance start/end/edge sınırı.")
            labels += [v for pair in m["edges"] for v in pair]
            if (
                any(not isinstance(v, str) or not 1 <= len(v) <= 128 for v in labels)
                or len(set(labels)) > 32
            ):
                raise ProjectError("Conformance en fazla32activity.")
        elif s.conformance is not None:
            raise ProjectError("Conformance modeli yalnız ayrı conformance task'ında.")
        return s

    def data(self):
        return asdict(self)
