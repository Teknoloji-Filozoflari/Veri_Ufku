import hashlib
import json
from pathlib import Path

from veri_ufku.learning.catalog import Catalog
from veri_ufku.learning.taxonomy import CONTEXT_ONLY, STAGES, learning_tree
from veri_ufku.ui.learning import LearningController


def test_published_topics_have_one_home_and_context_help_is_separate():
    catalog = Catalog()
    ids = [
        key for _, _, groups in STAGES for _, _, keys in groups for key in keys.split()
    ]
    assert len(ids) == len(set(ids))
    assert not set(ids) & CONTEXT_ONLY
    assert set(ids) | CONTEXT_ONLY == set(catalog.articles)
    tree = learning_tree([dict(id=k) for k in catalog.articles])
    assert len(tree) == 10
    assert {topic["id"] for topic in tree[-1]["groups"][0]["topics"]} == {
        "workflow-recipe",
        "workflow-drift",
        "workflow-model",
    }
    filtered = learning_tree([dict(id="mean-median")])
    assert filtered[0]["id"] == "analysis"
    assert filtered[0]["groups"][0]["id"] == "descriptive"


def test_source_preserved_and_reading_content_available_offline(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = root / "docs/learning_sources/VERI.md"
    provenance = json.loads((source.parent / "VERI_PROVENANCE.json").read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["sha256"]
    controller = LearningController(tmp_path, sandbox=True)
    controller.openArticle("data")
    guide = controller.article["guide"]
    assert len(guide) >= 10
    assert all(block["heading"] and block["text"] for block in guide)
    assert "Aralık ölçeğinde" in guide[3]["text"]
    assert "![[" not in json.dumps(controller.article)
    controller.setQuery("medyan")
    assert any(
        g["id"] == "descriptive" for stage in controller.tree for g in stage["groups"]
    )


def test_analysis_source_and_five_explanations():
    root = Path(__file__).resolve().parents[1]
    source = root / "docs/learning_sources/VERININ_ANALIZI.md"
    provenance = json.loads((source.parent / "ANALIZ_PROVENANCE.json").read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["sha256"]
    catalog = Catalog()
    keys = [
        "analysis-overview",
        "analysis-descriptive",
        "analysis-diagnostic",
        "analysis-predictive",
        "analysis-prescriptive",
        "analysis-exploratory",
    ]
    for key in keys:
        article = catalog.articles[key]
        assert all(block["heading"] for block in article["guide"])
        assert (
            article["sources"][0]["reference"]
            == "docs/learning_sources/VERININ_ANALIZI.md"
        )
        assert "![[" not in json.dumps(article)
    tree = learning_tree([dict(id=key) for key in keys])
    assert tree[0]["id"] == "analysis"
    assert len(tree[0]["groups"]) == 6
    assert tree[0]["groups"][4]["topics"][0]["id"] == "analysis-prescriptive"


def test_cleaning_source_excludes_code_and_preserves_training_scope():
    root = Path(__file__).resolve().parents[1]
    source = root / "docs/learning_sources/VERI_TEMIZLEME.md"
    raw = source.read_text()
    assert (
        "```" not in raw and "pd.concat" not in raw and "def detect_outliers" not in raw
    )
    catalog = Catalog()
    keys = [
        "cleaning-overview",
        "cleaning-clean",
        "cleaning-merge",
        "cleaning-transform",
        "cleaning-reduce",
        "cleaning-minmax",
        "cleaning-zscore",
        "cleaning-decimal",
    ]
    for key in keys:
        article = catalog.articles[key]
        assert "```" not in json.dumps(article)
        assert all(block["heading"] for block in article["guide"])
    assert "otomatik silinmez" in catalog.articles["cleaning-clean"]["guide"][2]["text"]
    assert "yalnız eğitim" in catalog.articles["cleaning-minmax"]["guide"][2]["text"]
    assert "garantisi değildir" in catalog.articles["cleaning-zscore"]["critical"]
    tree = learning_tree([dict(id=key) for key in keys])
    assert tree[0]["id"] == "cleaning"
    assert {g["id"] for g in tree[0]["groups"]} == {
        "cleaning-intro",
        "clean",
        "merge",
        "transform",
        "reduce",
    }
