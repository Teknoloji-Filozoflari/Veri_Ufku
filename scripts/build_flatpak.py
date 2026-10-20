"""Build an actual Flatpak from verified locked runtime files, using official CLI."""

import argparse
import base64
import csv
import fnmatch
import hashlib
import importlib.metadata
import json
import re
import shutil
import subprocess
import sysconfig
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open("rb") as stream:
        h = hashlib.file_digest(stream, "sha256")
    return h.hexdigest()


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def runtime_packages(lock, extras=()):
    from generate_environment_profile import profile

    # Exact reviewed selector handles extra dependency edges (e.g. psycopg[binary]).
    selected = profile()["groups"]
    if any(e not in selected or e == "core" for e in extras):
        raise ValueError("Unknown optional profile")
    wanted = set(selected["core"])
    for extra in extras:
        wanted.update(selected[extra])
    packages = {p["name"]: p for p in lock["package"]}
    return {n: packages[n] for n in sorted(wanted)}


def stage(root, config, extras=()):
    site = Path(sysconfig.get_paths()["purelib"])
    if not site.is_relative_to(ROOT / ".venv"):
        raise ValueError("Run with the locked project's uv Python, never system Python")
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    runtime = runtime_packages(lock, extras)
    destination = root / "files/lib/python3.13/site-packages"
    destination.mkdir(parents=True)
    base_id = config["native-base-app"] + "//" + config["runtime-version"]
    base_commit = subprocess.check_output(
        ["flatpak", "info", "--user", "--show-commit", base_id], text=True
    ).strip()
    if base_commit != config["native-base-app-commit"]:
        raise ValueError("Native dependency BaseApp commit differs from lock")
    base = (
        Path(
            subprocess.check_output(
                ["flatpak", "info", "--user", "--show-location", base_id], text=True
            ).strip()
        )
        / "files"
    )
    for relative, expected in config["native-files"].items():
        source = base / relative
        if sha(source) != expected:
            raise ValueError("Native library differs from reviewed BaseApp")
        target = root / "files" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    installed = {
        normalized(d.metadata["Name"]): d
        for d in importlib.metadata.distributions(path=[str(site)])
    }
    inventory = []
    for name, package in runtime.items():
        dist = installed[normalized(name)]
        if dist.version != package["version"]:
            raise ValueError(f"Unlocked distribution: {name}")
        record = dist.read_text("RECORD")
        if not record:
            raise ValueError(f"Missing wheel RECORD: {name}")
        copied = []
        omitted = []
        for relative, expected, _ in csv.reader(record.splitlines()):
            if any(
                fnmatch.fnmatch(relative, pattern)
                for pattern in config.get("exclude-files", [])
            ):
                omitted.append(relative)
                continue
            source = site / relative
            if (
                not source.resolve().is_relative_to(site)
                or "__pycache__" in source.parts
            ):
                continue
            if not source.is_file():
                raise ValueError(f"Missing installed runtime file: {source}")
            if expected:
                algorithm, value = expected.split("=", 1)
                if (
                    algorithm != "sha256"
                    or base64.urlsafe_b64encode(bytes.fromhex(sha(source)))
                    .decode()
                    .rstrip("=")
                    != value
                ):
                    raise ValueError(f"Modified wheel file: {source}")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(dict(path=relative, sha256=sha(target)))
        inventory.append(
            dict(
                name=name,
                version=dist.version,
                license=dist.metadata.get("License-Expression")
                or dist.metadata.get("License"),
                files=copied,
                omitted=omitted,
                sdist=package.get("sdist"),
                wheels=package.get("wheels"),
            )
        )
    shutil.copytree(
        ROOT / "src/veri_ufku",
        destination / "veri_ufku",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    # Metadata and console script come from the actual built application wheel.
    subprocess.run(
        [
            "uv",
            "build",
            "--wheel",
            "--no-build-isolation",
            "--offline",
            "--out-dir",
            str(root / "wheel"),
        ],
        cwd=ROOT,
        check=True,
    )
    wheel = next((root / "wheel").glob("veri_ufku-*.whl"))
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--no-deps",
            "--no-compile-bytecode",
            "--target",
            str(root / "app-wheel"),
            str(wheel),
        ],
        check=True,
    )
    for p in (root / "app-wheel").glob("*.dist-info"):
        shutil.copytree(p, destination / p.name)
    bin_dir = root / "files/bin"
    bin_dir.mkdir()
    shutil.copy2(ROOT / "packaging/flatpak/veri-ufku", bin_dir / "veri-ufku")
    (bin_dir / "veri-ufku").chmod(0o755)
    share = root / "files/share"
    app_id = config["app-id"]
    for size in (16, 24, 32, 48, 64, 128, 256, 512):
        target = share / f"icons/hicolor/{size}x{size}/apps/{app_id}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f"src/veri_ufku/assets/branding/icon-{size}.png", target)
    launcher = share / f"applications/{app_id}.desktop"
    launcher.parent.mkdir(parents=True)
    shutil.copy2(ROOT / f"src/veri_ufku/assets/branding/{app_id}.desktop", launcher)
    notices = share / "veri-ufku"
    notices.mkdir()
    for file in (
        "LICENSE",
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "docs/THIRD_PARTY_NOTICES.md",
        "docs/USER_GUIDE.md",
        "docs/INSTALL_TR.md",
        "docs/INSTALL_EN.md",
        "docs/PLUGIN_API_EN.md",
        "docs/KNOWN_LIMITATIONS.md",
        "docs/LICENSING.md",
    ):
        shutil.copy2(ROOT / file, notices / Path(file).name)
    shutil.copytree(ROOT / "packaging/flatpak", notices / "build-sources")
    shutil.copy2(
        ROOT / "scripts/build_flatpak.py", notices / "build-sources/build_flatpak.py"
    )
    shutil.copy2(ROOT / "uv.lock", notices / "build-sources/uv.lock")
    shutil.copy2(ROOT / "pyproject.toml", notices / "build-sources/pyproject.toml")
    shutil.copytree(ROOT / "docs/third_party", notices / "third_party")
    checks = notices / "checks"
    checks.mkdir()
    for name in (
        "measure_phase07.py",
        "measure_phase13.py",
        "measure_phase25.py",
        "measure_phase27.py",
        "package_smoke74.py",
    ):
        shutil.copy2(ROOT / "scripts" / name, checks / name)
    from generate_environment_profile import profile

    (notices / "selected-profile.json").write_text(
        json.dumps(
            dict(
                schema="FlatpakProfile/v1",
                lock=profile(),
                extras=list(extras),
                offline_installer=False,
            ),
            indent=2,
        )
        + "\n"
    )
    shutil.copy2(ROOT / "tests/fixtures/projects/schema4.json", checks / "schema4.json")
    (notices / "runtime-inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"
    )
    from release_inventory import inventory as sbom

    (notices / "python-sbom.cdx.json").write_text(
        json.dumps(sbom(extras, inventory), ensure_ascii=False, indent=2) + "\n"
    )
    for name in ("generate_environment_profile.py", "release_inventory.py"):
        shutil.copy2(ROOT / "scripts" / name, notices / "build-sources" / name)
    return inventory


