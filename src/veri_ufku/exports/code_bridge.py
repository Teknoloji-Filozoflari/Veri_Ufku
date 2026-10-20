"""Closed GUI profile -> readable Python/SQLite/notebook; reference-only bundles."""

import hashlib
import importlib.metadata as md
import json
import platform
import re
import sqlite3
import zipfile
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path

from packaging.requirements import Requirement

from veri_ufku.analytics.contracts import ProfileSpec
from veri_ufku.analytics.dataset import checked, profile
from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.exports.files import publish
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, entity_id
from veri_ufku.storage.project_store import ProjectStore

MAX_CODE = 16384
SQL = """-- SQLite3. Input table aliases protect source names; no data literals.
-- input_data contains only the selected immutable column, first-N if requested.
-- Parameters: :finite_bound (maximum finite IEEE754 Float64).
SELECT COUNT(*) AS used_n,
       COALESCE(SUM(CASE WHEN value IS NULL THEN 1 ELSE 0 END), 0) AS null_n,
       COUNT(CASE WHEN value BETWEEN -:finite_bound AND :finite_bound THEN value END) AS finite_n,
       MIN(CASE WHEN value BETWEEN -:finite_bound AND :finite_bound THEN value END) AS minimum,
       MAX(CASE WHEN value BETWEEN -:finite_bound AND :finite_bound THEN value END) AS maximum,
       AVG(CASE WHEN value BETWEEN -:finite_bound AND :finite_bound THEN value END) AS mean
FROM input_data;
"""


@dataclass(frozen=True)
class CodeRecipe:
    column_id: str
    sample: bool = True
    ddof: int = 1
    sample_limit: int = 10000
    task: str = "profile"

    @classmethod
    def from_dict(cls, raw):
        try:
            r = cls(**raw)
        except (TypeError, ValueError):
            raise ProjectError("CodeRecipe kapalı şema geçersiz.") from None
        entity_id(r.column_id, "col")
        if (
            r.task != "profile"
            or type(r.sample) is not bool
            or type(r.ddof) is not int
            or r.ddof not in (0, 1)
            or type(r.sample_limit) is not int
            or not 1 <= r.sample_limit <= 10000
        ):
            raise ProjectError(
                "Yalnız dataset numeric profile, first-N<=10000 ve ddof0/1 destekli."
            )
        return r

    def data(self):
        return asdict(self)


def environment():
    """Exact installed runtime closure: names/versions only, no URLs/env/credentials."""
    pins = {}
    todo = ["veri-ufku"]
    while todo:
        name = todo.pop()
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key in pins:
            continue
        dist = md.distribution(name)
        v = dist.version
        if not re.fullmatch(r"[a-z0-9-]{1,80}", key) or not re.fullmatch(
            r"[A-Za-z0-9.+!-]{1,80}", v
        ):
            raise ProjectError("Environment name/version kapalı alan sınırı.")
        pins[key] = v
        for text in dist.requires or ():
            req = Requirement(text)
            if req.marker is None or req.marker.evaluate({"extra": ""}):
                todo.append(req.name)
    return dict(
        python=platform.python_version(),
        implementation=platform.python_implementation(),
        machine=platform.machine(),
        packages=dict(sorted(pins.items())),
        engine_hash=engine_hash(),
    )


def engine_hash():
    from veri_ufku.analytics import contracts, dataset

    return digest(
        {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__), Path(contracts.__file__), Path(dataset.__file__))
        }
    )


def reference(request, recipe):
    recipe = CodeRecipe.from_dict(recipe)
    entity_id(request["version_id"], "dv")
    entity_id(request["source_snapshot_id"], "snapshot")
    fp = request["fingerprint"]
    if (
        set(fp) != {"size", "sha256"}
        or type(fp["size"]) is not int
        or fp["size"] < 0
        or not re.fullmatch(r"[0-9a-f]{64}", fp["sha256"])
    ):
        raise ProjectError("Dataset reference fingerprint geçersiz.")
    if recipe.column_id not in {c["id"] for c in request["columns"]}:
        raise ProjectError("ColumnId sürümde yok.")
    return dict(
        schema="DatasetReference/v1",
        dataset_version=request["version_id"],
        source_snapshot_id=request["source_snapshot_id"],
        fingerprint=dict(fp),
        column_id=recipe.column_id,
    )


