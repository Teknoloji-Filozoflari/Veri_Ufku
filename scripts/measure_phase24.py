"""Reproducible CPU-only production-path benchmark; scopes/errors are explicit."""

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from veri_ufku.jobs.limits import configure_threads

configure_threads(2)


def environment():
    return dict(
        environment="ENV-24",
        date=datetime.now(UTC).isoformat(),
        platform=platform.platform(),
        python=platform.python_version(),
        cpu=Path("/proc/cpuinfo").read_text().split("model name", 1)[1].splitlines()[0],
        meminfo=Path("/proc/meminfo").read_text(),
        affinity=sorted(os.sched_getaffinity(0)),
        lock_sha256=hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        filesystem=subprocess.check_output(["df", "-T", ".", "/tmp"], text=True),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        libraries={
            n: __import__("importlib.metadata", fromlist=["version"]).version(n)
            for n in ("polars", "PySide6", "numpy", "scikit-learn", "duckdb")
        },
        policy="warm OS cache, fresh process/project per trial; 50ms RSS (shared pages may double count), 250ms worker scratch+project staging logical bytes on NVMe Btrfs (published artifacts excluded); 4 logical CPUs, native library threads 2; host RAM is not reduced to 8GiB",
        minimum_hardware_acceptance=False,
    )


