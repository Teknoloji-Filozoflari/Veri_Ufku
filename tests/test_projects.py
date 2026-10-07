"""Real SQLite/Parquet, process death and two-writer safety checks."""

import copy
import json
import os
import signal
import sqlite3
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

from veri_ufku.storage.project_model import ProjectError, digest, encode
from veri_ufku.storage.project_store import CRASH_POINTS, ProjectStore


def populate(store, source):
    ref = store.stage_source(source, portable=True)
    uri = store.stage_parquet(
        pl.DataFrame({"value": [1, 2, None], "name": ["a", "a", "b"]})
    )
    store.state.update(
        import_settings={"delimiter": ";", "encoding": "utf8"},
        seed=42,
        help_preferences={"depth": 2},
    )
    store.state["datasets"].append(
        dict(
            dataset_id="dataset:00000000-0000-4000-8000-000000000001",
            version_id="dv:00000000-0000-4000-8000-000000000001",
            source_id=ref["id"],
            snapshot_uri=uri,
        )
    )
    store.state["operations"] = [
        dict(
            id="op:00000000-0000-4000-8000-000000000001",
            dataset_version_ids=["dv:00000000-0000-4000-8000-000000000001"],
            seed=42,
            parameters={"mode": "test"},
        )
    ]
    store.state["results"] = [
        dict(
            id="result:00000000-0000-4000-8000-000000000001",
            dataset_version_ids=["dv:00000000-0000-4000-8000-000000000001"],
            seed=42,
            metrics={"count": 3},
        )
    ]
    return uri


def test_roundtrip_save_as_sources_and_autosave(tmp_path):
    source = tmp_path / "source.csv"
    original = b"value;name\n1;a\n2;a\n;b\n"
    source.write_bytes(original)
    store = ProjectStore.create(tmp_path / "project", "Kalıcı durum")
    uri = populate(store, source)
    store.save()
    saved = copy.deepcopy(store.state)
    active = (store.root / "ACTIVE").read_bytes()
    store.state["name"] = "Kurtarılacak"
    store.save(autosave=True)
    assert (store.root / "ACTIVE").read_bytes() == active
    assert store.results_status()[0]["current"]
    store.close()
    reopened = ProjectStore.open(tmp_path / "project")
    assert reopened.state == saved
    assert pl.read_parquet(reopened.path(uri)).to_dict(as_series=False) == {
        "value": [1, 2, None],
        "name": ["a", "a", "b"],
    }
    reopened.restore_autosave()
    assert reopened.state["name"] == "Kurtarılacak"
    assert (reopened.root / "ACTIVE").read_bytes() == active
    fork = reopened.save_as(tmp_path / "fork")
    assert fork.state == reopened.state
    fork.close()
    source.unlink()
    assert "missing" in reopened.source_statuses().values()
    assert not reopened.results_status()[0]["current"]
    replacement = tmp_path / "replacement.csv"
    replacement.write_bytes(original)
    reopened.relink(reopened.state["sources"][0]["id"], replacement)
    reopened.save()
    assert reopened.results_status()[0]["current"]
    replacement.write_bytes(b"changed")
    assert "changed" in reopened.source_statuses().values()
    with pytest.raises(ProjectError, match="aynı değil"):
        reopened.relink(reopened.state["sources"][0]["id"], replacement)
    assert not reopened.results_status()[0]["current"]
    # Immutable portable bytes remain available, source writes only come from this test.
    copied = reopened.path(reopened.state["sources"][0]["copy_uri"])
    assert copied.read_bytes() == original
    reopened.close()


CHILD_SAVE = """
import os, signal, sys
from pathlib import Path
import polars as pl
from veri_ufku.storage.project_store import ProjectStore
p = ProjectStore.open(sys.argv[1])
p.state['name'] = 'new'
source = p.stage_source(Path(sys.argv[1]).parent / 'source.csv', portable=True) if sys.argv[3] == 'source' else p.state['sources'][0]
uri = p.stage_parquet(pl.DataFrame({'value': [9, 8, 7]}))
p.state['datasets'].append(dict(dataset_id='dataset:00000000-0000-4000-8000-000000000002', version_id='dv:00000000-0000-4000-8000-000000000002', source_id=source['id'], snapshot_uri=uri))
def checkpoint(point):
    if point == sys.argv[2]:
        os.kill(os.getpid(), signal.SIGKILL)
p.save(checkpoint=checkpoint)
"""


