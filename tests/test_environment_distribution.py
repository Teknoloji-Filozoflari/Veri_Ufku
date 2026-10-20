"""Core/extra lock, safe profiles, immutable-source plans and release gates."""

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from veri_ufku.modeling.validation import digest
from veri_ufku.packaging.environment import (
    export_profile,
    import_profile,
    inspect_cache,
    lock_profile,
    scan,
    update_plan,
    validate_report,
)
from veri_ufku.packaging.optional import LazyModule
from veri_ufku.storage.project_model import ProjectError, encode

ROOT = Path(__file__).resolve().parents[1]


def script(name, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_derived_core_optional_lock_matches_actual_lock(monkeypatch):
    generated = script("generate_environment_profile", monkeypatch).profile()
    assert generated == lock_profile()
    core = generated["groups"]["core"]
    for name in (
        "torch",
        "h5py",
        "xarray",
        "rasterio",
        "statsmodels",
        "soundfile",
        "networkx",
        "fastavro",
        "pyreadstat",
    ):
        assert name not in core
    assert "psycopg-binary" in generated["groups"]["connectors"]
    assert core["pyside6"] == "6.11.2" and core["pyarrow"] == "26.0.0"
    assert generated["worker_environments"]["status"] == "not-configured"


def test_report_export_import_approved_closed_metadata_and_no_install(tmp_path):
    report = scan()
    validate_report(report)
    assert report["groups"]["core"]["status"] == "versions-match-not-runtime-validation"
    work = tmp_path / "work"
    work.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    path = tmp_path / "environment.json"
    receipt = export_profile(report, path, project, work)
    assert receipt["report_hash"] == report["report_hash"]
    raw = path.read_bytes()
    assert str(Path.home()).encode() not in raw and b"PASSWORD=" not in raw
    with pytest.raises(ProjectError):
        import_profile(path, False)
    compared = import_profile(path, True)
    assert compared["lock_match"] and compared["effect"].startswith("Comparison only")
    assert path.read_bytes() == raw and not list(project.iterdir())
    with pytest.raises(ProjectError):
        export_profile(report, path, project, work)
    broken = copy.deepcopy(report)
    broken["run"] = "arbitrary executable input"
    broken["report_hash"] = digest(
        {k: v for k, v in broken.items() if k != "report_hash"}
    )
    path.write_bytes(encode(broken))
    with pytest.raises(ProjectError):
        import_profile(path, True)


def test_metadata_secret_path_and_stale_hash_rejected():
    report = scan()
    for name, value in [
        ("password", "RAW_SENTINEL"),
        ("external", "/home/private/data"),
        ("command", "pip install arbitrary"),
    ]:
        r = copy.deepcopy(report)
        r[name] = value
        r["report_hash"] = digest({k: v for k, v in r.items() if k != "report_hash"})
        with pytest.raises(ProjectError):
            validate_report(r)
    report["groups"]["core"]["packages"][0]["actual"] = "changed"
    with pytest.raises(ProjectError):
        validate_report(report)


def test_optional_failure_is_explicit_not_fake_fallback(monkeypatch):
    monkeypatch.setattr(
        "importlib.import_module",
        lambda _: (_ for _ in ()).throw(ImportError("SECRET=DO_NOT_LOG")),
    )
    with pytest.raises(ProjectError) as e:
        LazyModule("h5py", "arrays").File
    assert "arrays" in str(e.value) and "DO_NOT_LOG" not in str(e.value)


def test_local_update_integrity_plan_never_applies_or_migrates(tmp_path):
    import hashlib

    path = tmp_path / "candidate.flatpak"
    path.write_bytes(b"synthetic opaque candidate; integrity only")
    before = path.read_bytes()
    expected = hashlib.sha256(before).hexdigest()
    for approved, sha in [(False, expected), (True, "0" * 64)]:
        with pytest.raises(ProjectError):
            update_plan(path, sha, "a" * 64, approved)
    plan = update_plan(path, expected, "a" * 64, True)
    assert (
        plan["artifact_sha256"] == expected
        and "NOT undo schema migration" in plan["rollback"]["project"]
    )
    assert (
        "External host Flatpak action only" in plan["apply"]
        and path.read_bytes() == before
    )
    assert "integrity only" in plan["artifact_authenticity"]


def test_explicit_cache_hash_no_deserialize_symlink_and_size(tmp_path):
    import hashlib

    root = tmp_path / "model"
    root.mkdir()
    payload = b"not executed"
    (root / "weights.bin").write_bytes(payload)
    with pytest.raises(ProjectError):
        inspect_cache(root, False)
    result = inspect_cache(root, True)
    assert result["files"][0]["sha256"] == hashlib.sha256(payload).hexdigest()
    assert "not-deserialized" in result["files"][0][
        "status"
    ] and "weights.bin" not in str(result)
    (root / "outside").symlink_to(tmp_path)
    with pytest.raises(ProjectError):
        inspect_cache(root, True)


def test_scoped_sbom_and_scan_not_performed_never_claims_clean(monkeypatch):
    m = script("release_inventory", monkeypatch)
    bom = m.inventory()
    assert bom["bomFormat"] == "CycloneDX" and bom["specVersion"] == "1.6"
    names = {c["name"] for c in bom["components"]}
    assert "torch" not in names
    assert "torch" in {c["name"] for c in m.inventory(("neural",))["components"]}
    result = m.scan(online=False)
    assert result["status"] == "not-scanned"
    with pytest.raises(ValueError):
        m.inventory(("untrusted-extra",))


def test_release_ci_readonly_pinned_no_publication():
    import yaml

    raw = (ROOT / ".github/workflows/release-candidate.yml").read_text()
    data = yaml.safe_load(raw)
    assert data["permissions"] == {"contents": "read"}
    events = data.get("on", data.get(True, {}))
    assert "pull_request_target" not in events and "packages: write" not in raw
    assert "persist-credentials: false" in raw
    for step in data["jobs"]["core-candidate"]["steps"]:
        if "uses" in step:
            assert len(step["uses"].split("@")[1].split()[0]) == 40
    assert "--scan --online" in raw and "gh release" not in raw


def test_absent_optional_backends_gui_startup_subprocess(tmp_path):
    # Import blocker + discovery absence simulation is separately identified from actual core Flatpak.
    code = r"""
import importlib.abc,importlib.util,os,sys
blocked={'h5py','h5netcdf','xarray','zarr','pint','soundfile','networkx','statsmodels','fastavro','pyreadstat','pyproj','pyogrio','rasterio','shapely','torch','pymc','arviz','vosk','keyring','cryptography','duckdb','pymysql','psycopg','boto3'}
class Missing(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in blocked:raise ImportError('optional deliberately absent')
sys.meta_path.insert(0,Missing())
find=importlib.util.find_spec
importlib.util.find_spec=lambda name,*a,**k:None if name.split('.')[0] in blocked else find(name,*a,**k)
from veri_ufku.app import create_application
app,window,bridge=create_application()
assert not blocked.intersection(sys.modules)
app._veri_ufku_resources[-1]();window.deleteLater();app.processEvents()
print('OPTIONAL_ABSENCE_GUI PASS')
"""
    import os

    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        **{
            "XDG_" + k + "_HOME": str(tmp_path / k)
            for k in ("CONFIG", "STATE", "CACHE", "DATA")
        },
    }
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stderr[-3000:]
    assert "OPTIONAL_ABSENCE_GUI PASS" in result.stdout