def resolve(project_root, ref):
    """Opening a reference reads data-only project state; never executes code."""
    if (
        set(ref)
        != {
            "schema",
            "dataset_version",
            "source_snapshot_id",
            "fingerprint",
            "column_id",
        }
        or ref["schema"] != "DatasetReference/v1"
    ):
        raise ProjectError("Dataset reference kapalı şema geçersiz.")
    with closing(ProjectStore.open(project_root, writable=False)) as store:
        d = next(
            (
                d
                for d in store.state["datasets"]
                if d["version_id"] == ref["dataset_version"]
            ),
            None,
        )
        if (
            not d
            or d["import_metadata"]["source_snapshot_id"] != ref["source_snapshot_id"]
        ):
            raise ProjectError(
                "Dataset reference projede yok; remapping otomatik değil."
            )
        request = dict(
            path=str(store.path(d["snapshot_uri"])),
            fingerprint=ref["fingerprint"],
            columns=d["import_metadata"]["columns"],
            semantic_metadata=d.get("semantic_metadata", {}),
            version_id=d["version_id"],
            row_count=d["import_metadata"]["row_count"],
            snapshot_uri=d["snapshot_uri"],
            source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
        )
        reference(request, dict(column_id=ref["column_id"]))
        checked(request, Control())
        # Path is pinned through store's /proc fd, so copy pathname to real project root.
        request["path"] = str(Path(project_root).resolve() / d["snapshot_uri"])
        return request


def verify_environment(expected):
    actual = environment()
    if actual != expected:
        raise ProjectError(
            "Environment/engine lock farklı; aynı Python/paket build'i kullanın. Sessiz uyumluluk varsayılmaz."
        )


def run_profile(request, recipe, workspace, control=None):
    r = CodeRecipe.from_dict(recipe)
    control = control or Control(budget=ComputeBudget(sample_limit_rows=r.sample_limit))
    result = profile(
        request,
        ProfileSpec(r.column_id, sample=r.sample, target="dataset", ddof=r.ddof),
        workspace,
        control,
    )
    if result["role"] != "measurement" or result["numeric"]["suppressed"]:
        raise ProjectError(
            "Kod köprüsü yalnız numeric measurement profilini destekliyor; diğer analizler çevrilmez."
        )
    # Analytical fields only: no examples/raw rows/names/user semantic annotations.
    return {
        k: result[k]
        for k in (
            "counts",
            "numeric",
            "used_n",
            "population_n",
            "scope",
            "sampling_method",
            "representative_sample",
        )
    }


def run_sql(request, recipe, control=None, *, query_text=None):
    """SQLite query-only transaction/authorizer, not SELECT-prefix trust."""
    import math

    import polars as pl

    if query_text is not None and query_text != SQL:
        raise ProjectError(
            "SQL şablonu değişti; GUI eşdeğerliği doğrulanmıyor. Kapalı query.sql kullanın."
        )

    r = CodeRecipe.from_dict(recipe)
    control = control or Control()
    checked(request, control)
    c = next(c for c in request["columns"] if c["id"] == r.column_id)
    dtype = pl.read_parquet_schema(request["path"])[c["name"]]
    if dtype not in (
        pl.Float64,
        pl.Float32,
        pl.Int64,
        pl.Int32,
        pl.Int16,
        pl.Int8,
        pl.UInt32,
        pl.UInt16,
        pl.UInt8,
    ):
        raise ProjectError(
            "SQL equivalence yalnız bounded integer/float; decimal/UInt64/nested yok."
        )
    if request["row_count"] > 100000:
        raise ProjectError("SQLite bridge100000row bütçesi.")
    query = pl.scan_parquet(request["path"]).select(c["name"])
    if r.sample:
        query = query.head(r.sample_limit)
    values = query.collect(engine="streaming").to_series().to_list()
    # sqlite3 turns NaN into NULL, so reject instead of claiming identical counts.
    if any(v is not None and (not math.isfinite(v) or abs(v) > 2**53) for v in values):
        raise ProjectError(
            "SQL eşdeğerliği NaN/inf veya |value|>2^53 için desteklenmiyor; Python profilini kullanın."
        )
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE input_data(value)")
        db.executemany("INSERT INTO input_data VALUES (?)", ((v,) for v in values))
        db.commit()
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
        db.set_authorizer(
            lambda action, *args: (
                sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY
            )
        )
        db.set_progress_handler(lambda: control.check() or 0, 100)
        cursor = db.execute(
            SQL, {"finite_bound": float.fromhex("0x1.fffffffffffffp+1023")}
        )
        row = dict(
            zip([d[0] for d in cursor.description], cursor.fetchone(), strict=True)
        )
        db.set_authorizer(None)
        db.rollback()
    row["null_n"] = row["null_n"] or 0
    checked(request, control)
    return row


