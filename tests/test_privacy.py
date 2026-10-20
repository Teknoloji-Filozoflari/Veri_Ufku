"""Real bounded PII projection/crypto, human journals and safe cache cleanup."""

import base64
import copy
import hashlib
import hmac
import io
import json
import os
import time
import zipfile
from contextlib import closing

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.exports import privacy as core
from veri_ufku.exports import privacy_cleanup as cleanup
from veri_ufku.exports import privacy_keys as keys
from veri_ufku.exports.privacy_contracts import policy
from veri_ufku.importers.delimited import Control
from veri_ufku.storage import privacy_store as storage
from veri_ufku.storage.project_model import ProjectError, encode, validate_state
from veri_ufku.storage.project_store import ProjectStore, file_hash


def reviewed(tmp_path):
    store, ref, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "email": ["a@example.org", "b@example.org", None],
                "amount": [1, 2, 3],
                "password": ["RAW_PW", "OTHER", None],
            }
        ),
    )
    p = dict(
        version=ref["version_id"],
        reviewer="Yerel inceleyen",
        rationale="Riskler incelendi",
        key_ref="",
        rules=[
            dict(column=column(ref, "email"), classification="pii", strategy="mask"),
            dict(
                column=column(ref, "amount"), classification="not-pii", strategy="keep"
            ),
        ],
    )
    return store, ref, work, p


def test_candidates_review_redaction_export_reopen_source_preserved(tmp_path):
    store, ref, work, p = reviewed(tmp_path)
    with closing(store):
        before = file_hash(tmp_path / "source.parquet")
        snapshot = file_hash(__import__("pathlib").Path(ref["path"]))
        req = storage.request_for(
            store, store.state, dict(action="scan", version=ref["version_id"])
        )
        scan = core.pii_scan(req)
        assert scan["columns"][0]["email"] == 2 and "a@example.org" not in str(scan)
        assert len(scan["columns"][0]["example_row_ids"]) == 2
        state = storage.review(store, store.state, p)
        rid = state["results"][-1]["id"]
        req = storage.request_for(store, state, dict(action="preview", review_id=rid))
        table, pv = core.project_policy(req, p, None, Control())
        assert table.to_pylist() == [
            {"column_1": "[redacted]", "column_2": 1},
            {"column_1": "[redacted]", "column_2": 2},
            {"column_1": None, "column_2": 3},
        ]
        assert "__vu_row_id" not in table.column_names and "RAW_PW" not in str(pv)
        params = dict(
            action="export",
            review_id=rid,
            format="zip",
            destination=str(tmp_path / "safe.zip"),
            preview_hash=pv["preview_hash"],
            reviewed=True,
            encryption_key_ref="",
        )
        export = core.export(req, params, work, Control())
        with zipfile.ZipFile(tmp_path / "safe.zip") as z:
            raw = b"".join(z.read(n) for n in z.namelist())
            assert b"a@example.org" not in raw and b"RAW_PW" not in raw
            assert b"__vu_row_id" not in raw
            assert pl.read_parquet(io.BytesIO(z.read("data.parquet"))).height == 3
        storage.publish(store, state, export)
        assert (
            file_hash(tmp_path / "source.parquet") == before
            and file_hash(__import__("pathlib").Path(ref["path"])) == snapshot
        )
        validate_state(store.state)
        old = copy.deepcopy(store.state)
        with pytest.raises(ProjectError):
            from veri_ufku.storage.validation_store import transaction

            transaction(store, {**old, "results": []}, lambda d: None)
        root = store.root
    with closing(ProjectStore.open(root)) as reopened:
        assert reopened.state == old
        assert storage.dependencies(old)["marked_versions"] == [ref["version_id"]]


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(key_ref=None),
        lambda p: p.update(rules=[None]),
        lambda p: p["rules"][0].update(strategy="keep"),
        lambda p: p["rules"].append(p["rules"][0]),
        lambda p: p.update(reviewer="secret=HIDE_ME"),
    ],
)
def test_closed_human_policy(change, tmp_path):
    store, ref, work, p = reviewed(tmp_path)
    with closing(store):
        change(p)
        with pytest.raises((ProjectError, ValueError)):
            policy(p)


