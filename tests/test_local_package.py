"""Local package keeps the report and operation text, not raw cells."""

import json
import zipfile
from contextlib import closing

import polars as pl
import pytest
from test_dataset import prepare

from veri_ufku.exports.local_package import export
from veri_ufku.importers.delimited import Control


def test_package_lists_identity_and_omits_raw_cells(tmp_path):
    secret = "kisi@example.com"
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"kod": [1, 2], "eposta": [secret, "baska@example.com"]})
    )
    request["report_context"] = {
        "project_seed": 17,
        "operations": [
            {
                "seed": 17,
                "spec": {
                    "kind": "replace",
                    "parameters": {"replacement": secret},
                },
            }
        ],
        "result_seeds": [],
    }
    destination = tmp_path / "paket.zip"
    with closing(store):
        info = export(
            request,
            {
                "format": "zip",
                "title": "Paket",
                "purpose": "kayıt",
                "scope": "full",
                "table_rows": 20,
                "include_personal": False,
            },
            work,
            destination,
            store.root,
            Control(),
        )
    assert info["raw_included"] is False
    assert destination.is_file()
    with zipfile.ZipFile(destination) as archive:
        names = set(archive.namelist())
        assert names == {
            "README.txt",
            "veri.json",
            "islemler.py",
            "tohum.txt",
            "ortam.txt",
            "rapor.html",
        }
        blob = "\n".join(
            archive.read(name).decode() for name in names if name != "veri.json"
        )
        identity = json.loads(archive.read("veri.json"))
        history = archive.read("islemler.py").decode()
        seed = archive.read("tohum.txt").decode()
        listed = archive.read("veri.json").decode()
    assert secret not in blob
    assert "replace" in history
    assert "tohum 17" in seed
    assert identity["raw_included"] is False
    assert identity["dataset_version"] == request["version_id"]
    assert all(str(item).startswith("col:") for item in identity["column_ids"])
    assert "eposta" not in listed


def test_summary_omits_cells_that_the_sample_keeps(tmp_path):
    marker = "benzersiz-hucre"
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"kod": [marker, "diger"], "n": [1, 2]})
    )
    destination = tmp_path / "ozet.zip"
    sample = tmp_path / "ornek.zip"
    with closing(store):
        export(
            request,
            {"format": "zip", "scope": "full", "table_rows": 20, "share_mode": "ozet"},
            work,
            destination,
            store.root,
            Control(),
        )
        export(
            request,
            {
                "format": "zip",
                "scope": "full",
                "table_rows": 20,
                "share_mode": "orneklem",
            },
            work,
            sample,
            store.root,
            Control(),
        )
    with zipfile.ZipFile(destination) as archive:
        summary = archive.read("rapor.html").decode()
        identity = json.loads(archive.read("veri.json"))
    with zipfile.ZipFile(sample) as archive:
        shown = archive.read("rapor.html").decode()
    assert marker not in summary
    assert "hücre değeri içermez" in summary
    assert identity["share_mode"] == "ozet"
    assert marker in shown


def test_full_copy_mode_is_refused(tmp_path):
    from veri_ufku.storage.project_model import ProjectError

    with pytest.raises(ProjectError):
        export(
            {},
            {"format": "zip", "share_mode": "full-copy"},
            tmp_path,
            tmp_path / "tam.zip",
            tmp_path / "proje",
            Control(),
        )
