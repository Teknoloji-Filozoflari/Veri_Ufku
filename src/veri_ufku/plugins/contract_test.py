"""Author CLI: explicit trusted-code contract test in a bounded disposable process."""

import argparse
import contextlib
import io
import multiprocessing as mp
from pathlib import Path

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits
from veri_ufku.plugins.discovery import inspect
from veri_ufku.plugins.sdk import ContextV1, input_contract, output, parameters
from veri_ufku.storage.project_model import ProjectError, decode


def entry(code, data, kind, cancel, sender, budget):
    try:
        apply_process_limits(budget)
        import os

        fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(fd, 1)
        os.dup2(fd, 2)
        os.close(fd)
        scope = {"__name__": "explicit_contract_plugin"}
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            exec(compile(code, "<trusted-contract-plugin>", "exec"), scope)
            value = output(
                scope["run"](data, ContextV1(Control(cancel, budget=budget))),
                kind,
                [r["row_id"] for r in data["records"]],
            )
        sender.send(("result", value))
    except BaseException as e:
        sender.send(("error", type(e).__name__))
    finally:
        sender.close()


def run(manifest_path, data, trust=False, timeout=10):
    inspected, code = inspect(manifest_path)
    if trust is not True or not inspected["compatible"]:
        raise ProjectError(
            "Contract test explicit trusted code ve uyumlu ortam gerektirir."
        )
    input_contract(data, inspected["manifest"]["capability"]["kind"])
    parameters(inspected["manifest"], data["params"])
    if not 0 < timeout <= 60:
        raise ProjectError("Contract timeout0..60s.")
    budget = ComputeBudget(max_wall_seconds=timeout)
    ctx = mp.get_context("spawn")
    cancel = ctx.Event()
    recv, send = ctx.Pipe(False)
    p = ctx.Process(target=entry, args=(code, data, data["kind"], cancel, send, budget))
    from veri_ufku.jobs.admission import start

    start(p, budget)
    send.close()
    try:
        if not recv.poll(timeout):
            raise ProjectError("Plugin contract timeout; sonuç başarılı sayılmadı.")
        try:
            kind, value = recv.recv()
        except EOFError:
            raise ProjectError("Plugin contract process çöktü.") from None
        if kind != "result":
            raise ProjectError("Plugin contract başarısız: " + value)
        return value
    finally:
        cancel.set()
        p.join(0.2)
        if p.is_alive():
            p.kill()
            p.join(2)
        p.close()
        recv.close()


def main():
    p = argparse.ArgumentParser(
        description="Explicit trusted plugin contract; NOT OS sandbox"
    )
    p.add_argument("--manifest", required=True)
    p.add_argument("--request", required=True)
    p.add_argument("--trust-code", action="store_true")
    p.add_argument("--timeout", type=float, default=10)
    args = p.parse_args()
    path = Path(args.request)
    if path.stat().st_size > 8 * 1024**2:
        raise ProjectError("Contract fixture8MiB limit")
    run(args.manifest, decode(path.read_bytes()), args.trust_code, args.timeout)
    print(
        "PLUGIN_CONTRACT PASS: manifest/API/dependencies/finite JSON/kind/RowId; not scientific validation"
    )


if __name__ == "__main__":
    main()
