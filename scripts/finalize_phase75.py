"""Aggregate actual Phase75 evidence without treating retries, skips or missing results as success."""

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    value = hashlib.sha256()
    with p.open("rb") as stream:
        while chunk := stream.read(1024**2):
            value.update(chunk)
    return value.hexdigest()


def counts(paths):
    cases = {}
    for p in paths:
        for c in ET.parse(p).iter("testcase"):
            key = c.get("classname", "") + "::" + c.get("name", "")
            outcome = next(
                (k for k in ("failure", "error", "skipped") if c.find(k) is not None),
                "passed",
            )
            cases[key] = dict(
                outcome=outcome,
                seconds=float(c.get("time", 0)),
                evidence=str(p.relative_to(ROOT)),
            )
    return dict(
        unique_cases=len(cases),
        outcomes={
            k: sum(c["outcome"] == k for c in cases.values())
            for k in ("passed", "failure", "error", "skipped")
        },
        cases=cases,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    e = a.output.resolve()
    value = dict(
        schema="FinalEvidence75/v1",
        recorded_at=datetime.now(UTC).isoformat(),
        formal_release_verified=False,
        human_novice="not-performed",
        human_expert="not-performed",
        independent_learning_review="pending",
        physical_AT_minHW="not-performed",
        scope="Bounded explicit synthetic source/wheel CPU tests; all-method correctness or absence of critical errors is not guaranteed",
        runs={},
    )
    for kind in ("source", "wheel"):
        paths = [
            p
            for p in (e / (kind + "-compute")).glob("*/tests.xml")
            if p.parent.name != "numeric"
        ]
        paths += list((e / (kind + "-numeric-delivery")).glob("*/tests.xml"))
        value["runs"][kind + "-compute"] = counts(paths)
    for folder in sorted(e.iterdir()):
        summary = folder / "summary.json"
        if folder.is_dir() and (
            "gui" in folder.name
            or "table" in folder.name
            or summary.is_file()
            and json.loads(summary.read_text()).get("kind") == "gui"
        ):
            paths = list(folder.glob("*/tests.xml"))
            if paths:
                value["runs"][folder.name] = counts(paths)
            if summary.exists():
                value["runs"].setdefault(folder.name, {})["group_process_outcomes"] = (
                    json.loads(summary.read_text())["cases"]
                )
            partial = []
            for file in folder.glob("*/fixtures.json"):
                report = json.loads(file.read_text())
                if report.get("exitstatus") is None:
                    partial.append(
                        dict(
                            evidence=str(file.relative_to(ROOT)),
                            scope="Completed call hooks only; group did not finish; no suite success",
                            cases=[
                                dict(nodeid=c["nodeid"], outcome=c["outcome"])
                                for c in report["cases"]
                            ],
                        )
                    )
            if partial:
                value["runs"].setdefault(folder.name, {})["partial_call_witnesses"] = (
                    partial
                )
    refs = []
    file = e / "source-numeric-delivery/numeric/fixtures.json"
    if file.exists():
        for case in json.loads(file.read_text())["cases"]:
            for key, detail in case.get("properties", []):
                if key == "scientific_witness":
                    refs.append(
                        dict(
                            nodeid=case["nodeid"],
                            test_file_sha256=case["test_file_sha256"],
                            outcome=case["outcome"],
                            **json.loads(detail),
                        )
                    )
    value["numeric_references"] = refs
    with (e / "numeric-references.csv").open("w", newline="") as stream:
        fields = [
            "method",
            "input_sha256",
            "actual",
            "reference",
            "absolute_tolerance",
            "relative_tolerance",
            "assumptions",
            "outcome",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in refs:
            writer.writerow({k: row[k] for k in fields})
    candidates = []
    for profile in ("core", "professional"):
        prior = ROOT / f"docs/evidence/phase74/package/final-{profile}-build.json"
        info = json.loads(prior.read_text())
        artifact = Path(info["bundle"])
        exists = artifact.is_file()
        candidates.append(
            dict(
                profile=profile,
                path=str(artifact),
                exists=exists,
                expected_sha256=info["bundle_sha256"],
                actual_sha256=sha(artifact) if exists else None,
                match=exists and sha(artifact) == info["bundle_sha256"],
                scope="Existing Phase74 unsigned local candidate; actual previous runtime smoke, no fresh OS claim; no external publication",
            )
        )
    value["distribution_candidates"] = candidates
    # Artifact manifests bind all implementation bytes; no model deserialization.
    package = Path("/tmp/veri-ufku-f75-wheel/veri_ufku")
    source = ROOT / "src/veri_ufku"
    source_hashes = {
        str(p.relative_to(source)): sha(p)
        for p in source.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    wheel_hashes = {
        str(p.relative_to(package)): sha(p)
        for p in package.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    value["package_parity"] = dict(
        files=len(source_hashes),
        source_wheel_equal=source_hashes == wheel_hashes,
        source_hashes=source_hashes,
    )
    (e / "final-results.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                k: {"count": v.get("unique_cases"), "outcomes": v.get("outcomes")}
                for k, v in value["runs"].items()
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
