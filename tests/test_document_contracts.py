"""Negative tests for durable acceptance records; no analytic implementation tests."""

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_docs", ROOT / "scripts/check_docs.py"
)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class DocumentContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="veri-ufku-contract-")
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "docs", self.root / "docs")
        for filename in [
            "README.md",
            "AGENTS.md",
            "pyproject.toml",
            "uv.lock",
            CHECKER.SOURCE,
        ]:
            shutil.copy2(ROOT / filename, self.root / filename)
        shutil.copytree(ROOT / "scripts", self.root / "scripts")
        shutil.copytree(ROOT / "src", self.root / "src")
        shutil.copytree(ROOT / "tests", self.root / "tests")
        shutil.copytree(ROOT / ".github", self.root / ".github")

    def tearDown(self):
        self.temp.cleanup()

    def mutate(self, filename, before, after):
        path = self.root / filename
        text = path.read_text()
        self.assertIn(before, text)
        path.write_text(text.replace(before, after, 1))

    def test_current_documents(self):
        self.assertEqual(CHECKER.check(self.root), [])

    def test_progress_conflict_is_rejected(self):
        row = next(
            line
            for line in (self.root / "docs/PROGRESS.md").read_text().splitlines()
            if line.startswith("| 01 |")
        )
        state = row.split("|")[2].strip()
        other = "sürüyor" if state == "doğrulandı" else "doğrulandı"
        self.mutate("docs/PROGRESS.md", f"| 01 | {state} |", f"| 01 | {other} |")
        self.assertTrue(any("Progress conflict" in e for e in CHECKER.check(self.root)))

    def test_false_completion_is_rejected(self):
        self.mutate(
            "docs/REQUIREMENTS_MATRIX.md",
            "| başlanmadı | mevcut değil | zorunlu |",
            "| doğrulandı | mevcut değil | zorunlu |",
        )
        self.assertTrue(
            any("pending requirement" in e for e in CHECKER.check(self.root))
        )

    def test_missing_evidence_is_rejected(self):
        self.mutate(
            "docs/REQUIREMENTS_MATRIX.md",
            "docs/evidence/PHASE00.md#e00-001",
            "docs/evidence/missing.md#e00-001",
        )
        self.assertTrue(
            any("Missing evidence file" in e for e in CHECKER.check(self.root))
        )

    def test_dependency_cycle_is_rejected(self):
        self.mutate(
            "docs/REQUIREMENTS_MATRIX.md",
            "| 01 | Çalışan proje iskeleti ve görev altyapısı | 00 |",
            "| 01 | Çalışan proje iskeleti ve görev altyapısı | 01 |",
        )
        self.assertTrue(any("Dependency cycle" in e for e in CHECKER.check(self.root)))

    def test_unverified_dependency_is_rejected(self):
        self.mutate(
            "docs/REQUIREMENTS_MATRIX.md",
            "| 00 | Kapsam, mimari ve geliştirme planı | — |",
            "| 00 | Kapsam, mimari ve geliştirme planı | 01 |",
        )
        self.assertTrue(
            any("unverified dependency" in e for e in CHECKER.check(self.root))
        )

    def test_source_scope_loss_is_rejected(self):
        self.mutate("docs/REQUIREMENTS_MATRIX.md", "F05-S001", "F05-REMOVED")
        self.assertTrue(
            any("Source requirement lost" in e for e in CHECKER.check(self.root))
        )

    def test_duplicate_id_is_rejected(self):
        self.mutate("docs/REQUIREMENTS_MATRIX.md", "F00-002", "F00-001")
        self.assertTrue(
            any("Duplicate requirement" in e for e in CHECKER.check(self.root))
        )

    def test_broken_link_is_rejected(self):
        self.mutate("README.md", "docs/PRODUCT.md", "docs/MISSING.md")
        self.assertTrue(any("Broken local link" in e for e in CHECKER.check(self.root)))


if __name__ == "__main__":
    unittest.main()
