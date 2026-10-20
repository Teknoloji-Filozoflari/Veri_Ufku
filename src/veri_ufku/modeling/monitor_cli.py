"""Explicit local batch command and separately opted-in loopback server."""

import argparse
import json
import multiprocessing as mp
import signal
from contextlib import closing
from pathlib import Path

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.monitor_service import run_headless
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def main():
    parser = argparse.ArgumentParser(
        description="Veri_Ufku local monitoring; no automatic deployment/training/API"
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--spec")
    parser.add_argument("--allow-batch-scoring", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--allow-api", action="store_true")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--credential-ref", default="")
    parser.add_argument("--seconds", type=float, default=600)
    args = parser.parse_args()
    try:
        if not args.allow_batch_scoring:
            raise ProjectError(
                "Batch scoring ayrı --allow-batch-scoring opt-in gerektirir."
            )
        if not 0 < args.seconds <= 600:
            raise ProjectError("Erken600s limitini aşamaz.")
        budget = ComputeBudget(max_wall_seconds=args.seconds)
        with closing(ProjectStore.open(args.project)) as store:
            cancel = mp.get_context("spawn").Event()

            def score(spec):
                state = run_headless(store, spec, args.cache, budget, cancel)
                value = state["results"][-1]["monitoring"]
                return dict(
                    run_id=value["run_id"],
                    status=value["status"],
                    record_id=state["results"][-1]["id"],
                    labels="configured"
                    if value["spec"]["labels"]
                    else "unavailable; no performance claim",
                )

            previous = {
                s: signal.signal(s, lambda number, frame: cancel.set())
                for s in (signal.SIGINT, signal.SIGTERM)
            }
            try:
                if args.serve:
                    if (
                        not args.allow_api
                        or args.spec
                        or not args.credential_ref
                        or args.bind != "127.0.0.1"
                        or not 1024 <= args.port <= 65535
                    ):
                        raise ProjectError(
                            "API için ayrı allow-api/keyring reference/loopback port1024..65535 gerekli; spec dosyası kabul edilmez."
                        )
                    from veri_ufku.importers.credentials import load
                    from veri_ufku.modeling.monitor_api import LocalBatchServer

                    token = load(args.credential_ref)
                    with LocalBatchServer(
                        (args.bind, args.port), token, score, enabled=True
                    ) as server:
                        token = None
                        server.timeout = 0.25
                        print(
                            "Veri_Ufku loopback API explicitly started; bearer auth; no remote bind; Ctrl+C closes."
                        )
                        while not cancel.is_set():
                            server.handle_request()
                else:
                    if args.allow_api or not args.spec:
                        raise ProjectError(
                            "Batch spec dosyası gerekli; API ayrı serve eylemi."
                        )
                    path = Path(args.spec)
                    if path.stat().st_size > 65536:
                        raise ProjectError("Recipe64KiB sınırı.")
                    print(
                        json.dumps(
                            score(json.loads(path.read_text())), ensure_ascii=False
                        )
                    )
            finally:
                for s, handler in previous.items():
                    signal.signal(s, handler)
        return 0
    except Canceled:
        print("Veri_Ufku monitoring canceled; no incomplete success result.")
        return 2
    except (ValueError, KeyError, TypeError, OSError) as e:
        print(
            "Veri_Ufku monitoring failed: "
            + (str(e) if isinstance(e, ProjectError) else type(e).__name__)
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
