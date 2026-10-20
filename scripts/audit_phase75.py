"""Final evidence inventory, never promote source presence or module tests to scientific acceptance."""

import argparse
import csv
import hashlib
import json
import platform
import re
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from audit_phase28 import TESTS as EARLY_TESTS
from check_docs import table_rows

from veri_ufku.domain.capabilities import CAPABILITIES, availability

ROOT = Path(__file__).resolve().parents[1]
TESTS = {
    **EARLY_TESTS,
    **dict(
        zip(
            [str(i) for i in range(28, 75)],
            [
                "workspace",
                "workspace",
                "advanced_import advanced_import_gui",
                "connectors connector_gui connector_optional_servers",
                "data_contracts data_contracts_gui",
                "missing_sampling missing_sampling_gui",
                "arrays arrays_gui",
                "distributions distributions_gui",
                "multivariate multivariate_gui",
                "composition composition_gui",
                "geo geo_gui",
                "dashboard dashboard_gui",
                "statistical_models statistical_models_gui",
                "resampling resampling_gui",
                "experiments experiments_gui",
                "bayes bayes_gui",
                "causal causal_gui",
                "survival survival_gui",
                "dimensions dimensions_gui",
                "unsupervised unsupervised_gui",
                "model_families model_families_gui model_family_support",
                "search search_gui",
                "uncertainty uncertainty_gui",
                "explanation explanation_gui",
                "experiment_registry experiment_registry_gui",
                "temporal temporal_gui",
                "signals signals_gui",
                "nlp nlp_gui",
                "neural neural_gui",
                "vision vision_gui",
                "audio audio_gui",
                "recommendation recommendation_gui",
                "patterns patterns_gui",
                "graphs graphs_gui",
                "streams streams_gui",
                "code_bridge code_bridge_gui",
                "workflow workflow_gui",
                "repro repro_gui",
                "compute_budget compute_budget_gui",
                "monitoring monitoring_gui",
                "scenarios scenarios_gui",
                "learning_lab learning_lab_gui",
                "report_builder report_builder_gui",
                "share share_gui",
                "privacy privacy_gui",
                "plugins plugins_gui",
                "environment_distribution environment_gui",
            ],
            strict=True,
        )
    ),
}
TESTS["75"] = "release_benchmarks release_audit"


def hash_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def release_gate(requirements, checks, human_review):
    """No waiver by excluding unproven mandatory requirements after seeing results."""
    return (
        bool(requirements)
        and all(r["verified"] is True for r in requirements)
        and bool(checks)
        and all(v is True for v in checks)
        and human_review is True
    )


def parse_cases(paths):
    cases = []
    for path in paths:
        sidecar = path.parent / "fixtures.json"
        witnesses = (
            json.loads(sidecar.read_text()).get("cases", [])
            if sidecar.is_file()
            else []
        )
        for c in ET.parse(path).iter("testcase"):
            module = c.get("classname", "").split(".")[-1]
            witness = next(
                (
                    w
                    for w in witnesses
                    if w["nodeid"].split("::", 1)[-1] == c.get("name")
                    and Path(w["nodeid"].split("::", 1)[0]).stem == module
                ),
                None,
            )
            test_file = ROOT / "tests" / (module + ".py")
            status = next(
                (
                    tag
                    for tag in ("failure", "error", "skipped")
                    if c.find(tag) is not None
                ),
                "passed",
            )
            cases.append(
                dict(
                    module=module,
                    name=c.get("name"),
                    status=status,
                    seconds=float(c.get("time", 0)),
                    junit=str(path.relative_to(ROOT)),
                    junit_sha256=hash_file(path),
                    test_source_current=(
                        witness["test_file_sha256"] == hash_file(test_file)
                    )
                    if witness and test_file.is_file()
                    else None,
                    witness_manifest=str(sidecar.relative_to(ROOT))
                    if sidecar.is_file()
                    else None,
                )
            )
    return cases


def classification(maturity, implemented):
    # No stable claim based on a registry adjective alone; independent acceptance is absent.
    return "deneysel" if implemented and maturity != "mevcut değil" else "eksik"


