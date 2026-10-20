"""Local, bounded, explicit Unicode text analysis; never logs document contents."""

import math
import unicodedata
from collections import Counter
from datetime import UTC, datetime

import numpy as np
import polars as pl
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer

from veri_ufku.analytics.dataset import checked
from veri_ufku.analytics.text_contracts import STOPWORDS, TextSpec
from veri_ufku.importers.delimited import Control
from veri_ufku.storage.project_model import ProjectError, uid


def normalize(value, spec):
    if value is None:
        return ""
    if not isinstance(value, str) or len(value) > 10000:
        raise ProjectError(
            "Belge String olmalı ve en fazla10000 karakter içermeli; belge içeriği raporlanmaz."
        )
    value = unicodedata.normalize(spec.normalization, value)
    if spec.lowercase:
        if spec.language == "tr":
            value = value.replace("I", "ı").replace("İ", "i")
        value = value.casefold()
    return value


def basic_tokens(value, spec):
    result, token = [], []
    for char in normalize(value, spec):
        kind = unicodedata.category(char)[0]
        if kind in ("L", "M") or kind == "N" and spec.numbers:
            token.append(char)
        elif token:
            result.append("".join(token))
            token = []
    if token:
        result.append("".join(token))
    return result


class Analyzer:
    def __init__(self, spec):
        self.spec = spec
        self.stops = set()
        for word in [*STOPWORDS[spec.stopwords], *spec.custom_stopwords.split()]:
            self.stops.update(basic_tokens(word, spec))

    def tokens(self, value):
        return [
            token for token in basic_tokens(value, self.spec) if token not in self.stops
        ]

    def __call__(self, value):
        tokens = self.tokens(value)
        if len(tokens) > 3000:
            raise ProjectError("Belge token sınırı3000 aşıldı; içerik loglanmaz.")
        return [
            " ".join(tokens[i : i + n])
            for n in range(self.spec.ngram_min, self.spec.ngram_max + 1)
            for i in range(len(tokens) - n + 1)
        ]


def vectorize(documents, spec, control=None):
    control = control or Control()
    analyzer = Analyzer(spec)
    counts, documents_with_term = Counter(), Counter()
    total = 0
    for i, value in enumerate(documents):
        if i % 128 == 0:
            control.check()
            control.progress("Metin tokenizasyonu ve vocab bütçesi", i, len(documents))
        terms = analyzer(value)
        counts.update(terms)
        documents_with_term.update(set(terms))
        total += len(terms)
        if len(counts) > 50000 or total > 5000000:
            raise ProjectError(
                "Aday vocab50000 veya n-gram5000000 sınırı aşıldı; ayarları daraltın. Sessiz örneklem yok."
            )
    if not counts:
        return None, None, counts, documents_with_term
    selected = sorted(counts, key=lambda term: (-counts[term], term))[
        : spec.max_features
    ]
    vocabulary = {term: i for i, term in enumerate(sorted(selected))}
    vectorizer = TfidfVectorizer(
        analyzer=analyzer,
        vocabulary=vocabulary,
        lowercase=False,
        norm="l2",
        smooth_idf=True,
        sublinear_tf=False,
        dtype=np.float64,
    )
    matrix = vectorizer.fit_transform(documents)
    if matrix.nnz > 5000000:
        raise ProjectError("Seyrek TF-IDF5 milyon dolu hücre sınırı aşıldı.")
    control.check()
    return vectorizer, matrix, counts, documents_with_term


class TextPreparation(BaseEstimator, TransformerMixin):
    """A sklearn pipeline step: vocabulary/IDF learned exclusively in fit(X_train)."""

    def __init__(self, spec, columns):
        self.spec, self.columns = spec, columns

    def documents(self, X):
        config = TextSpec.from_dict(self.spec)
        name = next(c["name"] for c in self.columns if c["id"] == config.column)
        if X[name].dtype not in (pl.String, pl.Null):
            raise ProjectError("TF-IDF yalnız String/boş metin sütununu kabul eder.")
        if sum(len(v) for v in X[name] if isinstance(v, str)) > 10000000:
            raise ProjectError(
                "Eğitim/uygulama metni toplam10 milyon karakter bütçesini aşıyor."
            )
        return [normalize(v, config) for v in X[name]]

    def fit(self, X, y=None):
        config = TextSpec.from_dict(self.spec)
        self.fit_row_ids_ = X["__vu_row_id"].to_list()
        self.vectorizer_, matrix, counts, df = vectorize(self.documents(X), config)
        if self.vectorizer_ is None:
            raise ProjectError(
                "Eğitim fold'unda token yok; tümü boş/durak sözcük. TF-IDF sınıflandırma reddedildi."
            )
        self.summary_ = dict(
            tfidf=dict(
                vocabulary=dict(self.vectorizer_.vocabulary_),
                idf=self.vectorizer_.idf_.tolist(),
                candidate_vocab=len(counts),
                retained_vocab=matrix.shape[1],
                fit_scope="training_fold",
                null_policy="empty_document",
                options=config.data(),
            )
        )
        return self

    def transform(self, X):
        matrix = self.vectorizer_.transform(self.documents(X))
        if matrix.nnz > 5000000:
            raise ProjectError("Seyrek TF-IDF bütçesi aşıldı.")
        return matrix


