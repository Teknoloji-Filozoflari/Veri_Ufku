"""Recorded lineage, bounded closed bundles and real exact/numeric re-runs."""

import copy
import json
import zipfile
from contextlib import closing
from pathlib import Path

import polars as pl
import pytest
from test_dataset import column, prepare
from test_workflow import recipe, run

from veri_ufku.analytics.contracts import ProfileSpec
from veri_ufku.analytics.dataset import profile
from veri_ufku.exports.repro import (
    build,
    environment,
    open_bundle,
    preview,
    raw,
    sanitize,
)
from veri_ufku.modeling.repro_verify import compare, rerun
from veri_ufku.operations.contracts import build as operation
from veri_ufku.operations.engine import calculate
from veri_ufku.storage.lineage import graph
from veri_ufku.storage.neural_store import publish
from veri_ufku.storage.project_model import ProjectError, uid


def saved_profile(store, r, work):
    p = profile(r, ProfileSpec(column(r, "x"), sample=False), work)
    ident = "result:" + uid()
    store.state["results"].append(
        dict(
            id=ident,
            dataset_version_ids=[r["version_id"]],
            seed=None,
            capability_id="dataset.profile",
            profile=p,
        )
    )
    store.save()
    return ident


def bundle(store, focus, tmp, include=False):
    work = tmp / "bundlework"
    work.mkdir(exist_ok=True)
    dest = tmp / (uid() + ".vurepro")
    p = preview(store, focus, include)
    result = build(store, focus, include, p["preview_hash"], work, dest)
    return dest, p, result


def test_lineage_recorded_report_operation_source_and_legacy_gap(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        renamed = store.publish_operation(
            calculate(
                r, operation(r, "rename", [column(r, "x")], dict(name="renamed")), work
            )
        )
        ident = "result:" + uid()
        store.state["results"].append(
            dict(
                id=ident,
                dataset_version_ids=[renamed["version_id"]],
                seed=None,
                analysis=dict(
                    spec=dict(method="example"),
                    provenance=dict(dataset_versions=[renamed["version_id"]]),
                ),
            )
        )
        report = "result:" + uid()
        store.state["results"].append(
            dict(
                id=report,
                dataset_version_ids=[renamed["version_id"]],
                seed=None,
                export=dict(
                    format="html", lineage_record_ids=[ident], lineage_context_version=1
                ),
            )
        )
        g = graph(store.state, store.manifest, report)
        assert {n["kind"] for n in g["nodes"]} == {
            "source",
            "dataset",
            "operation",
            "analysis",
            "report",
        }
        assert any(e["source"] == ident and e["target"] == report for e in g["edges"])
        legacy = next(n for n in g["nodes"] if n["id"] == ident)
        assert legacy["metadata"]["hardware"] == "not_recorded"
        assert legacy["metadata"]["capture"] == "not_recorded"
        assert any(
            n["metadata"]
            .get("row_lineage", {})
            .get("status", "")
            .startswith("preserved_identity")
            for n in g["nodes"]
            if n["kind"] == "dataset"
        )
        original = copy.deepcopy(store.state)
        clean, changes = sanitize(g)
        assert changes and b"/tmp/" not in raw(clean)
        assert store.state == original


def test_profile_reference_bundle_exact_and_reopen_hash(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.0, 6.0, 8.0]})
    )
    with closing(store):
        ident = saved_profile(store, r, work)
        path, p, receipt = bundle(store, ident, tmp_path)
        assert p["rerun_supported"] and not p["include_data"]
        opened = open_bundle(path)
        assert opened["manifest"]["focus"] == ident and receipt["member_count"] >= 8
        assert not any(n.startswith("data/") for n in opened["manifest"]["members"])
        verify = tmp_path / "verify"
        verify.mkdir()
        result = rerun(path, str(store.root), "exact", verify)
        assert result["status"] == "matched" and result["difference_count"] == 0
        assert json.loads((verify / "reference-report.json").read_text()) == json.loads(
            (verify / "actual-report.json").read_text()
        )
        with pytest.raises(ProjectError, match="erişimi gerekir"):
            rerun(path, "", "exact", tmp_path / "verify")
        with pytest.raises(ProjectError):
            build(store, ident, False, p["preview_hash"], work, path)


