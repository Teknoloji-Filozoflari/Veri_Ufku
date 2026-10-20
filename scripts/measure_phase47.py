"""Source/installed Phase47 real QML walkthrough, render and captured safe artifacts."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tests"))
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    import pytest
    import test_exploration_gui as cases
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest
    from test_unsupervised_gui import visual_find

    import veri_ufku

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E47-GUI",
        environment="ENV-47",
        date=datetime.now(UTC).isoformat(),
        package_file=veri_ufku.__file__,
        cases=[],
    )

    def capture(app, window, c, method, mode):
        folder = output / (method + "-" + mode)
        folder.mkdir(exist_ok=True)
        record = next(r for r in c.projects.draft["results"] if r["id"] == c.record_id)
        value = record["unsupervised"]
        (folder / "result.json").write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        )
        shutil.copyfile(
            c.projects.store.path(value["assignments_uri"]),
            folder / "assignments.parquet",
        )
        artifacts = [
            dict(
                path=str(p.relative_to(output)),
                bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            )
            for p in (folder / "result.json", folder / "assignments.parquet")
        ]
        screenshots = []
        for width, height in ((1366, 900), (1000, 720)):
            window.setWidth(width)
            window.setHeight(height)
            for name in (
                "unsupervisedMethod",
                "explorationCost",
                "explorationEvaluation",
                "explorationDendrogram"
                if method == "agglomerative"
                else "explorationState",
            ):
                item = window.findChild(QObject, name) or visual_find(
                    window.contentItem(), name
                )
                container = item.parentItem()
                while container is not None:
                    if container.property("contentY") is not None:
                        position = item.mapToItem(
                            container.property("contentItem"), 0, 0
                        )
                        container.setProperty("contentY", max(0, position.y() - 25))
                        break
                    container = container.parentItem()
                QTest.qWait(100)
                target = folder / (name + "-" + str(width) + ".png")
                assert window.grabWindow().save(str(target))
                screenshots.append(str(target.relative_to(output)))
        report["cases"].append(
            dict(
                method=method,
                mode=mode,
                current=c.current,
                artifacts=artifacts,
                screenshots=screenshots,
                fit_scope=value["fit_scope"],
            )
        )

    cases.CAPTURE = capture
    for method, mode in cases.CASES:
        with (
            tempfile.TemporaryDirectory(prefix="veri-ufku-f47-") as t,
            pytest.MonkeyPatch.context() as patch,
        ):
            cases.test_real_exploration_controls(Path(t), patch, method, mode)
        print("PASS", method, mode, flush=True)
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
