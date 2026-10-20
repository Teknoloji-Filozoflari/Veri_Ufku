"""Real source/installed Qt controls, reliable diagrams, package/prediction and final journal."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--forest-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tests"))
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    import pytest
    import test_uncertainty_gui as cases
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest
    from test_unsupervised_gui import visual_find

    import veri_ufku

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E50-GUI",
        environment="ENV-50",
        date=datetime.now(UTC).isoformat(),
        package_file=veri_ufku.__file__,
        cases=[],
        controls=[],
    )

    if args.forest_only:
        report = json.loads((output / "walkthrough.json").read_text())

    def capture(app, window, projects, c, method, purpose, stage):
        folder = output / (method + "-" + purpose)
        folder.mkdir(exist_ok=True)
        value = {
            k: v
            for k, v in c.result.items()
            if k not in ("model_package", "worker_pid")
        }
        path = folder / (stage + ".json")
        path.write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        )
        images = []
        for width, height in ((1366, 900), (1000, 720)):
            window.setWidth(width)
            window.setHeight(height)
            for name in (
                "uncertaintyScope",
                "uncertaintyReliability"
                if purpose == "classification"
                else "uncertaintyHelp",
                "uncertaintyCoverage",
            ):
                item = window.findChild(QObject, name) or visual_find(
                    window.contentItem(), name
                )
                assert item is not None
                parent = item.parentItem()
                while parent is not None:
                    if parent.property("contentY") is not None:
                        pos = item.mapToItem(parent.property("contentItem"), 0, 0)
                        parent.setProperty("contentY", max(0, pos.y() - 20))
                        break
                    parent = parent.parentItem()
                QTest.qWait(100)
                target = folder / (stage + "-" + name + "-" + str(width) + ".png")
                assert window.grabWindow().save(str(target))
                images.append(str(target.relative_to(output)))
        record = next(
            r["baseline"]
            for r in projects.draft["results"]
            if r.get("baseline", {}).get("run_id") == c.result["run_id"]
        )
        package = projects.store.path(record["model_package_uri"])
        target = folder / (stage + ".vumodel")
        target.write_bytes(package.read_bytes())
        report["cases"].append(
            dict(
                method=method,
                purpose=purpose,
                stage=stage,
                scope=c.result["evaluations"][0]["scope"],
                n=c.result["evaluations"][0]["evaluation_n"],
                fit_calls=c.result["fit_count"],
                calibration_n=c.result["uncertainty"]["calibration_n"],
                conformal_n=c.result["uncertainty"]["conformal_n"],
                partition_id=c.result["uncertainty"]["partition_id"],
                empirical_coverage=c.result["evaluations"][0]["uncertainty_report"][
                    "empirical_coverage"
                ],
                prior_test_use_ids=c.result["prior_test_use_ids"],
                screenshots=images,
                artifacts=[
                    dict(
                        path=str(p.relative_to(output)),
                        bytes=p.stat().st_size,
                        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                    )
                    for p in (path, target)
                ],
            )
        )
        (output / "walkthrough.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )

    cases.CAPTURE = capture
    if args.forest_only:
        for method, purpose in (
            ("isotonic", "classification"),
            ("interval", "regression"),
        ):
            with (
                tempfile.TemporaryDirectory(prefix="veri-ufku-f50-forest-") as t,
                pytest.MonkeyPatch.context() as patch,
            ):
                cases.test_forest_probability_and_interval_gui(
                    Path(t), patch, method, purpose
                )
            report["controls"].append(
                dict(path="native-forest-" + method, status="passed")
            )
            print("PASS native forest", method, purpose, flush=True)
    else:
        for method, purpose in cases.CASES:
            with (
                tempfile.TemporaryDirectory(prefix="veri-ufku-f50-") as t,
                pytest.MonkeyPatch.context() as patch,
            ):
                cases.test_actual_uncertainty_gui_safe_model_final_and_reopen(
                    Path(t), patch, method, purpose
                )
            print("PASS", method, purpose, flush=True)
        for name in (
            "test_binary_cost_constraints_cancel_and_new_file_prediction",
            "test_group_time_calibration_gui_and_coverage_scope",
        ):
            with (
                tempfile.TemporaryDirectory(prefix="veri-ufku-f50-control-") as t,
                pytest.MonkeyPatch.context() as patch,
            ):
                getattr(cases, name)(Path(t), patch)
            report["controls"].append(dict(path=name, status="passed"))
            print("PASS", name, flush=True)
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
