"""Real installed Flatpak GUI, workers, report and isolation checks; synthetic data."""

import argparse
import hashlib
import json
import os
import platform
import socket
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace


def run(output):
    import sys

    from PySide6.QtCore import QLibraryInfo, qVersion

    import veri_ufku

    site = Path("/app/lib/python3.13/site-packages")
    assert Path(veri_ufku.__file__).is_relative_to(site)
    assert not any("/.venv/" in p for p in sys.path)
    assert os.path.isfile("/.flatpak-info")
    errors = {}
    for family, address in (
        (socket.AF_INET, ("198.51.100.1", 9)),
        (socket.AF_INET6, ("2001:db8::1", 9)),
    ):
        with socket.socket(family) as stream:
            stream.settimeout(1)
            try:
                stream.connect(address)
            except OSError as error:
                errors[str(family)] = error.errno
            else:
                raise AssertionError("Flatpak network unexpectedly reachable")
    assert all(value in (99, 101) for value in errors.values()), errors
    output.mkdir(parents=True, exist_ok=True)
    from measure_phase13 import run as walkthrough

    walkthrough(
        SimpleNamespace(
            package_root=site, project_temp=None, output=output / "gui.json"
        )
    )
    gui = json.loads((output / "gui.json").read_text())
    gui["environment"] = "ENV-27"
    gui["date"] = datetime.now(UTC).isoformat()
    gui["backend"] = os.environ.get("QT_QPA_PLATFORM", "native")
    gui["offline_policy"] = (
        "Flatpak OS network namespace, no share=network; native sockets refused before walkthrough monkeypatch"
    )
    (output / "gui.json").write_text(
        json.dumps(gui, ensure_ascii=False, indent=2) + "\n"
    )
    record = dict(
        date=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        qt=qVersion(),
        package=str(veri_ufku.__file__),
        flatpak_info=Path("/.flatpak-info").read_text(),
        plugins=QLibraryInfo.path(QLibraryInfo.PluginsPath),
        qml=QLibraryInfo.path(QLibraryInfo.QmlImportsPath),
        namespace=os.readlink("/proc/self/ns/net"),
        network_errors=errors,
        backend=os.environ.get("QT_QPA_PLATFORM", "native"),
        scale=os.environ.get("QT_SCALE_FACTOR", "1"),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (output / "environment.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    )
    print("FLATPAK GUI PASS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
