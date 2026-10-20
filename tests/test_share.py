"""Real local containers, source identities, bounded scanners and no-overwrite forks."""

import copy
import io
import json
import zipfile
from contextlib import closing

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.exports.share_bundle import build, compare, open_bundle
from veri_ufku.exports.share_bundle import prepare as preview
from veri_ufku.importers.delimited import Control
from veri_ufku.storage import review_store as storage
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def spec(mode="metadata-only", version=""):
    return dict(mode=mode, version=version, rows=2, keep_numeric=[], sensitive_terms=[])


def bundle(store, s, work, tmp, allow=False):
    req = storage.request_for(store, store.state, dict(action="preview", spec=s))
    p, _ = preview(req, s, work)
    path = tmp / (__import__("uuid").uuid4().hex + ".vushare")
    result = build(req, s, work, path, p["preview_hash"], allow)
    # Fresh scratch per action as in GUI worker.
    (work / "review-share.vushare").unlink()
    return path, p, result


def test_three_modes_identity_restore_lock_and_no_overwrite(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "label": ["A", "B", "C"]})
    )
    with closing(store):
        before = store.commit_id
        s = spec("full-copy")
        path, p, result = bundle(store, s, work, tmp_path)
        assert not p["blocked"]
        opened = open_bundle(path)
        target = tmp_path / "restored"
        receipt = storage.restore(path, target, opened["fingerprint"])
        assert receipt["status"] == "restored-new-fork"
        with closing(ProjectStore.open(target)) as fork:
            assert fork.manifest["project_id"] != store.manifest["project_id"]
            a = store.state["datasets"][0]
            b = fork.state["datasets"][0]
            assert (
                a == b
                and a["import_metadata"]["columns"] == b["import_metadata"]["columns"]
            )
            assert pl.read_parquet(store.path(a["snapshot_uri"])).equals(
                pl.read_parquet(fork.path(b["snapshot_uri"]))
            )
            assert fork.state["sources"][0]["path"].startswith("/unresolved-source/")
            assert (
                fork.state["results"][-1]["review_event"]["origin"]["project_id"]
                == store.manifest["project_id"]
            )
            with closing(ProjectStore.open(target)) as second:
                assert second.read_only
                with pytest.raises(ProjectError):
                    second.save()
        with pytest.raises(ProjectError):
            storage.restore(path, target, opened["fingerprint"])
        for mode in ("metadata-only", "redacted-sample"):
            s = spec(mode, r["version_id"])
            s["keep_numeric"] = [column(r, "x")]
            path, p, _ = bundle(store, s, work, tmp_path)
            v = open_bundle(path)
            assert (
                v["projection"]["origin"]["project_id"] == store.manifest["project_id"]
            )
            if mode == "redacted-sample":
                frame = pl.read_parquet(io.BytesIO(v["payload"]["sample.parquet"]))
                original = pl.read_parquet(r["path"]).head(2)
                assert (
                    frame["__vu_row_id"].to_list() == original["__vu_row_id"].to_list()
                )
                assert (
                    frame["__vu_source_record_id"].to_list()
                    == original["__vu_source_record_id"].to_list()
                )
                assert frame["column-1"].to_list() == [1.0, 2.0]
                assert frame["column-2"].to_list() == ["[redacted]"] * 2
                refs = json.loads(v["payload"]["sample-reference.json"])
                assert [c["id"] for c in refs["columns"]] == [
                    c["id"] for c in r["columns"]
                ]
            else:
                assert set(v["payload"]) == {"projection.json"}
            with pytest.raises(ProjectError):
                storage.restore(path, tmp_path / "not-restorable", v["fingerprint"])
        assert store.commit_id == before


def test_secret_full_block_metadata_redaction_pii_and_changed_preview(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "password": ["password=DO_NOT_SEND", "password=DO_NOT_SEND"],
                "mail": ["a@example.org", "b@example.org"],
            }
        ),
    )
    with closing(store):
        store.state["help_preferences"]["note"] = "token=HIDDEN_VALUE"
        store.save()
        s = spec("full-copy")
        req = storage.request_for(store, store.state, dict(action="preview", spec=s))
        p, _ = preview(req, s, work)
        assert (
            p["blocked"]
            and "DO_NOT_SEND" not in str(p)
            and "HIDDEN_VALUE" not in str(p)
        )
        with pytest.raises(ProjectError):
            build(req, s, work, tmp_path / "bad.vushare", p["preview_hash"], True)
        for mode in ("metadata-only", "redacted-sample"):
            s = spec(mode, r["version_id"])
            path, p, _ = bundle(store, s, work, tmp_path)
            raw = b"".join(open_bundle(path)["payload"].values())
            assert (
                b"DO_NOT_SEND" not in raw
                and b"HIDDEN_VALUE" not in raw
                and b"a@example.org" not in raw
            )
        s = spec()
        req = storage.request_for(store, store.state, dict(action="preview", spec=s))
        p, _ = preview(req, s, work)
        req["state"]["name"] = "changed"
        with pytest.raises(ProjectError, match="Önizleme"):
            build(req, s, work, tmp_path / "changed.vushare", p["preview_hash"])


