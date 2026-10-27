"""UX4: offline sample catalog metadata + Verilerim index (no project schema change)."""

import json
from pathlib import Path

from veri_ufku.storage import user_library as library
from veri_ufku.ui.data_library import load_sample_catalog


def test_sample_catalog_offline_and_licensed():
    samples = load_sample_catalog()
    assert {s["id"] for s in samples} >= {
        "sample.sales",
        "sample.problem",
        "sample.magaza",
    }
    for sample in samples:
        assert sample["available"]
        assert sample["license"].startswith("CC0")
        assert sample["synthetic"] is True
        assert Path(sample["path"]).is_file()
        assert "http" not in sample.get("source_url", "x")


def test_verilerim_add_use_delete_preserves_source_and_other_index(tmp_path):
    data_home = tmp_path / "xdg-data"
    source = tmp_path / "musteri.csv"
    source.write_text("id,ad\n1,a\n2,b\n", encoding="utf-8")
    before = source.read_bytes()
    entry = library.add_file_entry(
        data_home,
        source,
        name="Müşteri deneme",
        description="test",
        tags=["demo", "tr"],
    )
    assert entry["id"].startswith("lib:")
    assert Path(entry["stored_path"]).is_file()
    assert source.read_bytes() == before
    assert library.disk_usage_bytes(data_home) > 0

    found = library.find_entry(data_home, entry["id"])
    assert found["name"] == "Müşteri deneme"
    assert found["fingerprint"]["sha256"] == entry["fingerprint"]["sha256"]

    other = tmp_path / "other.csv"
    other.write_text("x\n1\n", encoding="utf-8")
    second = library.add_file_entry(data_home, other, name="Diğer")
    assert library.remove_entry(data_home, entry["id"]) is True
    assert library.find_entry(data_home, entry["id"]) is None
    assert library.find_entry(data_home, second["id"]) is not None
    assert Path(second["stored_path"]).is_file()
    index = library.load_index(data_home)
    assert index["schema_version"] == 1
    assert len(index["entries"]) == 1


def test_library_index_is_not_project_store(tmp_path):
    data_home = tmp_path / "xdg-data"
    source = tmp_path / "a.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    library.add_file_entry(data_home, source, name="A")
    index_file = library.index_path(data_home)
    payload = json.loads(index_file.read_text(encoding="utf-8"))
    assert "ACTIVE" not in payload
    assert "datasets" not in payload
    assert "sources" not in payload
    assert "entries" in payload