SCRIPT = '''"""Generated Veri_Ufku profile: reference-only, explicit execution."""
import argparse
import json
import tempfile
import hashlib
from pathlib import Path
from veri_ufku.exports.code_bridge import resolve, run_profile, run_sql, verify_environment
from veri_ufku.modeling.validation import digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Local original project containing referenced snapshot")
    parser.add_argument("--output", required=True, help="NEW result JSON; may contain sensitive statistics")
    parser.add_argument("--sql", action="store_true", help="SQLite finite summary subset; not full Decimal profile")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    verify_environment(json.loads((root / "environment.lock.json").read_text()))
    recipe = json.loads((root / "recipe.json").read_text())
    reference = json.loads((root / "dataset-reference.json").read_text())
    request = resolve(args.project, reference)
    with tempfile.TemporaryDirectory(prefix="vu-profile-") as work:
        result = run_sql(request, recipe, query_text=(root / "query.sql").read_text()) if args.sql else run_profile(request, recipe, work)
    provenance = dict(dataset_reference_hash=digest(reference), recipe_hash=digest(recipe),
                      code_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      environment_hash=digest(json.loads((root / "environment.lock.json").read_text())),
                      backend="sqlite subset" if args.sql else "GUI Python profile",
                      sql_hash=hashlib.sha256((root / "query.sql").read_bytes()).hexdigest() if args.sql else None)
    # Exclusive create: never overwrite a source or existing output.
    with open(args.output, "x", encoding="utf-8") as out:
        json.dump(dict(result=result, provenance=provenance), out, ensure_ascii=False, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
'''


