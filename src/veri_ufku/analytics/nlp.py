"""Bounded topic/local NLP adapters with original offsets and training-pool isolation."""

import importlib.metadata
import json
import time
import warnings
from dataclasses import asdict
from datetime import UTC, datetime

import numpy as np
import polars as pl
from sklearn.decomposition import NMF, LatentDirichletAllocation
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

from veri_ufku.analytics.dataset import checked
from veri_ufku.analytics.nlp_contracts import NLPSpec
from veri_ufku.analytics.nlp_models import inspect, parse
from veri_ufku.analytics.text import Analyzer, vectorize
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.storage.project_model import ProjectError, digest, encode, uid


def utf16_offset(text, index):
    if type(index) is not int or not 0 <= index <= len(text):
        raise ProjectError("Original Unicode offset geçersiz.")
    return len(text[:index].encode("utf-16-le")) // 2


def annotations(values, documents, ids, extra):
    byid = dict(zip(ids, documents))
    seen = set()
    for a in values:
        if (
            not isinstance(a, dict)
            or set(a) != {"row_id", "label", "spans", "reviewer", "decision"}
            or a["row_id"] not in byid
            or a["row_id"] in seen
            or a["decision"] not in ("approved", "rejected")
            or not isinstance(a["reviewer"], str)
            or not 1 <= len(a["reviewer"]) <= 100
            or a["label"] is not None
            and a["label"] not in extra.document_labels
            or not isinstance(a["spans"], list)
            or len(a["spans"]) > 100
        ):
            raise ProjectError("Annotation schema/RowId/reviewer/decision geçersiz.")
        seen.add(a["row_id"])
        text = byid[a["row_id"]]
        for span in a["spans"]:
            if (
                not isinstance(span, dict)
                or set(span) != {"start", "end", "label"}
                or span["label"] not in extra.entity_labels
                or type(span["start"]) is not int
                or type(span["end"]) is not int
                or not 0 <= span["start"] < span["end"] <= len(text)
            ):
                raise ProjectError(
                    "Annotation offset original Unicode codepoint exclusive end olmalı."
                )
    return values


def embedding(text, model, base):
    tokens = Analyzer(base).tokens(text)
    vectors = [model["vectors"][t] for t in tokens if t in model["vectors"]]
    n = len(next(iter(model["vectors"].values()), []))
    v = np.mean(vectors, axis=0) if vectors else np.zeros(n)
    norm = np.linalg.norm(v)
    v = v / norm if norm > 0 else v
    return v, dict(
        token_count=len(tokens),
        known_token_count=len(vectors),
        oov_token_count=len(tokens) - len(vectors),
        pooling="mean static word vectors, L2 normalize; order/context/negation lost",
    )


def entities(text, model, extra):
    output = []
    for rule in model["entities"]:
        if rule["label"] not in extra.entity_labels:
            raise ProjectError("Model NER labels seçili entity schema dışında.")
        start = 0
        while True:
            i = text.find(rule["phrase"], start)
            if i < 0:
                break
            end = i + len(rule["phrase"])
            start = end
            if (i and text[i - 1].isalnum()) or (
                end < len(text) and text[end].isalnum()
            ):
                continue
            output.append(
                dict(
                    start=i,
                    end=end,
                    utf16_start=utf16_offset(text, i),
                    utf16_end=utf16_offset(text, end),
                    label=rule["label"],
                    source="model_suggestion",
                    ground_truth=False,
                    matching="exact case-sensitive literal on unnormalized original",
                    text_hash=digest(text.encode()),
                )
            )
            if len(output) > 200:
                raise ProjectError("NER200 span/document sınırı.")
    return sorted(output, key=lambda x: (x["start"], x["end"], x["label"]))


def local_predictions(vectors, ids, model, extra):
    c = model["classifier"]
    if not c:
        raise ProjectError(
            "Yerel bundle classifier ağırlığı yok; sentiment/classification üretilemez."
        )
    if not set(c["labels"]) <= set(extra.document_labels):
        raise ProjectError("Model class mapping label schema dışında.")
    logits = np.asarray(vectors) @ np.asarray(c["coefficient"]).T + np.asarray(
        c["intercept"]
    )
    logits -= logits.max(axis=1, keepdims=True)
    p = np.exp(logits)
    p /= p.sum(axis=1, keepdims=True)
    return [
        dict(
            row_id=i,
            label=c["labels"][int(np.argmax(v))],
            scores=v.tolist(),
            label_order=c["labels"],
            score_kind="uncalibrated linear softmax, not demonstrated probability reliability",
            source="model_suggestion",
            ground_truth=False,
        )
        for i, v in zip(ids, p)
    ]


