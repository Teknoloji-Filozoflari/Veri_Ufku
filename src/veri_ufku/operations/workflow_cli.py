"""Explicit CLI invocation, not a scheduler or daemon."""

import argparse
import json
import multiprocessing as mp
import signal
from contextlib import closing
from pathlib import Path

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.operations.workflow_service import run_headless
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def main():
    parser = argparse.ArgumentParser(
        description="Veri_Ufku typed DAG: explicit local headless run; no background schedule"
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--dag", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--allow-export", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--export-token", default="")
    parser.add_argument("--seconds", type=float, default=600)
    args = parser.parse_args()
    try:
        path = Path(args.dag)
        if path.stat().st_size > 65536:
            raise ProjectError("DAG64KiB sınırı.")
        spec = json.loads(path.read_text())
        with closing(ProjectStore.open(args.project)) as store:
            if store.read_only:
                raise ProjectError(
                    "CLI yayın için yazılabilir proje gerekir; başka GUI writer varsa kapatın."
                )
            cancel = mp.get_context("spawn").Event()
            previous = {
                signum: signal.signal(signum, lambda number, frame: cancel.set())
                for signum in (signal.SIGINT, signal.SIGTERM)
            }
            try:
                state = run_headless(
                    store,
                    spec,
                    args.cache,
                    args.output_dir,
                    args.allow_export,
                    args.dry_run,
                    args.export_token,
                    ComputeBudget(max_wall_seconds=args.seconds),
                    cancel,
                )
            finally:
                for signum, handler in previous.items():
                    signal.signal(signum, handler)
            result = state["results"][-1]["neural"]
            print(
                json.dumps(
                    dict(
                        run_id=result["run_id"],
                        status=result["status"],
                        nodes=[
                            {
                                k: n.get(k)
                                for k in (
                                    "case",
                                    "node",
                                    "kind",
                                    "status",
                                    "cache_key",
                                    "error",
                                )
                            }
                            for n in result["nodes"]
                        ],
                    ),
                    ensure_ascii=False,
                )
            )
            return 0 if result["status"] in ("completed", "dry_run") else 2
    except (ValueError, OSError, KeyError) as e:
        print(
            "Veri_Ufku DAG failed: "
            + (str(e) if isinstance(e, ProjectError) else type(e).__name__)
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
