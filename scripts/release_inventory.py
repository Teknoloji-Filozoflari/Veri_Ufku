"""CycloneDX1.6 lock/package inventory and explicit bounded OSV dependency scan."""

import argparse
import hashlib
import importlib.metadata as md
import json
import ssl
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from generate_environment_profile import profile


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def selected(extras=()):
    p = profile()
    result = dict(p["groups"]["core"])
    for e in extras:
        if e not in p["groups"] or e == "core":
            raise ValueError("Unknown extra")
        result.update(p["groups"][e])
    return p, result


def inventory(extras=(), packaged=None):
    p, packages = selected(extras)
    components = []
    package_records = {x["name"]: x for x in packaged or []}
    components.append(
        dict(
            type="application",
            name="veri-ufku",
            version=p["app_version"],
            **{"bom-ref": "veri-ufku"},
            licenses=[dict(expression="GPL-3.0-or-later")],
        )
    )
    for name, v in sorted(packages.items()):
        c = dict(
            type="library",
            name=name,
            version=v,
            purl="pkg:pypi/" + name + "@" + v,
            **{"bom-ref": name},
            properties=[],
        )
        try:
            dist = md.distribution(name)
            expression = dist.metadata.get("License-Expression")
        except md.PackageNotFoundError:
            expression = None
        if expression:
            c["licenses"] = [dict(expression=expression)]
        else:
            c["properties"].append(
                dict(
                    name="veri_ufku:license-review",
                    value="See bundled exact distribution/native notices; metadata expression absent",
                )
            )
        if name in package_records:
            r = package_records[name]
            if r["version"] != v:
                raise ValueError("Packaged inventory differs from lock")
            c["properties"].append(
                dict(
                    name="veri_ufku:packaged-file-inventory-sha256",
                    value=hashlib.sha256(
                        json.dumps(r["files"], sort_keys=True).encode()
                    ).hexdigest(),
                )
            )
        else:
            c["properties"].append(
                dict(
                    name="veri_ufku:scope",
                    value="lock-only; packaged bytes not supplied",
                )
            )
        components.append(c)
    return dict(
        bomFormat="CycloneDX",
        specVersion="1.6",
        version=1,
        metadata=dict(
            timestamp=datetime.now(UTC).isoformat(),
            properties=[
                dict(name="veri_ufku:lock-sha256", value=p["lock_sha256"]),
                dict(
                    name="veri_ufku:scope",
                    value="Selected Python closure; native libraries/Flatpak runtime require separate runtime inventory and commit records; no vulnerability clearance",
                ),
            ],
        ),
        components=components,
        dependencies=[dict(ref="veri-ufku", dependsOn=sorted(packages))],
    )


def scan(extras=(), online=False):
    p, packages = selected(extras)
    base = dict(
        schema="DependencyScan/v1",
        date=datetime.now(UTC).isoformat(),
        lock_sha256=p["lock_sha256"],
        packages=packages,
        scope="PyPI package/version advisory matches only; OS/native/driver/model data not comprehensively scanned",
        database="OSV API live responses",
        status="not-scanned",
        findings=[],
    )
    if not online:
        return base
    opener = urllib.request.build_opener(
        NoRedirect(),
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
    )
    items = sorted(packages.items())
    try:
        for start in range(0, len(items), 50):
            batch = items[start : start + 50]
            data = json.dumps(
                dict(
                    queries=[
                        dict(package=dict(name=n, ecosystem="PyPI"), version=v)
                        for n, v in batch
                    ]
                )
            ).encode()
            req = urllib.request.Request(
                "https://api.osv.dev/v1/querybatch",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Veri_Ufku-release-audit/1",
                },
                method="POST",
            )
            with opener.open(req, timeout=30) as response:
                raw = response.read(16 * 1024**2 + 1)
            if len(raw) > 16 * 1024**2:
                raise ValueError("OSV response bound")
            value = json.loads(raw)
            if set(value) != {"results"} or len(value["results"]) != len(batch):
                raise ValueError("OSV response schema")
            for (name, ver), entry in zip(batch, value["results"], strict=True):
                if entry.get("next_page_token"):
                    raise ValueError("OSV pagination incomplete; not clean")
                for vuln in entry.get("vulns", []):
                    ident = vuln.get("id", "")
                    if not isinstance(ident, str) or len(ident) > 160:
                        raise ValueError("OSV invalid identifier")
                    base["findings"].append(
                        dict(
                            package=name,
                            version=ver,
                            id=ident,
                            modified=vuln.get("modified"),
                        )
                    )
        base["status"] = (
            "findings-require-review"
            if base["findings"]
            else "no-matches-in-scanned-scope"
        )
    except Exception as e:
        base.update(
            status="scan-unavailable-or-incomplete", error_type=type(e).__name__
        )
    return base


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--extra", action="append", default=[])
    p.add_argument("--all-extras", action="store_true")
    p.add_argument("--inventory", type=Path)
    p.add_argument("--scan", action="store_true")
    p.add_argument("--online", action="store_true")
    a = p.parse_args()
    extras = list(set(profile()["groups"]) - {"core"}) if a.all_extras else a.extra
    value = (
        scan(extras, a.online)
        if a.scan
        else inventory(
            extras, json.loads(a.inventory.read_text()) if a.inventory else None
        )
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    if a.scan:
        print(value["status"])
        if value["status"] not in ("no-matches-in-scanned-scope",):
            raise SystemExit(2)
    else:
        print(
            "SBOM",
            len(value["components"]),
            "components; selected Python inventory only",
        )


if __name__ == "__main__":
    main()