def retrieval(rank, relevance, k):
    if not relevance:
        return None
    if not all(x["row_id"] in relevance for x in rank):
        raise ProjectError(
            "Retrieval evaluation ranked tüm corpus için gerçek relevance judgment ister; unjudged negatif sayılmaz."
        )
    judged = [relevance[x["row_id"]] for x in rank]
    limit = min(k, len(relevance))
    rel = sum(x > 0 for x in relevance.values())
    if not rel:
        raise ProjectError("Relevance positives yok; başarı/recall uydurulmaz.")
    dcg = sum((2**v - 1) / np.log2(i + 2) for i, v in enumerate(judged[:limit]))
    ideal = sorted(relevance.values(), reverse=True)[:limit]
    idcg = sum((2**v - 1) / np.log2(i + 2) for i, v in enumerate(ideal))
    return dict(
        k=limit,
        precision=sum(x > 0 for x in judged[:limit]) / limit,
        recall=sum(x > 0 for x in judged[:limit]) / rel,
        ndcg=float(dcg / idcg),
        judged_n=len(relevance),
        scope="complete non-test corpus human query judgments including zero-vector documents; no guarantee for other queries",
    )


def source(frame, columns, base, extra):
    col = next((c for c in columns if c["id"] == base.column), None)
    if not col or frame[col["name"]].dtype != pl.String or frame.height > 500:
        raise ProjectError(
            "NLP String column/500 row bütçesi; missing rows otomatik atılmaz."
        )
    raw = frame[col["name"]].to_list()
    ids = frame["__vu_row_id"].to_list()
    if (
        len(set(ids)) != len(ids)
        or any(not isinstance(t, str) or len(t) > 5000 for t in raw)
        or sum(map(len, raw)) > 500000
    ):
        raise ProjectError(
            "NLP unique RowId, sonlu5000 chars/doc ve500000 total chars."
        )
    parts = extra.partitions or {i: "train" for i in ids}
    if set(parts) != set(ids):
        raise ProjectError(
            "Split tüm kaynak RowIdlerini tam train/validation/test olarak kapsamalı."
        )
    seen = {}
    for i, text in zip(ids, raw):
        h = digest(text.encode())
        if text.strip() and h in seen and seen[h] != parts[i]:
            raise ProjectError(
                "Aynı kaynak metin farklı splitlerde; duplicate leakage reddedildi."
            )
        seen[h] = parts[i]
    annotations(extra.annotations, raw, ids, extra)
    return raw, ids, parts