def trial(n, output):
    import copy

    import polars as pl

    from veri_ufku.analytics.contracts import ProfileSpec, ViewSpec
    from veri_ufku.analytics.dataset import page, profile
    from veri_ufku.charts.contracts import ChartSpec
    from veri_ufku.charts.engine import calculate as chart
    from veri_ufku.charts.plot import render
    from veri_ufku.exports.reports import ReportSpec, export
    from veri_ufku.importers.delimited import Control, capture, hash_artifact
    from veri_ufku.importers.native import StructuredSettings
    from veri_ufku.importers.registry import get_adapter
    from veri_ufku.jobs.manager import rss_bytes
    from veri_ufku.modeling.contracts import PreparationSpec
    from veri_ufku.modeling.preparation import calculate as prepare
    from veri_ufku.modeling.validation import ValidationSpec
    from veri_ufku.operations.contracts import build
    from veri_ufku.operations.engine import calculate as operate
    from veri_ufku.operations.relational_contracts import EQUALITY
    from veri_ufku.storage.project_model import ProjectError, uid
    from veri_ufku.storage.project_store import ProjectStore

    # Each application job has its own disposable process. Keep this orchestration
    # process free of RLIMIT_AS accumulation across unrelated stages; Control
    # still checks RSS/disk/time, and model fit below gets an isolated OS-limited worker.
    records = []
    with tempfile.TemporaryDirectory(
        prefix="vu-bench24-", dir=output.parent.resolve()
    ) as directory:
        base = Path(directory)
        work = base / "work"
        work.mkdir()
        source = base / "fixture.parquet"
        (
            pl.LazyFrame()
            .select(pl.int_range(0, n).alias("key"))
            .with_columns((pl.col("key") % 997).cast(pl.Float64).alias("x"))
            .with_columns(
                (pl.col("x") * 3 + 7).alias("y"),
                pl.when(pl.col("key") % 53 == 0)
                .then(None)
                .otherwise(pl.col("x"))
                .alias("nullable"),
                pl.when(pl.col("key") % 101 == 0)
                .then(float("nan"))
                .when(pl.col("key") % 107 == 0)
                .then(float("inf"))
                .otherwise(pl.col("x"))
                .alias("nonfinite"),
                (pl.col("key") % 23).cast(pl.String).alias("category"),
                pl.concat_str(
                    pl.lit("Türkçe uzun not ğüşiöç " * 8), pl.col("key")
                ).alias("text"),
                (pl.col("x") / 10).cast(pl.Decimal(18, 2)).alias("money"),
                pl.from_epoch(pl.col("key") + 1700000000, time_unit="s")
                .dt.replace_time_zone("UTC")
                .alias("when"),
            )
            .sink_parquet(source, engine="streaming")
        )
        source_sha = hash_artifact(source, Control())
        store = ProjectStore.create(base / "project")

        def measure(stage, call, scope="full", used=None):
            peak = dict(rss_bytes=0, temp_bytes=0, threads=0)
            stop = threading.Event()

            def disk_bytes():
                total = 0
                for root in (work, base / "project" / "staging"):
                    for path in root.rglob("*"):
                        try:
                            if path.is_file():
                                total += path.stat().st_size
                        except FileNotFoundError:
                            pass
                return total

            def sample():
                ticks = 0
                while not stop.is_set():
                    peak["rss_bytes"] = max(
                        peak["rss_bytes"],
                        rss_bytes(os.getpid())
                        + sum(
                            rss_bytes(int(pid))
                            for pid in Path(
                                "/proc/self/task/" + str(os.getpid()) + "/children"
                            )
                            .read_text()
                            .split()
                        ),
                    )
                    status = Path("/proc/self/status").read_text()
                    peak["threads"] = max(
                        peak["threads"],
                        int(status.split("Threads:")[1].splitlines()[0]),
                    )
                    if ticks % 5 == 0:
                        peak["temp_bytes"] = max(
                            peak["temp_bytes"],
                            disk_bytes(),
                        )
                    ticks += 1
                    stop.wait(0.05)

            watcher = threading.Thread(target=sample)
            watcher.start()
            start = time.perf_counter()
            error = None
            try:
                result = call()
            except ProjectError as failure:
                result, error = None, str(failure)
            finally:
                elapsed = time.perf_counter() - start
                stop.set()
                watcher.join()
            records.append(
                dict(
                    stage=stage,
                    seconds=elapsed,
                    scope=scope,
                    population_n=n,
                    used_n=n if used is None else used,
                    error=error,
                    **peak,
                )
            )
            return result

        def ingest(path):
            snap = capture(path, work, any_format=True)
            return store.publish_import(
                get_adapter("parquet").import_data(
                    snap, StructuredSettings(adapter_id="parquet"), work, Control()
                )
            )

        def req(d):
            return dict(
                path=str(store.path(d["snapshot_uri"])),
                fingerprint=hash_artifact(store.path(d["snapshot_uri"]), Control()),
                columns=d["import_metadata"]["columns"],
                row_count=d["import_metadata"]["row_count"],
                version_id=d["version_id"],
                snapshot_uri=d["snapshot_uri"],
                source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
            )

        def col(r, name):
            return next(c["id"] for c in r["columns"] if c["name"] == name)

        try:
            d = measure("import_capture_parse_publish", lambda: ingest(source))
            assert d is not None, records
            r = req(d)
            measure(
                "page_200", lambda: page(r, ViewSpec()), "bounded_page", min(n, 200)
            )
            measure(
                "profile_exact",
                lambda: profile(r, ProfileSpec(col(r, "nullable"), sample=False), work),
            )
            spec = build(
                r,
                "filter",
                [col(r, "x")],
                {
                    "filters": [
                        {
                            "column_id": col(r, "x"),
                            "operator": "ge",
                            "literal": {"dtype": "Float64", "text": "500"},
                        }
                    ]
                },
            )
            filtered = measure("filter_write_verify", lambda: operate(r, spec, work))
            assert filtered is not None, records
            # Many left rows / bounded right lookup, output lineage still full.
            rightpath = base / "right.parquet"
            pl.DataFrame(
                {"key": list(range(1000)), "label": ["eşleşme"] * 1000}
            ).write_parquet(rightpath)
            other = req(ingest(rightpath))
            rr = dict(r, secondary=other)
            parameters = dict(
                secondary_version_id=other["version_id"],
                left_keys=[col(r, "key")],
                right_keys=[col(other, "key")],
                how="left",
                nulls_equal=False,
                right_outputs=[
                    dict(
                        column_id=c["id"],
                        output=dict(
                            id="col:" + uid(),
                            name=c["name"] + "_right",
                            original_name=c["name"],
                            type=c["type"],
                        ),
                    )
                    for c in other["columns"]
                ],
                max_output_rows=n,
                equality=EQUALITY,
            )
            joined = measure(
                "join_lazy_lineage",
                lambda: operate(
                    rr, build(rr, "join", [col(r, "key")], parameters), work
                ),
            )
            assert joined is not None, records
            measure(
                "chart_compute_render",
                lambda: render(
                    chart(
                        r,
                        ChartSpec(
                            "histogram",
                            x=col(r, "x"),
                            scope="sample",
                            sample_rows=10000,
                        ),
                        work,
                    ),
                    work,
                ),
                "explicit_first_N_sample",
                min(n, 10000),
            )
            measure(
                "report_html_publish",
                lambda: export(
                    r,
                    ReportSpec("html", scope="full"),
                    work,
                    base / "report.html",
                    store.root,
                ),
                "full_counts_table_first_100",
                min(n, 100),
            )
            mr = dict(
                r,
                origin_version=r["version_id"],
                history_state=copy.deepcopy(store.state),
            )

            def prep(request):
                return prepare(
                    request,
                    PreparationSpec(
                        "regression",
                        (col(request, "x"),),
                        target=col(request, "y"),
                        source_version=request["version_id"],
                        family="linear",
                        prediction_context="Ölçüm öncesi",
                    ),
                    work,
                )

            p = measure("model_preflight_full", lambda: prep(mr))
            used = n
            if p is None:
                assert n > 100000
                samplepath = base / "explicit-first-10000.parquet"
                pl.scan_parquet(source).head(10000).sink_parquet(
                    samplepath, engine="streaming"
                )
                md = ingest(samplepath)
                mr = dict(
                    req(md),
                    origin_version=md["version_id"],
                    history_state=copy.deepcopy(store.state),
                )
                p, used = prep(mr), 10000
            validation = ValidationSpec(
                prediction_moment="Ölçüm öncesi",
                availability={
                    col(mr, "x"): dict(offset_seconds=0, note="Bilinen özellik")
                },
            )

            def isolated_fit():
                request_path = base / "model-request.json"
                request_path.write_text(
                    json.dumps(
                        dict(
                            request=dict(
                                mr,
                                preparation=p,
                                path=mr["path"].replace(
                                    "/proc/self/", f"/proc/{os.getpid()}/", 1
                                ),
                            ),
                            parameters=validation.data(),
                            workspace=str(work),
                        )
                    )
                )
                completed = subprocess.run(
                    [
                        sys.executable,
                        __file__,
                        "--model-request",
                        str(request_path),
                        "--output",
                        str(base / "model-result.json"),
                    ],
                    check=True,
                )
                return completed.returncode == 0

            trained = measure(
                "model_fit_cv",
                isolated_fit,
                "full" if used == n else "explicit_first_N_sample",
                used,
            )
            assert trained is not None, records
            assert source_sha == hash_artifact(source, Control())
            output.write_text(
                json.dumps(
                    dict(rows=n, seed=42, fixture=source_sha, records=records),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        finally:
            store.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rows", type=int)
    parser.add_argument("--model-request", type=Path)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.model_request:
        from veri_ufku.domain.contracts import ComputeBudget
        from veri_ufku.jobs.limits import apply_process_limits
        from veri_ufku.modeling.baseline import calculate as fit

        data = json.loads(args.model_request.read_text())
        apply_process_limits(ComputeBudget())
        result = fit(data["request"], data["parameters"], data["workspace"])
        args.output.write_text(
            json.dumps(
                dict(run_id=result["run_id"], evaluations=len(result["evaluations"]))
            )
        )
        return
    if args.rows:
        trial(args.rows, args.output)
        return
    result = dict(environment=environment(), trials=[], summary=[])
    for label, n in (("small", 10000), ("medium", 100000), ("large", 1000001)):
        for repeat in range(args.repeats):
            path = args.output.with_name(f"{label}-{repeat + 1}.json")
            subprocess.run(
                [sys.executable, __file__, "--rows", str(n), "--output", str(path)],
                check=True,
            )
            value = json.loads(path.read_text())
            result["trials"].append(dict(size=label, repeat=repeat + 1, **value))
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        stages = result["trials"][-1]["records"]
        for item in stages:
            items = [
                r
                for t in result["trials"]
                if t["size"] == label
                for r in t["records"]
                if r["stage"] == item["stage"]
            ]
            result["summary"].append(
                dict(
                    size=label,
                    stage=item["stage"],
                    scope=item["scope"],
                    used_n=item["used_n"],
                    population_n=n,
                    n=len(items),
                    median_seconds=statistics.median(i["seconds"] for i in items),
                    max_seconds=max(i["seconds"] for i in items),
                    peak_rss_bytes=max(i["rss_bytes"] for i in items),
                    peak_temp_bytes=max(i["temp_bytes"] for i in items),
                    peak_threads=max(i["threads"] for i in items),
                    errors=[i["error"] for i in items if i["error"]],
                )
            )
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