def test_diff_comments_bound_old_context_and_collision(tmp_path):
    from veri_ufku.analytics.contracts import metadata_version

    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0]}))
    with closing(store):
        left, _, _ = bundle(store, spec(), work, tmp_path)
        a = open_bundle(left)
        bound = storage.subject(
            a["projection"], "dataset:" + r["version_id"], a["fingerprint"]
        )
        state = storage.append_review(
            store,
            store.state,
            bound,
            "Yerel inceleyen",
            "Birim varsayımı gözden geçirildi.",
            dict.fromkeys(storage.CHECKS, True),
            "keep-local",
        )
        event = state["results"][-1]["review_event"]
        saved = copy.deepcopy(event)
        assert (
            storage.binding_status(event, state, store.manifest)
            == "same recorded entity/artifact context"
        )
        d = metadata_version(
            state["datasets"][0], column(r, "x"), "measurement", "m", [], "uzunluk"
        )
        store.state["datasets"].append(d)
        store.save()
        right, _, _ = bundle(store, spec(), work, tmp_path)
        diff = compare(a, open_bundle(right))
        assert any(
            x["id"] == d["version_id"] and x["change"] == "added"
            for x in diff["categories"]["schema"]
        )
        assert diff["categories"]["learning_notes"] and diff["same_origin"]
        assert event == saved and event["subject"]["entity"]["id"] == r["version_id"]
        foreign = copy.deepcopy(a)
        foreign["projection"]["origin"]["project_id"] = "different-origin"
        collision = compare(a, foreign)
        assert collision["categories"]["schema"][0]["identity_collision"]
        # Old review is protected by the existing append-only journal.
        erased = copy.deepcopy(store.state)
        erased["results"] = []
        with pytest.raises(ProjectError):
            storage.append_review(
                store,
                erased,
                bound,
                "Yerel inceleyen",
                "Yeni yorum.",
                dict.fromkeys(storage.CHECKS, False),
            )


def test_real_operation_metric_and_learning_note_diff(tmp_path):
    from veri_ufku.analytics.contracts import ProfileSpec
    from veri_ufku.analytics.dataset import profile
    from veri_ufku.operations.contracts import build as operation
    from veri_ufku.operations.engine import calculate
    from veri_ufku.storage.project_model import uid

    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0]}))
    with closing(store):
        a, _, _ = bundle(store, spec(), work, tmp_path)
        result = calculate(
            r, operation(r, "rename", [column(r, "x")], {"name": "amount"}), work
        )
        store.publish_operation(result)
        value = profile(r, ProfileSpec(column(r, "x"), sample=False), work)
        store.state["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[r["version_id"]],
                seed=None,
                capability_id="dataset.profile",
                profile=value,
            )
        )
        store.state["help_preferences"]["learning-note"] = (
            "Birim ve örnekleme kapsamını kontrol et."
        )
        store.save()
        b, _, _ = bundle(store, spec(), work, tmp_path)
        d = compare(open_bundle(a), open_bundle(b))
        assert all(
            d["categories"][k]
            for k in (
                "schema",
                "operations",
                "params",
                "runs_metrics",
                "learning_notes",
            )
        )
        assert len(d["categories"]["operations"]) == 1
        assert any(v["change"] == "added" for v in d["categories"]["runs_metrics"])


def test_pii_consent_opaque_hash_and_malicious_members(tmp_path):
    from veri_ufku.storage.project_model import uid

    store, r, work = prepare(
        tmp_path, pl.DataFrame({"mail": ["a@example.org", "b@example.org"]})
    )
    with closing(store):
        s = spec("full-copy")
        req = storage.request_for(store, store.state, dict(action="preview", spec=s))
        p, _ = preview(req, s, work)
        assert p["pii_found"] and not p["blocked"]
        with pytest.raises(ProjectError, match="PII"):
            build(req, s, work, tmp_path / "no.vushare", p["preview_hash"])
        path, p, _ = bundle(store, s, work, tmp_path, allow=True)
        assert open_bundle(path)["manifest"]["pii_included"]
        with zipfile.ZipFile(path) as z:
            members = {n: z.read(n) for n in z.namelist()}
        bad = tmp_path / "corrupt.vushare"
        with zipfile.ZipFile(bad, "w") as z:
            for n, data in members.items():
                z.writestr(n, b"wrong" if n == "projection.json" else data)
        with pytest.raises(ProjectError, match="hash"):
            open_bundle(bad)
        with zipfile.ZipFile(tmp_path / "traversal.vushare", "w") as z:
            for n, data in members.items():
                z.writestr(n, data)
            z.writestr("../escape", b"data")
        with pytest.raises(ProjectError):
            open_bundle(tmp_path / "traversal.vushare")
        artifact = store.path("staging") / uid()
        artifact.write_bytes(b"\x00opaque-model-DO_NOT_PARSE")
        from veri_ufku.storage.project_store import file_hash

        store.pending["sources/" + uid() + ".bin"] = (
            artifact,
            dict(**file_hash(artifact), kind="source", rows=None, schema=None),
        )
        store.save()
        req = storage.request_for(store, store.state, dict(action="preview", spec=s))
        p, _ = preview(req, s, work)
        assert p["blocked"] and any(
            f["reason"] == "unscannable-binary" for f in p["findings"]
        )
        with pytest.raises(ProjectError):
            build(req, s, work, tmp_path / "opaque.vushare", p["preview_hash"], True)


