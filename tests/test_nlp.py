"""Topics, Turkish offsets, real offline safe bundles and human/pool isolation."""

import copy
import hashlib
import json
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from threading import Event

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.analytics.nlp import (
    embedding,
    entities,
    retrieval,
    utf16_offset,
    validate_source,
)
from veri_ufku.analytics.nlp_contracts import METHODS, NLPSpec
from veri_ufku.analytics.nlp_models import download, inspect, parse
from veri_ufku.analytics.text import TextSpec, calculate, validate_run
from veri_ufku.importers.delimited import Canceled, Control
from veri_ufku.storage.project_model import ProjectError, validate_state
from veri_ufku.storage.text_store import export_annotations, load, publish, revise


def bundle(folder, language="tr"):
    m = dict(
        schema="LocalNLPBundle/v1",
        name="CC0 synthetic fixture, not production quality",
        languages=[language],
        license="CC0-1.0",
        training_dataset="Hand authored synthetic vector/gazetteer reference; not benchmark trained",
        dataset_license="CC0-1.0",
        assumptions="Turkish NFC lower tokens, exact original case-sensitive gazetteer, linear scores; order/negation/context lost",
        vectors={
            "güzel": [1, 0],
            "iyi": [1, 0],
            "mükemmel": [1, 0],
            "kötü": [0, 1],
            "berbat": [0, 1],
            "elma": [1, 1],
        },
        entities=[
            dict(phrase="İstanbul", label="LOC"),
            dict(phrase="Şule", label="PER"),
            dict(phrase="I\u0307pek", label="PER"),
        ],
        classifier=dict(
            labels=["negative", "positive"],
            coefficient=[[0, 2], [2, 0]],
            intercept=[0, 0],
        ),
    )
    folder.mkdir(exist_ok=True)
    raw = json.dumps(m, ensure_ascii=False).encode()
    (folder / "model.json").write_bytes(raw)
    return m


def fixture(tmp_path, op="nmf", language="tr"):
    texts = [
        "güzel iyi elma",
        "mükemmel güzel armut",
        "kötü berbat bozuk",
        "berbat kötü çürük",
        "güzel ürün farklı",
        "kötü ürün başka",
        "iyi yeni başka",
        "TESTLABEL_GİZLİ geleceği görme",
        "İstanbul 👩‍💻 Şule ve I\u0307pek geldi",
    ]
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(text=texts)))
    frame = pl.read_parquet(r["path"])
    ids = frame["__vu_row_id"].to_list()
    parts = {
        i: ("test" if j == 7 else "validation" if j in (4, 5) else "train")
        for j, i in enumerate(ids)
    }
    anns = [
        dict(
            row_id=ids[j],
            label="positive" if j in (0, 1, 4) else "negative",
            spans=[],
            reviewer="human-fixture",
            decision="approved",
        )
        for j in (0, 1, 2, 3, 4, 5)
    ]
    folder = tmp_path / "local-model"
    bundle(folder, language)
    ex = NLPSpec(
        operation=op,
        model_folder=str(folder),
        query="mükemmel",
        partitions=parts,
        annotations=anns,
    )
    base = TextSpec(column(r, "text"), advanced=ex.data(), max_features=100)
    return store, r, work, base, ex, ids, texts


@pytest.mark.parametrize("op", METHODS)
def test_real_adapter_atomic_store_offline_reopen_source_protected(tmp_path, op):
    store, r, work, base, ex, ids, texts = fixture(tmp_path, op)
    with closing(store):
        if op == "retrieval":
            # Zero-vector documents are not retrieved, never silently treated as judged negatives.
            model, _ = inspect(ex.model_folder)
            ranked = {
                ids[j]: int(j in (0, 1, 4, 6))
                for j, t in enumerate(texts)
                if ex.partitions[ids[j]] != "test"
            }
            base = replace(base, advanced=replace(ex, relevance=ranked).data())
        original = Path(r["path"]).read_bytes()
        v = calculate(r, base.data(), work)
        assert v["status"] == "completed"
        validate_run(v, store.state["datasets"][-1])
        validate_source(v, pl.read_parquet(r["path"]), r["columns"])
        state, item = publish(store, store.state, v)
        validate_state(state)
        from veri_ufku.storage.experiment_store import rows

        assert v["run_id"] in {x["run_id"] for x in rows(store, state)}
        Path(
            ex.model_folder, "model.json"
        ).unlink()  # opening saved snapshots must not refetch/external-load
        assert load(store, item)["advanced"] == v["advanced"]
        assert (
            Path(r["path"]).read_bytes() == original
            and not item["text_analysis"]["previews"]
        )
        a = v["advanced"]
        assert all(
            x["row_id"] != ids[7]
            for key in [
                "entities",
                "topic_scores",
                "predictions",
                "embeddings",
                "active_learning",
            ]
            for x in a[key]
        )
        if op == "retrieval":
            assert a["metrics"]["ndcg"] <= 1 and a["metrics"]["judged_n"] == len(ranked)
        if op in ("nmf", "lda"):
            assert all(t["name"] is None for t in a["topics"]) and {
                "testlabel",
                "gizli",
                "geleceği",
            }.isdisjoint(a["fit"]["vocabulary"])
        if op == "classification":
            assert a["metrics"]["n"] == 2


