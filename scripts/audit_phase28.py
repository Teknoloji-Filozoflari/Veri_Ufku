"""Read-only Phase 28 evidence audit; static presence never grants acceptance."""

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from check_docs import check, table_rows

from veri_ufku.domain.capabilities import CAPABILITIES

TESTS = {
    "00": "document_contracts",
    "01": "config jobs gui",
    "02": "presentation_preferences gui",
    "03": "learning learning_gui learning_tree learning_tree_gui",
    "04": "projects project_gui security_audit security_gui",
    "05": "delimited import_gui",
    "06": "structured_import import_gui",
    "07": "dataset dataset_gui data_inspection data_workspace_gui",
    "08": "quality quality_gui",
    "09": "operations operations_gui",
    "10": "cleaning cleaning_gui",
    "11": "relational relational_gui relational_backends phase11_formats",
    "12": "charts charts_gui",
    "13": "exports exports_gui",
    "14": "statistics statistics_gui",
    "15": "preparation preparation_gui",
    "16": "validation validation_gui",
    "17": "regression regression_gui",
    "18": "classification classification_gui",
    "19": "unsupervised unsupervised_gui",
    "20": "lifecycle lifecycle_gui",
    "21": "time_series time_series_gui",
    "22": "text text_gui",
    "23": "recipes recipes_gui",
    "24": "performance",
    "25": "usability",
    "26": "security_audit security_gui",
    "27": "packaging",
}


def audit(root, junit):
    rows = table_rows((root / "docs/REQUIREMENTS_MATRIX.md").read_text())
    phases = {r[0]: r for r in rows if len(r) == 7 and r[0].isdigit()}
    requirements = [r for r in rows if len(r) == 10 and r[0] != "ID"]
    cases = []
    for case in ET.parse(junit).iter("testcase"):
        status = next(
            (
                tag
                for tag in ("failure", "error", "skipped")
                if case.find(tag) is not None
            ),
            "passed",
        )
        cases.append(
            dict(
                module=case.get("classname"),
                name=case.get("name"),
                seconds=float(case.get("time", "0")),
                status=status,
            )
        )
    graph = {
        phase: [] if row[2] == "—" else row[2].split(",")
        for phase, row in phases.items()
    }

    ancestor_cache = {}

    def ancestors(phase, stack=()):
        if phase in stack:
            raise ValueError("Dependency cycle: " + " -> ".join((*stack, phase)))
        if phase in ancestor_cache:
            return ancestor_cache[phase]
        ancestor_cache[phase] = set(graph[phase]) | {
            ancestor
            for parent in graph[phase]
            for ancestor in ancestors(parent, (*stack, phase))
        }
        return ancestor_cache[phase]

    closures = {p: sorted(ancestors(p)) for p in graph}
    evidence = []
    for number in range(28):
        phase = f"{number:02d}"
        source_rows = [
            r for r in requirements if re.fullmatch(f"F{phase}-S\\d{{3}}", r[0])
        ]
        modules = {"tests.test_" + n for n in TESTS[phase].split()}
        runtime = [c for c in cases if c["module"] in modules]
        paths = sorted({p.strip() for r in source_rows for p in r[6].split(";")})
        evidence.append(
            dict(
                phase=phase,
                state=phases[phase][3],
                scope=phases[phase][5],
                entry_gate=number <= 20 or number >= 24,
                pending_source_requirements=[
                    r[0] for r in source_rows if r[5] != "doğrulandı"
                ],
                historical_evidence=sorted({r[7] for r in source_rows if r[7] != "—"}),
                implementation_paths=paths,
                missing_paths=[p for p in paths if not (root / p).is_file()],
                runtime_cases=runtime,
                runtime_status={
                    s: sum(c["status"] == s for c in runtime)
                    for s in ("passed", "failure", "error", "skipped")
                },
                runtime_is_whole_phase_acceptance=False,
            )
        )
    qt_violations = []
    gui_supervisors = []
    for folder in (
        "domain",
        "analytics",
        "modeling",
        "operations",
        "importers",
        "storage",
        "jobs",
        "statistics",
        "charts",
    ):
        for path in (root / "src/veri_ufku" / folder).rglob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                names = (
                    [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else []
                )
                if any(name.startswith("PySide6") for name in names):
                    relative = str(path.relative_to(root))
                    if relative == "src/veri_ufku/jobs/supervision.py":
                        # Existing Phase24 parent QObject monitors UI controllers;
                        # no analytic worker imports it. Record this exception.
                        gui_supervisors.append(relative)
                    else:
                        qt_violations.append(relative)
    hashes = {}
    for folder in ("src", "tests", "scripts", "docs/adr"):
        for path in sorted((root / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                hashes[str(path.relative_to(root))] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    memory = next(
        line
        for line in Path("/proc/meminfo").read_text().splitlines()
        if line.startswith("MemTotal:")
    )
    return dict(
        environment_id="ENV-28",
        utc=datetime.now(UTC).isoformat(),
        environment=dict(
            os=platform.platform(),
            python=platform.python_version(),
            cpu=next(
                (
                    line.split(":", 1)[1].strip()
                    for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.startswith("model name")
                ),
                platform.processor(),
            ),
            available_cpus=sorted(os.sched_getaffinity(0)),
            memory=memory,
            packages={
                name: importlib.metadata.version(name)
                for name in (
                    "PySide6",
                    "polars",
                    "numpy",
                    "scipy",
                    "scikit-learn",
                    "skops",
                    "pytest",
                    "hatchling",
                )
            },
        ),
        lock_sha256=hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(
            (root / "Veri_Ufku_Birlestirilmis_Gelistirme_Promptlari.md").read_bytes()
        ).hexdigest(),
        original_source_record=(root / "docs/evidence/source.sha256")
        .read_text()
        .strip(),
        junit_sha256=hashlib.sha256(junit.read_bytes()).hexdigest(),
        checks=check(root),
        phases=evidence,
        pending_common_requirements=[
            dict(id=r[0], scope=r[3], maturity=r[4], validation=r[5], evidence=r[7])
            for r in requirements
            if r[1] in ("ortak", "ortak-prof") and r[5] != "doğrulandı"
        ],
        capabilities={key: asdict(value) for key, value in CAPABILITIES.items()},
        dependencies=graph,
        transitive_dependencies=closures,
        order_is_topological=all(
            int(parent) < int(child)
            for child, parents in graph.items()
            for parent in parents
        ),
        unresolved_ancestors={
            p: [a for a in closures[p] if phases[a][3] != "doğrulandı"]
            for p in graph
            if int(p) >= 28
        },
        qt_boundary_violations=sorted(set(qt_violations)),
        gui_supervisor_in_jobs=sorted(set(gui_supervisors)),
        files=hashes,
        runtime_summary={
            s: sum(c["status"] == s for c in cases)
            for s in ("passed", "failure", "error", "skipped")
        },
        cases=cases,
        static_inventory_is_acceptance=False,
        real_user_test=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(Path(__file__).resolve().parents[1], args.junit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        "PHASE28_EVIDENCE",
        result["runtime_summary"],
        "document_errors",
        len(result["checks"]),
        "Qt boundaries",
        result["qt_boundary_violations"],
    )
    # A completed report can still show a closed entry gate.
    if result["qt_boundary_violations"] or result["runtime_summary"]["error"]:
        raise SystemExit(1)
