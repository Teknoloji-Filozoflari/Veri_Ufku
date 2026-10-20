"""Independent Turkish/Unicode/count/IDF references and training-only vocab proof."""

import copy
import json
import math
from contextlib import closing
from dataclasses import replace

import polars as pl
import pytest
from test_dataset import column, prepare
from test_preparation import request

from veri_ufku.analytics.text import (
    Analyzer,
    TextPreparation,
    TextSpec,
    calculate,
    normalize,
    vectorize,
)
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.baseline import calculate as evaluate
from veri_ufku.modeling.classification import settings
from veri_ufku.modeling.contracts import PreparationSpec
from veri_ufku.modeling.preparation import calculate as preparation
from veri_ufku.modeling.validation import ValidationSpec
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.text_store import load, publish


def test_turkish_dotted_dotless_unicode_and_language_choices():
    tr = TextSpec("col:any")
    assert Analyzer(tr)("I İ ı i IŞIK İSTANBUL") == [
        "ı",
        "i",
        "ı",
        "i",
        "ışık",
        "istanbul",
    ]
    assert Analyzer(tr)("I\u0307STANBUL c\u0327 ç c") == ["istanbul", "ç", "ç", "c"]
    assert Analyzer(replace(tr, language="en"))("I İ ı i") == ["i", "i\u0307", "ı", "i"]
    assert Analyzer(replace(tr, lowercase=False))("I İ") == ["I", "İ"]
    assert normalize("Ａ ﬁ", replace(tr, normalization="NFKC")) == "a fi"
    assert (
        normalize("Ａ ﬁ", tr) == "ａ fi"
    )  # casefold itself expands ligature; no accent stripping
    assert Analyzer(tr)("Çağrı—ŞİŞE 😊 42") == ["çağrı", "şişe", "42"]
    assert Analyzer(replace(tr, numbers=False))("a42 b 9") == ["a", "b"]


def test_stopwords_ngram_and_manual_tfidf_reference():
    s = TextSpec("col:x", stopwords="tr", ngram_max=2)
    assert Analyzer(s)("IŞIK ve İSTANBUL") == ["ışık", "istanbul", "ışık istanbul"]
    assert Analyzer(replace(s, custom_stopwords="İSTANBUL"))("ışık ve istanbul") == [
        "ışık"
    ]
    v, m, counts, df = vectorize(["elma elma armut", "armut", ""], TextSpec("col:x"))
    assert counts == {"elma": 2, "armut": 2} and df == {"elma": 1, "armut": 2}
    idf_elma = 1 + math.log(4 / 2)
    idf_armut = 1 + math.log(4 / 3)
    assert v.idf_[v.vocabulary_["elma"]] == pytest.approx(idf_elma)
    norm = math.sqrt((2 * idf_elma) ** 2 + idf_armut**2)
    assert m[0, v.vocabulary_["elma"]] == pytest.approx(2 * idf_elma / norm)
    assert m[2].nnz == 0


@pytest.mark.parametrize("values", [[None, None], ["", " \t"], ["ve", "ile"]])
def test_empty_columns_and_stopword_only_are_defined(tmp_path, values):
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(text=values)))
    with closing(store):
        result = calculate(r, TextSpec(column(r, "text"), stopwords="tr").data(), work)
        assert result["retained_vocab"] == 0 and not result["tfidf"]
        assert result["empty_after"] == 2


def test_real_counts_preview_not_persisted_similarity_and_source_unchanged(
    tmp_path, caplog
):
    store, r, work = prepare(
        tmp_path, pl.DataFrame(dict(text=["GİZLİ parola987 IŞIK", "IŞIK", None, " "]))
    )
    with closing(store):
        before = open(r["path"], "rb").read()
        spec = TextSpec(column(r, "text"), preview=True, similarity=True)
        result = calculate(r, spec.data(), work)
        assert result["null_text"] == 1 and result["whitespace_text"] == 1
        assert result["previews"][0]["before"].startswith("GİZLİ parola987")
        assert result["similarities"] and 0 < result["similarities"][0]["cosine"] < 1
        state, record = publish(store, store.state, result)
        assert load(store, record)["previews"] == []
        assert "GİZLİ parola987" not in json.dumps(state, ensure_ascii=False)
        assert "parola987" not in caplog.text
        assert open(r["path"], "rb").read() == before