def test_turkish_original_unicode_codepoints_utf16_emoji_combining():
    raw = "İstanbul 👩‍💻 Şule ve I\u0307pek geldi"
    model = dict(
        entities=[
            dict(phrase="İstanbul", label="LOC"),
            dict(phrase="Şule", label="PER"),
            dict(phrase="I\u0307pek", label="PER"),
        ]
    )
    spans = entities(raw, model, NLPSpec())
    assert [raw[s["start"] : s["end"]] for s in spans] == [
        "İstanbul",
        "Şule",
        "I\u0307pek",
    ]
    for s in spans:
        assert (
            raw.encode("utf-16-le")[s["utf16_start"] * 2 : s["utf16_end"] * 2].decode(
                "utf-16-le"
            )
            == raw[s["start"] : s["end"]]
        )
        assert not s["ground_truth"]
    assert utf16_offset(raw, raw.index("Şule")) > raw.index("Şule")


def test_wrong_model_language_missing_model_safe_weights_and_hash(tmp_path):
    store, r, work, base, ex, ids, _ = fixture(tmp_path, "ner", language="en")
    with closing(store):
        with pytest.raises(ProjectError, match="model dili"):
            calculate(r, base.data(), work)
        none = calculate(
            r, replace(base, advanced=replace(ex, model_folder="").data()).data(), work
        )
        assert (
            none["status"] == "unavailable"
            and none["advanced"]["notes"]
            and not none["advanced"]["entities"]
        )
        for bad in [b"{}", b'{"schema":"pickle"}', b'{"x":NaN}', b'{"x":1,"x":2}']:
            with pytest.raises(ProjectError):
                parse(bad)
        _, meta = inspect(ex.model_folder)
        assert meta["bytes"] == Path(ex.model_folder, "model.json").stat().st_size
        assert (
            meta["sha256"]
            == hashlib.sha256(
                Path(ex.model_folder, "model.json").read_bytes()
            ).hexdigest()
        )
        assert meta["dataset_license"] == "CC0-1.0"


def test_embedding_cosine_reference_oov_and_relevance_required(tmp_path):
    m = bundle(tmp_path / "model")
    base = TextSpec("col:x")
    a, c = embedding("güzel iyi unknown", m, base)
    b, _ = embedding("mükemmel", m, base)
    assert a @ b == pytest.approx(1) and c["oov_token_count"] == 1
    assert retrieval([dict(row_id="a")], {}, 1) is None
    assert retrieval([dict(row_id="a"), dict(row_id="b")], {"a": 1, "b": 0}, 1) == dict(
        k=1,
        precision=1,
        recall=1,
        ndcg=1.0,
        judged_n=2,
        scope="complete non-test corpus human query judgments including zero-vector documents; no guarantee for other queries",
    )
    with pytest.raises(ProjectError):
        retrieval([dict(row_id="a")], {"b": 1}, 1)


def test_training_pool_test_label_poison_and_train_only_vocabulary(tmp_path):
    store, r, work, base, ex, ids, _ = fixture(tmp_path, "active-learning")
    with closing(store):
        a = calculate(r, base.data(), work)
        test = dict(
            row_id=ids[7],
            label="positive",
            spans=[],
            reviewer="test-label",
            decision="approved",
        )
        b = calculate(
            r,
            replace(
                base, advanced=replace(ex, annotations=ex.annotations + [test]).data()
            ).data(),
            work,
        )
        assert a["advanced"]["fit"] == b["advanced"]["fit"]
        assert a["advanced"]["active_learning"] == b["advanced"]["active_learning"]
        assert {x["row_id"] for x in a["advanced"]["active_learning"]} <= {
            i for i, p in ex.partitions.items() if p == "train"
        } - {x["row_id"] for x in ex.annotations}
        assert {"testlabel", "gizli", "geleceği"}.isdisjoint(
            a["advanced"]["fit"]["vocabulary"]
        )