@pytest.mark.parametrize("artifact_kind", ["source", "parquet"])
@pytest.mark.parametrize("point", CRASH_POINTS)
def test_sigkill_at_every_publication_boundary(tmp_path, point, artifact_kind):
    source = tmp_path / "source.csv"
    source.write_bytes(b"never modified\n")
    original = source.read_bytes()
    store = ProjectStore.create(tmp_path / "project", "old")
    old_uri = populate(store, source)
    store.state["name"] = "old"
    store.save()
    old_commit = store.commit_id
    store.close()
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            CHILD_SAVE,
            str(tmp_path / "project"),
            point,
            artifact_kind,
        ],
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == -signal.SIGKILL, result.stderr
    recovered = ProjectStore.open(tmp_path / "project", recover_lock=True)
    try:
        expected = "new" if point in {"pointer_replaced", "root_synced"} else "old"
        assert recovered.state["name"] == expected
        assert (recovered.commit_id != old_commit) == (expected == "new")
        assert recovered.path(old_uri).is_file()
        assert pl.read_parquet(recovered.path(old_uri)).height == 3
        assert source.read_bytes() == original
        assert list(recovered.path("staging").iterdir()) == []
        # Recovered SQLite rows, active payload and every artifact have been verified by open.
    finally:
        recovered.close()