def test_secret_column_keep_forbidden_and_preview_binding(tmp_path):
    store, ref, work, p = reviewed(tmp_path)
    with closing(store):
        p["rules"] = [
            dict(
                column=column(ref, "password"),
                classification="not-pii",
                strategy="keep",
            )
        ]
        req = dict(
            source=ref,
            project_id=store.manifest["project_id"],
            review_id="local-review",
            project_root=str(store.root),
        )
        with pytest.raises(ProjectError, match="Secret"):
            core.project_policy(req, p, None, Control())
        p["rules"][0].update(strategy="mask", classification="pii")
        req["policy"] = p
        _, pv = core.project_policy(req, p, None, Control())
        with pytest.raises(ProjectError, match="önizlemesini"):
            core.export(
                req, dict(reviewed=True, preview_hash="changed"), work, Control()
            )


def test_real_standard_hmac_fernet_roundtrip_wrong_key_no_leak(tmp_path):
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    other = Fernet.generate_key()
    message = json.dumps(
        ["Veri_Ufku.pseudonym/v1", "p", "c", "Çağrı"],
        ensure_ascii=False,
        sort_keys=True,
    ).encode()
    expected = (
        "psn_"
        + hmac.new(base64.urlsafe_b64decode(key), message, hashlib.sha256).hexdigest()
    )
    assert keys.pseudonym(key, "p", "c", "Çağrı") == expected
    assert keys.pseudonym(key, "p", "c", "Çağrı") != keys.pseudonym(
        key, "other", "c", "Çağrı"
    )
    encrypted = keys.encrypt(b"private content", key)
    assert (
        b"private content" not in encrypted
        and keys.decrypt(encrypted, key) == b"private content"
    )
    for raw, k in [
        (encrypted, other),
        (encrypted[:-8] + b"BROKEN!!", key),
        (b"plaintext", key),
    ]:
        with pytest.raises(ProjectError) as e:
            keys.decrypt(raw, k)
        assert key.decode() not in str(e.value) and "private content" not in str(
            e.value
        )


def test_encrypted_export_inspection_pseudonym_and_no_key_in_manifest(tmp_path):
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    seal = Fernet.generate_key()
    store, ref, work, p = reviewed(tmp_path)
    with closing(store):
        p.update(key_ref="local-hmac")
        p["rules"][0]["strategy"] = "pseudonym"
        req = dict(
            source=ref,
            project_id=store.manifest["project_id"],
            project_root=str(store.root),
            review_id="local-review",
            policy=p,
        )
        table, pv = core.project_policy(req, p, key, Control())
        assert table.column(0)[0].as_py().startswith("psn_")
        params = dict(
            format="sealed",
            destination=str(tmp_path / "safe.vupseal"),
            reviewed=True,
            preview_hash=pv["preview_hash"],
            encryption_key_ref="local-fernet",
        )
        core.export(req, params, work, Control(), key, seal)
        opened = core.inspect_sealed(tmp_path / "safe.vupseal", seal)
        assert opened["manifest"]["encryption_key_ref"] == "local-fernet"
        assert seal.decode() not in str(opened) and key.decode() not in str(opened)
        raw = keys.decrypt((tmp_path / "safe.vupseal").read_bytes(), seal)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            assert b"a@example.org" not in b"".join(z.read(n) for n in z.namelist())


def test_keyring_failure_no_fallback_no_exception_secrets(monkeypatch, capsys):
    import veri_ufku.importers.credentials as credentials

    def unavailable():
        raise RuntimeError("private-key=DO_NOT_LEAK")

    monkeypatch.setattr(credentials, "backend", unavailable)
    for f, args in [
        (keys.load, ("hmac", "local")),
        (keys.generate, ("fernet", "local")),
    ]:
        with pytest.raises(ProjectError) as e:
            f(*args)
        assert "DO_NOT_LEAK" not in str(e.value)
    assert not capsys.readouterr().out and not capsys.readouterr().err


def orphan(root, name="monitor-old"):
    d = root / name
    d.mkdir(parents=True)
    (d / "marker.json").write_bytes(
        encode(
            dict(schema="PrivacyScratch/v1", owner="Veri_Ufku.privacy", pid=2147483647)
        )
    )
    (d / "payload.zip").write_bytes(b"old cache")
    for p in d.iterdir():
        os.utime(p, (time.time() - 40 * 86400,) * 2)
    return d


