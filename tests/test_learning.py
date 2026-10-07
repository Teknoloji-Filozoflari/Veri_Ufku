import copy
import json
from pathlib import Path

import pytest

from veri_ufku.learning.catalog import Catalog, validate, validate_bindings
from veri_ufku.ui.learning import LearningController

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_offline_search_turkish_categories_glossary_and_sources():
    catalog = Catalog()
    assert set(catalog.articles) >= {
        "data",
        "rows-columns",
        "data-types",
        "missing",
        "mean-median",
        "sample",
        "correlation",
        "prediction",
        "leakage",
    }
    assert [a["id"] for a in catalog.search("MEDYAN", "Özetler")] == ["mean-median"]
    assert [a["id"] for a in catalog.search("SIZINTI", "Modelleme")] == ["leakage"]
    assert catalog.search("şu içerikte olmayan sözcükler") == []
    assert len(catalog.search(glossary=True)) == 18
    # Independent editorial fixtures: no statistics engine called to check them.
    article = catalog.articles["mean-median"]
    assert article["example"]["before"] == "Tutarlar: 10, 20, 90."
    assert (
        article["example"]["after"]
        == "Ortalama 40; sıralı listenin ortasındaki medyan 20."
    )
    assert (
        catalog.articles["correlation"]["critical"]
        == "Korelasyon nedensellik değildir."
    )
    assert all(a["critical"] and a["sources"] for a in catalog.articles.values())
    assert catalog.article_for("model") == "prediction"
    assert catalog.article_for("prepare") == "operation-preview"
    assert catalog.article_for("demo.io") == "tasks"
    assert validate_bindings(ROOT, catalog) >= 6


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(schema_version=99),
        lambda d: d["articles"][0].pop("title"),
        lambda d: d["articles"][0]["contexts"].append("missing.screen"),
        lambda d: d.update(content_version=True),
        lambda d: d["articles"].append(copy.deepcopy(d["articles"][0])),
        lambda d: d["articles"][0]["related"].append("does-not-exist"),
        lambda d: d["contexts"].update(model="does-not-exist"),
        lambda d: d["articles"][0]["guide"].append(
            {"kind": "html", "text": "<script>alert(1)</script>"}
        ),
        lambda d: d["articles"][0].update(try_action="model.fit"),
        lambda d: d["articles"][0]["sources"][0].update(
            reference="javascript:alert(1)"
        ),
        lambda d: d["actions"]["learn.example"].update(feature="model.fit"),
    ],
)
def test_invalid_content_and_unimplemented_actions_rejected(mutation):
    data = copy.deepcopy(Catalog().data)
    mutation(data)
    with pytest.raises(ValueError):
        validate(data)


def test_missing_qml_help_and_capability_links_fail_gate(tmp_path, monkeypatch):
    from dataclasses import replace

    from veri_ufku.domain.capabilities import CAPABILITIES

    directory = tmp_path / "src/veri_ufku/ui/qml"
    directory.mkdir(parents=True)
    (directory / "Broken.qml").write_text('UiButton { helpContext: "missing.help" }')
    with pytest.raises(ValueError, match="Missing help context"):
        validate_bindings(tmp_path)
    (directory / "Broken.qml").write_text(
        "UiButton { helpContext: 'missing.help' }\nUiButton { helpContext: \"home\" }"
    )
    with pytest.raises(ValueError, match="Missing help context"):
        validate_bindings(tmp_path)
    (directory / "Broken.qml").write_text('UiButton { helpContext: "home" }')
    monkeypatch.setitem(
        CAPABILITIES,
        "demo.cpu",
        replace(CAPABILITIES["demo.cpu"], help_links=("absent",)),
    )
    with pytest.raises(ValueError, match="Missing capability article"):
        validate_bindings(tmp_path)


def test_optional_marks_atomic_reload_opt_out_and_existing_bad_file(
    tmp_path, monkeypatch
):
    from PySide6.QtCore import QSaveFile

    runtime = tmp_path / "settings.json"
    runtime.write_bytes(b'{"locale":"tr"}')
    before = runtime.read_bytes()
    library = LearningController(tmp_path)
    library.openArticle("leakage")
    library.toggleRead()
    assert not library.path.exists()  # No implicit reading history or writes.
    library.setMarksEnabled(True)
    library.toggleRead()
    library.toggleBookmark()
    assert library.path.stat().st_mode & 0o777 == 0o600
    saved = library.path.read_bytes()
    reloaded = LearningController(tmp_path)
    reloaded.openArticle("leakage")
    assert reloaded.marksEnabled and reloaded.isRead and reloaded.isBookmarked
    with monkeypatch.context() as patch:
        patch.setattr(QSaveFile, "commit", lambda _self: False)
        reloaded.toggleBookmark()
    assert reloaded.isBookmarked and reloaded.path.read_bytes() == saved
    assert reloaded.errorText
    reloaded.setMarksEnabled(False)
    assert not reloaded.isRead and not reloaded.isBookmarked
    assert not LearningController(tmp_path).marksEnabled
    assert runtime.read_bytes() == before
    library.path.write_text('{"schema_version":999}')
    malformed = library.path.read_bytes()
    damaged = LearningController(tmp_path)
    damaged.setMarksEnabled(True)
    assert damaged.path.read_bytes() == malformed
    assert damaged.errorText and damaged.results
    assert json.loads(malformed)["schema_version"] == 999


def test_example_project_separate_query_article_marks_and_no_disk_writes(tmp_path):
    library = LearningController(tmp_path)
    library.openArticle("learn")
    library.setQuery("sızıntı")
    library.setCategory("Modelleme")
    library.setDepth(2)
    library.setMarksEnabled(True)
    library.toggleBookmark()
    before = library.path.read_bytes()
    library.tryExample()
    example = library.exampleLibrary
    assert example.projectId.startswith("learning-example:")
    assert example.article["id"] == "mean-median"
    example.setQuery("eksik")
    example.openArticle("missing")
    example.setMarksEnabled(True)
    example.toggleRead()
    assert library.query == "sızıntı" and library.category == "Modelleme"
    assert library.article["id"] == "learn" and library.depth == 2
    assert library.path.read_bytes() == before
    assert not example.marksEnabled
    library.openArticle("prediction")
    old_id = example.projectId
    library.tryExample()
    assert example.projectId == old_id  # Unavailable model has no try action.
