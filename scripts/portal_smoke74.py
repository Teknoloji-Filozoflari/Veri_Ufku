"""Real document portal grant into a readonly packaged Platform sandbox, no chooser claim."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--builddir", type=Path)
    p.add_argument("--installation", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if bool(a.builddir) == bool(a.installation):
        p.error("select builddir or isolated user installation")
    a.output.mkdir(parents=True, exist_ok=True)
    origin = a.output.parent / "portal-origin"
    origin.mkdir(exist_ok=True)
    source = origin / "portal-source.csv"
    source.write_text("x,y\n1,2\n3,4\n", encoding="utf8")
    granted = subprocess.run(
        [
            "flatpak",
            "document-export",
            "--transient",
            "--app=org.veriufku.Veri_Ufku",
            "--allow-read",
            str(source),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    command = [
        "flatpak",
        "run" if a.installation else "build",
        *([] if a.installation else ["--runtime", "--readonly"]),
        "--unshare=network",
        "--socket=session-bus",
        "--nofilesystem=home",
        "--nofilesystem=xdg-documents",
        "--nofilesystem=xdg-download",
        "--env=QT_QPA_PLATFORM=offscreen",
        "--env=QT_QUICK_BACKEND=software",
        "--filesystem=" + str(a.output.resolve()),
        *(
            ["org.veriufku.Veri_Ufku"]
            if a.installation
            else [str(a.builddir.resolve()), "/app/bin/veri-ufku"]
        ),
        "--environment-smoke",
        "--portal-file",
        granted,
        "--portal-sha256",
        expected,
        "--output",
        str(a.output.resolve() / "portal-package.json"),
    ]
    env = os.environ.copy()
    if a.installation:
        env["FLATPAK_USER_DIR"] = str(a.installation.resolve())
    result = subprocess.run(
        command, env=env, capture_output=True, text=True, timeout=120
    )
    (a.output / "portal-command.json").write_text(
        json.dumps(
            dict(
                granted_path=granted,
                source_sha256=expected,
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                scope="Actual transient Documents portal grant and packaged GUI/worker; not human FileChooser interaction",
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    assert source.read_text() == "x,y\n1,2\n3,4\n"
    result.check_returncode()
    print("PORTAL74 PASS")


if __name__ == "__main__":
    main()
