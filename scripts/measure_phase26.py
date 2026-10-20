"""Five real QML paths in an OS network namespace, with worker inheritance."""

import argparse
import errno
import hashlib
import json
import multiprocessing
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


def network_probe():
    interfaces = [
        line.split(":")[0].strip()
        for line in Path("/proc/net/dev").read_text().splitlines()[2:]
    ]
    failures = []
    for family, address in (
        (socket.AF_INET, ("192.0.2.1", 443)),
        (socket.AF_INET6, ("2001:db8::1", 443, 0, 0)),
    ):
        with socket.socket(family, socket.SOCK_STREAM) as stream:
            stream.settimeout(0.5)
            try:
                stream.connect(address)
            except OSError as error:
                assert error.errno in (errno.ENETUNREACH, errno.EADDRNOTAVAIL), error
                failures.append(dict(family=int(family), errno=error.errno))
            else:
                raise AssertionError("OS namespace unexpectedly has a network route")
    assert interfaces == ["lo"], interfaces
    routes = Path("/proc/net/route").read_text().splitlines()
    assert not [line for line in routes if not line.startswith("Iface")], routes
    return dict(
        net_namespace=os.readlink("/proc/self/ns/net"),
        interfaces=interfaces,
        routes=routes,
        attempts=failures,
    )


def probe_worker(queue):
    queue.put(network_probe())


def recovery_walkthrough(output):
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtTest import QTest

    from veri_ufku.app import create_application

    with tempfile.TemporaryDirectory(
        prefix="vu26-recovery-", dir=output.parent
    ) as folder:
        for key in ("CONFIG", "CACHE", "STATE"):
            os.environ["XDG_" + key + "_HOME"] = str(Path(folder) / key.lower())
        app, window, _ = create_application()
        projects = app._veri_ufku_resources[0]._projects_resources

        def spin(predicate):
            end = time.monotonic() + 15
            while time.monotonic() < end:
                app.processEvents()
                if predicate():
                    return
                QTest.qWait(5)
            raise AssertionError("Recovery UI timeout")

        try:
            projects.request("create", str(Path(folder) / "project"))
            spin(lambda: not projects.busy)
            assert not projects.errorText
            active = (projects.store.root / "ACTIVE").read_bytes()
            projects.setName("Sentetik kurtarma önizlemesi")
            projects.request("autosave")
            spin(lambda: not projects.busy)
            button = window.findChild(QObject, "restoreAutosaveButton")
            button.forceActiveFocus()
            QTest.keyClick(window, Qt.Key_Space)
            dialog = window.findChild(QObject, "recoveryDialog")
            spin(lambda: dialog.property("visible"))
            preview = projects.recoveryPreview
            text = window.findChild(QObject, "recoveryPreviewText").property("text")
            assert preview["name"] in text
            screenshot = output.with_name(output.stem + "-recovery.png")
            QTest.qWait(100)
            assert window.grabWindow().save(str(screenshot))
            dialog.accept()
            spin(lambda: not projects.busy)
            assert projects.dirty and not projects.errorText
            assert (projects.store.root / "ACTIVE").read_bytes() == active
            projects.request("save")
            spin(lambda: not projects.busy)
            assert not projects.dirty and not projects.errorText
            assert (projects.store.root / "ACTIVE").read_bytes() != active
            active = (projects.store.root / "ACTIVE").read_bytes()
            app._veri_ufku_resources[-2].setTextScale(2)
            window.setWidth(720)
            window.setHeight(560)
            projects.setName("Büyük yazıda sentetik kurtarma")
            projects.request("autosave")
            spin(lambda: not projects.busy)
            button.forceActiveFocus()
            QTest.keyClick(window, Qt.Key_Space)
            spin(lambda: dialog.property("visible"))
            assert dialog.property("height") <= window.height()
            large_screenshot = output.with_name(output.stem + "-recovery-200-small.png")
            QTest.qWait(100)
            assert window.grabWindow().save(str(large_screenshot))
            dialog.reject()
            spin(lambda: not dialog.property("visible"))
            assert (projects.store.root / "ACTIVE").read_bytes() == active
            return dict(
                preview=preview,
                manual_preserved_until_save=True,
                screenshot=str(screenshot),
                large_screenshot=str(large_screenshot),
                cancel_preserved_manual=True,
            )
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()


def run(output, parent_namespace, package_root):
    parent = network_probe()
    assert parent["net_namespace"] != parent_namespace
    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    worker = ctx.Process(target=probe_worker, args=(queue,))
    worker.start()
    child = queue.get(timeout=10)
    worker.join(10)
    assert worker.exitcode == 0 and child["net_namespace"] == parent["net_namespace"]
    queue.close()
    queue.join_thread()
    if package_root:
        sys.path.insert(0, str(package_root))
    import veri_ufku

    if package_root:
        assert Path(veri_ufku.__file__).is_relative_to(package_root)
    from measure_phase25 import run as walkthrough

    walkthrough(output.with_name(output.stem + "-walkthrough.json"), package_root)
    recovery = recovery_walkthrough(output)
    root = Path(__file__).resolve().parents[1]
    record = dict(
        date=datetime.now(UTC).isoformat(),
        environment="ENV-26-OFFLINE",
        package=str(veri_ufku.__file__),
        parent=parent,
        spawn=child,
        recovery=recovery,
        scope="Linux user+network namespace: loopback only, no routes; actual native IPv4/IPv6 network/address unreachable; namespace inherited by spawn workers. Five QML/worker/project/export paths; synthetic input only.",
        source_sha256=hashlib.sha256(
            (root / "Veri_Ufku_Birlestirilmis_Gelistirme_Promptlari.md").read_bytes()
        ).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        clean_machine_install=False,
        real_user_test=False,
    )
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print("OFFLINE NAMESPACE PASS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase26/offline.json")
    )
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--inside", action="store_true")
    parser.add_argument("--parent-namespace")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    if args.inside:
        run(args.output, args.parent_namespace, args.package_root)
    else:
        cmd = [
            "unshare",
            "--user",
            "--map-root-user",
            "--net",
            sys.executable,
            str(Path(__file__).resolve()),
            "--inside",
            "--parent-namespace",
            os.readlink("/proc/self/ns/net"),
            "--output",
            str(args.output),
        ]
        if args.package_root:
            cmd += ["--package-root", str(args.package_root.resolve())]
        raise SystemExit(subprocess.call(cmd))
