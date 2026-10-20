import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

root = Path.cwd()
if len(sys.argv) > 1:
    import os
    import tempfile
    import threading
    import time

    sys.path.insert(0, str(root / "tests"))
    from test_streams import fixture

    from veri_ufku.modeling.streams import calculate

    def rss():
        return int(Path("/proc/self/statm").read_text().split()[1]) * os.sysconf(
            "SC_PAGE_SIZE"
        )

    n = int(sys.argv[1])
    peak = [rss()]
    stop = threading.Event()
    with tempfile.TemporaryDirectory(prefix="vu62-memory-") as tmp:
        store, r, w, s = fixture(Path(tmp), n=n)
        before = rss()

        def sample():
            while not stop.wait(0.005):
                peak[0] = max(peak[0], rss())

        thread = threading.Thread(target=sample)
        thread.start()
        start = time.monotonic()
        try:
            result = calculate(
                r, {**s.data(), "checkpoint_every": 128, "buffer": 8, "window": 1}, w
            )
            assert result["status"] == "completed"
            data = dict(
                n=n,
                baseline_rss=before,
                peak_rss=peak[0],
                increment_rss=max(0, peak[0] - before),
                seconds=time.monotonic() - start,
                state_bytes=len(json.dumps(result["state"])),
                pending_peak=result["state"]["peak_pending"],
                closed_windows=result["state"]["closed_windows"],
            )
        finally:
            stop.set()
            thread.join()
            store.close()
        print(json.dumps(data))
else:
    records = []
    for n in (512, 4096):
        run = subprocess.run(
            [sys.executable, __file__, str(n)], cwd=root, capture_output=True, text=True
        )
        assert run.returncode == 0, run.stderr
        records.append(json.loads(run.stdout))
    assert records[1]["peak_rss"] < records[0]["peak_rss"] + 64 * 1024**2
    assert all(v["state_bytes"] < 20000 and v["pending_peak"] <= 8 for v in records)
    Path("docs/evidence/phase62/memory.json").write_text(
        json.dumps(
            dict(
                id="E62-MEM-01",
                at=datetime.now(UTC).isoformat(),
                python=sys.version,
                scope="fresh CPU subprocess RSS,512 vs4096; not long-run/minimum hardware/GUI total2GiB acceptance",
                records=records,
                passed=True,
            ),
            indent=2,
        )
    )