def calculate(request, parameters, workspace, control=None):
    control = control or Control()
    spec = TextSpec.from_dict(parameters)
    if spec.advanced is not None:
        from veri_ufku.analytics.nlp import calculate as advanced_calculate

        return advanced_calculate(request, spec, workspace, control)
    checked(request, control)
    col = next((c for c in request["columns"] if c["id"] == spec.column), None)
    if not col or not 0 <= request["row_count"] <= 100000:
        raise ProjectError("Metin sütunu veya100000 kayıt bütçesi geçersiz.")
    frame = pl.read_parquet(request["path"], columns=["__vu_row_id", col["name"]])
    if frame[col["name"]].dtype not in (pl.String, pl.Null):
        raise ProjectError(
            "Serbest metin sütunu String olmalı; boş Null kolon incelemesi desteklenir."
        )
    if (
        frame.height != request["row_count"]
        or frame["__vu_row_id"].n_unique() != frame.height
    ):
        raise ProjectError("Metin kapsamı veya kaynak RowId sayısı uyuşmuyor.")
    raw = frame[col["name"]].to_list()
    if sum(len(v) for v in raw if isinstance(v, str)) > 10000000:
        raise ProjectError(
            "Toplam10 milyon karakter bütçesi aşıldı; açık daha küçük veri sürümü seçin."
        )
    documents = [normalize(v, spec) for v in raw]
    vectorizer, matrix, counts, df = vectorize(documents, spec, control)
    analyzer = Analyzer(spec)
    frequencies = [
        dict(term=t, count=n, document_count=df[t])
        for t, n in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:100]
    ]
    tfidf = []
    if vectorizer is not None:
        means = np.asarray(matrix.mean(axis=0)).ravel()
        tfidf = [
            dict(
                term=term,
                idf=float(vectorizer.idf_[idx]),
                mean_weight=float(means[idx]),
            )
            for term, idx in sorted(
                vectorizer.vocabulary_.items(),
                key=lambda item: (-means[item[1]], item[0]),
            )[:100]
        ]
    previews = []
    if spec.preview:
        previews = [
            dict(
                row_id=frame["__vu_row_id"][i],
                before=(raw[i] or "")[:200],
                normalized=documents[i][:200],
                tokens=analyzer.tokens(raw[i])[:30],
            )
            for i in range(min(5, len(raw)))
        ]
    pairs = []
    if spec.similarity and matrix is not None:
        if len(raw) > 1000:
            raise ProjectError(
                "Tam çift benzerliği en fazla1000 belge; açık küçük veri sürümü seçin."
            )
        similarity = (matrix @ matrix.T).tocoo()
        pairs = [
            dict(
                left=frame["__vu_row_id"][int(i)],
                right=frame["__vu_row_id"][int(j)],
                cosine=float(v),
            )
            for i, j, v in zip(similarity.row, similarity.col, similarity.data)
            if i < j
        ]
        pairs = sorted(pairs, key=lambda p: (-p["cosine"], p["left"], p["right"]))[:30]
    lengths = [len(v or "") for v in raw]
    checked(request, control)
    return dict(
        schema="TextRun/v1",
        run_id="text:" + uid(),
        dataset_version=request["version_id"],
        snapshot_fingerprint=request["fingerprint"],
        created_at=datetime.now(UTC).isoformat(),
        spec=spec.data(),
        rows=len(raw),
        null_text=sum(v is None for v in raw),
        empty_text=sum(v == "" for v in raw),
        whitespace_text=sum(
            isinstance(v, str) and bool(v) and not v.strip() for v in raw
        ),
        empty_after=sum(not analyzer.tokens(v) for v in raw),
        length=dict(
            unit="Unicode code points before normalization; not bytes or graphemes",
            minimum=min(lengths, default=0),
            maximum=max(lengths, default=0),
            mean=sum(lengths) / len(lengths) if lengths else None,
        ),
        candidate_vocab=len(counts),
        retained_vocab=matrix.shape[1] if matrix is not None else 0,
        frequencies=frequencies,
        tfidf=tfidf,
        similarities=pairs,
        previews=previews,
        fit_scope="descriptive_selected_column_only; never classification vocabulary",
        warning="Token/stopword/Unicode/dil seçimi sonuçları değiştirir. Benzerlik ortak ağırlıklı sözcüktür; anlam/duygu/konu veya doğruluk etiketi değildir. Ham önizleme yalnız açık seçimle gösterilir ve sonuç kaydına alınmaz.",
    )


def validate_run(value, dataset):
    if value.get("advanced"):
        from veri_ufku.analytics.nlp import validate

        return validate(value, dataset)
    TextSpec.from_dict(value["spec"])
    if (
        value["schema"] != "TextRun/v1"
        or value["dataset_version"] != dataset["version_id"]
        or value["rows"] != dataset["import_metadata"]["row_count"]
    ):
        raise ProjectError("Metin sonuç kapsamı uyuşmuyor.")
    if value["spec"]["column"] not in {
        c["id"] for c in dataset["import_metadata"]["columns"]
    }:
        raise ProjectError("Metin sonucu bilinmeyen sütuna bağlı.")
    counts = [
        value[k] for k in ("null_text", "empty_text", "whitespace_text", "empty_after")
    ]
    if (
        any(type(n) is not int or not 0 <= n <= value["rows"] for n in counts)
        or sum(counts[:3]) > value["rows"]
    ):
        raise ProjectError("Boş metin sayım bağı geçersiz.")
    if any(
        not isinstance(p["term"], str)
        or not 0 < p["document_count"] <= p["count"] <= 5000000
        or p["document_count"] > value["rows"]
        for p in value["frequencies"]
    ):
        raise ProjectError("Metin frekans/doc-frequency kaydı geçersiz.")
    if not 0 <= value["retained_vocab"] <= value["candidate_vocab"] <= 50000:
        raise ProjectError("Metin vocab kaydı geçersiz.")
    if any(
        not math.isfinite(row[k])
        for row in value["tfidf"]
        for k in ("idf", "mean_weight")
    ):
        raise ProjectError("TF-IDF kayıt değerleri geçersiz.")