def test_cleanup_preview_stale_symlink_hardlink_sources_protected(tmp_path):
    cache = tmp_path / "privacy"
    project = tmp_path / "project"
    project.mkdir()
    source = tmp_path / "source"
    source.write_bytes(b"never delete source")
    old = orphan(cache)
    bad = orphan(cache, "bad-hardlink")
    (bad / "payload.zip").unlink()
    os.link(source, bad / "payload.zip")
    (cache / "symlink").symlink_to(project, target_is_directory=True)
    plan = cleanup.preview(cache, project, 30)
    assert len(plan["candidates"]) == 1 and set(plan["protected"]) == {
        "bad-hardlink",
        "symlink",
    }
    with pytest.raises(ProjectError):
        cleanup.apply(cache, project, plan, False)
    (old / "payload.zip").write_bytes(b"changed")
    with pytest.raises(ProjectError):
        cleanup.apply(cache, project, plan, True)
    os.utime(old / "payload.zip", (time.time() - 40 * 86400,) * 2)
    fresh = cleanup.preview(cache, project, 30)
    result = cleanup.apply(cache, project, fresh, True)
    assert (
        result["removed"] == ["monitor-old"]
        and source.read_bytes() == b"never delete source"
    )
    assert project.exists() and bad.exists() and (cache / "symlink").is_symlink()
    with pytest.raises(ProjectError):
        cleanup.preview(project / "cache", project)


def test_live_scratch_and_cancel_are_protected(tmp_path):
    import threading

    from veri_ufku.jobs.workers import Canceled

    cache = tmp_path / "privacy"
    project = tmp_path / "project"
    project.mkdir()
    d = orphan(cache)
    (d / "marker.json").write_bytes(
        encode(
            dict(schema="PrivacyScratch/v1", owner="Veri_Ufku.privacy", pid=os.getpid())
        )
    )
    os.utime(d / "marker.json", (time.time() - 40 * 86400,) * 2)
    p = cleanup.preview(cache, project, 30)
    assert not p["candidates"] and p["protected"] == [d.name]
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(Canceled):
        cleanup.preview(cache, project, 30, Control(cancel=cancel))
    assert d.exists()


def test_log_does_not_record_key_or_source_values(tmp_path):
    import inspect

    from veri_ufku.logging_setup import EventLog

    # The event schema records technical error metadata only; no exception text/cells/key field.
    assert "message" not in inspect.signature(EventLog.event).parameters
    log = EventLog(tmp_path)
    from veri_ufku.domain.contracts import AppError

    secret = "PRIVATE_KEY_SENTINEL"
    try:
        raise RuntimeError(secret + " a@example.org")
    except RuntimeError as e:
        log.event(
            "privacy-failed", "job-fixture", AppError.create("worker", type(e).__name__)
        )
    log.close()
    text = (tmp_path / "application.log").read_text()
    assert "a@example.org" not in text and "PRIVATE_KEY_SENTINEL" not in text


def test_keyring_namespace_reference_roundtrip_stub_not_live_service(monkeypatch):
    import veri_ufku.importers.credentials as credentials

    class Vault:
        def __init__(self):
            self.values = {}

        def get_password(self, service, ref):
            return self.values.get((service, ref))

        def set_password(self, service, ref, value):
            self.values[service, ref] = value

    vault = Vault()
    monkeypatch.setattr(credentials, "backend", lambda: vault)
    receipt = keys.generate("hmac", "project-local")
    key = keys.load("hmac", "project-local")
    assert len(base64.urlsafe_b64decode(key)) == 32 and key.decode() not in str(receipt)
    assert set(vault.values) == {("Veri_Ufku.privacy.hmac", "project-local")}
    with pytest.raises(ProjectError):
        keys.generate("hmac", "project-local")
    with pytest.raises(ProjectError):
        keys.load("fernet", "project-local")


def test_existing_lineage_graph_tracks_derived_results_without_guessing(tmp_path):
    from veri_ufku.analytics.contracts import ProfileSpec
    from veri_ufku.analytics.dataset import profile
    from veri_ufku.operations.contracts import build
    from veri_ufku.operations.engine import calculate
    from veri_ufku.storage.lineage import graph
    from veri_ufku.storage.project_model import uid

    store, ref, work, p = reviewed(tmp_path)
    with closing(store):
        storage.review(store, store.state, p)
        out = store.publish_operation(
            calculate(
                ref,
                build(ref, "rename", [column(ref, "amount")], dict(name="amount2")),
                work,
            )
        )
        from veri_ufku.operations.workflow import references

        r = references(store, store.state)[out["version_id"]]
        v = profile(r, ProfileSpec(column(ref, "amount"), sample=False), work)
        ident = "result:" + uid()
        store.state["results"].append(
            dict(
                id=ident,
                dataset_version_ids=[out["version_id"]],
                seed=None,
                capability_id="dataset.profile",
                profile=v,
            )
        )
        store.save()
        links = storage.dependencies(store.state, store.manifest)
        assert ident in {x["id"] for x in links["potential_results"]}
        g = graph(store.state, store.manifest)
        assert any(
            n["metadata"].get("record_kind") == "privacy_event" for n in g["nodes"]
        )
