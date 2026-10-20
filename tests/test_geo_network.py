"""Real local TLS server: explicit GET, attribution/cache, bounded responses."""

import json
import ssl
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import pytest
from phase31_servers import tls_files
from rasterio.io import MemoryFile

from veri_ufku.importers.connector_contracts import ConnectorSpec
from veri_ufku.importers.connectors import capture
from veri_ufku.importers.delimited import Control
from veri_ufku.importers.registry import get_adapter
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


@contextmanager
def server(root):
    cert, key = tls_files(root)
    calls = []
    state = {"mode": "normal"}
    with MemoryFile() as memory:
        with memory.open(
            driver="PNG", width=256, height=256, count=1, dtype="uint8"
        ) as ds:
            ds.write(np.full((1, 256, 256), 42, dtype="uint8"))
        image = memory.read()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            calls.append(self.path)
            if state["mode"] == "slow":
                time.sleep(2)
            if state["mode"] == "redirect":
                self.send_response(302)
                self.send_header("Location", "/tile")
                self.end_headers()
                return
            if state["mode"] == "retry" and len(calls) == 1:
                self.send_response(503)
                self.send_header("Retry-After", "0")
                self.end_headers()
                return
            raw = (
                image
                if self.path.startswith("/tile")
                else json.dumps(
                    {
                        "items": [
                            {
                                "id": "place1",
                                "lon": 27.0,
                                "lat": 40.0,
                                "confidence": 0.8,
                            },
                            {
                                "id": "place2",
                                "lon": 28.0,
                                "lat": 41.0,
                                "confidence": 0.6,
                            },
                        ],
                        "next": None,
                        "total": 2,
                    }
                ).encode()
            )
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "image/png" if self.path.startswith("/tile") else "application/json",
            )
            self.send_header("Content-Length", str(len(raw)))
            self.send_header(
                "Cache-Control",
                "no-store" if state["mode"] == "no-store" else "public,max-age=3600",
            )
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ssl.SSLEOFError):
                pass

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    http.socket = ctx.wrap_socket(http.socket, server_side=True)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"https://localhost:{http.server_port}", str(cert), calls, state
    finally:
        http.shutdown()
        http.server_close()
        thread.join()


@pytest.mark.parametrize("kind", ("tile", "geocoding"))
def test_real_tls_capture_preview_publish_reopen_without_network(tmp_path, kind):
    with server(tmp_path) as (url, ca, calls, state):
        spec = ConnectorSpec(
            kind=kind,
            endpoint=url + ("/tile" if kind == "tile" else "/places"),
            ca_file=ca,
            terms_acknowledged=True,
            attribution="Local fixture · test licence",
            cache_policy="project-permitted",
        )
        work = tmp_path / "work"
        work.mkdir()
        snap, settings = capture(spec, None, work, Control())
        adapter = get_adapter(kind)
        preview = adapter.preview(snap, settings, Control())
        assert preview["importable"]
        result = adapter.import_data(snap, settings, work, Control())
        assert len(calls) == 1
        assert (
            result["settings"]["format_metadata"]["connector"]["spec"]["attribution"]
            == "Local fixture · test licence"
        )
        store = ProjectStore.create(tmp_path / "project", "Geo online")
        store.publish_import(result, portable=True)
        store.close()
        store = ProjectStore.open(tmp_path / "project")
        store.close()
        assert len(calls) == 1
        if kind == "tile":
            assert result["settings"]["format_metadata"]["parts"][0]["geospatial"][
                "raster"
            ]
        else:
            assert result["examined"] == 2


@pytest.mark.parametrize(
    "mode,match",
    (("redirect", "HTTP 302"), ("no-store", "no-store"), ("slow", "timeout")),
)
def test_tile_redirect_cache_and_timeout_control(tmp_path, mode, match):
    with server(tmp_path) as (url, ca, calls, state):
        state["mode"] = mode
        spec = ConnectorSpec(
            kind="tile",
            endpoint=url + "/tile",
            ca_file=ca,
            terms_acknowledged=True,
            attribution="fixture",
            cache_policy="project-permitted",
            timeout=1,
            retries=0,
        )
        work = tmp_path / "work"
        work.mkdir()
        with pytest.raises(ProjectError, match=match):
            capture(spec, None, work, Control())
        assert len(calls) == 1


def test_tile_retry_one_result_and_explicit_cancel(tmp_path):
    with server(tmp_path) as (url, ca, calls, state):
        state["mode"] = "retry"
        spec = ConnectorSpec(
            kind="tile",
            endpoint=url + "/tile",
            ca_file=ca,
            terms_acknowledged=True,
            attribution="fixture",
            cache_policy="project-permitted",
        )
        work = tmp_path / "work"
        work.mkdir()
        snap, _ = capture(spec, None, work, Control())
        assert snap and len(calls) == 2
        event = threading.Event()
        event.set()
        with pytest.raises(Canceled):
            capture(spec, None, work, Control(event))
        assert len(calls) == 2


def test_geo_network_terms_cache_attribution_required():
    with pytest.raises(ProjectError, match="Attribution"):
        ConnectorSpec(kind="tile", endpoint="https://example.org/tile")
    with pytest.raises(ProjectError, match="credential"):
        ConnectorSpec(
            kind="geocoding",
            endpoint="https://example.org/?api_key=hidden",
            attribution="fixture",
            cache_policy="project-permitted",
        )


@pytest.mark.parametrize("kind", ["tile", "geocoding"])
def test_geo_online_qml_explicit_read_reopen(tmp_path, monkeypatch, kind):
    from PySide6.QtCore import QObject
    from test_import_gui import setup, spin, teardown

    server_root = tmp_path / "server"
    server_root.mkdir()
    with server(server_root) as (url, ca, calls, state):
        app, window, _, projects, imports = setup(tmp_path, monkeypatch)
        try:
            window.setProperty("selectedSection", 1)
            window.findChild(QObject, "datasetTabs").setProperty("currentIndex", 1)
            window.findChild(QObject, "importAdvancedButton").clicked.emit()
            panel = window.findChild(QObject, "connectorPanel")
            if not panel.property("expanded"):
                window.findChild(QObject, "connectorToggle").clicked.emit()
            combo = window.findChild(QObject, "connectorKind")
            index = imports.connectorKinds.index(kind)
            combo.setProperty("currentIndex", index)
            combo.activated.emit(index)
            for name, value in dict(
                connectorEndpoint=url + ("/tile" if kind == "tile" else "/geo"),
                connectorCA=ca,
                geoOnlineAttribution="CC0 fixture",
            ).items():
                window.findChild(QObject, name).setProperty("text", value)
            window.findChild(QObject, "geoOnlineCache").setProperty("checked", True)
            window.findChild(QObject, "connectorTerms").setProperty("checked", True)
            app.processEvents()
            assert len(calls) == 0 and not imports.busy
            window.findChild(QObject, "connectorRead").clicked.emit()
            spin(app, lambda: not imports.busy)
            assert imports.ready, imports.errorText
            n = len(calls)
            imports.importData()
            spin(app, lambda: not imports.busy)
            assert not imports.errorText, imports.errorText
            root = projects.store.root
            projects.save()
            spin(app, lambda: not projects.busy)
            projects.open(str(root))
            spin(app, lambda: not projects.busy)
            assert not projects.errorText and len(calls) == n
        finally:
            teardown(app, window)
