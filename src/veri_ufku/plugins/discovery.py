"""Explicit manifest inspection; no plugin imports, pip installs or startup scanning."""

import hashlib
import importlib.metadata
import platform
import sys
from pathlib import Path

from veri_ufku.domain.capabilities import CAPABILITIES
from veri_ufku.domain.contracts import (
    Capability,
    ExecutionKind,
    InputRole,
    InputSchema,
    LearningLink,
    MethodSupport,
    Parameter,
)
from veri_ufku.modeling.validation import digest
from veri_ufku.plugins.sdk import manifest
from veri_ufku.storage.project_model import ProjectError, decode


def inspect(path):
    path = Path(path).absolute()
    if (
        path.is_symlink()
        or path.name != "manifest.json"
        or path.parent.resolve() != path.parent
        or not path.is_file()
        or path.stat().st_size > 65536
    ):
        raise ProjectError(
            "Plugin explicit yerel manifest.json, symlink olmayan yol ve64KiB sınırı gerekli."
        )
    raw = path.read_bytes()
    m = manifest(decode(raw))
    code = path.parent / "plugin.py"
    if code.is_symlink() or not code.is_file() or code.stat().st_size > 65536:
        raise ProjectError(
            "Plugin self-contained plugin.py64KiB sınırı; zip/install çalıştırılmaz."
        )
    source = code.read_bytes()
    if hashlib.sha256(source).hexdigest() != m["code_sha256"]:
        raise ProjectError(
            "Plugin kod hash'i manifestle uyuşmuyor; güveni yeniden değerlendirin."
        )
    try:
        source.decode("utf-8")
    except UnicodeError:
        raise ProjectError("Plugin UTF8 Python kaynak gerekli.") from None
    dependencies = {}
    missing = []
    for name, expected in m["dependencies"].items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = "missing"
        dependencies[name] = dict(expected=expected, actual=actual)
        if actual != expected:
            missing.append(name)
    if platform.python_version_tuple()[:2] != ("3", "13"):
        missing.append("Python3.13")
    env = dict(
        python=platform.python_version(),
        executable=sys.executable,
        dependencies=dependencies,
        isolation="same locked application environment; no automatic dependency install; fresh process, NOT OS sandbox",
    )
    result = dict(
        schema="PluginInspection/v1",
        manifest=m,
        package_hash=digest(dict(manifest=m, code_sha256=m["code_sha256"])),
        environment=env,
        compatible=not missing,
        missing=missing,
        trust="Arbitrary Python retains same-user filesystem/network/keyring rights. Manifest permissions are disclosures, not OS enforcement. Run only trusted code.",
        runtime="bounded report artifact; importer/transform table previews do not become active datasets; model JSON state has no host predict/load adapter",
    )
    result["inspection_hash"] = digest(result)
    return result, source


def register(inspection):
    """Extend the existing registry only after explicit user inspection/trust."""
    m = inspection["manifest"]
    c = m["capability"]
    ident = "plugin." + m["id"] + "." + c["id"]
    cap = Capability(
        ident,
        ExecutionKind.CPU,
        "plugin_api_v1",
        kind="analysis",
        version=1,
        semantic_version=c["method_version"],
        inputs=InputSchema(
            "PluginInput/v1", (InputRole("selected", ("finite scalar JSON",)),)
        ),
        parameters=tuple(
            Parameter(k, v["type"], v["default"]) for k, v in c["parameters"].items()
        )
        or (Parameter("seed", "integer", 0),),
        support_details=(
            MethodSupport("bounded_json", "supported", "10000rows/1MiBoutput"),
        ),
        operations=(
            MethodSupport("execute", "supported", "explicit trusted process"),
            MethodSupport("persist", "supported", "safe JSON"),
            MethodSupport("predict", "unsupported", "No host model predict adapter"),
        ),
        artifact_kinds=("text",),
        learning=(LearningLink("plugins-sdk"),),
        backend=m["id"] + "@" + m["version"] + " code:" + m["code_sha256"],
        input_schema=c["input_schema"],
        parameter_schema="manifest typed scalar parameters",
        output_type=c["output_schema"],
        help_links=("plugins-sdk",),
        assumptions=(
            "Trusted same-user Python; no OS sandbox",
            "Recorded JSON report remains readable without code; recompute needs explicit trust/hash match",
        ),
        supports=(("cancel", True), ("safe_serialization", True)),
        limits=(("rows", 10000), ("output_bytes", 1048576)),
        evidence_refs=("docs/evidence/PHASE73.md",),
        requirement_ids=("F73-S001", "F73-S002", "F73-S003", "F73-S004"),
    )
    old = CAPABILITIES.get(ident)
    if old and old != cap:
        raise ProjectError(
            "Plugin capability identity/version çakışması; bu oturumda üzerine yazılmaz."
        )
    CAPABILITIES[ident] = cap
    return ident
