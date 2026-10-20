"""Opt-in loopback-only batch API. Import does not create a socket or load secrets."""

import hmac
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

from veri_ufku.storage.project_model import ProjectError


class LocalBatchServer(HTTPServer):
    allow_reuse_address = False
    request_queue_size = 2

    def __init__(self, address, token, score, *, enabled=False):
        if (
            enabled is not True
            or address[0] != "127.0.0.1"
            or type(address[1]) is not int
            or not 0 <= address[1] <= 65535
        ):
            raise ProjectError(
                "API kapalı varsayılan; ayrı opt-in ve127.0.0.1 bind gerekli."
            )
        if not isinstance(token, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{32,128}", token
        ):
            raise ProjectError(
                "API auth sistem keyring içinde32..128 karakter random bearer olmalı."
            )
        self._token = token
        self.score = score
        super().__init__(address, Handler)

    def handle_error(self, request, client_address):
        pass  # Never echo request payload, paths, exception or auth to logs.

    def server_close(self):
        super().server_close()
        self._token = ""


class Handler(BaseHTTPRequestHandler):
    server_version = "Veri_Ufku"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(2)

    def log_message(self, *args):
        pass

    def reply(self, status, value):
        raw = json.dumps(value, allow_nan=False, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.reply(
            405, dict(error="POST /score only; no project open action starts API")
        )

    def do_POST(self):
        if self.path != "/score":
            return self.reply(404, dict(error="unknown endpoint"))
        auth = self.headers.get_all("Authorization", [])
        if len(auth) != 1 or not hmac.compare_digest(
            auth[0].encode(), ("Bearer " + self.server._token).encode()
        ):
            return self.reply(401, dict(error="authentication required"))
        length = self.headers.get_all("Content-Length", [])
        if (
            self.headers.get("Transfer-Encoding")
            or len(length) != 1
            or not length[0].isdigit()
            or not 1 <= int(length[0]) <= 65536
            or self.headers.get("Content-Type") != "application/json"
        ):
            return self.reply(400, dict(error="bounded JSON request required"))
        try:
            raw = self.rfile.read(int(length[0]))
            if len(raw) != int(length[0]):
                raise ValueError()

            def pairs(items):
                d = {}
                for k, v in items:
                    if k in d:
                        raise ValueError()
                    d[k] = v
                return d

            value = json.loads(
                raw,
                object_pairs_hook=pairs,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
            )
            if not isinstance(value, dict) or set(value) != {"spec"}:
                raise ValueError()
            from veri_ufku.modeling.monitor_contracts import MonitorSpec

            spec = MonitorSpec.from_dict(value["spec"])
            result = self.server.score(spec.data())
            self.reply(200, result)
        except (ValueError, KeyError, TypeError, OSError, RecursionError):
            self.reply(
                422,
                dict(
                    error="invalid recipe or bounded scoring failed; inspect local run, no automatic retry"
                ),
            )
