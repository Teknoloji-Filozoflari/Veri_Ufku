"""Read-only inventory of the authorized phases 00–13; inventory is not acceptance."""

import argparse
import ast
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from check_docs import SOURCE, check, table_rows

from veri_ufku.domain.capabilities import CAPABILITIES

TESTS = {
    "00": ["document_contracts"],
    "01": ["config", "jobs", "gui"],
    "02": ["presentation_preferences", "gui"],
    "03": ["learning", "learning_gui"],
    "04": ["projects", "project_gui"],
    "05": ["delimited", "import_gui"],
    "06": ["structured_import", "import_gui"],
    "07": ["dataset", "dataset_gui"],
    "08": ["quality", "quality_gui"],
    "09": ["operations", "operations_gui"],
    "10": ["cleaning", "cleaning_gui"],
    "11": ["relational", "relational_gui", "relational_backends", "phase11_formats"],
    "12": ["charts", "charts_gui"],
    "13": ["exports", "exports_gui"],
}


def inventory(root):
    errors = check(root)
    rows = table_rows((root / "docs/REQUIREMENTS_MATRIX.md").read_text())
    requirements = [r for r in rows if len(r) == 10 and r[0] != "ID"]
    ids = {r[0] for r in requirements}
    files = sorted(
        p
        for folder in ("src", "tests", "scripts", "docs", ".github")
        for p in (root / folder).rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and not p.is_relative_to(root / "docs/evidence")
    )
    files.extend(
        root / p
        for p in ("README.md", "AGENTS.md", "pyproject.toml", "uv.lock", SOURCE)
    )
    hashes = {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in files
    }
    boundaries = []
    for p in files:
        if p.suffix != ".py":
            continue
        tree = ast.parse(p.read_text(), filename=str(p))
        if p.is_relative_to(root / "src/veri_ufku"):
            module = p.relative_to(root / "src/veri_ufku")
            qt = any(
                isinstance(node, ast.ImportFrom)
                and (node.module or "").startswith("PySide6")
                or isinstance(node, ast.Import)
                and any(alias.name.startswith("PySide6") for alias in node.names)
                for node in ast.walk(tree)
            )
            boundaries.append(dict(module=str(module), qt_import=qt))
            if qt and module.parts[0] in (
                "domain",
                "jobs",
                "analytics",
                "operations",
                "charts",
                "importers",
                "storage",
            ):
                errors.append(
                    "Qt import in calculation/storage boundary: " + str(module)
                )
    capabilities = {}
    for key, capability in CAPABILITIES.items():
        if key.startswith("demo."):
            phase = "01"
        else:
            phases = {r[1:3] for r in capability.requirement_ids if r.startswith("F")}
            if len(phases) != 1:
                errors.append("Missing/ambiguous phase mapping: " + key)
                continue
            phase = phases.pop()
        for requirement in capability.requirement_ids:
            if requirement not in ids:
                errors.append(
                    "Unknown capability requirement: " + key + ":" + requirement
                )
        for evidence in capability.evidence_refs:
            if not (root / evidence).is_file():
                errors.append("Missing capability evidence: " + key)
        capabilities.setdefault(phase, []).append(key)
    phases = []
    for number in range(14):
        phase = f"{number:02d}"
        row = next(r for r in rows if len(r) == 7 and r[0] == phase)
        source = [
            r for r in requirements if re.fullmatch("F" + phase + r"-S\d{3}", r[0])
        ]
        paths = sorted({p.strip() for r in source for p in r[6].split(";")})
        tests = ["tests/test_" + name + ".py" for name in TESTS[phase]]
        for path in [*paths, *tests, "docs/evidence/PHASE" + phase + ".md"]:
            if not (root / path).is_file():
                errors.append("Missing phase path: " + phase + ":" + path)
        phases.append(
            dict(
                phase=phase,
                title=row[1],
                state=row[3],
                maturity=row[4],
                scope=row[5],
                source_requirements=[r[0] for r in source],
                pending_source_requirements=[
                    r[0] for r in source if r[5] != "doğrulandı"
                ],
                implementation_paths=paths,
                capabilities=capabilities.get(phase, []),
                regression_modules=tests,
            )
        )
    return dict(
        environment="ENV-AUDIT-00-13",
        utc=datetime.now(UTC).isoformat(),
        authorized_phases="00–13",
        human_user_test=False,
        inventory_is_runtime_acceptance=False,
        phases=phases,
        module_boundaries=boundaries,
        files=hashes,
        errors=errors,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = inventory(Path(__file__).resolve().parents[1])
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        "PHASE_INVENTORY", "FAIL" if result["errors"] else "PASS", len(result["files"])
    )
    if result["errors"]:
        print("\n".join(result["errors"]))
        raise SystemExit(1)
