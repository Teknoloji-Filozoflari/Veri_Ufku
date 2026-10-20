"""Closed, portable NLP exploration recipe; model scripts are never imported."""

from dataclasses import asdict, dataclass, field

from veri_ufku.storage.project_model import ProjectError

METHODS = (
    "tfidf",
    "nmf",
    "lda",
    "embeddings",
    "search",
    "ner",
    "sentiment",
    "classification",
    "annotation",
    "active-learning",
    "retrieval",
    "model",
)


@dataclass(frozen=True)
class NLPSpec:
    operation: str = "nmf"
    topics: int = 2
    seed: int = 55
    model_folder: str = ""
    query: str = ""
    top_k: int = 10
    partitions: dict[str, str] = field(default_factory=dict)
    document_labels: list[str] = field(default_factory=lambda: ["negative", "positive"])
    entity_labels: list[str] = field(default_factory=lambda: ["PER", "LOC", "ORG"])
    annotations: list[dict] = field(default_factory=list)
    relevance: dict[str, int] = field(default_factory=dict)

    def data(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        try:
            if not isinstance(value, dict) or set(value) - set(
                cls.__dataclass_fields__
            ):
                raise ValueError
            s = cls(**value)
            s.validate()
            return s
        except (ValueError, TypeError) as error:
            raise ProjectError(
                "NLP tarifi geçersiz; içerik hata mesajına eklenmez."
            ) from error

    def validate(self):
        if self.operation not in METHODS:
            raise ProjectError("Desteklenmeyen NLP görevi.")
        for key, lo, hi in [("topics", 2, 8), ("seed", 0, 2**32 - 1), ("top_k", 1, 50)]:
            if (
                type(getattr(self, key)) is not int
                or not lo <= getattr(self, key) <= hi
            ):
                raise ProjectError("NLP sayısal bütçesi geçersiz.")
        if (
            not isinstance(self.model_folder, str)
            or len(self.model_folder) > 4096
            or not isinstance(self.query, str)
            or len(self.query) > 5000
        ):
            raise ProjectError("Model klasörü/query sınırı geçersiz.")
        if (
            not isinstance(self.partitions, dict)
            or len(self.partitions) > 500
            or any(
                not isinstance(k, str) or v not in ("train", "validation", "test")
                for k, v in self.partitions.items()
            )
        ):
            raise ProjectError("RowId→train/validation/test planı gerekli.")
        for labels in [self.document_labels, self.entity_labels]:
            if (
                not isinstance(labels, list)
                or not 1 <= len(labels) <= 32
                or len(set(labels)) != len(labels)
                or any(not isinstance(x, str) or not 1 <= len(x) <= 40 for x in labels)
            ):
                raise ProjectError("Benzersiz document/entity label schema gerekli.")
        if (
            not isinstance(self.annotations, list)
            or len(self.annotations) > 500
            or any(not isinstance(x, dict) for x in self.annotations)
        ):
            raise ProjectError("Human annotation listesi sınırı500.")
        if (
            not isinstance(self.relevance, dict)
            or len(self.relevance) > 500
            or any(
                not isinstance(k, str) or type(v) is not int or not 0 <= v <= 3
                for k, v in self.relevance.items()
            )
        ):
            raise ProjectError("Relevance insan etiketleri0..3 olmalı.")
