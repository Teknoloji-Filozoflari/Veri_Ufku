"""Read-only publication gate catches unsafe inputs without exposing their values."""

import importlib.util
import subprocess
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "check_publish", Path(__file__).resolve().parents[1] / "scripts/check_publish.py"
)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def repository(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.setattr(CHECK, "REQUIRED", ("README.md",))
    (tmp_path / "README.md").write_text("Example project\n")
    return tmp_path


def test_secrets_large_file_and_external_symlink_rejected_without_values(
    tmp_path, monkeypatch
):
    root = repository(tmp_path, monkeypatch)
    token = "ghp_" + "A" * 36
    (root / "secret.txt").write_text(token)
    (root / "outside").symlink_to("/etc/passwd")
    with (root / "large.bin").open("wb") as stream:
        stream.truncate(101 * 1024**2)
    result = CHECK.inspect(root)
    assert {r["reason"] for r in result["errors"]} == {
        "github-token",
        "symlink-needs-review",
        "over-100-MiB",
    }
    assert token not in str(result)
    assert not (root / ".git/index").exists()


def test_ignore_does_not_hide_tracked_credentials(tmp_path, monkeypatch):
    root = repository(tmp_path, monkeypatch)
    (root / ".env").write_text("fixture=yes")
    subprocess.run(["git", "-C", str(root), "add", ".env"], check=True)
    (root / ".gitignore").write_text(".env\n")
    before = (root / ".git/index").read_bytes()
    result = CHECK.inspect(root)
    assert any(r["reason"] == "tracked-but-ignored" for r in result["errors"])
    assert (root / ".git/index").read_bytes() == before


def test_ignored_generated_files_and_required_source(tmp_path, monkeypatch):
    root = repository(tmp_path, monkeypatch)
    (root / ".gitignore").write_text("build/\n")
    (root / "build").mkdir()
    (root / "build/cache").write_text("not an input")
    result = CHECK.inspect(root)
    assert result["candidate_files"] == 2 and result["errors"] == []
    (root / "README.md").unlink()
    assert (
        CHECK.inspect(root)["errors"][0]["reason"]
        == "required-publication-file-missing"
    )
