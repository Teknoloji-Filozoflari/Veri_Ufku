"""Actual statistical worker retains multidimensional slice through save/reopen."""

import argparse
import json
import math
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo / "tests"))
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    import pytest
    from phase34_fixtures import fixture
    from test_import_gui import setup, spin, teardown

    import veri_ufku
    from veri_ufku.statistics.contracts import AnalysisSpec

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    with (
        tempfile.TemporaryDirectory(prefix="veri-ufku-f34-analysis-") as directory,
        pytest.MonkeyPatch.context() as patch,
    ):
        root = Path(directory)
        app, window, _, projects, imports = setup(root, patch)
        try:
            source, _ = fixture(root, "netcdf")
            imports.choose(str(source))
            spin(app, lambda: not imports.busy)
            for key, value in [
                ("array_variable", "temperature"),
                ("array_slice", '{"time":1,"latitude":[1,3,1],"longitude":[0,4,2]}'),
                ("array_decode", True),
                ("array_unit", "kelvin"),
            ]:
                imports.setOption(key, value)
            imports.refreshPreview()
            spin(app, lambda: not imports.busy)
            assert imports.ready, imports.errorText
            imports.importData()
            spin(app, lambda: not imports.busy)
            assert not imports.errorText, imports.errorText
            dataset = projects.draft["datasets"][-1]
            metadata = dataset["import_metadata"]["settings"]["format_metadata"]
            columns = {
                c["name"]: c["id"] for c in dataset["import_metadata"]["columns"]
            }
            stats = app._veri_ufku_resources[0]._statistics_resources
            spec = AnalysisSpec(
                "numeric",
                "pearson",
                columns["longitude"],
                y=columns["value"],
                question="Bu seçili kesitte boylam ve ölçüm ilişkisi nedir?",
                hypothesis="Doğrusal korelasyon sıfır.",
                unit="kelvin",
                observation_unit="sentetik grid hücresi",
                independent=True,
                measurement_confirmed=True,
            )
            stats.create(json.dumps(spec.data()), True)
            spin(app, lambda: not stats.busy)
            assert stats.preflightCurrent, stats.errorText
            data = spec.data()
            data["assumptions_confirmed"] = True
            stats.create(json.dumps(data), False)
            spin(app, lambda: not stats.busy)
            assert not stats.errorText, stats.errorText
            assert stats.result["provenance"]["array_source"] == metadata
            effect = stats.result["primary"]["effect"]["value"]
            assert math.isclose(effect, 1 / math.sqrt(5), rel_tol=1e-12), (
                effect,
                stats.result,
            )
            stats.save()
            spin(app, lambda: not stats.busy)
            assert not stats.errorText, stats.errorText
            assert projects.closeProject() and projects.open(str(root / "project"))
            saved = projects.draft["results"][-1]["analysis"]
            assert saved["provenance"]["array_source"] == metadata
            report = dict(
                id="E34-ANALYSIS",
                environment="ENV-34",
                date=datetime.now(UTC).isoformat(),
                package_file=veri_ufku.__file__,
                method="pearson",
                effect=effect,
                reference=1 / math.sqrt(5),
                slice=metadata["parts"][0]["multidimensional"]["selection"],
                worker=True,
                save_reopen=True,
                passed=True,
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            )
            print("PASS: actual analysis worker + selected slice provenance + reopen")
        finally:
            teardown(app, window)


if __name__ == "__main__":
    main()