def calculate(request, base, workspace, control=None):
    from veri_ufku.storage.experiment_store import capture

    control = control or Control()
    started = time.monotonic()
    extra = NLPSpec.from_dict(base.advanced)
    if base.preview and request["row_count"] > 500:
        raise ProjectError("NLP500 rows bütçesi.")
    checked(request, control)
    access = datetime.now(UTC).isoformat()
    frame = pl.read_parquet(request["path"])
    raw, ids, parts = source(frame, request["columns"], base, extra)
    if any(parts.get(i) != "test" for i in request.get("protected_test_row_ids", [])):
        raise ProjectError("Önceden ayrılmış test RowId training/active pool olamaz.")
    if frame.height != request["row_count"]:
        raise ProjectError("NLP source row count uyuşmuyor.")
    permitted = [j for j, i in enumerate(ids) if parts[i] != "test"]
    train = [j for j, i in enumerate(ids) if parts[i] == "train"]
    if not permitted or not train:
        raise ProjectError("Training pool yok; test training/exploration için açılmaz.")
    model = None
    meta = None
    status = "completed"
    notes = []
    topics = []
    scores = []
    vocabulary = []
    embedded = []
    ner = []
    predictions = []
    rank = []
    metrics = None
    active = []
    fitted = None
    if extra.operation in (
        "model",
        "embeddings",
        "search",
        "ner",
        "sentiment",
        "retrieval",
    ):
        if not extra.model_folder:
            status = "unavailable"
            notes.append(
                "Model yok. Yerel model.json seçin veya explicit HTTPS download isteği başlatın. Transformer/spaCy/ONNX desteklenmiyor; kalite garanti edilmez."
            )
        else:
            model, meta = inspect(extra.model_folder)
            if base.language not in model["languages"]:
                raise ProjectError(
                    "Yanlış model dili: seçilen dil model beyanında yok. Türkçe destek/kalite varsayılmaz."
                )
            notes.append(meta["backend"])
            notes.append(meta["quality"])
    op = extra.operation
    if op in ("tfidf", "nmf", "lda", "classification", "active-learning"):
        labels = {
            a["row_id"]: a["label"]
            for a in extra.annotations
            if a["decision"] == "approved" and a["label"] is not None
        }
        fit = (
            train
            if op in ("tfidf", "nmf", "lda")
            else [j for j in train if ids[j] in labels]
        )
        if not fit:
            raise ProjectError(
                "Training approved human labels/token pool yok; pretrained suggestion ground truth olamaz."
            )
        vec, m, _, _ = vectorize([raw[j] for j in fit], base, control)
        if m is None:
            raise ProjectError(
                "Training token/vocabulary yok; topic/model oluşturulmadı."
            )
        vocabulary = vec.get_feature_names_out().tolist()
        allm = vec.transform([raw[j] for j in permitted])
        control.check()
        fitted = dict(
            fit_row_ids=[ids[j] for j in fit],
            vocabulary=vocabulary,
            idf=vec.idf_.tolist(),
            fit_scope="training corpus only; held test not read for fitting or labeling suggestions",
        )
        if op in ("nmf", "lda"):
            if extra.topics > min(m.shape):
                raise ProjectError("Topic count training n/vocabulary sınırını aşar.")
            if op == "lda":
                counter = CountVectorizer(
                    analyzer=Analyzer(base), vocabulary=vec.vocabulary_, lowercase=False
                )
                m = counter.transform([raw[j] for j in fit])
                allm = counter.transform([raw[j] for j in permitted])
                est = LatentDirichletAllocation(
                    n_components=extra.topics,
                    learning_method="batch",
                    max_iter=30,
                    random_state=extra.seed,
                    n_jobs=1,
                )
            else:
                est = NMF(
                    n_components=extra.topics,
                    init="nndsvda",
                    max_iter=400,
                    tol=1e-3,
                    random_state=extra.seed,
                )
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                est.fit(m)
                weights = est.transform(allm)
            if any(issubclass(w.category, ConvergenceWarning) for w in caught):
                raise ProjectError(
                    "Topic optimizer yakınsamadı; ready/güvenilir rozeti yok."
                )
            notes.extend(str(w.message) for w in caught)
            topics = [
                dict(
                    topic=i,
                    terms=[vocabulary[j] for j in np.argsort(row)[::-1][:10]],
                    weights=[float(row[j]) for j in np.argsort(row)[::-1][:10]],
                    name=None,
                    name_source="human naming pending",
                )
                for i, row in enumerate(est.components_)
            ]
            scores = [
                dict(
                    row_id=ids[j],
                    weights=w.tolist(),
                    meaning="LDA conditional topic mixture"
                    if op == "lda"
                    else "NMF nonnegative activation, not class probability",
                )
                for j, w in zip(permitted, weights)
            ]
            fitted.update(
                backend="LDA raw counts" if op == "lda" else "NMF TF-IDF",
                components=est.components_.tolist(),
                iterations=int(est.n_iter_),
            )
        elif op in ("classification", "active-learning"):
            y = [labels[ids[j]] for j in fit]
            if len(set(y)) < 2:
                raise ProjectError("Training human labels en az2 sınıf gerekli.")
            est = LogisticRegression(max_iter=500, random_state=extra.seed)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                est.fit(m, y)
            if any(issubclass(w.category, ConvergenceWarning) for w in caught):
                raise ProjectError("Text classifier convergence başarısız.")
            proba = est.predict_proba(allm)
            pred = est.predict(allm)
            predictions = [
                dict(
                    row_id=ids[j],
                    label=str(v),
                    scores=p.tolist(),
                    label_order=est.classes_.tolist(),
                    score_kind="uncalibrated LogisticRegression softmax",
                    ground_truth=False,
                    source="model_suggestion",
                )
                for j, v, p in zip(permitted, pred, proba)
            ]
            valid = [
                x
                for x in predictions
                if parts[x["row_id"]] == "validation" and x["row_id"] in labels
            ]
            if any(labels[x["row_id"]] not in est.classes_ for x in valid):
                raise ProjectError("Validation unseen class.")
            if valid:
                metrics = dict(
                    n=len(valid),
                    accuracy=sum(x["label"] == labels[x["row_id"]] for x in valid)
                    / len(valid),
                    scope="validation human labels only; final test closed",
                    baseline_accuracy=sum(
                        labels[x["row_id"]] == max(sorted(set(y)), key=y.count)
                        for x in valid
                    )
                    / len(valid),
                )
            active = [
                dict(
                    row_id=x["row_id"],
                    uncertainty=float(1 - max(x["scores"])),
                    meaning="uncalibrated least-confidence training-pool suggestion",
                    ground_truth=False,
                )
                for x in predictions
                if parts[x["row_id"]] == "train" and x["row_id"] not in labels
            ]
            active = sorted(active, key=lambda x: (-x["uncertainty"], x["row_id"]))[
                : extra.top_k
            ]
            fitted.update(
                coefficient=est.coef_.tolist(),
                intercept=est.intercept_.tolist(),
                classes=est.classes_.tolist(),
            )
    if model is not None:
        if op in ("embeddings", "search", "retrieval", "sentiment"):
            if not model["vectors"]:
                raise ProjectError("Embedding vector weights yok.")
            embedded = [
                dict(row_id=ids[j], vector=v.tolist(), coverage=c)
                for j in permitted
                for v, c in [embedding(raw[j], model, base)]
            ]
        if op == "ner":
            ner = [
                dict(row_id=ids[j], spans=entities(raw[j], model, extra))
                for j in permitted
            ]
        if op == "sentiment":
            predictions = local_predictions(
                [x["vector"] for x in embedded],
                [x["row_id"] for x in embedded],
                model,
                extra,
            )
        if op in ("search", "retrieval"):
            q, coverage = embedding(extra.query, model, base)
            if not np.linalg.norm(q):
                raise ProjectError(
                    "Query model vocabulary dışında/boş; semantic score uydurulmaz."
                )
            rank = [
                dict(
                    row_id=x["row_id"],
                    cosine=float(np.clip(q @ np.array(x["vector"]), -1, 1)),
                    meaning="static embedding cosine, not calibrated probability",
                    coverage=x["coverage"],
                )
                for x in embedded
                if np.linalg.norm(x["vector"])
            ]
            rank = sorted(rank, key=lambda x: (-x["cosine"], x["row_id"]))
            if extra.relevance:
                if set(extra.relevance) != {ids[j] for j in permitted}:
                    raise ProjectError(
                        "Relevance tüm non-test corpus için query-specific insan judgment ister; OOV/zero-vector belgeler dahil."
                    )
                metrics = retrieval(rank, extra.relevance, extra.top_k)
    checked(request, control)
    control.check()
    created = datetime.now(UTC).isoformat()
    cap = "text.nlp." + op
    prov = asdict(
        Provenance(
            provenance_id="provenance:" + uid(),
            dataset_versions=(request["version_id"],),
            config_revision=0,
            capability_id=cap,
            parameters_hash=digest(encode(base.data())),
            environment=(("sklearn", importlib.metadata.version("scikit-learn")),),
            created_at=created,
            scope="original-source codepoint offsets; training-only fit and unlabeled suggestions; test excluded",
            seed=extra.seed,
            seed_reason="seeded topic initialization; deterministic fixed classifier",
            source_snapshot_ids=(request["source_snapshot_id"],),
        )
    )
    previews = (
        [
            dict(row_id=ids[j], before=raw[j][:200], normalized=raw[j][:200], tokens=[])
            for j in permitted[:5]
        ]
        if base.preview
        else []
    )
    captured = capture(
        dict(spec=base.data(), model_sha256=meta["sha256"] if meta else None)
    )
    captured["config_scope"] = (
        "full TextSpec/NLPSpec/partitions/human annotations plus runtime model SHA256"
    )
    return dict(
        schema="TextRun/v1",
        run_id="text:" + uid(),
        status=status,
        dataset_version=request["version_id"],
        snapshot_fingerprint=request["fingerprint"],
        source_snapshot_id=request["source_snapshot_id"],
        created_at=created,
        data_access_at=access,
        elapsed_seconds=time.monotonic() - started,
        seed=extra.seed,
        spec=base.data(),
        rows=len(raw),
        previews=previews,
        frequencies=[],
        tfidf=[],
        similarities=[],
        retained_vocab=len(vocabulary),
        candidate_vocab=len(vocabulary),
        warning="Model predictions are suggestions, never ground truth. Model language/license/training assumptions are author declarations. Cosine/softmax not calibrated reliability. Test excluded; no pretrained quality badge.",
        experiment_capture=captured,
        advanced=dict(
            schema="NLPRun/v1",
            status=status,
            operation=op,
            provenance=json.loads(encode(prov)),
            model_meta=meta,
            model_bundle=model,
            source_documents=[
                dict(
                    row_id=i,
                    sha256=digest(t.encode()),
                    codepoints=len(t),
                    utf16_units=utf16_offset(t, len(t)),
                    partition=parts[i],
                )
                for i, t in zip(ids, raw)
            ],
            partitions=parts,
            test_withheld=sum(v == "test" for v in parts.values()),
            topics=topics,
            topic_scores=scores,
            embeddings=embedded,
            entities=ner,
            predictions=predictions,
            search_results=rank[: extra.top_k],
            retrieval_corpus_rank=rank,
            excluded_zero_vector_row_ids=[
                x["row_id"] for x in embedded if not np.linalg.norm(x["vector"])
            ],
            metrics=metrics,
            active_learning=active,
            fit=fitted,
            annotations=extra.annotations,
            revision_id="annotation:" + uid(),
            revisions=[],
            notes=notes,
            compute_budget=asdict(control.budget),
        ),
    )


