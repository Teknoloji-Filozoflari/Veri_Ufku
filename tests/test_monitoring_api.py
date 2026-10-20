"""Actual opt-in loopback HTTP, bounded schema/auth; no request or credential logs."""

import http.client
import json
import threading
from contextlib import closing

import pytest
from test_monitoring import fixture

from veri_ufku.modeling.monitor_api import LocalBatchServer
from veri_ufku.modeling.monitor_service import run_headless
from veri_ufku.storage.project_model import ProjectError


def test_api_default_closed_and_nonloopback_rejected():
    for address, enabled in [
        (("127.0.0.1", 0), False),
        (("0.0.0.0", 8767), True),
        (("localhost", 8767), True),
    ]:
        with pytest.raises(ProjectError):
            LocalBatchServer(address, "x" * 48, lambda _: {}, enabled=enabled)
    with pytest.raises(ProjectError):
        LocalBatchServer(("127.0.0.1", 0), "short", lambda _: {}, enabled=True)


def test_real_loopback_auth_schema_and_scoring(tmp_path, capsys):
    store, r, w, work, s = fixture(tmp_path)
    token = "test_only_ephemeral_not_stored_" + ("x" * 32)
    calls = []

    def score(spec):
        state = run_headless(store, spec, tmp_path / "cache")
        calls.append(state["results"][-1]["id"])
        return dict(
            status="completed", run_id=state["results"][-1]["monitoring"]["run_id"]
        )

    with (
        closing(store),
        LocalBatchServer(("127.0.0.1", 0), token, score, enabled=True) as server,
    ):
        t = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.01}
        )
        t.start()

        def request(body, auth=None, path="/score"):
            connection = http.client.HTTPConnection(
                "127.0.0.1", server.server_port, timeout=30
            )
            headers = {"Content-Type": "application/json"}
            if auth is not None:
                headers["Authorization"] = "Bearer " + auth
            connection.request("POST", path, body, headers)
            response = connection.getresponse()
            value = response.read()
            status = response.status
            connection.close()
            return status, value

        try:
            raw = json.dumps({"spec": s.data()})
            assert request(raw)[0] == 401
            assert request(raw, "wrong-token")[0] == 401
            assert request(raw, token, "/score?token=secret")[0] == 404
            assert request('{"spec":{},"spec":{}}', token)[0] == 422
            assert (
                request(json.dumps({"spec": s.data(), "code": "arbitrary"}), token)[0]
                == 422
            )
            assert request("x" * 65537, token)[0] == 400
            status, value = request(raw, token)
            assert status == 200, value
            assert json.loads(value)["status"] == "completed" and len(calls) == 1
            assert store.state["results"][-1]["monitoring"]["models"] == []
        finally:
            server.shutdown()
            t.join(5)
    captured = capsys.readouterr()
    assert token not in captured.out + captured.err
    assert captured.out == captured.err == ""
