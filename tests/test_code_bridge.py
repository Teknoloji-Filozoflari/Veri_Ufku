"""Phase63 exported-script equivalence, reference hygiene and explicit kernel controls."""

import copy
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.analytics.contracts import ProfileSpec
from veri_ufku.analytics.dataset import profile
from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.exports.code_bridge import (
    CodeRecipe,
    bundle,
    environment,
    resolve,
    run_profile,
    run_sql,
    verify_environment,
)
from veri_ufku.modeling.code_kernel import Kernel, mask
from veri_ufku.modeling.code_workspace import cell_hash, record, validate
from veri_ufku.storage.neural_store import load, publish
from veri_ufku.storage.project_model import ProjectError


def fixture(tmp_path, values=None):
    store, r, w = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                amount=[1.0, 2.0, 3.0, 4.0, None] if values is None else values,
                private=["PRIVATE_ROW_SENTINEL"]
                * (5 if values is None else len(values)),
            )
        ),
    )
    recipe = CodeRecipe(column(r, "amount"), sample=False)
    return store, r, w, recipe


@pytest.mark.parametrize("fmt", ["python", "sql", "notebook"])
def test_reference_export_script_equivalence(tmp_path, fmt, monkeypatch):
    store, r, w, recipe = fixture(tmp_path)
    try:
        r["credential"] = {
            "password": "TOP_SECRET_SENTINEL",
            "url": "https://user:secret@host",
        }
        r["semantic_metadata"] = {
            recipe.column_id: {
                "role": "measurement",
                "confirmed": True,
                "private_note": "TOP_SECRET_SENTINEL",
            }
        }
        monkeypatch.setenv("API_TOKEN", "TOP_SECRET_SENTINEL")
        dest = tmp_path / "bundle.zip"
        receipt = bundle(r, recipe.data(), fmt, w, dest, store.root)
        extracted = tmp_path / "extracted"
        extracted.mkdir()
        with zipfile.ZipFile(dest) as z:
            for name in z.namelist():
                raw = z.read(name)
                for secret in (
                    "PRIVATE_ROW_SENTINEL",
                    "TOP_SECRET_SENTINEL",
                    "user:secret",
                    "private_note",
                    str(store.root),
                    str(tmp_path / "source.parquet"),
                ):
                    assert secret.encode() not in raw, (name, secret)
            z.extractall(extracted)
        assert receipt["format"] == fmt
        expected = run_profile(r, recipe.data(), w)
        output = tmp_path / "result.json"
        env = {
            **os.environ,
            "PYTHONPATH": str(
                Path(__import__("veri_ufku").__file__).resolve().parent.parent
            ),
        }
        p = subprocess.run(
            [
                sys.executable,
                str(extracted / "run.py"),
                "--project",
                str(store.root),
                "--output",
                str(output),
            ],
            env=env,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert p.returncode == 0, p.stderr
        assert json.loads(output.read_text())["result"] == expected
        assert json.loads(output.read_text())["provenance"]["code_hash"]
        sqlout = tmp_path / "sql-result.json"
        sqlrun = subprocess.run(
            [
                sys.executable,
                str(extracted / "run.py"),
                "--project",
                str(store.root),
                "--output",
                str(sqlout),
                "--sql",
            ],
            env=env,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert sqlrun.returncode == 0, sqlrun.stderr
        assert json.loads(sqlout.read_text())["result"]["mean"] == 2.5
        if fmt == "notebook":
            notebook = json.loads((extracted / "analysis.ipynb").read_text())
            assert notebook["nbformat"] == 4
            assert all(
                c["execution_count"] is None and c["outputs"] == []
                for c in notebook["cells"]
                if c["cell_type"] == "code"
            )
            # Execute exported code cells in order, external-kernel semantics; no nbformat dependency.
            ns = {}
            old = Path.cwd()
            try:
                os.chdir(extracted)
                cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
                exec(cells[0]["source"], ns)
                ns["PROJECT_PATH"] = str(store.root)
                ns["OUTPUT_PATH"] = str(tmp_path / "notebook-result.json")
                exec(cells[1]["source"], ns)
                assert (
                    json.loads((tmp_path / "notebook-result.json").read_text())[
                        "result"
                    ]
                    == expected
                )
            finally:
                os.chdir(old)
    finally:
        store.close()


def test_sql_reference_and_unsupported_nonfinite(tmp_path):
    store, r, w, recipe = fixture(tmp_path)
    try:
        gui = profile(r, ProfileSpec(recipe.column_id, sample=False), w)
        sql = run_sql(r, recipe.data())
        assert sql == dict(
            used_n=5, null_n=1, finite_n=4, minimum=1.0, maximum=4.0, mean=2.5
        )
        assert (
            sql["mean"] == float(gui["numeric"]["mean"])
            and sql["finite_n"] == gui["numeric"]["finite_n"]
        )
        locked = environment()
        locked["engine_hash"] = "different"
        with pytest.raises(ProjectError, match="Environment"):
            verify_environment(locked)
        bad = {**r["fingerprint"], "sha256": "0" * 64}
        ref = dict(
            schema="DatasetReference/v1",
            dataset_version=r["version_id"],
            source_snapshot_id=r["source_snapshot_id"],
            fingerprint=bad,
            column_id=recipe.column_id,
        )
        with pytest.raises(ProjectError):
            resolve(store.root, ref)
    finally:
        store.close()


@pytest.mark.parametrize(
    "values", [[1.0, float("nan")], [1.0, float("inf")], [float(2**54), 1.0]]
)
def test_sql_no_silent_semantic_loss(tmp_path, values):
    store, r, w, recipe = fixture(tmp_path, values)
    try:
        with pytest.raises(ProjectError, match="SQL eşdeğerliği"):
            run_sql(r, recipe.data())
    finally:
        store.close()


def test_no_overwrite_and_closed_recipe(tmp_path):
    store, r, w, recipe = fixture(tmp_path)
    try:
        dest = tmp_path / "existing.zip"
        dest.write_bytes(b"existing")
        with pytest.raises(ProjectError):
            bundle(r, recipe.data(), "python", w, dest, store.root)
        assert dest.read_bytes() == b"existing"
        with pytest.raises(ProjectError):
            CodeRecipe.from_dict({**recipe.data(), "password": "secret"})
        with pytest.raises(ProjectError):
            CodeRecipe.from_dict({**recipe.data(), "task": "arbitrary_model"})
    finally:
        store.close()


def run_kernel(tmp_path, source, timeout=3, cancel=False):
    tmp_path.mkdir(exist_ok=True)
    k = Kernel(
        source,
        tmp_path,
        ComputeBudget(max_wall_seconds=5, cancel_grace_ms=100),
        timeout,
    )
    start = time.monotonic()
    try:
        while not k.poll():
            if cancel and time.monotonic() - start > 0.1:
                k.cancel()
            assert time.monotonic() - start < 8
            time.sleep(0.01)
        return k.status, k.display, k.raw_bytes, k.process.returncode
    finally:
        k.close()


@pytest.mark.parametrize(
    "kind", ["success", "timeout", "cancel", "output", "exception", "environment"]
)
def test_fresh_kernel_output_timeout_cancel(tmp_path, kind, monkeypatch):
    monkeypatch.setenv("API_TOKEN", "SECRET_NOT_INHERITED")
    code = {
        "success": 'print("Türkçe çıktı")',
        "timeout": "while True: pass",
        "cancel": "import time\ntime.sleep(30)",
        "output": 'print("x"*1000000)',
        "exception": 'raise RuntimeError("TOP_SECRET_EXCEPTION")',
        "environment": 'import os\nprint(os.getenv("API_TOKEN", "absent"))\nprint("token=secret-value")',
    }[kind]
    status, text, n, _ = run_kernel(
        tmp_path,
        code,
        timeout=0.25 if kind == "timeout" else 3,
        cancel=kind == "cancel",
    )
    expected = {
        "success": "completed",
        "timeout": "timeout",
        "cancel": "canceled",
        "output": "output_limit",
        "exception": "failed",
        "environment": "completed",
    }[kind]
    assert status == expected
    assert n <= 65536
    if kind == "success":
        assert "Türkçe çıktı" in text
    if kind == "exception":
        assert "RuntimeError" in text and "TOP_SECRET_EXCEPTION" not in text
    if kind == "environment":
        assert (
            "absent" in text
            and "[MASKED]" in text
            and "secret-value" not in text
            and "SECRET_NOT_INHERITED" not in text
        )


def test_cell_hash_safe_journal_without_code_or_output(tmp_path):
    store, r, w, recipe = fixture(tmp_path)
    try:
        r.update(run_id="run:code63", prior_test_use_ids=[])
        raw = 'print("PRIVATE_CELL_SECRET")'
        data = record(r, cell_hash(raw), 1, 3)
        state = publish(store, store.state, data)
        data.update(
            status="completed", output_bytes=22, exit_code=0, elapsed_seconds=0.2
        )
        state = publish(store, state, data)
        actual = load(store, state["results"][-1])
        assert actual["code_recipe"]["cell_hash"] == cell_hash(raw)
        assert cell_hash(raw) != cell_hash(raw + "\n")
        assert b"PRIVATE_CELL_SECRET" not in json.dumps(state).encode()
        assert all(
            "model_package_uri" not in rec["neural"]
            for rec in state["results"]
            if "neural" in rec
        )
        bad = copy.deepcopy(actual)
        bad["source"] = "PRIVATE_CELL_SECRET"
        with pytest.raises(ProjectError):
            validate(bad)
        assert (
            mask("https://user:password@host token=abc")
            == "https://[MASKED]@host token=[MASKED]"
        )
    finally:
        store.close()


def test_sql_authority_not_select_prefix(tmp_path, monkeypatch):
    import veri_ufku.exports.code_bridge as bridge

    store, r, w, recipe = fixture(tmp_path)
    before = Path(r["path"]).read_bytes()
    try:
        import sqlite3

        monkeypatch.setattr(
            bridge, "SQL", "WITH x AS (SELECT 1) DELETE FROM input_data;"
        )
        with pytest.raises(sqlite3.DatabaseError):
            run_sql(r, recipe.data())
        assert Path(r["path"]).read_bytes() == before
    finally:
        store.close()


def test_null_physical_type_rejected_and_sample_scope(tmp_path):
    store, r, w, recipe = fixture(tmp_path, [None, None])
    try:
        # All-null physical Null is not silently treated as numeric SQL input.
        with pytest.raises(ProjectError, match="SQL equivalence"):
            run_sql(r, recipe.data())
    finally:
        store.close()
    other = tmp_path / "sample"
    other.mkdir()
    store, r, w, recipe = fixture(other)
    try:
        output = run_profile(r, {**recipe.data(), "sample": True, "sample_limit": 2}, w)
        assert (
            output["used_n"] == 2
            and output["population_n"] == 5
            and output["numeric"]["mean"] == "1.5"
        )
        assert output["scope"] == "sample"
    finally:
        store.close()


def test_kernel_fresh_state_and_no_source_traceback(tmp_path):
    one = tmp_path / "one"
    two = tmp_path / "two"
    assert run_kernel(one, "x=77\nprint(x)")[0] == "completed"
    status, text, _, _ = run_kernel(two, "print(x)")
    assert status == "failed" and text.strip() == "Cell failed: NameError"
    assert not list(two.iterdir())  # Source travels through stdin, never a code file.


def test_process_group_cancel_reaps_nonescaped_children(tmp_path):
    code = 'import subprocess,sys,time\np=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"])\nprint(p.pid,flush=True)\ntime.sleep(30)'
    status, text, _, _ = run_kernel(tmp_path, code, cancel=True)
    assert status == "canceled"
    pid = int(text.strip())
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        path = Path("/proc") / str(pid) / "stat"
        if not path.exists() or path.read_text().split()[2] == "Z":
            break
        time.sleep(0.01)
    else:
        pytest.fail("same-process-group child survived cancel")


def test_kernel_file_budget_not_os_sandbox(tmp_path):
    budget = ComputeBudget(temp_disk_bytes=1024, max_wall_seconds=3)
    k = Kernel(
        'with open("large.bin","wb") as f: f.write(b"x"*4096)', tmp_path, budget, 2
    )
    try:
        deadline = time.monotonic() + 5
        while not k.poll():
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert k.status == "failed"
        assert (tmp_path / "large.bin").stat().st_size <= 1024
    finally:
        k.close()


def test_kernel_memory_budget(tmp_path):
    k = Kernel(
        "a=bytearray(256*1024**2)",
        tmp_path,
        ComputeBudget(ram_bytes=32 * 1024**2, max_wall_seconds=3),
        2,
    )
    try:
        deadline = time.monotonic() + 5
        while not k.poll():
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert k.status in ("failed", "budget_exhausted")
        assert "MemoryError" in k.display or k.status == "budget_exhausted"
    finally:
        k.close()


def test_edited_notebook_hash_changes_without_embedding_source(tmp_path):
    store, r, w, recipe = fixture(tmp_path)
    try:
        dest = tmp_path / "edited.zip"
        bundle(r, recipe.data(), "notebook", w, dest, store.root)
        folder = tmp_path / "nb"
        folder.mkdir()
        with zipfile.ZipFile(dest) as z:
            z.extractall(folder)
        path = folder / "analysis.ipynb"
        nb = json.loads(path.read_text())
        cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
        import hashlib

        old = hashlib.sha256(cells[0]["source"].encode()).hexdigest()
        cells[0]["source"] += "\n# PRIVATE_NOTEBOOK_CODE_SENTINEL"
        path.write_text(json.dumps(nb))
        ns = {}
        exec(cells[0]["source"], ns)
        out = tmp_path / "nb-result.json"
        ns.update(
            PROJECT_PATH=str(store.root), OUTPUT_PATH=str(out), BUNDLE_PATH=folder
        )
        exec(cells[1]["source"], ns)
        report = json.loads(out.read_text())
        assert report["provenance"]["saved_cell_hashes"][0] != old
        assert "PRIVATE_NOTEBOOK_CODE_SENTINEL" not in out.read_text()
    finally:
        store.close()


def test_edited_sql_not_silently_ignored(tmp_path):
    store, r, w, recipe = fixture(tmp_path)
    try:
        with pytest.raises(ProjectError, match="SQL şablonu değişti"):
            run_sql(r, recipe.data(), query_text="SELECT 42;")
    finally:
        store.close()


def test_max_cell_transmitted_without_disk_source(tmp_path):
    source = 'print("whole-cell")\n#' + "a" * 16000
    status, text, _, _ = run_kernel(tmp_path, source)
    assert status == "completed" and text.strip() == "whole-cell"
    assert not list(tmp_path.iterdir())
