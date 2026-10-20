"""Live Secret Service integration; absent daemon is explicitly NOT tested."""

import os
from contextlib import closing
from pathlib import Path

import pytest
from phase31_servers import secret_service
from test_privacy import reviewed

from veri_ufku.exports.privacy_keys import generate, load
from veri_ufku.exports.privacy_worker import calculate
from veri_ufku.importers.delimited import Control
from veri_ufku.storage import privacy_store as storage


def test_live_secret_service_pseudonym_sealed_export_reopen(tmp_path, monkeypatch):
    binary = Path(
        os.environ.get(
            "VERI_UFKU_TEST_KEYRING_DAEMON",
            "/tmp/veri-ufku-f31-servers/root/usr/bin/gnome-keyring-daemon",
        )
    )
    if not binary.is_file():
        pytest.skip(
            "Real Secret Service daemon unavailable; live key handling NOT validated"
        )
    keyroot = tmp_path / "service"
    keyroot.mkdir()
    with secret_service(keyroot, binary) as env:
        for k in ("DBUS_SESSION_BUS_ADDRESS", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
            monkeypatch.setenv(k, env[k])
        build = tmp_path / "build"
        build.mkdir()
        store, ref, work, p = reviewed(build)
        with closing(store):
            generate("hmac", "privacy-test-hmac")
            generate("fernet", "privacy-test-fernet")
            p.update(key_ref="privacy-test-hmac")
            p["rules"][0]["strategy"] = "pseudonym"
            storage.review(store, store.state, p)
            rid = store.state["results"][-1]["id"]
            req = storage.request_for(
                store, store.state, dict(action="preview", review_id=rid)
            )
            preview = calculate(req, work, Control())
            assert "hmac_key" not in preview and load(
                "hmac", "privacy-test-hmac"
            ).decode() not in str(preview)
            dest = tmp_path / "safe.vupseal"
            req = storage.request_for(
                store,
                store.state,
                dict(
                    action="export",
                    review_id=rid,
                    format="sealed",
                    destination=str(dest),
                    preview_hash=preview["preview_hash"],
                    reviewed=True,
                    encryption_key_ref="privacy-test-fernet",
                ),
            )
            value = calculate(req, work, Control())
            storage.publish(store, store.state, value)
            req = storage.request_for(
                store,
                store.state,
                dict(
                    action="inspect",
                    archive=str(dest),
                    encryption_key_ref="privacy-test-fernet",
                ),
            )
            opened = calculate(req, work, Control())
            assert opened["manifest"]["rows"] == 3
            for purpose, ref in [
                ("hmac", "privacy-test-hmac"),
                ("fernet", "privacy-test-fernet"),
            ]:
                key = load(purpose, ref)
                assert (
                    key.decode() not in str(store.state)
                    and key not in dest.read_bytes()
                )
                assert all(
                    key not in path.read_bytes()
                    for path in keyroot.rglob("*")
                    if path.is_file()
                )
