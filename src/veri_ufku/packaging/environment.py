"""Bounded local environment inventory; no optional backend imports or network."""

import hashlib
import importlib.metadata as md
import platform
import re
from pathlib import Path

from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, decode, encode

LOCK = Path(__file__).with_name("environment-lock.json")
SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,99}")


def lock_profile():
    return decode(LOCK.read_bytes())


def version(name):
    if name == "python":
        return platform.python_version()
    name = {"sklearn": "scikit-learn", "PIL": "pillow"}.get(name, name)
    try:
        v = md.version(name)
    except md.PackageNotFoundError:
        return None
    return v if SAFE.fullmatch(v) else "unrecognized-version"


def scan(artifact_versions=(), control=None):
    control = control or Control()
    profile = lock_profile()
    groups = {}
    for group, packages in profile["groups"].items():
        rows = []
        for name, expected in packages.items():
            control.check()
            actual = version(name)
            rows.append(
                dict(
                    name=name,
                    expected=expected,
                    actual=actual,
                    status="match"
                    if actual == expected
                    else "missing"
                    if actual is None
                    else "mismatch",
                )
            )
        groups[group] = dict(
            status="versions-match-not-runtime-validation"
            if all(r["status"] == "match" for r in rows)
            else "unavailable-or-incompatible",
            packages=rows,
        )
    from PySide6.QtCore import QLibraryInfo, qVersion

    qtroot = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.QmlImportsPath))
    pluginroot = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    qml = {
        n: (qtroot / n / "qmldir").is_file()
        for n in ("QtQuick", "QtQuick/Controls", "QtQuick/Layouts")
    }
    qplugins = {
        n: any(pluginroot.glob(n))
        for n in (
            "platforms/libqoffscreen.so",
            "platforms/libqwayland*.so",
            "platformthemes/libqxdgdesktopportal.so",
        )
    }
    native = {
        n: dict(
            distribution=version(n),
            status="installed-not-loaded" if version(n) else "missing",
        )
        for n in (
            "rasterio",
            "pyogrio",
            "pyproj",
            "shapely",
            "h5py",
            "soundfile",
            "torch",
        )
    }
    gpu = dict(
        status="not-compute-validated",
        nvidia_driver=None,
        drm_vendors=[],
        cuda_backend=version("torch"),
        automatic_gpu_fallback=False,
    )
    nvidia = Path("/proc/driver/nvidia/version")
    if nvidia.is_file():
        m = re.search(r"\b\d{3,4}\.\d+(?:\.\d+)?\b", nvidia.read_text()[:4096])
        gpu["nvidia_driver"] = m.group() if m else "present-unparsed"
    for p in list(Path("/sys/class/drm").glob("card*/device/vendor"))[:16]:
        try:
            value = p.read_text().strip()
            if re.fullmatch(r"0x[0-9a-fA-F]{4}", value):
                gpu["drm_vendors"].append(value)
        except OSError:
            pass
    artifacts = []
    for r in list(artifact_versions)[:500]:
        # Only closed version strings/identities, never arbitrary project params, paths or values.
        recorded = {
            k: v
            for k, v in r.get("versions", {}).items()
            if isinstance(k, str)
            and SAFE.fullmatch(k)
            and isinstance(v, str)
            and SAFE.fullmatch(v)
        }
        artifacts.append(
            dict(
                id=r["id"],
                recorded_versions=recorded,
                comparison={
                    k: dict(
                        recorded=v,
                        installed=version(k),
                        status="match" if version(k) == v else "missing-or-mismatch",
                    )
                    for k, v in recorded.items()
                },
                policy="Read data-only artifact; recompute/load requires its method-specific compatibility checks",
            )
        )
    result = dict(
        schema="EnvironmentReport/v1",
        python=platform.python_version(),
        expected_python=profile["python"],
        python_match=platform.python_version() == profile["python"],
        platform=profile["platform"],
        host_os=platform.freedesktop_os_release().get("ID", "unknown"),
        lock_sha256=profile["lock_sha256"],
        groups=groups,
        qt=dict(
            version=qVersion(),
            qml=qml,
            plugins=qplugins,
            status="files-present-not-portal-validation",
        ),
        native=native,
        gpu=gpu,
        artifacts=artifacts,
        worker_environments=profile["worker_environments"],
        model_cache=dict(
            status="no-global-model-cache-scan",
            policy="Only explicit user-selected local model folders are inspected; installed name is not model quality/license proof",
        ),
        offline_installer=profile["offline_installer"],
        local_extra_installer=profile["local_extra_installer"],
        limits=[
            "Version metadata is not backend/native/GPU execution validation.",
            "Current runtime extras share one Python; incompatible stacks need separately provisioned environments.",
            "No environment variables, credentials, user data or external file paths exported.",
        ],
    )
    result["report_hash"] = digest(result)
    return result


