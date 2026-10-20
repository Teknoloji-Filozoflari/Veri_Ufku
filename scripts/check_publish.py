"""Read-only Git publication checks; never print matched credential values."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PATTERNS = {
    "github-token": rb"(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})",
    "private-key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "aws-access-key": rb"AKIA[0-9A-Z]{16}",
    "credential-url": rb"https?://[^\s/:]+:[^\s/@]+@",
}
# Exact reviewed synthetic credential-URL fixtures; any changed match still fails.
REVIEWED_URL_FIXTURES = {
    "docs/evidence/phase63/source-native-first.xml": [
        "ec25b8fa54a9d7a878a86e6f38233af24d5d27d184b396136d6d7f0251d33c19"
    ],
    "docs/evidence/phase63/source-native-second.xml": [
        "ec25b8fa54a9d7a878a86e6f38233af24d5d27d184b396136d6d7f0251d33c19"
    ],
    "tests/test_code_bridge.py": [
        "093866188144b0216fb125431572e8ac2df8980dfeeb6ebeb3d9f3987d1e4c1d",
        "ec25b8fa54a9d7a878a86e6f38233af24d5d27d184b396136d6d7f0251d33c19",
    ],
    "tests/test_connectors.py": [
        "ec25b8fa54a9d7a878a86e6f38233af24d5d27d184b396136d6d7f0251d33c19"
    ],
    "tests/test_nlp.py": [
        "7ddcba9e3e77c3b73ed526aa78b7b1219560d13715c1c1bfa6e4556b15e7096b"
    ],
    "tests/test_report_builder.py": [
        "fbddae166ead16d1dd67736b19403ab1ac0095e344f663573848af911a7ce273"
    ],
    "tests/test_repro.py": [
        "ec25b8fa54a9d7a878a86e6f38233af24d5d27d184b396136d6d7f0251d33c19"
    ],
}

REQUIRED = (
    ".gitignore",
    ".python-version",
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "uv.lock",
    "src/veri_ufku/app.py",
    "packaging/flatpak/bundle.json",
    "examples/plugins/mean/manifest.json",
    "output/branding/v2/02-veri-baglari.png",
)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def inspect(root):
    """Inspect current working-tree inputs, not historical commits or binary secrets."""
    paths = sorted(
        set(
            git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
            .decode()
            .rstrip("\0")
            .split("\0")
        )
        - {""}
    )
    errors, warnings = [], []
    for required in REQUIRED:
        if required not in paths or not (root / required).is_file():
            errors.append(
                dict(path=required, reason="required-publication-file-missing")
            )
    ignored = git(root, "ls-files", "-z", "--cached", "--ignored", "--exclude-standard")
    for path in ignored.decode().split("\0"):
        if path:
            errors.append(dict(path=path, reason="tracked-but-ignored"))
    total, count = 0, 0
    for relative in paths:
        path = root / relative
        if path.is_symlink():
            errors.append(dict(path=relative, reason="symlink-needs-review"))
            continue
        if not path.exists():
            continue  # A tracked deletion is a valid publication change.
        if not path.is_file():
            errors.append(dict(path=relative, reason="not-a-regular-file"))
            continue
        size = path.stat().st_size
        count += 1
        total += size
        if size > 100 * 1024**2:
            errors.append(dict(path=relative, reason="over-100-MiB"))
            continue
        if size > 50 * 1024**2:
            warnings.append(dict(path=relative, reason="over-50-MiB"))
        if path.name in {".env", "credentials", "id_rsa", "id_ed25519"}:
            errors.append(dict(path=relative, reason="credential-filename"))
        data = path.read_bytes()
        # Compressed/binary artifacts require a separate review. No safety guarantee.
        if b"\0" in data[:8192]:
            continue
        for name, pattern in PATTERNS.items():
            for match in re.finditer(pattern, data):
                if name == "credential-url" and hashlib.sha256(
                    match.group()
                ).hexdigest() in REVIEWED_URL_FIXTURES.get(relative, ()):
                    continue
                errors.append(dict(path=relative, reason=name))
                break
    return dict(
        candidate_files=count,
        logical_bytes=total,
        errors=errors,
        warnings=warnings,
        scope="working-tree text patterns and file size; not history, PII or binary audit",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect(args.root)
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(content)
    print(content, end="")
    return bool(result["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