def probe_writer(root, sender):
    try:
        with closing(ProjectStore.open(root)) as store:
            denied = False
            try:
                store.save()
            except ProjectError:
                denied = True
            sender.send(dict(read_only=store.read_only, write_denied=denied))
    finally:
        sender.close()


def test_actual_second_process_writer_and_cancel(tmp_path):
    import multiprocessing as mp
    import threading

    from veri_ufku.jobs.workers import Canceled

    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1.0]}))
    with closing(store):
        context = mp.get_context("spawn")
        receiver, sender = context.Pipe(False)
        process = context.Process(target=probe_writer, args=(str(store.root), sender))
        process.start()
        sender.close()
        try:
            assert receiver.poll(30)
            assert receiver.recv() == dict(read_only=True, write_denied=True)
            process.join(5)
            assert process.exitcode == 0
        finally:
            if process.is_alive():
                process.kill()
                process.join()
            process.close()
            receiver.close()
        event = threading.Event()
        event.set()
        req = storage.request_for(
            store, store.state, dict(action="preview", spec=spec("full-copy"))
        )
        before = store.commit_id
        with pytest.raises(Canceled):
            preview(req, req["spec"], work, Control(event))
        assert store.commit_id == before


def test_artifact_version_context_and_metadata_secret(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    from veri_ufku.storage.project_model import uid
    from veri_ufku.storage.project_store import file_hash

    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1.0, 2.0]}))
    with closing(store):
        path, p, _ = bundle(store, spec(), work, tmp_path)
        opened = open_bundle(path)
        bound = storage.subject(opened["projection"], "dataset:" + r["version_id"])
        state = storage.append_review(
            store,
            store.state,
            bound,
            "Yerel inceleyen",
            "Özgün artifact incelendi.",
            dict.fromkeys(storage.CHECKS, True),
        )
        e = copy.deepcopy(state["results"][-1]["review_event"])
        altered = copy.deepcopy(store.manifest)
        altered["artifacts"][r["snapshot_uri"]]["sha256"] = "0" * 64
        assert (
            storage.binding_status(e, state, altered)
            == "historical/missing context; not rebound"
        )
        assert (
            e["subject"]["entity"]["artifacts"][r["snapshot_uri"]]["sha256"] != "0" * 64
        )
        artifact = store.path("staging") / uid()
        pq.write_table(
            pa.table({"a": [1]}).replace_schema_metadata(
                {"api_key": "HIDDEN_METADATA"}
            ),
            artifact,
        )
        store.pending["sources/" + uid() + ".bin"] = (
            artifact,
            dict(**file_hash(artifact), kind="source", rows=None, schema=None),
        )
        store.save()
        s = spec("full-copy")
        req = storage.request_for(store, store.state, dict(action="preview", spec=s))
        p, _ = preview(req, s, work)
        assert p["blocked"] and "HIDDEN_METADATA" not in str(p)


def test_sample_nonfinite_numeric_and_sensitive_terms_not_exported(tmp_path):
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"x": [float("nan"), float("inf")], "person": ["PrivateName", "Other"]}
        ),
    )
    with closing(store):
        s = spec("redacted-sample", r["version_id"])
        s["keep_numeric"] = [column(r, "x")]
        s["sensitive_terms"] = ["PrivateName"]
        path, p, _ = bundle(store, s, work, tmp_path)
        opened = open_bundle(path)
        frame = pl.read_parquet(io.BytesIO(opened["payload"]["sample.parquet"]))
        assert frame["column-1"].is_nan()[0] and frame["column-1"][1] == float("inf")
        assert b"PrivateName" not in b"".join(opened["payload"].values())
        assert p["sample_preview"][0]["column-1"] == "nan"
        s = spec("full-copy")
        s["sensitive_terms"] = ["PrivateName"]
        req = storage.request_for(store, store.state, dict(action="preview", spec=s))
        p, _ = preview(req, s, work)
        assert p["blocked"] and "PrivateName" not in str(p)