def build(output, extras=()):
    config = json.loads((ROOT / "packaging/flatpak/bundle.json").read_text())
    if output.exists():
        raise FileExistsError(
            "Choose a fresh build directory; existing outputs are preserved"
        )
    output.mkdir(parents=True)
    results = []

    def run(args):
        started = time.monotonic()
        result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
        results.append(
            dict(
                command=args,
                exit_code=result.returncode,
                date=datetime.now(UTC).isoformat(),
                seconds=time.monotonic() - started,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        )
        (output / "commands.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n"
        )
        result.check_returncode()
        return result.stdout.strip()

    for key in ("runtime", "sdk"):
        commit = run(
            [
                "flatpak",
                "info",
                "--user",
                "--show-commit",
                config[key] + "//" + config["runtime-version"],
            ]
        )
        if commit != config[key + "-commit"]:
            raise ValueError(f"{key} commit differs from reviewed packaging lock")
    directory = output / "builddir"
    run(
        [
            "flatpak",
            "build-init",
            "--arch=" + config["arch"],
            str(directory),
            config["app-id"],
            config["sdk"],
            config["runtime"],
            config["runtime-version"],
        ]
    )
    inventory = stage(directory, config, extras)
    run(["flatpak", "build", str(directory), "/app/bin/veri-ufku", "--version"])
    run(
        [
            "flatpak",
            "build-finish",
            "--command=" + config["command"],
            *config["finish-args"],
            str(directory),
        ]
    )
    repo = output / "repo"
    run(
        [
            "flatpak",
            "build-export",
            "--disable-sandbox",
            str(repo),
            str(directory),
            config["branch"],
        ]
    )
    bundle = output / "Veri_Ufku-0.1.0-candidate-x86_64.flatpak"
    run(
        [
            "flatpak",
            "build-bundle",
            str(repo),
            str(bundle),
            config["app-id"],
            config["branch"],
        ]
    )
    record = dict(
        date=datetime.now(UTC).isoformat(),
        config=config,
        bundle=str(bundle),
        bundle_sha256=sha(bundle),
        lock_sha256=sha(ROOT / "uv.lock"),
        dependencies=[dict(name=p["name"], version=p["version"]) for p in inventory],
        published=False,
        selected_extras=list(extras),
        offline_installer=False,
        worker_environment="same runtime selected extras; managed external environments not wired",
    )
    (output / "build.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    )
    print(bundle, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extra", action="append", default=[])
    args = parser.parse_args()
    build(args.output.resolve(), tuple(args.extra))
