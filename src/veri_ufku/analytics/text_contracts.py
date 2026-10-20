"""Lightweight declarative settings; no model libraries in the GUI."""

from dataclasses import asdict, dataclass

from veri_ufku.storage.project_model import ProjectError

STOPWORDS = {
    "none": (),
    "tr": (
        "ve",
        "veya",
        "ile",
        "bir",
        "bu",
        "şu",
        "o",
        "için",
        "ama",
        "de",
        "da",
        "mi",
        "mı",
        "mu",
        "mü",
    ),
    "en": ("the", "a", "an", "and", "or", "with", "for", "of", "to", "in", "is", "are"),
}


@dataclass(frozen=True)
class TextSpec:
    column: str
    language: str = "tr"
    normalization: str = "NFC"
    lowercase: bool = True
    numbers: bool = True
    stopwords: str = "none"
    custom_stopwords: str = ""
    ngram_min: int = 1
    ngram_max: int = 1
    max_features: int = 2000
    preview: bool = False
    similarity: bool = False
    advanced: dict | None = None

    @classmethod
    def from_dict(cls, value):
        try:
            if not isinstance(value, dict) or set(value) - set(
                cls.__dataclass_fields__
            ):
                raise ValueError()
            result = cls(**value)
            result.validate()
            return result
        except (TypeError, ValueError) as error:
            raise ProjectError(
                "Metin ayarları geçersiz; içerik hata/log mesajına eklenmez."
            ) from error

    def data(self):
        data = asdict(self)
        if self.advanced is None:
            data.pop("advanced")
        return data

    def validate(self):
        if self.advanced is not None:
            from veri_ufku.analytics.nlp_contracts import NLPSpec

            NLPSpec.from_dict(self.advanced)
        if (
            not isinstance(self.column, str)
            or self.language not in ("tr", "en", "other")
            or self.normalization not in ("NFC", "NFKC")
            or self.stopwords not in STOPWORDS
        ):
            raise ProjectError("Metin sütunu/dil/Unicode/durak sözcük seçimi geçersiz.")
        if any(
            type(getattr(self, k)) is not bool
            for k in ("lowercase", "numbers", "preview", "similarity")
        ):
            raise ProjectError("Metin onayları geçersiz.")
        if (
            not isinstance(self.custom_stopwords, str)
            or len(self.custom_stopwords) > 4000
        ):
            raise ProjectError("Özel durak sözcükleri en fazla4000 karakter olabilir.")
        if (
            any(
                type(getattr(self, k)) is not int
                for k in ("ngram_min", "ngram_max", "max_features")
            )
            or not 1 <= self.ngram_min <= self.ngram_max <= 3
            or not 1 <= self.max_features <= 10000
        ):
            raise ProjectError("N-gram1–3; seçili vocab sınırı1–10000 olmalı.")