def test_opt_in_snapshot_reopens_without_original_project(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        ident = saved_profile(store, r, work)
        path, p, _ = bundle(store, ident, tmp_path, True)
        opened = open_bundle(path)
        assert opened["manifest"]["include_data"]
        assert sum(n.startswith("data/") for n in opened["manifest"]["members"]) == 1
        out = tmp_path / "verify"
        out.mkdir()
        assert rerun(path, "", "exact", out)["status"] == "matched"
        assert p["storage"]["retention"].startswith("retain historical")


def rewrite(path, target, change):
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}
    manifest = json.loads(files["manifest.json"])
    change(files, manifest)
    files["manifest.json"] = raw(manifest)
    with zipfile.ZipFile(target, "w") as z:
        for n, v in files.items():
            z.writestr(n, v)


def test_corruption_schema_and_environment_fail_closed(tmp_path):
    import hashlib

    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        ident = saved_profile(store, r, work)
        path, _, _ = bundle(store, ident, tmp_path)
        bad = tmp_path / "bad.vurepro"
        rewrite(path, bad, lambda files, m: files.update({"config.json": b"{}"}))
        with pytest.raises(ProjectError, match="size|hash"):
            open_bundle(bad)
        migrated = tmp_path / "future.vurepro"
        rewrite(path, migrated, lambda files, m: m.update(schema="ReproBundle/v999"))
        with pytest.raises(ProjectError, match="migration"):
            open_bundle(migrated)
        changed = tmp_path / "newenv.vurepro"

        def newenv(files, m):
            env = json.loads(files["environment.lock.json"])
            env["workflow"]["environment"]["statsmodels"] = "999.0"
            b = raw(env)
            files["environment.lock.json"] = b
            m["members"]["environment.lock.json"] = dict(
                size=len(b), sha256=hashlib.sha256(b).hexdigest()
            )

        rewrite(path, changed, newenv)
        open_bundle(changed)  # data-only integrity is not a backend compatibility claim
        out = tmp_path / "verify"
        out.mkdir()
        with pytest.raises(ProjectError, match="backend/code/platform"):
            rerun(changed, str(store.root), "numeric", out)


def test_secret_redaction_and_data_rejection(tmp_path, monkeypatch):
    secret = "password=never-export-this-value"
    monkeypatch.setenv("FAKE_API_TOKEN", secret)
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "password": [secret] * 3})
    )
    with closing(store):
        ident = saved_profile(store, r, work)
        # User annotation and absolute file paths in historical capture must be redacted.
        record = store.state["results"][-1]
        record["profile"]["provenance"]["environment"] = [
            ["password", secret],
            ["path", "/home/person/private"],
        ]
        path, p, _ = bundle(store, ident, tmp_path)
        with zipfile.ZipFile(path) as z:
            allbytes = b"".join(z.read(n) for n in z.namelist())
        assert secret.encode() not in allbytes and b"/home/person" not in allbytes
        assert b"FAKE_API_TOKEN" not in allbytes and b"/proc/" not in allbytes
        with pytest.raises(ProjectError, match="Secret adlı"):
            bundle(store, ident, tmp_path, True)
        assert not any(Path(tmp_path).glob("*.pkl"))