def build(junits):
    rows = table_rows((ROOT / "docs/REQUIREMENTS_MATRIX.md").read_text())
    phases = [r for r in rows if len(r) == 7 and r[0].isdigit()]
    requirements = {
        r[0]: r for r in rows if len(r) == 10 and re.fullmatch(r"F\d\d-[SP]\d{3}", r[0])
    }
    cases = parse_cases(junits)
    artifacts = {}

    def tracked(path):
        p = ROOT / path
        if p.is_file():
            artifacts[path] = hash_file(p)
        return p.is_file()

    p_rows = []
    for p in phases:
        req = [r for k, r in requirements.items() if k.startswith("F" + p[0] + "-")]
        tests = ["tests/test_" + n + ".py" for n in TESTS.get(p[0], "").split()]
        for t in tests:
            tracked(t)
        matched = [
            c
            for c in cases
            if c["module"] in {"test_" + n for n in TESTS.get(p[0], "").split()}
        ]
        p_rows.append(
            dict(
                phase=p[0],
                title=p[1],
                state=p[3],
                maturity=p[4],
                classification=classification(
                    p[4], any(r[4] != "mevcut değil" for r in req)
                ),
                scope=p[5],
                mandatory_unverified=[
                    r[0] for r in req if r[3] == "zorunlu" and r[5] != "doğrulandı"
                ],
                subrequirements=[
                    dict(
                        id=r[0],
                        classification=classification(r[4], r[4] != "mevcut değil"),
                        verification=r[5],
                        scope=r[3],
                        paths=r[6],
                        evidence=r[7],
                    )
                    for r in req
                ],
                candidate_test_files=tests,
                current_cases=matched,
                whole_phase_reverified=False,
            )
        )
    content = json.loads((ROOT / "src/veri_ufku/learning/content/tr.json").read_text())
    articles = {a["id"]: a for a in content["articles"]}
    caps = []
    for ident, c in sorted(CAPABILITIES.items()):
        present, reason = availability(c)
        req = [requirements[k] for k in c.requirement_ids if k in requirements]
        paths = sorted(
            {
                s.strip()
                for r in req
                for s in r[6].split(";")
                if s.strip().startswith("src/")
            }
        )
        existing = [p for p in paths if tracked(p)]
        phases_for_c = sorted({r[1].zfill(2) for r in req})
        tpaths = sorted(
            {
                "tests/test_" + n + ".py"
                for p in phases_for_c
                for n in TESTS.get(p, "").split()
            }
        )
        tests = [p for p in tpaths if tracked(p)]
        associated = [
            case for case in cases if case["module"] in {Path(p).stem for p in tests}
        ]
        missing_help = [a for a in c.help_links if a not in articles]
        refs = [p for p in c.evidence_refs if tracked(p.split("#")[0])]
        caps.append(
            dict(
                id=ident,
                classification=classification(
                    c.maturity, bool(existing) and not missing_help
                ),
                declared=asdict(c),
                phases=phases_for_c,
                implementation_paths=existing,
                unresolved_paths=[p for p in paths if p not in existing],
                candidate_test_files=tests,
                gui_test_files=[p for p in tests if p.endswith("_gui.py")],
                help_ids=list(c.help_links),
                missing_help=missing_help,
                historical_evidence=refs,
                current_associated_cases=associated,
                witness_scope="phase-associated test modules, not individual-method proof; no promotion from names",
                operations=[
                    dict(
                        name=v.name,
                        classification="deneysel"
                        if v.status in ("supported", "conditional")
                        else "eksik",
                        declared_status=v.status,
                        condition=v.condition,
                    )
                    for v in c.operations
                ],
                supports=[
                    dict(
                        name=v.name,
                        classification="deneysel"
                        if v.status in ("supported", "conditional")
                        else "eksik",
                        declared_status=v.status,
                        condition=v.condition,
                    )
                    for v in c.support_details
                ],
                independently_expert_reviewed=False,
                environment_presence=dict(
                    available=present,
                    reason=reason,
                    scope="metadata only; not backend execution validation",
                ),
                whole_method_reverified=False,
            )
        )
    for p in (
        "src/veri_ufku/domain/capabilities.py",
        "src/veri_ufku/ui/workspace.py",
        "src/veri_ufku/ui/qml/Main.qml",
        "uv.lock",
        "docs/REQUIREMENTS_MATRIX.md",
    ):
        tracked(p)
    for folder in ("src/veri_ufku",):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                tracked(str(path.relative_to(ROOT)))
    mandatory = [
        dict(verified=r[5] == "doğrulandı")
        for r in requirements.values()
        if r[0].startswith("F75-") and r[3] == "zorunlu"
    ]
    verified = release_gate(
        mandatory, [bool(cases) and all(c["status"] == "passed" for c in cases)], False
    )
    return dict(
        schema="ReleaseAudit/v1",
        date=datetime.now(UTC).isoformat(),
        environment=dict(
            python=platform.python_version(), platform=platform.platform()
        ),
        scope="All76phase classifications and static416capabilities; current tests are explicit bounded selection. Not full method/expert/human certification.",
        phase_rows=p_rows,
        capabilities=caps,
        artifact_hashes=artifacts,
        summary=dict(
            phases=len(p_rows),
            capabilities=len(caps),
            classes={
                k: sum(c["classification"] == k for c in caps)
                for k in ("kararlı", "deneysel", "eksik")
            },
            current_cases=len(cases),
            case_outcomes={
                k: sum(c["status"] == k for c in cases)
                for k in ("passed", "failure", "error", "skipped")
            },
        ),
        release_verified=verified,
        reason="Mandatory human/expert/minHW/AT/cleanOS gates remain open; all-method completion not claimed",
    )


