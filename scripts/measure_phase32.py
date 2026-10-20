"""Source/wheel real QML/spawn/approval/undo/reopen witnesses and actual renders."""

import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/phase32/gui")
    )
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo / "tests"))
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    import polars as pl
    import pytest
    from PySide6.QtCore import QObject, qVersion
    from PySide6.QtTest import QTest
    from test_data_contracts_gui import (
        click,
        finish,
        loaded,
        test_export_directory_watch_event_after_shutdown_does_not_start_io,
        test_phase07_ordinal_dictionary_extension_preserves_existing_order,
        test_qml_categories_manual_approval_and_real_worker_cancel,
        test_qml_dictionary_quality_policy_export_help_reopen,
        test_qml_foreign_key_unique_wrong_unit_type_actual_second_dataset,
        test_qml_no_automatic_merge_human_decision_journal_undo,
    )
    from test_import_gui import spin, teardown

    import veri_ufku
    from veri_ufku.operations.contracts import active_datasets
    from veri_ufku.storage.project_model import uid
    from veri_ufku.storage.project_store import ProjectStore

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    record = dict(
        id="E32-GUI",
        environment="ENV-32",
        started=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        qt=qVersion(),
        package_file=str(Path(veri_ufku.__file__).resolve()),
        mode="offscreen/software",
        cases=[],
        screenshots=[],
    )
    cases = (
        test_qml_dictionary_quality_policy_export_help_reopen,
        test_qml_no_automatic_merge_human_decision_journal_undo,
        test_qml_categories_manual_approval_and_real_worker_cancel,
        test_qml_foreign_key_unique_wrong_unit_type_actual_second_dataset,
        test_phase07_ordinal_dictionary_extension_preserves_existing_order,
        test_export_directory_watch_event_after_shutdown_does_not_start_io,
    )
    with tempfile.TemporaryDirectory(prefix="veri-ufku-phase32-") as temp:
        base = Path(temp)
        for i, case in enumerate(cases):
            path = base / str(i)
            path.mkdir()
            started = time.monotonic()
            with pytest.MonkeyPatch.context() as patch:
                case(path, patch)
            record["cases"].append(
                dict(id=case.__name__, passed=True, seconds=time.monotonic() - started)
            )
            print("PASS", case.__name__, flush=True)
        path = base / "render"
        path.mkdir()
        with pytest.MonkeyPatch.context() as patch:
            app, window, projects, data, operations, source = loaded(path, patch)
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            try:

                def render(state, focus):
                    spin(app, lambda: not data.busy and not projects.busy)
                    for width in (1366, 720):
                        window.setWidth(width)
                        window.setHeight(900)
                        obj = window.findChild(QObject, focus)
                        obj.forceActiveFocus()
                        # Position the evidence camera through the real scrollable
                        # content; this is not a physical keyboard/AT acceptance.
                        container = obj.parentItem()
                        while container is not None:
                            offset = container.property("contentY")
                            content = container.property("contentItem")
                            if offset is not None and content is not None:
                                y = obj.mapToItem(content, 0.0, 0.0).y()
                                limit = max(
                                    0.0,
                                    container.property("contentHeight")
                                    - container.height(),
                                )
                                container.setProperty(
                                    "contentY", min(limit, max(0.0, y - 120.0))
                                )
                                break
                            container = container.parentItem()
                        QTest.qWait(160)
                        app.processEvents()
                        file = output / f"{state}-{width}.png"
                        assert window.grabWindow().save(str(file))
                        record["screenshots"].append(
                            dict(
                                state=state,
                                width=width,
                                height=900,
                                path=file.name,
                                sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                            )
                        )

                cols = {c["name"]: c["id"] for c in data.datasetColumns}
                data.selectColumn(cols["grade"])
                spin(app, lambda: not data.busy)
                window.findChild(QObject, "contractMeaning").setProperty(
                    "text", "Ordinal grade, source unchanged"
                )
                window.findChild(QObject, "contractMeasurementLevel").setProperty(
                    "currentIndex", 2
                )
                window.findChild(QObject, "contractOrder").setProperty(
                    "text", "low|mid|high"
                )
                click(window, "contractPreviewMetadata")
                finish(app, operations)
                render("dictionary", "contractMeaning")
                click(window, "contractApply")
                finish(app, operations)
                spin(app, lambda: not data.busy)
                parent = data.dataset()
                frame = pl.read_parquet(projects.store.path(parent["snapshot_uri"]))
                linked = dict(
                    id="result:" + uid(),
                    dataset_version_ids=[parent["version_id"]],
                    seed=None,
                )
                projects.draft["results"].append(linked)
                window.findChild(QObject, "entityNameColumn").setProperty(
                    "currentIndex", 0
                )
                window.findChild(QObject, "entityBlockColumn").setProperty(
                    "currentIndex", 1
                )
                click(window, "entityFindCandidates")
                finish(app, operations)
                assert not operations.canApply
                assert len(operations.preview["diagnostics"]["candidates"]) == 1
                render("candidates", "entityFindCandidates")
                window.findChild(QObject, "entityReviewer").setProperty(
                    "text", "Synthetic reviewer"
                )
                window.findChild(QObject, "entityReason").setProperty(
                    "text", "Independent fixture identity evidence, not name alone"
                )
                click(window, "entityApprovePair")
                finish(app, operations)
                assert (
                    operations.canApply
                    and data.dataset()["version_id"] == parent["version_id"]
                )
                render("approved-preview", "contractApply")
                click(window, "contractApply")
                finish(app, operations)
                spin(app, lambda: not data.busy)
                merged = data.dataset()
                actual = pl.read_parquet(projects.store.path(merged["snapshot_uri"]))
                assert actual["__vu_row_id"].equals(frame["__vu_row_id"]) and actual[
                    "__vu_source_record_id"
                ].equals(frame["__vu_source_record_id"])
                assert actual["canonical_id"][0] == actual["canonical_id"][1]
                assert linked["id"] in [
                    r["id"] for r in operations.identityJournal[0]["related_results"]
                ]
                inverse = pl.read_parquet(projects.store.path(merged["lineage_uri"]))
                assert (
                    inverse["source_record_id"].to_list()
                    == frame["__vu_source_record_id"].to_list()
                )
                click(window, "contractUndo")
                finish(app, operations)
                spin(app, lambda: not data.busy)
                assert data.dataset()["version_id"] == parent["version_id"]
                assert pl.read_parquet(
                    projects.store.path(data.dataset()["snapshot_uri"])
                ).equals(frame)
                click(window, "contractRedo")
                finish(app, operations)
                spin(app, lambda: not data.busy)
                assert data.dataset()["version_id"] == merged["version_id"]
                portable = base / "portable"
                projects.store.save_as(portable)
                with closing(ProjectStore.open(portable)) as store:
                    d = active_datasets(store.state)[0]
                    assert d["version_id"] == merged["version_id"] and pl.read_parquet(
                        store.path(d["snapshot_uri"])
                    ).equals(actual)
                    assert store.state["results"][-1] == linked
                assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
                record.update(
                    approval_required=True,
                    candidates_do_not_publish=True,
                    source_unchanged=True,
                    source_hash=source_hash,
                    source_ids_preserved=True,
                    linked_result_preserved=True,
                    inverse_rows=inverse.height,
                    undo_redo_passed=True,
                    portable_reopen_passed=True,
                )
            finally:
                teardown(app, window)
    record.update(completed=datetime.now(UTC).isoformat(), passed=True)
    (output / "walkthrough.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        "PASS: source/wheel Phase32 QML, six renders, human approval, full identity inverse, linked result and portable undo/reopen",
        flush=True,
    )


if __name__ == "__main__":
    main()