def test_workflow_safe_model_artifact_and_numeric_policy(tmp_path):
    store, r, _ = prepare(
        tmp_path,
        pl.DataFrame(
            {"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], "y": [2.0, 4.1, 5.9, 8.0, 10.1, 11.9]}
        ),
    )
    export = tmp_path / "export"
    export.mkdir()
    with closing(store):
        value = run(
            store, recipe(r, True), tmp_path, allow_export=True, output_dir=str(export)
        )
        state = publish(store, store.state, value)
        ident = state["results"][-1]["id"]
        path, p, _ = bundle(store, ident, tmp_path)
        assert p["rerun_supported"], p["redactions"]
        out = tmp_path / "verify"
        out.mkdir()
        result = rerun(path, str(store.root), "numeric", out)
        assert result["status"] == "matched", result
        reference = {
            "m": dict(coefficients=[2.0], predictions=[3.0], row_ids=["row:original"])
        }
        actual = copy.deepcopy(reference)
        actual["m"]["coefficients"][0] += 1e-10
        assert (
            compare(reference, actual, dict(kind="workflow"), "numeric")["status"]
            == "matched"
        )
        assert (
            compare(reference, actual, dict(kind="workflow"), "exact")["status"]
            == "different"
        )
        actual["m"]["row_ids"] = ["row:other"]
        assert (
            compare(reference, actual, dict(kind="workflow"), "numeric")["status"]
            == "different"
        )


def test_changed_data_does_not_pass_numeric_tolerance(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        ident = saved_profile(store, r, work)
        path, _, _ = bundle(store, ident, tmp_path)
        native = store.path(r["snapshot_uri"])
        old = native.read_bytes()
        try:
            native.write_bytes(old + b"changed")
            out = tmp_path / "verify"
            out.mkdir()
            with pytest.raises(ProjectError, match="fingerprint|hash|checksum|değiş"):
                rerun(path, str(store.root), "numeric", out)
        finally:
            native.write_bytes(old)


def test_multisource_graph_preserves_recorded_relation_uri(tmp_path):
    from test_relational import add_source, join_params

    store, r, work = prepare(tmp_path, pl.DataFrame({"key": [1, 2], "x": [10, 20]}))
    with closing(store):
        other = add_source(
            store, work, pl.DataFrame({"key": [1, 3], "value": [30, 40]})
        )
        r["secondary"] = other
        result = calculate(
            r, operation(r, "join", [column(r, "key")], join_params(r, other)), work
        )
        d = store.publish_operation(result)
        g = graph(store.state, store.manifest, d["version_id"])
        join = next(
            n
            for n in g["nodes"]
            if n["kind"] == "operation" and n["metadata"]["spec"]["kind"] == "join"
        )
        assert {e["source"] for e in g["edges"] if e["target"] == join["id"]} == {
            r["version_id"],
            other["version_id"],
        }
        dataset = next(n for n in g["nodes"] if n["id"] == d["version_id"])
        relation = dataset["metadata"]["row_lineage"]
        assert (
            relation["uri"] == d["lineage_uri"] and relation["fingerprint"]["size"] > 0
        )
        edges = pl.read_parquet(store.path(relation["uri"]))
        assert set(edges["input_version_id"]) == {r["version_id"], other["version_id"]}
        assert "not_recorded" not in str(relation)
        dest, p, _ = bundle(store, d["version_id"], tmp_path)
        assert not p[
            "rerun_supported"
        ]  # dataset-level lineage is not a join replay adapter
        assert relation["uri"].encode() in raw(
            open_bundle(dest)["payload"]["lineage.json"]
        )


def test_malicious_bundle_paths_methods_duplicates_and_budget(tmp_path):

    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        ident = saved_profile(store, r, work)
        path, p, _ = bundle(store, ident, tmp_path)
        invalid = tmp_path / "invalid.vurepro"

        def path_injection(files, m):
            m["references"][0]["version_id"] = "dv:../../outside"

        rewrite(path, invalid, path_injection)
        with pytest.raises(ProjectError):
            open_bundle(invalid)
        method = tmp_path / "method.vurepro"
        rewrite(path, method, lambda files, m: m["methods"].update(workflow=99))
        with pytest.raises(ProjectError, match="method/version"):
            open_bundle(method)
        duplicate = tmp_path / "duplicate.vurepro"
        with zipfile.ZipFile(path) as z, zipfile.ZipFile(duplicate, "w") as out:
            for n in z.namelist():
                out.writestr(n, z.read(n))
            out.writestr("config.json", b"{}")
        with pytest.raises(ProjectError, match="duplicate"):
            open_bundle(duplicate)
        from dataclasses import replace

        from veri_ufku.domain.contracts import ComputeBudget
        from veri_ufku.importers.delimited import Control

        tiny = Control(budget=replace(ComputeBudget(), temp_disk_bytes=16))
        with pytest.raises(ProjectError, match="budget"):
            build(
                store,
                ident,
                False,
                p["preview_hash"],
                work,
                tmp_path / "tiny.vurepro",
                tiny,
            )
        stale = copy.deepcopy(store.state)
        store.state["results"][-1]["profile"]["provenance"]["created_at"] = "new-time"
        with pytest.raises(ProjectError, match="önizleme"):
            build(
                store, ident, False, p["preview_hash"], work, tmp_path / "stale.vurepro"
            )
        store.state = stale


def test_preview_redaction_disables_changed_config_and_legacy_no_replay(tmp_path):
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        spec = recipe(r)
        from test_workflow import node

        spec["nodes"].insert(
            1,
            node(
                "rename",
                "transform",
                dict(
                    kind="rename",
                    columns=[column(r, "x")],
                    parameters=dict(name="not exported name"),
                ),
                "source",
            ),
        )
        state = publish(store, store.state, run(store, spec, tmp_path))
        ident = state["results"][-1]["id"]
        p = preview(store, ident)
        assert not p["rerun_supported"] and p["replay"] is None
        assert any("name" in c["field"] for c in p["redactions"])
        legacy = "result:" + uid()
        store.state["results"].append(
            dict(
                id=legacy,
                dataset_version_ids=[r["version_id"]],
                seed=None,
                export=dict(format="html"),
            )
        )
        p = preview(store, legacy)
        assert not p["rerun_supported"]
        assert not any(n["kind"] == "analysis" for n in p["lineage"]["nodes"])


def test_profile_tolerance_never_loosens_decimal_or_integer(tmp_path):
    reference = dict(count=3, numeric=dict(mean="2.0000000000000000001"), used_n=3)
    changed = copy.deepcopy(reference)
    changed["numeric"]["mean"] = "2.0000000000000000002"
    result = compare(reference, changed, dict(kind="profile"), "numeric")
    assert result["status"] == "different"
    changed = copy.deepcopy(reference)
    changed["count"] = 3.0
    assert (
        compare(reference, changed, dict(kind="profile"), "numeric")["status"]
        == "different"
    )
    with pytest.raises(ProjectError):
        compare(reference, changed, dict(kind="profile"), "anything")


def test_data_pattern_and_external_path_redaction(tmp_path):
    value = dict(
        password="plain-secret",
        credential_ref="keyring:something",
        path="/very/private",
        description="personal free note",
        extra="https://user:secret@example.org/private",
        environment=dict(API_TOKEN="secret-in-env"),
        unknown="Bearer 0123456789",
    )
    value["historical_pairs"] = [
        ["password", "plain-pair-secret"],
        ["path", "relative-external-file"],
    ]
    clean, redactions = sanitize(value)
    encoded = raw(clean)
    assert all(
        v.encode() not in encoded
        for v in (
            "plain-secret",
            "secret-in-env",
            "0123456789",
            "keyring:something",
            "/very/private",
            "user:secret",
            "personal free note",
            "plain-pair-secret",
            "relative-external-file",
        )
    )
    assert redactions and all("value" not in v for v in redactions)
    store, r, work = prepare(
        tmp_path,
        pl.DataFrame({"x": [1.0, 2.0, 3.0], "text": ["Bearer private-token"] * 3}),
    )
    with closing(store):
        ident = saved_profile(store, r, work)
        with pytest.raises(ProjectError, match="Secret örüntüsü"):
            bundle(store, ident, tmp_path, True)


def test_workflow_graph_traces_model_and_report_nodes(tmp_path):
    store, r, _ = prepare(
        tmp_path,
        pl.DataFrame(
            {"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], "y": [2.0, 4.1, 5.9, 8.0, 10.1, 11.9]}
        ),
    )
    export = tmp_path / "export"
    export.mkdir()
    with closing(store):
        value = run(
            store, recipe(r, True), tmp_path, allow_export=True, output_dir=str(export)
        )
        state = publish(store, store.state, value)
        ident = state["results"][-1]["id"]
        model = ident + "/default/fit"
        g = graph(state, store.manifest, ident + "/default/export")
        assert any(n["id"] == model and n["kind"] == "model" for n in g["nodes"])
        assert any(n["kind"] == "source" for n in g["nodes"])
        assert any(
            e["source"] == model and e["target"] == ident + "/default/predict"
            for e in g["edges"]
        )
        assert any(
            n["id"] == ident + "/default/export" and n["kind"] == "report"
            for n in g["nodes"]
        )


def test_canceled_bundle_never_publishes_and_environment_captures_no_env(
    tmp_path, monkeypatch
):
    from threading import Event

    from veri_ufku.importers.delimited import Control
    from veri_ufku.jobs.workers import Canceled

    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "plain-value-never-export")
    assert b"plain-value-never-export" not in raw(environment())
    store, r, work = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 6.0]})
    )
    with closing(store):
        ident = saved_profile(store, r, work)
        p = preview(store, ident)
        event = Event()
        event.set()
        with pytest.raises(Canceled):
            build(
                store,
                ident,
                False,
                p["preview_hash"],
                work,
                tmp_path / "cancel.vurepro",
                Control(event),
            )
        assert not (tmp_path / "cancel.vurepro").exists()