def test_two_real_processes_readonly_and_stale_lock(tmp_path):
    path = tmp_path / "project"
    store = ProjectStore.create(path)
    store.close()
    writer = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-c",
            "from veri_ufku.storage.project_store import ProjectStore; import sys; p=ProjectStore.open(sys.argv[1]); print('LOCKED',flush=True); sys.stdin.read(); p.close()",
            str(path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert writer.stdout.readline().strip() == "LOCKED"
        second = ProjectStore.open(path, recover_lock=True)
        assert second.read_only
        with pytest.raises(ProjectError, match="salt okunur"):
            second.save()
        second.close()
        writer.kill()
        writer.wait(timeout=5)
        reader = ProjectStore.open(path)
        assert reader.stale_lock and reader.read_only
        reader.close()
        recovered = ProjectStore.open(path, recover_lock=True)
        assert recovered.stale_lock and not recovered.read_only
        recovered.save()
        recovered.close()
    finally:
        if writer.poll() is None:
            writer.kill()
            writer.wait(timeout=5)


def rewrite_manifest(path, change):
    pointer = json.loads((path / "ACTIVE").read_bytes())
    manifest_path = path / "commits" / pointer["commit_id"] / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    change(manifest, pointer)
    raw = encode(manifest)
    manifest_path.write_bytes(raw)
    pointer["manifest_sha256"] = digest(raw)
    (path / "ACTIVE").write_bytes(encode(pointer))
    with sqlite3.connect(path / "metadata.sqlite") as db:
        db.execute(
            "UPDATE commits SET manifest_hash=?, payload=? WHERE commit_id=?",
            (digest(raw), raw, pointer["commit_id"]),
        )


def test_future_version_and_invalid_fields_paths_sizes(tmp_path):
    path = tmp_path / "project"
    p = ProjectStore.create(path)
    p.close()
    baseline = {
        str(f.relative_to(path)): f.read_bytes() for f in path.rglob("*") if f.is_file()
    }
    rewrite_manifest(
        path,
        lambda m, ptr: (m.update(format_version=99), ptr.update(format_version=99)),
    )
    active = (path / "ACTIVE").read_bytes()
    with pytest.raises(ProjectError, match="şema sürümü"):
        ProjectStore.open(path)
    assert (path / "ACTIVE").read_bytes() == active
    # Independent malformed fixtures, not a parser-only happy path.
    for change in [
        lambda m, p: m.update(extra="unknown"),
        lambda m, p: m["state"].update(seed=-1),
        lambda m, p: m["artifacts"].update({"../escape": {"size": 0}}),
        lambda m, p: m["artifacts"].update(
            {
                "sources/safe.bin": dict(
                    size=2**50, sha256="0" * 64, kind="source", rows=None, schema=None
                )
            }
        ),
    ]:
        for uri, raw in baseline.items():
            (path / uri).write_bytes(raw)
        rewrite_manifest(path, change)
        with pytest.raises(ProjectError):
            ProjectStore.open(path)


def test_samefile_symlink_collision_cleanup_and_fs_policy(tmp_path, monkeypatch):
    path = tmp_path / "project"
    store = ProjectStore.create(path)
    linked = tmp_path / "alias"
    linked.symlink_to(path, target_is_directory=True)
    for target in (path, linked, path / "nested", tmp_path):
        with pytest.raises(ProjectError, match="hedef"):
            store.save_as(target)
    source = tmp_path / "source"
    source.write_bytes(b"source")
    ref = store.stage_source(source, portable=True)
    store.save()
    artifact = store.path(ref["copy_uri"])
    staging = store.path("staging") / "unfinished"
    staging.mkdir()
    os.link(artifact, staging / "linked")
    store.quarantine_staging()
    assert artifact.read_bytes() == b"source"
    with pytest.raises(ProjectError):
        store.save_as(source)
    monkeypatch.setattr("veri_ufku.storage.project_store.filesystem", lambda p: "nfs")
    with pytest.raises(ProjectError, match="doğrulanmadı"):
        ProjectStore.create(tmp_path / "network")
    store.close()


def test_corrupt_active_no_blind_recovery_and_artifact_symlink(tmp_path):
    path = tmp_path / "project"
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    store = ProjectStore.create(path)
    ref = store.stage_source(source, portable=True)
    store.save()
    store.close()
    artifact = path / ref["copy_uri"]
    artifact.unlink()
    artifact.symlink_to(source)
    with pytest.raises(ProjectError, match="sembolik"):
        ProjectStore.open(path)
    (path / "ACTIVE").write_bytes(b"partial")
    with pytest.raises(ProjectError, match="geçersiz"):
        ProjectStore.open(path)
    assert (path / "ACTIVE").read_bytes() == b"partial"


def test_failed_save_keeps_active_and_can_retry(tmp_path):
    store = ProjectStore.create(tmp_path / "project")
    store.state["name"] = "draft"
    before = (store.root / "ACTIVE").read_bytes()

    def fail(point):
        if point == "metadata_committed":
            raise OSError("disk failed")

    with pytest.raises(OSError):
        store.save(checkpoint=fail)
    assert (store.root / "ACTIVE").read_bytes() == before
    store.save()
    store.close()
    reader = ProjectStore.open(tmp_path / "project")
    assert reader.state["name"] == "draft"
    reader.close()


def test_legacy_fixture_migrates_to_copy_and_preserves_original(tmp_path):
    fixture = Path(__file__).parent / "fixtures/projects/schema0.json"
    manifest = json.loads(fixture.read_text())
    path = tmp_path / "legacy"
    store = ProjectStore.create(path)
    store.close()
    raw = encode(manifest)
    (path / "commits/legacy-0001").mkdir()
    (path / "commits/legacy-0001/manifest.json").write_bytes(raw)
    (path / "ACTIVE").write_bytes(
        encode(
            dict(commit_id="legacy-0001", manifest_sha256=digest(raw), format_version=0)
        )
    )
    with sqlite3.connect(path / "metadata.sqlite") as db:
        db.execute(
            "INSERT INTO commits VALUES (?,?,?)", ("legacy-0001", digest(raw), raw)
        )
    original = (
        (path / "ACTIVE").read_bytes(),
        (path / "metadata.sqlite").read_bytes(),
        raw,
    )
    legacy = ProjectStore.open(path)
    assert legacy.read_only
    assert legacy.state["seed"] is None
    migrated = legacy.save_as(tmp_path / "migrated")
    assert migrated.state["name"] == "Eski proje"
    assert migrated.manifest["format_version"] == 5
    assert migrated.manifest["migration"] == [
        {"from_version": 0, "to_version": 5, "original_commit": "legacy-0001"}
    ]
    migrated.close()
    legacy.close()
    assert original == (
        (path / "ACTIVE").read_bytes(),
        (path / "metadata.sqlite").read_bytes(),
        (path / "commits/legacy-0001/manifest.json").read_bytes(),
    )


def test_metadata_open_never_reads_external_source(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.write_bytes(b"preserved")
    store = ProjectStore.create(tmp_path / "project")
    store.stage_source(source)
    store.save()
    store.close()

    def forbidden(*args):
        raise AssertionError("Metadata opening must not read/reprocess external data")

    monkeypatch.setattr("veri_ufku.storage.project_store.source_fingerprint", forbidden)
    reader = ProjectStore.open(tmp_path / "project")
    assert reader.state["sources"][0]["path"] == str(source)
    assert source.read_bytes() == b"preserved"
    reader.close()


def test_source_changes_during_capture_are_rejected(tmp_path, monkeypatch):
    from veri_ufku.storage import project_store

    source = tmp_path / "source"
    source.write_bytes(b"original")
    original_hash = project_store.file_hash
    count = 0

    def change_after_read(path):
        nonlocal count
        result = original_hash(path)
        count += 1
        if count == 1:
            source.write_bytes(b"modified by test producer")
        return result

    store = ProjectStore.create(tmp_path / "project")
    monkeypatch.setattr(project_store, "file_hash", change_after_read)
    before = (store.root / "ACTIVE").read_bytes()
    with pytest.raises(ProjectError, match="değişti"):
        store.stage_source(source, portable=True)
    assert not store.state["sources"]
    assert (store.root / "ACTIVE").read_bytes() == before
    store.close()


def test_replaced_project_directory_stops_writer(tmp_path):
    path = tmp_path / "project"
    store = ProjectStore.create(path)
    old = tmp_path / "renamed-project"
    path.rename(old)
    path.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ProjectError, match="dizini değişti"):
        store.save()
    assert not (tmp_path / "ACTIVE").exists()
    store.close()


def test_old_autosave_cannot_replace_newer_manual_or_unsaved_state(tmp_path):
    store = ProjectStore.create(tmp_path / "project")
    store.state["name"] = "autosaved"
    store.save(autosave=True)
    store.state["name"] = "new manual"
    store.save()
    store.state["name"] = "unsaved work"
    active = (store.root / "ACTIVE").read_bytes()
    with pytest.raises(ProjectError, match="başka bir temel"):
        store.restore_autosave()
    assert store.state["name"] == "unsaved work"
    assert (store.root / "ACTIVE").read_bytes() == active
    store.close()


def test_save_as_intervening_destination_is_never_overwritten(tmp_path, monkeypatch):
    from veri_ufku.storage import project_store

    store = ProjectStore.create(tmp_path / "project")
    original_publish = project_store.publish_directory
    target = tmp_path / "fork"

    def intervening(parent, temporary, destination):
        target.mkdir()
        (target / "user-content").write_bytes(b"keep")
        original_publish(parent, temporary, destination)

    monkeypatch.setattr(project_store, "publish_directory", intervening)
    before = (store.root / "ACTIVE").read_bytes()
    with pytest.raises(ProjectError, match="bu sırada"):
        store.save_as(target)
    assert (target / "user-content").read_bytes() == b"keep"
    assert (store.root / "ACTIVE").read_bytes() == before
    store.close()


def test_pointer_fsync_failure_reports_unknown_durability_and_preserves_both(
    tmp_path, monkeypatch
):
    from veri_ufku.storage import project_store

    store = ProjectStore.create(tmp_path / "project", "old")
    original_sync = project_store.sync_dir
    old_commit = store.commit_id
    store.state["name"] = "new"

    def fail_root(path):
        if path == store.base:
            raise OSError("fsync failed")
        original_sync(path)

    monkeypatch.setattr(project_store, "sync_dir", fail_root)
    with pytest.raises(ProjectError, match="dayanıklılık doğrulanamadı"):
        store.save()
    assert store.path(f"commits/{old_commit}/manifest.json").is_file()
    monkeypatch.setattr(project_store, "sync_dir", original_sync)
    store.close()
    recovered = ProjectStore.open(tmp_path / "project")
    assert recovered.state["name"] == "new"
    recovered.close()


@pytest.mark.parametrize("kind", ["source", "parquet"])
def test_sigkill_during_actual_artifact_writing(tmp_path, kind):
    source = tmp_path / "source.csv"
    source.write_bytes(b"keep source bytes\n" * 100000)
    original = source.read_bytes()
    store = ProjectStore.create(tmp_path / "project", "old")
    active = (store.root / "ACTIVE").read_bytes()
    store.close()
    code = """
import os, signal, sys
from pathlib import Path
import polars as pl
from veri_ufku.storage.project_store import ProjectStore
p = ProjectStore.open(sys.argv[1])
def kill(point):
    os.kill(os.getpid(), signal.SIGKILL)
if sys.argv[2] == 'source':
    p.stage_source(Path(sys.argv[1]).parent / 'source.csv', True, checkpoint=kill)
else:
    p.stage_parquet(pl.DataFrame({'x': range(10000)}), checkpoint=kill)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path / "project"), kind],
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == -signal.SIGKILL, result.stderr
    recovered = ProjectStore.open(tmp_path / "project", recover_lock=True)
    assert recovered.state["name"] == "old"
    assert (recovered.root / "ACTIVE").read_bytes() == active
    assert source.read_bytes() == original
    assert not list(recovered.path("staging").iterdir())
    recovered.close()
