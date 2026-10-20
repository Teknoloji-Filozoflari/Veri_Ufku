"""Bounded offline ranking recipes. IDs are typed and time is explicit Unix seconds."""

import json
import math
from dataclasses import asdict, dataclass

from veri_ufku.storage.project_model import ProjectError


def identity(value):
    if (
        type(value) not in (str, int)
        or isinstance(value, str)
        and not 1 <= len(value) <= 128
    ):
        raise ProjectError(
            "Kimlik boş olmayan string veya integer olmalı; sessiz dönüştürülmez."
        )
    return json.dumps(
        [type(value).__name__, value], ensure_ascii=False, separators=(",", ":")
    )


@dataclass(frozen=True)
class RecommendationSpec:
    task: str = "popularity"
    feedback: str = "implicit"
    user: str = ""
    item: str = ""
    value: str = ""
    time: str = ""
    query: str = ""
    features: tuple = ()
    split: str = "temporal"
    cutoff: float = 0
    k: int = 5
    candidates: str = "full"
    negatives: int = 20
    seen_filter: bool = True
    rating_min: float = 1
    rating_max: float = 5
    relevant_rating: float = 4
    factors: int = 4
    epochs: int = 10
    regularization: float = 0.1
    alpha: float = 10
    seed: int = 59

    @classmethod
    def from_dict(cls, raw):
        try:
            s = cls(**{**raw, "features": tuple(raw.get("features", ()))})
        except (TypeError, ValueError):
            raise ProjectError("Öneri tarifi kapalı şemaya uymuyor.") from None
        if (
            s.task not in ("popularity", "content", "factorization", "ranker")
            or s.feedback not in ("implicit", "explicit")
            or s.split not in ("temporal", "leave_last_out")
            or s.candidates not in ("full", "sampled")
            or not isinstance(s.query, str)
            or type(s.seen_filter) is not bool
            or any(
                not isinstance(getattr(s, p), str) or not getattr(s, p)
                for p in ("user", "item", "value", "time")
            )
            or any(not isinstance(x, str) or not x for x in s.features)
            or len(set(s.features)) != len(s.features)
            or len(s.features) > 16
        ):
            raise ProjectError(
                "User/item/value/time ColumnId, feedback, split veya aday şeması geçersiz."
            )
        for p, low, high in (
            ("k", 1, 50),
            ("negatives", 1, 128),
            ("factors", 1, 16),
            ("epochs", 1, 50),
            ("seed", 0, 2**32 - 1),
        ):
            v = getattr(s, p)
            if type(v) is not int or not low <= v <= high:
                raise ProjectError(
                    "Öneri K/negative/factor/epoch/seed bütçesi geçersiz."
                )
        for p, low, high in (
            ("cutoff", -1e12, 1e12),
            ("regularization", 0.0001, 10),
            ("alpha", 0.01, 100),
            ("rating_min", -100, 100),
            ("rating_max", -100, 100),
            ("relevant_rating", -100, 100),
        ):
            v = getattr(s, p)
            if (
                type(v) not in (int, float)
                or not math.isfinite(v)
                or not low <= v <= high
            ):
                raise ProjectError(
                    "Öneri zaman/rating/regularization parametresi geçersiz."
                )
        if (
            not s.rating_min < s.rating_max
            or not s.rating_min <= s.relevant_rating <= s.rating_max
        ):
            raise ProjectError("Explicit rating aralığı ve relevance eşiği geçersiz.")
        if len({s.user, s.item, s.value, s.time}) != 4 or set(s.features) & {
            s.user,
            s.item,
            s.value,
            s.time,
            s.query,
        }:
            raise ProjectError(
                "Kimlik, hedef, zaman ve content feature rolleri ayrı olmalı."
            )
        if s.task in ("content", "ranker") and not s.features:
            raise ProjectError(
                "Content/ranker için as-of mevcut sayısal feature seçin."
            )
        if s.task == "ranker" and (
            s.seen_filter
            or not s.query
            or s.query in (s.user, s.item, s.value, s.time)
            or s.split != "temporal"
            or s.candidates != "full"
        ):
            raise ProjectError(
                "LTR ayrı query/group, temporal cutoff ve tam beyan edilmiş query candidate kümesi ister."
            )
        return s

    def data(self):
        return asdict(self)