def bundle(request, recipe, fmt, workspace, destination, project_root, control=None):
    control = control or Control()
    control.check()
    if fmt not in ("python", "sql", "notebook"):
        raise ProjectError("Code export formatı desteklenmiyor.")
    r = CodeRecipe.from_dict(recipe)
    ref = reference(request, r.data())
    env = environment()
    # Never copy request/settings/semantic fields, paths, outputs, cell source or env vars.
    files = {
        "recipe.json": json.dumps(r.data(), indent=2),
        "dataset-reference.json": json.dumps(ref, indent=2),
        "environment.lock.json": json.dumps(env, indent=2),
        "requirements.lock": "\n".join(k + "==" + v for k, v in env["packages"].items())
        + "\n",
        "run.py": SCRIPT,
        "query.sql": SQL,
    }
    files[
        "README.txt"
    ] = """Veri_Ufku reference-only export. No raw data, notebook outputs or credentials included.
Use the same local Veri_Ufku wheel/build and CPython version in environment.lock.json.
requirements.lock pins the installed runtime closure; it is NOT a wheelhouse or offline installer.
Obtain trusted compatible wheels yourself; no install/network action is performed here.
Dataset-reference.json records version/snapshot/ColumnId/fingerprint, NOT a file path or URL.
Provide the original local project explicitly; do not substitute a different dataset silently.
Run: python run.py --project /LOCAL/PROJECT --output /NEW/result.json
SQL subset: add --sql. Runner reads and verifies closed query.sql (edits rejected). query.sql expects input_data(value); parameter finite_bound is IEEE754 max.
run.py --sql loads ONLY the referenced column into a temporary in-memory SQLite table;
then query_only transaction/authorizer denies writes. Source project/snapshot stays read-only.
Python runs the same GUI full-dataset numeric measurement profile engine (no filters).
Sample=true means first immutable N, not random; ddof applies to Python profile only.
SQL returns used/null/finite counts, min/max/mean only: no median/std/quantiles claim.
SQL allows finite Float/Int values |value|<=2^53; otherwise refuses. Mean is floating arithmetic,
compare to GUI Decimal precision80 with tolerance, not byte equality. Empty null_n=0.
Profile aggregates may themselves be sensitive; review generated results before sharing.
Notebook outputs empty/execution_count null. Set PROJECT_PATH/OUTPUT_PATH then run cells in order.
Notebook state can be stale: restart and run all; optional Jupyter is external, not required by desktop.
Only this closed profile recipe converts GUI->code. Arbitrary Python has NO lossless GUI reverse mapping.
Editing code invalidates equivalence; results include recipe/reference/environment hashes.\nScripts hash executed script bytes; notebooks hash saved cell sources and last100 IPython inputs when supplied.\nExternal editor/history instrumentation can be removed by user code; no claim of automatic external notebook tracking.
No OS sandbox. Running arbitrary code has your user filesystem/network permissions even in another process.
"""
    if fmt == "notebook":
        setup = "from pathlib import Path\nimport json, tempfile, hashlib\nfrom veri_ufku.exports.code_bridge import resolve, run_profile, verify_environment\nfrom veri_ufku.modeling.validation import digest\nPROJECT_PATH = None  # Set explicitly; opening notebook does not run this.\nOUTPUT_PATH = None  # New file only.\nBUNDLE_PATH = Path.cwd()  # Folder containing recipe.json and locks\n"
        execute = 'assert PROJECT_PATH is not None and OUTPUT_PATH is not None, "Set explicit local paths"\nverify_environment(json.loads((BUNDLE_PATH / "environment.lock.json").read_text()))\nrecipe = json.loads((BUNDLE_PATH / "recipe.json").read_text())\nreference = json.loads((BUNDLE_PATH / "dataset-reference.json").read_text())\nrequest = resolve(PROJECT_PATH, reference)\nwith tempfile.TemporaryDirectory() as work:\n    result = run_profile(request, recipe, work)\nnotebook = json.loads((BUNDLE_PATH / "analysis.ipynb").read_text())\nsaved_cell_hashes = [hashlib.sha256(str(c["source"]).encode()).hexdigest() for c in notebook["cells"] if c["cell_type"] == "code"]\nshell = get_ipython() if "get_ipython" in globals() else None\nexecuted_cell_hashes = [hashlib.sha256(s.encode()).hexdigest() for s in shell.history_manager.input_hist_raw[-100:]] if shell is not None else []\nprovenance = dict(recipe_hash=digest(recipe), dataset_reference_hash=digest(reference), saved_cell_hashes=saved_cell_hashes, executed_cell_hashes=executed_cell_hashes, history_scope="last100 inputs when external IPython provides them; empty outside IPython", environment_hash=digest(json.loads((BUNDLE_PATH / "environment.lock.json").read_text())))\nwith open(OUTPUT_PATH, "x", encoding="utf-8") as out:\n    json.dump(dict(result=result, provenance=provenance), out, ensure_ascii=False, indent=2, allow_nan=False)\n'
        cells = [
            dict(
                cell_type="markdown",
                id="scope",
                metadata={},
                source="Reference-only numeric GUI profile. Explicit local paths; restart/run-all; no guaranteed reverse conversion. See README.txt.",
            ),
            *[
                dict(
                    cell_type="code",
                    id="cell-" + str(i),
                    metadata={
                        "veri_ufku": {
                            "code_hash": hashlib.sha256(s.encode()).hexdigest()
                        }
                    },
                    source=s,
                    execution_count=None,
                    outputs=[],
                )
                for i, s in enumerate((setup, execute))
            ],
        ]
        files["analysis.ipynb"] = json.dumps(
            dict(
                nbformat=4,
                nbformat_minor=5,
                metadata=dict(
                    kernelspec=dict(
                        display_name="Python3 (external optional)",
                        language="python",
                        name="python3",
                    ),
                    language_info=dict(name="python", version=env["python"]),
                    veri_ufku=dict(
                        recipe_hash=digest(r.data()),
                        reference_hash=digest(ref),
                        engine_hash=env["engine_hash"],
                    ),
                ),
                cells=cells,
            ),
            ensure_ascii=False,
            indent=2,
        )
    files["integrity.json"] = json.dumps(
        {k: hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()}, indent=2
    )
    path = Path(workspace) / "code-bundle.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, value in sorted(files.items()):
            control.check()
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o600 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, value)
    control.disk(workspace, force=True)
    return {
        **publish(path, destination, project_root, control),
        "recipe_hash": digest(r.data()),
        "reference_hash": digest(ref),
        "format": fmt,
    }