def render(value):
    out = [
        "## Faz75 güncel sınıflandırma — ana denetim tablosu",
        "",
        "Bu bölüm güncel sınıflandırmadır; yukarıdaki Faz28 kayıtları tarihsel kapsamdır. Kararlı=bağımsız kabul gerektirir; bu denetim hiçbir yöntemi kararlıya yükseltmez. Deneysel=bounded teknik yol; eksik=mevcut değil/unknown/unsupported. Alt işlemlerden birinin eksikliği yöntem ailesini tamamlandı yapmaz. Test dosyası/GUI testi varlığı çalıştırılmış yöntem kabulü değildir.",
        "",
        "[Makine denetimi ve kod/test hashleri](evidence/phase75/capability-audit.json), [gerçek koşular ve sınırlar](evidence/PHASE75.md). GUI tanığı yalnız karşılık gelen current JUnit case PASS ise bu koşuya aittir. Özel plugin session kayıtları static snapshot kapsamına girmez.",
        "",
        "| Faz | Teknik sınıf | Resmî durum / kapsam | Kanıtlanmamış zorunlu sayısı |",
        "|---|---|---|---|",
    ]
    for p in value["phase_rows"]:
        out.append(
            f"| {p['phase']} | {p['classification']} | {p['state']} / {p['scope']} | {len(p['mandatory_unverified'])} |"
        )
    out += [
        "",
        "### Her fazın alt gereksinimleri",
        "",
        "Kaynak S ve plan P kayıtları aynen ana matrise bağlıdır. `doğrulanmadı` tamamlandı değildir. Engelli/ertelendi bağımsız açık kalır.",
        "",
        "| Alt gereksinim | Sınıf | Doğrulama | Kapsam |",
        "|---|---|---|---|",
    ]
    for p in value["phase_rows"]:
        for r in p["subrequirements"]:
            out.append(
                f"| {r['id']} | {r['classification']} | {r['verification']} | {r['scope']} |"
            )
    out += [
        "",
        "### Runtime yöntemleri ve alt işlem destekleri",
        "",
        "JSON her method için backend/input/output/limits/assumptions/source/help/test/JUnit ve support_details ayrımını taşır. Aşağıdaki test sayısı phase-module ilişkisidir; direct bilimsel doğrulama sayısı değildir. `?` unknown ve `-` unsupported eksik kapsamdır.",
        "",
        "| Capability | Sınıf | Faz | GUI test dosyası | Alt işlem desteği | Güncel ilişkili PASS/fail/skip |",
        "|---|---|---|---|---|---|",
    ]
    for c in value["capabilities"]:
        ops = ", ".join(
            o["name"]
            + ":"
            + (
                {
                    "supported": "E",
                    "conditional": "E koşullu",
                    "unsupported": "- eksik",
                    "unknown": "? eksik",
                }[o["declared_status"]]
            )
            for o in c["operations"]
        )
        counts = "/".join(
            str(sum(t["status"] == s for t in c["current_associated_cases"]))
            for s in ("passed", "failure", "skipped")
        )
        gui = (
            ", ".join(Path(p).name for p in c["gui_test_files"])
            or "doğrulanmış bağ yok"
        )
        out.append(
            f"| {c['id']} | {c['classification']} | {','.join(c['phases'])} | {gui} | {ops} | {counts} |"
        )
    return "\n".join(out) + "\n"


