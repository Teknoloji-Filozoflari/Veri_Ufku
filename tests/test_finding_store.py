"""Bulgu defteri: kalıcılık, sürüm bağı, güncellik işareti ve rapor akışı."""

import copy

import polars as pl
import pytest

from veri_ufku.exports.report_contracts import recipe
from veri_ufku.storage import finding_store as storage
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore

SOURCE_ID = "source:00000000-0000-4000-8000-000000000001"
DATASET_ID = "dataset:00000000-0000-4000-8000-000000000001"
VERSION_ID = "dv:00000000-0000-4000-8000-000000000001"
VERSION_TWO = "dv:00000000-0000-4000-8000-000000000002"


def build(tmp_path, with_run=True):
    """A project store with one dataset version and an optional quality run."""
    source = tmp_path / "source.csv"
    source.write_text("value;name\n1;a\n2;a\n;b\n", encoding="utf-8")
    store = ProjectStore.create(tmp_path / "project", "Bulgu defteri")
    ref = store.stage_source(source, portable=True)
    uri = store.stage_parquet(
        pl.DataFrame(
            {
                "value": [1, 2, None],
                "name": ["a", "a", "b"],
                "__vu_row_id": ["r1", "r2", "r3"],
                "__vu_source_record_id": ["s1", "s2", "s3"],
                "__vu_start_line": [1, 2, 3],
                "__vu_end_line": [1, 2, 3],
            }
        )
    )
    store.state.update(import_settings={"delimiter": ";", "encoding": "utf-8-sig"})
    store.state["datasets"].append(
        dict(
            dataset_id=DATASET_ID,
            version_id=VERSION_ID,
            source_id=ref["id"],
            snapshot_uri=uri,
            import_metadata=dict(
                columns=[
                    dict(
                        id="col:00000000-0000-4000-8000-000000000001",
                        name="value",
                        original_name="value",
                        type="int64",
                    ),
                    dict(
                        id="col:00000000-0000-4000-8000-000000000002",
                        name="name",
                        original_name="name",
                        type="text",
                    ),
                ],
                row_count=3,
                bad_count=0,
                source_snapshot_id="snapshot:00000000-0000-4000-8000-000000000001",
                captured_at="2026-11-13T00:00:00+00:00",
                settings=dict(
                    delimiter=";", encoding="utf-8-sig", types=("int64", "text")
                ),
            ),
        )
    )
    if with_run:
        store.state["results"].append(
            dict(
                id="result:00000000-0000-4000-8000-000000000001",
                dataset_version_ids=[VERSION_ID],
                seed=None,
                capability_id="dataset.quality",
                quality=dict(
                    row_count=3,
                    columns=[{"id": "value"}, {"id": "name"}],
                    missing_total=1,
                ),
            )
        )
    store.save()
    return store


def test_finding_is_created_from_the_recorded_run(tmp_path):
    store = build(tmp_path)
    finding = storage.create(
        store.state,
        "incele",
        "Kaç satır eksik?",
        "dataset.quality taraması",
        interpretation="Eksiklik tek satırda.",
        decision="Doldurma yerine satırı incele.",
    )
    assert finding["result_status"] == "recorded"
    assert "3 satır" in finding["result"]
    assert finding["dataset_version_ids"] == [VERSION_ID]
    assert finding["stage"] == "incele"
    storage.validate(finding, {VERSION_ID})


def test_finding_without_a_record_is_not_recorded(tmp_path):
    store = build(tmp_path, with_run=False)
    finding = storage.create(store.state, "incele", "Soru", "Yöntem")
    assert finding["result_status"] == "not_recorded"
    assert finding["result"] == storage.NOT_RECORDED


def test_finding_is_marked_stale_when_the_version_changes(tmp_path):
    store = build(tmp_path)
    finding = storage.create(store.state, "veri", "Soru", "Yöntem")
    storage.append(store.state, finding)
    rows = storage.rows(store.state)
    assert rows and rows[0]["stale"] is False

    # A newer version of the same dataset makes the old finding out of date.
    store.state["datasets"].append(
        dict(
            dataset_id=DATASET_ID,
            version_id=VERSION_TWO,
            source_id=store.state["sources"][0]["id"],
            snapshot_uri=store.state["datasets"][0]["snapshot_uri"],
            parent_version_ids=[VERSION_ID],
            input_version_ids=[VERSION_ID],
            operation_id="op:00000000-0000-4000-8000-000000000001",
        )
    )
    store.state["operations"].append(
        dict(
            id="op:00000000-0000-4000-8000-000000000001",
            dataset_version_ids=[VERSION_ID],
            seed=None,
            parameters={"mode": "test"},
        )
    )
    from veri_ufku.operations.contracts import activate

    activate(store.state, store.state["datasets"][-1])
    rows = storage.rows(store.state)
    assert rows[0]["stale"] is True
    assert "güncel değil" in rows[0]["stale_reason"]