def test_human_topic_annotation_revision_undo_provenance_export_no_raw(tmp_path):
    store, r, work, base, ex, ids, texts = fixture(tmp_path, "nmf")
    with closing(store):
        v = calculate(r, base.data(), work)
        state, item = publish(store, store.state, v)
        ann = dict(
            row_id=ids[8],
            label=None,
            spans=[dict(start=0, end=8, label="LOC")],
            reviewer="expert-human",
            decision="approved",
        )
        state, new = revise(
            store,
            state,
            item["id"],
            dict(
                topic_names={"0": "İnsan konu adı"}, annotations=ex.annotations + [ann]
            ),
            "expert-human",
            v["advanced"]["revision_id"],
        )
        revised = load(store, new)
        assert (
            revised["derived_from_run_id"] == v["run_id"]
            and revised["advanced"]["topics"][0]["name"] == "İnsan konu adı"
        )
        assert (
            revised["advanced"]["metrics"] is None
            and revised["advanced"]["revisions"][0]["previous_annotations"]
            == ex.annotations
        )
        with pytest.raises(ProjectError):
            revise(store, state, new["id"], {}, "human", v["advanced"]["revision_id"])
        target = tmp_path / "labels.json"
        export_annotations(store, new, target)
        data = json.loads(target.read_text())
        assert not data["raw_text_included"] and all(
            "text" not in x for x in data["annotations"]
        )
        assert (
            "TESTLABEL_GİZLİ" not in target.read_text()
            and data["annotations"][-1]["spans"][0]["end"] == 8
        )
        state, undo = revise(
            store,
            state,
            new["id"],
            dict(annotations=ex.annotations),
            "human-undo",
            revised["advanced"]["revision_id"],
        )
        assert (
            load(store, undo)["advanced"]["annotations"] == ex.annotations
            and len(state["results"]) == 3
        )


def test_source_tamper_and_invalid_offsets_cancel_download_cache(tmp_path):
    store, r, work, base, ex, ids, texts = fixture(tmp_path, "ner")
    with closing(store):
        v = calculate(r, base.data(), work)
        bad = copy.deepcopy(v)
        bad["advanced"]["entities"][-1]["spans"][0]["start"] += 1
        with pytest.raises(ProjectError):
            validate_source(bad, pl.read_parquet(r["path"]), r["columns"])
        ev = Event()
        ev.set()
        with pytest.raises(Canceled):
            calculate(r, base.data(), work, Control(ev))
        for u in [
            "http://example.test/model",
            "https://u:p@example.test/model",
            "https://example.test/model?token=abc",
        ]:
            with pytest.raises(ProjectError):
                download(u, "a" * 64, 100, tmp_path)
        model = Path(ex.model_folder, "model.json").read_bytes()
        h = hashlib.sha256(model).hexdigest()
        cached = tmp_path / "nlp-models" / h
        cached.mkdir(parents=True)
        (cached / "model.json").write_bytes(model)
        assert download("https://example.test/model", h, len(model), tmp_path) == str(
            cached
        )
        (cached / "model.json").write_bytes(b"{}")
        with pytest.raises(ProjectError):
            download("https://example.test/model", h, len(model), tmp_path)


def test_real_https_download_verified_cache_size_hash_and_cancel(tmp_path, monkeypatch):
    import http.server
    import ssl
    import subprocess
    import threading
    from functools import partial

    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    folder = tmp_path / "https-model"
    bundle(folder)
    raw = (folder / "model.json").read_bytes()
    h = hashlib.sha256(raw).hexdigest()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Handler, directory=str(folder))
    )
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("SSL_CERT_FILE", str(cert))
    url = f"https://localhost:{server.server_port}/model.json"
    try:
        target = download(url, h, len(raw), tmp_path / "cache")
        assert Path(target, "model.json").read_bytes() == raw
        with pytest.raises(ProjectError):
            download(url, "a" * 64, len(raw), tmp_path / "bad")
        with pytest.raises(ProjectError):
            download(url, h, len(raw) + 1, tmp_path / "bad-size")
        ev = Event()
        ev.set()
        with pytest.raises(Canceled):
            download(url, h, len(raw), tmp_path / "cancel", Control(ev))
        assert not list((tmp_path / "cancel").glob("**/model.json"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_saved_test_membership_cannot_be_reset_for_new_active_pool(tmp_path):
    store, r, work, base, ex, ids, _ = fixture(tmp_path, "active-learning")
    with closing(store):
        v = calculate(r, base.data(), work)
        state, item = publish(store, store.state, v)
        assert item["text_analysis"]["advanced"]["protected_test_row_ids"] == [ids[7]]
        parts = dict(ex.partitions)
        parts[ids[7]] = "train"
        spec = replace(base, advanced=replace(ex, partitions=parts).data())
        with pytest.raises(ProjectError):
            calculate(dict(r, protected_test_row_ids=[ids[7]]), spec.data(), work)
        # Atomic publication also rejects callers that omitted the scheduling guard.
        candidate = calculate(r, spec.data(), work)
        with pytest.raises(ProjectError):
            publish(store, state, candidate)
        assert len(store.state["results"]) == 1


def test_unretrievable_relevant_document_stays_in_recall_denominator():
    result = retrieval([dict(row_id="known")], {"known": 1, "zero-vector": 1}, 2)
    assert result["precision"] == 0.5 and result["recall"] == 0.5 and result["ndcg"] < 1