def export_profile(report, destination, project_root, workspace, control=None):
    from veri_ufku.exports.files import publish

    control = control or Control()
    validate_report(report)
    path = Path(workspace) / "environment.json"
    path.write_bytes(encode(report))
    control.disk(workspace, force=True)
    return dict(
        action="export",
        receipt=publish(path, destination, project_root, control),
        report_hash=report["report_hash"],
    )


def validate_report(value):
    # Exports are immutable inventory data, never executable requirements/commands/paths.
    fields = {
        "schema",
        "python",
        "expected_python",
        "python_match",
        "platform",
        "host_os",
        "lock_sha256",
        "groups",
        "qt",
        "native",
        "gpu",
        "artifacts",
        "worker_environments",
        "model_cache",
        "offline_installer",
        "local_extra_installer",
        "limits",
        "report_hash",
    }
    if (
        not isinstance(value, dict)
        or set(value) != fields
        or value["schema"] != "EnvironmentReport/v1"
        or value["report_hash"]
        != digest({k: v for k, v in value.items() if k != "report_hash"})
    ):
        raise ProjectError("Environment report schema/hash bozuk.")
    if len(encode(value)) > 2 * 1024**2:
        raise ProjectError("Environment report2MiB sınırı.")
    from veri_ufku.exports.share_privacy import scan as sensitive

    if sensitive(value):
        raise ProjectError(
            "Environment raporu hassas değer/yol içeriyor; import/export reddedildi."
        )
    groups = value["groups"]
    if not isinstance(groups, dict) or set(groups) != set(lock_profile()["groups"]):
        raise ProjectError("Environment groups bilinmeyen şema.")
    for group in groups.values():
        if (
            not isinstance(group, dict)
            or set(group) != {"status", "packages"}
            or not isinstance(group["packages"], list)
            or len(group["packages"]) > 256
        ):
            raise ProjectError("Environment package şeması geçersiz.")
        for r in group["packages"]:
            if (
                not isinstance(r, dict)
                or set(r) != {"name", "expected", "actual", "status"}
                or any(
                    not isinstance(r[k], str) or not SAFE.fullmatch(r[k])
                    for k in ("name", "expected")
                )
                or r["actual"] is not None
                and (
                    not isinstance(r["actual"], str) or not SAFE.fullmatch(r["actual"])
                )
            ):
                raise ProjectError("Environment package alanı geçersiz.")
    return value


def import_profile(path, approved, control=None):
    control = control or Control()
    p = Path(path)
    if approved is not True:
        raise ProjectError(
            "Environment import explicit kullanıcı onayı gerekli; kurulum/kod çalıştırma yapılmaz."
        )
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 2 * 1024**2:
        raise ProjectError("Environment import gerçek JSON dosyası2MiB sınırı.")
    control.check()
    value = validate_report(decode(p.read_bytes()))
    current = scan(control=control)
    return dict(
        action="import-review",
        imported_report_hash=value["report_hash"],
        current_report_hash=current["report_hash"],
        lock_match=value["lock_sha256"] == current["lock_sha256"],
        differences=[
            dict(
                group=g,
                name=r["name"],
                imported=r["actual"],
                current=version(r["name"]),
            )
            for g, group in value["groups"].items()
            for r in group["packages"]
            if r["actual"] != version(r["name"])
        ],
        effect="Comparison only: no installation, environment switch, shell execution or project migration",
        report=value,
    )


