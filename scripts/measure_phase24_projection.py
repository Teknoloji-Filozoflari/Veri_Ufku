"""Fresh-process before/after reference for training's Parquet column projection."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from veri_ufku.jobs.limits import configure_threads

configure_threads(2)


def main():
    import polars as pl

    from veri_ufku.jobs.manager import rss_bytes

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--mode", choices=("all", "selected"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    if args.source:
        samples = []
        stop = threading.Event()

        def watch():
            while not stop.is_set():
                samples.append(rss_bytes(os.getpid()))
                stop.wait(0.01)

        watcher = threading.Thread(target=watch)
        watcher.start()
        start = time.perf_counter()
        frame = pl.read_parquet(
            args.source,
            columns=None if args.mode == "all" else ["x", "y", "__vu_row_id"],
        )
        seconds = time.perf_counter() - start
        samples.append(rss_bytes(os.getpid()))
        stop.set()
        watcher.join()
        assert frame.height == 100000
        args.output.write_text(
            json.dumps(
                dict(
                    mode=args.mode,
                    rows=frame.height,
                    columns=frame.width,
                    seconds=seconds,
                    peak_rss_bytes=max(samples),
                    dataframe_estimated_bytes=frame.estimated_size(),
                    sample_interval_ms=10,
                )
            )
        )
        return
    with tempfile.TemporaryDirectory(
        prefix="vu-projection24-", dir=args.output.parent.resolve()
    ) as temporary:
        source = Path(temporary) / "source.parquet"
        (
            pl.LazyFrame()
            .select(pl.int_range(0, 100000).alias("x"))
            .with_columns(
                (pl.col("x") * 3 + 7).alias("y"),
                pl.format("row-{}", pl.col("x")).alias("__vu_row_id"),
                *[
                    pl.concat_str(
                        pl.lit("Türkçe kullanılmayan uzun alan " * 9),
                        pl.col("x"),
                        pl.lit(str(i)),
                    ).alias(f"unused_{i}")
                    for i in range(12)
                ],
            )
            .sink_parquet(source, engine="streaming")
        )
        records = []
        for mode in ("all", "selected"):
            for repeat in range(3):
                target = Path(temporary) / "result.json"
                subprocess.run(
                    [
                        sys.executable,
                        __file__,
                        "--source",
                        str(source),
                        "--mode",
                        mode,
                        "--output",
                        str(target),
                    ],
                    check=True,
                )
                records.append(
                    dict(repeat=repeat + 1, **json.loads(target.read_text()))
                )
        args.output.write_text(
            json.dumps(
                dict(
                    environment="ENV-24",
                    fixture_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    script_sha256=hashlib.sha256(
                        Path(__file__).read_bytes()
                    ).hexdigest(),
                    scope="Parquet reader reference; not an entire model-training benchmark",
                    cache="warm OS cache; fresh process, 4 logical CPUs/native threads2",
                    records=records,
                ),
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
