"""Disposable Python subprocess. Resource limits are NOT a security sandbox."""

import codecs
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

from veri_ufku.jobs.admission import spawn
from veri_ufku.jobs.resources import rss_bytes
from veri_ufku.storage.project_model import ProjectError

MAX_OUTPUT = 65536
BOOTSTRAP = """import os, resource, sys
from pathlib import Path
budget = __import__("json").loads(sys.argv[1])
os.umask(0o077)
resource.setrlimit(resource.RLIMIT_CPU, (budget["cpu_seconds"], budget["cpu_seconds"]+1))
resource.setrlimit(resource.RLIMIT_FSIZE, (budget["file_bytes"], budget["file_bytes"]))
resource.setrlimit(resource.RLIMIT_NOFILE, (64,64))
baseline = next(int(x.split()[1])*1024 for x in Path("/proc/self/status").read_text().splitlines() if x.startswith("VmSize:"))
resource.setrlimit(resource.RLIMIT_AS, (baseline+budget["ram_bytes"], baseline+budget["ram_bytes"]))
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:budget["cpu_threads"]])
try:
    source = sys.stdin.buffer.read(16385).decode("utf-8")
    if len(source.encode()) > 16384: raise ValueError("Cell size")
    exec(compile(source, "<user-cell>", "exec"), {"__name__":"__main__"})
except BaseException as error:
    print("Cell failed: " + type(error).__name__, file=sys.stderr)
    sys.exit(1)
"""


def mask(text):
    # Best effort display masking, not a secret detector or a logging permission.
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[MASKED]", text)
    text = re.sub(
        r"(?i)((?:password|secret|token|api[_-]?key)\s*[:=]\s*)[^\s,;]+",
        r"\1[MASKED]",
        text,
    )
    text = re.sub(
        r"([a-zA-Z][a-zA-Z0-9+.-]*://)[^\s/@]+:[^\s/@]+@", r"\1[MASKED]@", text
    )
    return "".join(c for c in text if c in "\n\t" or ord(c) >= 32)


class Kernel:
    def __init__(self, source, workspace, budget, timeout):
        from veri_ufku.modeling.code_workspace import cell_hash

        cell_hash(source)
        if (
            type(timeout) not in (int, float)
            or not math.isfinite(timeout)
            or not 0 < timeout <= min(600, budget.max_wall_seconds)
        ):
            raise ProjectError("Kernel timeout bütçe sınırı dışında.")
        self.workspace = Path(workspace)
        self.budget = budget
        self.timeout = timeout
        self.output = ""
        self.raw_bytes = 0
        self.reason = None
        self.cancel_at = None
        self.finished = False
        self.decoders = {}
        self.streams = []
        limits = dict(
            cpu_seconds=max(1, math.ceil(timeout)),
            file_bytes=min(budget.temp_disk_bytes, 16 * 1024**2),
            ram_bytes=budget.ram_bytes,
            cpu_threads=budget.worker_threads,
        )
        env = {
            "PATH": os.defpath,
            "LANG": "C.UTF-8",
            "TZ": "UTC",
            **{
                k: str(budget.worker_threads)
                for k in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "POLARS_MAX_THREADS",
                )
            },
        }
        self._input = source.encode()
        self._sent = 0
        self.process = spawn(
            lambda: subprocess.Popen(
                [sys.executable, "-I", "-u", "-c", BOOTSTRAP, json.dumps(limits)],
                cwd=self.workspace,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                close_fds=True,
            ),
            budget,
        )
        os.set_blocking(self.process.stdin.fileno(), False)
        for stream in (self.process.stdout, self.process.stderr):
            os.set_blocking(stream.fileno(), False)
            self.streams.append(stream)
            self.decoders[stream.fileno()] = codecs.getincrementaldecoder("utf-8")(
                "replace"
            )
        self.started = time.monotonic()

    def signal_group(self, sig):
        try:
            os.killpg(self.process.pid, sig)
        except ProcessLookupError:
            pass

    def cancel(self, reason="canceled"):
        if self.reason is None:
            self.reason = reason
            self.cancel_at = time.monotonic()
            self.signal_group(signal.SIGTERM)

    def poll(self):
        if self.finished:
            return True
        if not self.process.stdin.closed:
            try:
                self._sent += os.write(
                    self.process.stdin.fileno(),
                    self._input[self._sent : self._sent + 8192],
                )
                if self._sent == len(self._input):
                    self.process.stdin.close()
                    self._input = b""
            except BlockingIOError:
                pass
            except BrokenPipeError:
                self.process.stdin.close()
                self._input = b""
        for stream in list(self.streams):
            # Per-tick work bounded even if child floods output forever.
            for _ in range(8):
                try:
                    chunk = os.read(stream.fileno(), 8192)
                except BlockingIOError:
                    break
                if not chunk:
                    self.streams.remove(stream)
                    break
                available = MAX_OUTPUT - self.raw_bytes
                kept = chunk[:available]
                self.raw_bytes += len(kept)
                self.output += self.decoders[stream.fileno()].decode(kept)
                if len(chunk) > available or self.raw_bytes >= MAX_OUTPUT:
                    self.cancel("output_limit")
                    break
        now = time.monotonic()
        if now - self.started > self.timeout:
            self.cancel("timeout")
        if rss_bytes(self.process.pid) > self.budget.ram_bytes:
            self.cancel("budget_exhausted")
        if (
            self.cancel_at
            and now - self.cancel_at >= self.budget.cancel_grace_ms / 1000
        ):
            self.signal_group(signal.SIGKILL)
        if self.process.poll() is not None:
            # Non-escaped descendants must not survive a cell or hold pipes open.
            self.signal_group(signal.SIGKILL)
            for stream in (self.process.stdout, self.process.stderr):
                stream.close()
            self.finished = True
            return True
        return False

    @property
    def status(self):
        return self.reason or (
            "completed" if self.process.returncode == 0 else "failed"
        )

    @property
    def display(self):
        return mask(self.output)

    def close(self):
        if not self.process.stdin.closed:
            self.process.stdin.close()
        self._input = b""
        self.signal_group(signal.SIGKILL)
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        for stream in (self.process.stdout, self.process.stderr):
            stream.close()