def test_finding_survives_a_project_reopen(tmp_path):
    store = build(tmp_path)
    finding = storage.create(store.state, "istatistik", "Fark var mı?", "Welch t")
    storage.append(store.state, finding)
    store.save()
    store.close()

    reopened = ProjectStore.open(tmp_path / "project")
    assert len(reopened.state["findings"]) == 1
    assert reopened.state["findings"][0]["question"] == "Fark var mı?"
    assert storage.rows(reopened.state)[0]["question"] == "Fark var mı?"


def test_remove_is_explicit_and_idempotent_safe(tmp_path):
    store = build(tmp_path)
    finding = storage.create(store.state, "veri", "Soru", "Yöntem")
    storage.append(store.state, finding)
    storage.remove(store.state, finding["id"])
    assert store.state["findings"] == []
    with pytest.raises(ProjectError):
        storage.remove(store.state, finding["id"])


def test_finding_bound_to_an_unknown_version_is_rejected(tmp_path):
    store = build(tmp_path)
    finding = storage.create(store.state, "veri", "Soru", "Yöntem")
    broken = copy.deepcopy(finding)
    broken["dataset_version_ids"] = [VERSION_TWO]
    with pytest.raises(ProjectError):
        storage.validate(broken, {VERSION_ID})


def test_findings_block_carries_every_finding_into_the_report(tmp_path):
    store = build(tmp_path)
    first = storage.create(store.state, "veri", "İlk soru", "İlk yöntem")
    second = storage.create(store.state, "incele", "İkinci soru", "İkinci yöntem")
    storage.append(store.state, first)
    storage.append(store.state, second)

    spec = recipe(
        dict(
            title="Bulgu raporu",
            protocol="exploratory",
            protocol_note="Not",
            blocks=[
                dict(
                    kind="findings",
                    title="Bulgular",
                    findings=[first["id"], second["id"]],
                )
            ],
            masked_columns=[],
            allow_graphics=False,
        )
    )
    assert spec["blocks"][0]["kind"] == "findings"

    from veri_ufku.storage.report_builder_store import request_for

    request = request_for(store, store.state, spec)
    assert set(request["findings"]) == {first["id"], second["id"]}
    assert not request["stale"]


def test_report_request_fails_when_a_finding_is_missing(tmp_path):
    store = build(tmp_path)
    finding = storage.create(store.state, "veri", "Soru", "Yöntem")
    spec = recipe(
        dict(
            title="Bulgu raporu",
            protocol="exploratory",
            protocol_note="Not",
            blocks=[dict(kind="findings", title="Bulgular", findings=[finding["id"]])],
            masked_columns=[],
            allow_graphics=False,
        )
    )
    store.state["findings"] = []
    from veri_ufku.storage.report_builder_store import request_for

    with pytest.raises(ProjectError):
        request_for(store, store.state, spec)


def test_report_output_contains_every_finding(tmp_path):
    """The report carries the notebook's findings with their rationale."""
    import base64

    import polars as pl
    from test_dataset import prepare

    from veri_ufku.exports.report_builder import calculate
    from veri_ufku.exports.report_contracts import template

    store, request, work = prepare(
        tmp_path,
        pl.DataFrame({"değer": [1.0, 2.0, 3.0], "isim": ["a", "b", "c"]}),
    )
    first = storage.create(store.state, "veri", "Kaç satır var?", "Sözlük kaydı")
    second = storage.create(store.state, "incele", "Eksik var mı?", "Kalite taraması")
    storage.append(store.state, first)
    storage.append(store.state, second)

    spec = template()
    spec["blocks"] = [
        dict(
            kind="findings",
            title="Bulgular",
            findings=[first["id"], second["id"]],
        )
    ]
    from veri_ufku.storage.report_builder_store import request_for

    req = request_for(store, store.state, spec)
    out = calculate(req, spec, work)
    markdown = base64.b64decode(out["files"]["report.md"]).decode()
    assert "Kaç satır var?" in markdown
    assert "Eksik var mı?" in markdown
    assert "Sözlük kaydı" in markdown
    assert "Kalite taraması" in markdown
    # A finding that is not recorded says so instead of inventing a number.
    assert "Bağlı kayıt yok" in markdown
