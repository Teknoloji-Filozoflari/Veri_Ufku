"""Derive a versioned Linux/x86_64 core/extra profile from the fixed uv lock format."""

import hashlib
import json
import tomllib
from pathlib import Path

from packaging.markers import Marker, default_environment

ROOT = Path(__file__).resolve().parents[1]


def profile(root=ROOT):
    raw = (root / "uv.lock").read_bytes()
    lock = tomllib.loads(raw.decode())
    if lock.get("version") != 1 or lock.get("revision") != 5:
        raise ValueError(
            "Unreviewed uv lock schema; regenerate adapter against pinned uv"
        )
    packages = {p["name"]: p for p in lock["package"]}
    if len(packages) != len(lock["package"]):
        raise ValueError("Multiple resolved package versions need explicit selector")
    app = packages["veri-ufku"]
    groups = {"core": app["dependencies"], **app.get("optional-dependencies", {})}
    env = {
        **default_environment(),
        "sys_platform": "linux",
        "platform_system": "Linux",
        "platform_machine": "x86_64",
        "python_version": "3.13",
        "python_full_version": "3.13.15",
        "extra": "",
    }

    def closure(entries):
        seen = set()
        visited = set()

        def visit(d):
            if d.get("marker") and not Marker(d["marker"]).evaluate(env):
                return
            n = d["name"]
            extras = tuple(sorted(d.get("extra", [])))
            key = (n, extras)
            if key in visited:
                return
            visited.add(key)
            seen.add(n)
            p = packages[n]
            for dep in p.get("dependencies", []):
                visit(dep)
            for extra in extras:
                for dep in p.get("optional-dependencies", {}).get(extra, []):
                    visit(dep)

        for d in entries:
            visit(d)
        return {n: packages[n]["version"] for n in sorted(seen)}

    result = dict(
        schema="EnvironmentLock/v1",
        python="3.13.15",
        platform="linux-x86_64",
        app_version=app["version"],
        lock_sha256=hashlib.sha256(raw).hexdigest(),
        groups={g: closure(deps) for g, deps in groups.items()},
        worker_environments=dict(
            status="not-configured",
            policy="Explicit separate worker environments required for incompatible stacks; no automatic install or routing; same-runtime extras only currently wired",
        ),
        offline_installer="unavailable: app bundle alone does not contain Flatpak runtime/OS prerequisites",
        local_extra_installer="unavailable: no reviewed local wheelhouse provisioning into running app",
        model_weights="model-specific explicit local folder import only; no universal installer or model license guarantee",
    )
    return result


if __name__ == "__main__":
    p = ROOT / "src/veri_ufku/packaging/environment-lock.json"
    p.write_text(json.dumps(profile(), ensure_ascii=False, indent=2) + "\n")
    print(p)