def validate(value, dataset):
    from veri_ufku.analytics.text_contracts import TextSpec
    from veri_ufku.domain.capabilities import CAPABILITIES

    try:
        base = TextSpec.from_dict(value["spec"])
        extra = NLPSpec.from_dict(base.advanced)
        a = value["advanced"]
        p = a["provenance"]
        if (
            value["schema"] != "TextRun/v1"
            or a["schema"] != "NLPRun/v1"
            or value["dataset_version"] != dataset["version_id"]
            or value["rows"] != dataset["import_metadata"]["row_count"]
            or base.column
            not in {x["id"] for x in dataset["import_metadata"]["columns"]}
            or p["capability_id"] != "text.nlp." + extra.operation
            or p["capability_id"] not in CAPABILITIES
            or p["parameters_hash"] != digest(encode(base.data()))
        ):
            raise ValueError
        if not a.get("details_uri"):
            docs = a["source_documents"]
            parts = a["partitions"]
            ids = {x["row_id"] for x in docs}
            if len(ids) != len(docs) or len(docs) != value["rows"] or set(parts) != ids:
                raise ValueError
            if (
                a["model_bundle"] is not None
                and digest(encode(parse(encode(a["model_bundle"]))))
                != a["model_meta"]["canonical_hash"]
            ):
                raise ValueError
            if any(parts[x["row_id"]] != "train" for x in a["active_learning"]) or any(
                parts[i] != "train" for i in (a["fit"] or {}).get("fit_row_ids", [])
            ):
                raise ValueError
            if any(
                parts[x["row_id"]] == "test"
                for key in [
                    "entities",
                    "predictions",
                    "topic_scores",
                    "embeddings",
                    "search_results",
                ]
                for x in a[key]
            ):
                raise ValueError
        encode(value)
    except (KeyError, ValueError, TypeError) as error:
        raise ProjectError("NLP archive/schema/provenance/split geçersiz.") from error


def validate_source(value, frame, columns):
    from veri_ufku.analytics.text_contracts import TextSpec

    base = TextSpec.from_dict(value["spec"])
    extra = NLPSpec.from_dict(base.advanced)
    raw, ids, parts = source(frame, columns, base, extra)
    a = value["advanced"]
    expected = [
        dict(
            row_id=i,
            sha256=digest(t.encode()),
            codepoints=len(t),
            utf16_units=utf16_offset(t, len(t)),
            partition=parts[i],
        )
        for i, t in zip(ids, raw)
    ]
    if expected != a["source_documents"] or parts != a["partitions"]:
        raise ProjectError("NLP original text/RowId/offset/split hash uyuşmuyor.")
    annotations(a["annotations"], raw, ids, extra)
    if a["model_bundle"] and a["entities"]:
        expected = [
            dict(row_id=i, spans=entities(t, a["model_bundle"], extra))
            for i, t in zip(ids, raw)
            if parts[i] != "test"
        ]
        if expected != a["entities"]:
            raise ProjectError("NER original Unicode offset eşlemesi uyuşmuyor.")