def learning_review(folder):
    worksheet = folder / "expert-review-worksheet.csv"
    if worksheet.exists():
        with worksheet.open(newline="") as stream:
            if any(
                row.get("reviewer")
                or row.get("reviewed_at")
                or row.get("decision")
                or row.get("issues")
                for row in csv.DictReader(stream)
            ):
                raise FileExistsError(
                    "Human review worksheet preserved; choose a fresh audit directory"
                )
    article_path = ROOT / "src/veri_ufku/learning/content/tr.json"
    lesson_path = ROOT / "src/veri_ufku/learning/content/lessons.tr.json"
    a = json.loads(article_path.read_text())
    lessons_data = json.loads(lesson_path.read_text())
    rows = []
    for kind, items in (
        ("article", a["articles"]),
        ("lesson", lessons_data["lessons"]),
    ):
        for v in items:
            rows.append(
                dict(
                    kind=kind,
                    id=v["id"],
                    content_sha256=hashlib.sha256(
                        json.dumps(v, ensure_ascii=False, sort_keys=True).encode()
                    ).hexdigest(),
                    content_version=v.get(
                        "content_version",
                        lessons_data["content_version"]
                        if kind == "lesson"
                        else a["content_version"],
                    ),
                    title=v["title"],
                    status="pending-independent-expert",
                    reviewer=None,
                    reviewed_at=None,
                    decision=None,
                    existing_technical_review_is_expert_approval=False,
                    checklist=[
                        "numeric reference and tolerance",
                        "assumptions and contraindications",
                        "false interpretation and uncertainty",
                        "units/measurement/design",
                        "source accuracy/version/license",
                        "Turkish clarity and accessibility",
                        "actual GUI/help/export correspondence",
                    ],
                )
            )
    (folder / "learning-review.json").write_text(
        json.dumps(
            dict(
                source_hashes={
                    str(article_path.relative_to(ROOT)): hash_file(article_path),
                    str(lesson_path.relative_to(ROOT)): hash_file(lesson_path),
                },
                rows=rows,
                expert_approved=False,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    with worksheet.open("w", newline="") as f:
        fields = [
            "kind",
            "id",
            "content_sha256",
            "status",
            "reviewer",
            "reviewed_at",
            "decision",
            "evidence",
            "issues",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fields})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--junit", type=Path, action="append", default=[])
    p.add_argument("--update-matrix", action="store_true")
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    value = build(a.junit)
    (a.output / "capability-audit.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    )
    learning_review(a.output)
    if a.update_matrix:
        path = ROOT / "docs/PRO_CAPABILITY_MATRIX.md"
        s = path.read_text()
        marker = "<!-- PHASE75 GENERATED AUDIT -->"
        s = s.split(marker)[0].rstrip() + "\n\n" + marker + "\n" + render(value)
        path.write_text(s)
    print(json.dumps(value["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