def update_plan(path, expected_sha256, current_commit, approved, control=None):
    control = control or Control()
    p = Path(path)
    if (
        approved is not True
        or not isinstance(expected_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
        or not isinstance(current_commit, str)
        or not re.fullmatch(r"[0-9a-f]{64}", current_commit)
    ):
        raise ProjectError(
            "Update plan açık onay/trusted expected SHA256 ve mevcut Flatpak commit64hex gerektirir."
        )
    if (
        p.suffix != ".flatpak"
        or p.is_symlink()
        or not p.is_file()
        or p.stat().st_size > 2 * 1024**3
    ):
        raise ProjectError("Update yalnız yerel .flatpak2GiB sınırı.")
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(1024**2):
            control.check()
            h.update(chunk)
    if h.hexdigest() != expected_sha256:
        raise ProjectError("Update artifact hash uyuşmuyor; uygulama/proje değişmedi.")
    result = dict(
        schema="UpdatePlan/v1",
        artifact_sha256=h.hexdigest(),
        size=p.stat().st_size,
        current_commit=current_commit,
        artifact_authenticity="SHA256 integrity only; expected digest must come from independently trusted publisher. Local unsigned candidate is not authenticated release.",
        apply="External host Flatpak action only; GUI does not install/restart or silently change runtime",
        rollback=dict(
            application="Host flatpak update --user --commit="
            + current_commit
            + " org.veriufku.Veri_Ufku; previous commit must still exist locally or in trusted repo",
            project="Application rollback does NOT undo schema migration. Back up the entire closed project first; old app may refuse newer schema; restore separate known-good backup without overwriting newer work.",
        ),
        offline="App bundle alone excludes runtime/driver/OS prerequisites; offline installer capability unavailable",
        requires=[
            "Close app/workers and back up projects separately",
            "Verify publisher provenance/signature outside this candidate planner",
            "Confirm target ref/arch/runtime/extras and available disk",
            "User explicitly selects host Flatpak install/update; then run packaged smoke before opening project",
            "Keep old app commit and project backup separately; do not assume downgrading app downgrades data",
        ],
    )
    result["plan_hash"] = digest(result)
    return result


def inspect_cache(path, approved, control=None):
    control = control or Control()
    root = Path(path)
    if approved is not True or root.is_symlink() or not root.is_dir():
        raise ProjectError(
            "Model cache için explicit gerçek yerel klasör seçimi gerekli."
        )
    files = []
    total = 0
    for p in root.iterdir():
        control.check()
        if len(files) >= 64:
            raise ProjectError("Model cache64entry sınırı; dar klasör seçin.")
        if p.is_symlink() or not p.is_file():
            raise ProjectError(
                "Cache inspect yalnız flat regular files; symlink/subdirectory yok."
            )
        size = p.stat().st_size
        total += size
        if total > 64 * 1024**2:
            raise ProjectError(
                "Cache inspect64MiB sınırı; büyük model bu inspector ile validated sayılmaz."
            )
        h = hashlib.sha256()
        with p.open("rb") as f:
            while chunk := f.read(1024**2):
                control.check()
                h.update(chunk)
        files.append(
            dict(
                alias="file-" + str(len(files) + 1),
                bytes=size,
                sha256=h.hexdigest(),
                format=p.suffix.lower()
                if p.suffix.lower() in (".json", ".safetensors", ".npz", ".bin", ".txt")
                else "other",
                status="bytes-hashed-not-deserialized-or-model-validated",
            )
        )
    return dict(
        action="model-cache-inspection",
        files=files,
        bytes=total,
        status="local bytes only; model-specific schema/license/language/weights validation remains required",
        download="not performed",
        installation="not performed",
    )
