"""Validate phase 00 documentation contracts without application dependencies."""

import hashlib
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

PHASE_STATES = {"başlanmadı", "sürüyor", "engelli", "doğrulandı"}
MATURITY = {"mevcut değil", "deneysel", "kararlı"}
SCOPES = {"zorunlu", "isteğe bağlı", "ertelendi"}
REQUIRED = (
    "PRODUCT",
    "ARCHITECTURE",
    "UX",
    "PROGRESS",
    "PRO_PROGRESS",
    "CORE_CONTRACTS",
    "REQUIREMENTS_MATRIX",
    "ACCEPTANCE_POLICY",
    "PROJECT_RULES",
    "UI_DESIGN_BRIEF",
    "UI_REFERENCES",
    "DESIGN_SYSTEM",
    "DESIGN_REVIEW",
    "PHASE_PLAN",
    "ENVIRONMENT",
    "PERFORMANCE",
    "DEVELOPMENT",
)
SOURCE = "Veri_Ufku_Birlestirilmis_Gelistirme_Promptlari.md"


def table_rows(text):
    return [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in text.splitlines()
        if line.startswith("| ") and not line.startswith("|---")
    ]


def check(root):
    root = Path(root)
    errors = []
    for name in REQUIRED:
        if not (root / "docs" / f"{name}.md").is_file():
            errors.append(f"Missing document: {name}")
    if errors:
        return errors
    source = (root / SOURCE).read_text()
    matrix = (root / "docs/REQUIREMENTS_MATRIX.md").read_text()
    phase_rows = [r for r in table_rows(matrix) if len(r) == 7 and r[0].isdigit()]
    phases = {}
    for row in phase_rows:
        number, _title, _deps, state, maturity, scope, reason = row
        if number in phases:
            errors.append(f"Duplicate phase: {number}")
        phases[number] = row
        if state not in PHASE_STATES or maturity not in MATURITY or scope not in SCOPES:
            errors.append(f"Invalid phase fields: {number}")
        if state == "engelli" and reason in {"", "—"}:
            errors.append(f"Missing blocker: {number}")
    if set(phases) != {f"{n:02d}" for n in range(76)}:
        errors.append("Expected exactly phases 00..75")
    graph = {}
    for number, row in phases.items():
        graph[number] = [] if row[2] == "—" else row[2].split(",")
        for dependency in graph[number]:
            if dependency not in phases:
                errors.append(f"Unknown dependency: {number}->{dependency}")
    visiting, visited = set(), set()

    def visit(number):
        if number in visiting:
            errors.append(f"Dependency cycle: {number}")
            return
        if number in visited or number not in graph:
            return
        visiting.add(number)
        for dependency in graph[number]:
            visit(dependency)
        visiting.remove(number)
        visited.add(number)

    for number, dependencies in graph.items():
        visit(number)
        if phases[number][3] == "doğrulandı":
            for dependency in dependencies:
                if dependency in phases and phases[dependency][3] != "doğrulandı":
                    errors.append(
                        f"Verified phase has unverified dependency: {number}->{dependency}"
                    )
    for filename, expected in [
        ("PROGRESS.md", range(28)),
        ("PRO_PROGRESS.md", range(28, 76)),
    ]:
        summary = [
            r
            for r in table_rows((root / "docs" / filename).read_text())
            if len(r) == 5 and r[0].isdigit()
        ]
        if {r[0] for r in summary} != {f"{n:02d}" for n in expected}:
            errors.append(f"Missing/extra summary phase: {filename}")
        if len(summary) != len({r[0] for r in summary}):
            errors.append(f"Duplicate summary phase: {filename}")
        for row in summary:
            if row[0] in phases and row[1:4] != phases[row[0]][3:6]:
                errors.append(f"Progress conflict: {filename}:{row[0]}")
    plan = table_rows((root / "docs/PHASE_PLAN.md").read_text())
    planned = {r[0]: r for r in plan if len(r) == 3 and r[0].isdigit()}
    if set(planned) != set(phases):
        errors.append("Phase plan incomplete")
    for number, row in planned.items():
        dependencies = "—" if row[2] == "Yok" else row[2].replace(" ", "")
        if number in phases and dependencies != phases[number][2]:
            errors.append(f"Dependency plan conflict: {number}")
    requirements = [r for r in table_rows(matrix) if len(r) == 10 and r[0] != "ID"]
    seen = set()
    for row in requirements:
        ident, phase, _, scope, maturity, validation, path, evidence, env, when = row
        if ident in seen:
            errors.append(f"Duplicate requirement: {ident}")
        seen.add(ident)
        if scope not in SCOPES or maturity not in MATURITY:
            errors.append(f"Invalid requirement fields: {ident}")
        if validation not in {"doğrulandı", "doğrulanmadı"}:
            errors.append(f"Invalid validation: {ident}")
        if phase not in phases and phase not in {"ortak", "ortak-prof"}:
            errors.append(f"Unknown requirement phase: {ident}")
        if validation == "doğrulandı":
            if any(value in {"", "—"} for value in [path, evidence, env, when]):
                errors.append(f"Missing verified evidence: {ident}")
            try:
                if date.fromisoformat(when) > datetime.now(UTC).date():
                    errors.append(f"Future evidence date: {ident}")
            except ValueError:
                errors.append(f"Invalid evidence date: {ident}")
            for candidate in path.split(";"):
                if not (root / candidate.strip()).is_file():
                    errors.append(f"Missing verified path: {ident}:{candidate}")
            filename, _, anchor = evidence.partition("#")
            evidence_file = root / filename
            if not evidence_file.is_file():
                errors.append(f"Missing evidence file: {ident}")
            elif anchor and f'id="{anchor}"' not in evidence_file.read_text():
                errors.append(f"Missing evidence anchor: {ident}")
            if phase in phases and scope == "ertelendi":
                errors.append(f"Deferred work cannot be accepted: {ident}")
        if (
            phase in phases
            and phases[phase][3] == "doğrulandı"
            and scope == "zorunlu"
            and validation != "doğrulandı"
        ):
            errors.append(f"Verified phase has pending requirement: {phase}:{ident}")
    # Ensure every source phase paragraph has a permanent record, without rerunning a generator.
    for match in re.finditer(
        r"^## Faz (\d{2}) — [^\n]+\n(.*?)(?=^## |\Z)", source, re.MULTILINE | re.DOTALL
    ):
        number = match[1]
        block = re.search(r"```text\n(.*?)\n```", match[2], re.DOTALL).group(1)
        paragraphs = [
            p.replace("\n", " ").strip().replace("|", "/")
            for p in block.split("\n\n")
            if p.strip()
        ]
        for index, paragraph in enumerate(paragraphs, 1):
            ident = f"F{number}-S{index:03d}"
            matches = [r for r in requirements if r[0] == ident]
            if len(matches) != 1 or matches[0][2] != paragraph:
                errors.append(
                    f"Source requirement lost/changed without mapping: {ident}"
                )
    for heading, filename, prefix in [
        ("Kalıcı ana proje promptu", "PROJECT_RULES.md", "CORE"),
        ("Kalıcı arayüz ve tasarım kuralları", "UI_DESIGN_BRIEF.md", "UI"),
    ]:
        section = re.search(
            r"^## " + re.escape(heading) + r"\n(.*?)(?=^## |\Z)",
            source,
            re.MULTILINE | re.DOTALL,
        ).group(1)
        block = re.search(r"```text\n(.*?)\n```", section, re.DOTALL).group(1)
        if block not in (root / "docs" / filename).read_text():
            errors.append(f"Permanent rules not preserved: {filename}")
        items = [
            line[2:].strip().replace("|", "/")
            for line in block.splitlines()
            if line.startswith("- ")
        ]
        for index, item in enumerate(items, 1):
            ident = f"{prefix}-{index:03d}"
            matches = [r for r in requirements if r[0] == ident]
            if len(matches) != 1 or matches[0][2] != item:
                errors.append(f"Common requirement lost: {ident}")
    # Local links are checked; network link success is a separate evidence type.
    for file in [
        root / "README.md",
        root / "AGENTS.md",
        *sorted((root / "docs").rglob("*.md")),
    ]:
        for target in re.findall(r"\]\(([^)]+)\)", file.read_text()):
            if re.match(r"^[a-z]+://", target) or target.startswith("#"):
                continue
            local = target.split("#", 1)[0]
            if local and not (file.parent / local).exists():
                errors.append(f"Broken local link: {file.relative_to(root)}:{local}")
    digest = (root / "docs/evidence/source.sha256").read_text().split()[0]
    if hashlib.sha256((root / SOURCE).read_bytes()).hexdigest() != digest:
        errors.append("Original source changed; update traceability explicitly")
    return errors


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    failures = check(root)
    if failures:
        print("\n".join(failures))
        sys.exit(1)
    print("PASS: 76 phases, source requirements, evidence, progress and local links")