def test_schema_identity_collision_and_sample_mask_tamper(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0], "person": ["A", "B"]})
    )
    with closing(store):
        path, p, _ = bundle(
            store, spec("redacted-sample", r["version_id"]), work, tmp_path
        )
        opened = open_bundle(path)
        raw = opened["payload"].copy()
        frame = pl.read_parquet(io.BytesIO(raw["sample.parquet"]))
        frame = frame.with_columns(pl.lit("UNMASKED").alias("column-2"))
        output = io.BytesIO()
        frame.write_parquet(output)
        raw["sample.parquet"] = output.getvalue()
        manifest = copy.deepcopy(opened["manifest"])
        import hashlib

        manifest["members"] = {
            n: dict(size=len(data), sha256=hashlib.sha256(data).hexdigest())
            for n, data in raw.items()
        }
        malicious = tmp_path / "tampered-mask.vushare"
        with zipfile.ZipFile(malicious, "w") as z:
            z.writestr("manifest.json", json.dumps(manifest))
            for n, data in raw.items():
                z.writestr(n, data)
        with pytest.raises(ProjectError, match="maske"):
            open_bundle(malicious)
        assert not (tmp_path / "escape").exists()


def test_cross_project_column_and_row_collision_are_explicit(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1.0, 2.0]}))
    with closing(store):
        path, _, _ = bundle(
            store, spec("redacted-sample", r["version_id"]), work, tmp_path
        )
        left = open_bundle(path)
        right = copy.deepcopy(left)
        right["projection"]["origin"]["project_id"] = "different-origin"
        # Different dataset keys do not hide duplicate ColumnId and included RowId.
        schema = right["projection"]["categories"]["schema"]
        value = schema.pop(r["version_id"])
        schema["different-dataset-key"] = value
        diff = compare(left, right)
        assert diff["identity_collisions"]["column_ids"] == [column(r, "x")]
        assert len(diff["identity_collisions"]["row_ids"]) == 2


def test_full_copy_cannot_hide_external_path_in_freeform_metadata(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1.0]}))
    with closing(store):
        store.state["help_preferences"]["note"] = "/home/private/research.csv"
        store.save()
        s = spec("full-copy")
        req = storage.request_for(store, store.state, dict(action="preview", spec=s))
        p, _ = preview(req, s, work)
        assert p["blocked"] and any(
            f["reason"] == "external-location" for f in p["findings"]
        )
        assert "/home/private" not in str(p)
        with pytest.raises(ProjectError):
            build(req, s, work, tmp_path / "unsafe.vushare", p["preview_hash"], True)
        path, _, _ = bundle(store, spec(), work, tmp_path)
        assert b"/home/private" not in b"".join(open_bundle(path)["payload"].values())


def test_human_review_transfers_with_original_artifact_context(tmp_path):
    store, r, work = prepare(tmp_path, pl.DataFrame({"x": [1.0, 2.0]}))
    with closing(store):
        first, _, _ = bundle(store, spec(), work, tmp_path)
        opened = open_bundle(first)
        bound = storage.subject(
            opened["projection"], "dataset:" + r["version_id"], opened["fingerprint"]
        )
        state = storage.append_review(
            store,
            store.state,
            bound,
            "Yerel inceleyen",
            "Özgün sürüm yorumu.",
            dict.fromkeys(storage.CHECKS, True),
            "defer",
        )
        original = copy.deepcopy(state["results"][-1]["review_event"])
        path, _, _ = bundle(store, spec("full-copy"), work, tmp_path)
        incoming = open_bundle(path)
        target = tmp_path / "reviewed-fork"
        storage.restore(path, target, incoming["fingerprint"])
        with closing(ProjectStore.open(target)) as fork:
            preserved = next(
                r["review_event"]
                for r in fork.state["results"]
                if r.get("review_event", {}).get("kind") == "human-review"
            )
            assert preserved == original
            assert (
                preserved["subject"]["entity"]["artifacts"]
                == bound["entity"]["artifacts"]
            )
            assert (
                storage.binding_status(preserved, fork.state, fork.manifest)
                == "external-origin; original context retained"
            )


def test_review_flag_exception_does_not_allow_secret_strings():
    from veri_ufku.exports.share_privacy import sanitize, scan

    assert scan({"secret-pii-reviewed": True}) == []
    assert sanitize({"secret-pii-reviewed": True}) == {"secret-pii-reviewed": True}
    for value in ("ACTUAL_CREDENTIAL", 123):
        assert any(
            f["reason"] == "secret-key" for f in scan({"secret-pii-reviewed": value})
        )
    assert any(
        f["reason"] == "secret-key" for f in scan({"api_key": "ACTUAL_CREDENTIAL"})
    )