def test_metadata_worker_and_budget_probe_do_not_load_model_runtime(tmp_path):
    import subprocess
    import sys

    code = 'from veri_ufku.importers.delimited import Control; from veri_ufku.exports.repro import environment; import sys; Control().check(); environment(); assert "torch" not in sys.modules and "sklearn" not in sys.modules'
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr


def test_workflow_preview_hash_stable_across_hash_seeds(tmp_path):
    import os
    import subprocess
    import sys

    store, r, _ = prepare(
        tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.1, 5.9, 8.0]})
    )
    export = tmp_path / "export"
    export.mkdir()
    with closing(store):
        state = publish(
            store,
            store.state,
            run(
                store,
                recipe(r, True),
                tmp_path,
                allow_export=True,
                output_dir=str(export),
            ),
        )
        ident = state["results"][-1]["id"]
        expected_plan = preview(store, ident)
        expected = expected_plan["preview_hash"]
        code = "from contextlib import closing; from veri_ufku.storage.project_store import ProjectStore; from veri_ufku.exports.repro import preview; import sys; s=ProjectStore.open(sys.argv[1],writable=False); import json; print(json.dumps(preview(s,sys.argv[2]))); s.close()"
        for seed in ("1", "2", "3"):
            result = subprocess.run(
                [sys.executable, "-c", code, str(store.root), ident],
                env={**os.environ, "PYTHONHASHSEED": seed},
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, result.stderr
            actual_plan = json.loads(result.stdout)
            if actual_plan["preview_hash"] != expected:

                def differences(a, b, path="root"):
                    if isinstance(a, dict) and isinstance(b, dict):
                        return [
                            v
                            for k in a.keys() | b.keys()
                            if k not in ("captured_hardware", "preview_hash")
                            for v in differences(a.get(k), b.get(k), path + "." + k)
                        ]
                    if isinstance(a, list) and isinstance(b, list):
                        if len(a) != len(b):
                            return [path + " length"]
                        return [
                            v
                            for i, (x, y) in enumerate(zip(a, b, strict=True))
                            for v in differences(x, y, path + "." + str(i))
                        ]
                    return [path] if a != b else []

                pytest.fail(str(differences(expected_plan, actual_plan)))
            assert actual_plan["preview_hash"] == expected


def test_legacy_dataset_without_import_metadata_keeps_graph_not_invented(tmp_path):
    store, r, _ = prepare(tmp_path, pl.DataFrame({"x": [1.0, 2.0, 3.0]}))
    with closing(store):
        store.state["datasets"][0].pop("import_metadata")
        p = preview(store, r["version_id"])
        assert not p["rerun_supported"] and p["references"] == []
        assert p["unavailable_reference_versions"] == [r["version_id"]]
        d = next(n for n in p["lineage"]["nodes"] if n["kind"] == "dataset")
        assert d["metadata"]["schema"] == "not_recorded"
        with pytest.raises(ProjectError, match="Legacy dataset"):
            preview(store, r["version_id"], True)