def test_training_vocabulary_and_idf_never_see_evaluation_documents():
    s = TextSpec("col:txt")
    cols = [dict(id="col:txt", name="text")]
    train = pl.DataFrame(
        dict(text=["elma armut", "elma", None], __vu_row_id=["a", "b", "c"])
    )
    held = pl.DataFrame(dict(text=["sadecegelecek elma"], __vu_row_id=["d"]))
    t = TextPreparation(s.data(), cols).fit(train)
    before = copy.deepcopy(t.summary_)
    out = t.transform(held)
    assert out.shape == (1, 2) and t.summary_ == before
    assert "sadecegelecek" not in t.vectorizer_.vocabulary_
    assert t.fit_row_ids_ == ["a", "b", "c"]
    with pytest.raises(ProjectError, match="token yok"):
        TextPreparation(s.data(), cols).fit(
            train.with_columns(pl.lit("").alias("text"))
        )


def test_existing_classification_pipeline_learns_only_each_train_fold(
    tmp_path, monkeypatch
):
    frame = pl.DataFrame(
        dict(
            text=[
                (
                    "ışık sıcak " + f"eşsiz{i}"
                    if i % 2
                    else "yağmur soğuk " + f"eşsiz{i}"
                )
                for i in range(120)
            ],
            label=["sıcak" if i % 2 else "soğuk" for i in range(120)],
        )
    )
    store, _, work = prepare(tmp_path, frame)
    with closing(store):
        r = request(store)
        textcol = column(r, "text")
        p = PreparationSpec(
            "classification",
            (textcol,),
            target=column(r, "label"),
            family="linear",
            source_version=r["version_id"],
            text=TextSpec(textcol).data(),
        )
        report = preparation(r, p, work)
        assert not report["blockers"]
        seen = []
        original = TextPreparation.fit

        def spy(self, X, y=None):
            result = original(self, X, y)
            seen.append(
                (
                    self.fit_row_ids_,
                    copy.deepcopy(self.vectorizer_.vocabulary_),
                    X["text"].to_list(),
                )
            )
            return result

        monkeypatch.setattr(TextPreparation, "fit", spy)
        spec = ValidationSpec(
            prediction_moment="Metin biliniyor",
            availability={textcol: dict(offset_seconds=0, note="Önceden bilinir")},
        )
        output = evaluate(
            dict(
                r,
                preparation=report,
                classification=settings(
                    dict(candidates=["baseline", "logistic"], positive_class="sıcak")
                ),
            ),
            spec.data(),
            work,
        )
        assert output["classification"] and output["model_package_unavailable"]
        test_ids = set(output["plan"]["membership"]["test"])
        assert seen and all(not set(ids) & test_ids for ids, vocab, docs in seen)
        for ids, vocab, docs in seen:
            allowed = set(
                term for doc in docs for term in Analyzer(TextSpec(textcol))(doc)
            )
            assert set(vocab) <= allowed
        assert output["selected_model"] == "logistic"


def test_limits_and_cooperative_cancel_never_echo_contents():
    with pytest.raises(ProjectError) as caught:
        Analyzer(TextSpec("col:x"))("TOPSECRET" * 2000)
    assert "TOPSECRET" not in str(caught.value)
    with pytest.raises(ProjectError, match="50000"):
        vectorize([f"word{i}" for i in range(50001)], TextSpec("col:x"))

    class Cancel:
        def is_set(self):
            return True

    with pytest.raises(Canceled):
        vectorize(["sensitive secret"], TextSpec("col:x"), Control(Cancel()))
