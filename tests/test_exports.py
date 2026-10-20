"""Independent export projections, safe spreadsheet values and local paged reports."""

import csv
import hashlib
import zipfile
from contextlib import closing
from datetime import date
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.exports.data import ExportSpec, export, generate, read_rows
from veri_ufku.exports.files import publish
from veri_ufku.exports.reports import ReportSpec, build, write_pdf
from veri_ufku.importers.delimited import Control
from veri_ufku.storage.project_model import ProjectError


@pytest.mark.parametrize("fmt", ["csv", "json", "jsonl", "parquet", "xlsx"])
def test_five_reopened_reference_values_and_types(tmp_path, fmt):
    frame = pl.DataFrame(
        {
            "=header": ["=1+1", "-sipariş", "Çağrı İıŞşÇçĞğÖöÜü", "", None],
            "n": [-12, 2, 3, 4, None],
            "d": [Decimal("-1.25"), Decimal("2.50"), None, Decimal("0.00"), None],
            "day": [date(2026, 1, 2), None, date(2026, 2, 3), None, None],
            "flag": [True, False, None, True, None],
        }
    )
    store, request, work = prepare(tmp_path, frame)
    with closing(store):
        before = Path(request["path"]).read_bytes()
        result = export(
            request,
            ExportSpec(fmt, accept_loss=True),
            work,
            tmp_path / ("out." + fmt),
            store.root,
        )
        assert result["verified_rows"] == 5 and result["projection_verified"]
        assert result["spreadsheet_safe"] and result["loss_accepted"]
        assert result["types_verified"] and bool(result["losses"]) == (fmt != "parquet")
        assert Path(request["path"]).read_bytes() == before
        path = result["published"]["path"]
        assert (
            hashlib.sha256(Path(path).read_bytes()).hexdigest()
            == result["published"]["sha256"]
        )
        if fmt == "parquet":
            assert pl.read_parquet(path).equals(frame)
            assert pl.read_parquet_schema(path) == frame.schema
        else:
            rows = list(read_rows(path, fmt, result["output_columns"], "\\N"))
            assert rows[0] == (
                ["'=1+1", "-12", "-1.25", "2026-01-02", "True"]
                if fmt == "csv"
                else ["=1+1", -12, "-1.25", "2026-01-02", True]
            )
            assert rows[2][0] == "Çağrı İıŞşÇçĞğÖöÜü"
            assert rows[3][0] == "" and rows[4] == [None] * 5
            if fmt == "csv":
                assert (
                    result["escaped_headers"] == 1
                    and result["spreadsheet_escaped"] == 2
                )
                with open(path, encoding="utf-8-sig") as inp:
                    assert next(csv.reader(inp))[0] == "'=header"
            if fmt == "xlsx":
                with zipfile.ZipFile(path) as z:
                    xml = z.read("xl/worksheets/sheet1.xml")
                    assert b"<f>" not in xml and b"inlineStr" in xml


def test_precision_nonfinite_and_ns_date_policy(tmp_path):
    frame = pl.DataFrame(
        {
            "integer": [12345678901234567, -12345678901234567],
            "x": [float("nan"), float("-inf")],
            "date": pl.Series(
                [1767225600123456789, None], dtype=pl.Datetime("ns", "Europe/Istanbul")
            ),
        }
    )
    store, request, work = prepare(tmp_path, frame)
    with closing(store):
        for fmt in ("json", "csv", "xlsx", "parquet"):
            result = generate(request, ExportSpec(fmt, accept_loss=True), work)
            if fmt == "parquet":
                assert pl.read_parquet(result["artifact"]).equals(frame)
                continue
            rows = list(
                read_rows(result["artifact"], fmt, result["output_columns"], "\\N")
            )
            assert str(rows[0][0]) == "12345678901234567"
            assert rows[0][1] == "nan" and rows[1][1] == (
                "'-inf" if fmt == "csv" else "-inf"
            )
            assert "123456789" in rows[0][2]
            assert result["nonfinite_to_text"] == 2
            assert result["numeric_to_text"] == (2 if fmt == "xlsx" else 0)


def test_safety_loss_limits_existing_and_filtered_scope(tmp_path):
    store, request, work = prepare(
        tmp_path, pl.DataFrame({"n": [1, 2, 3], "text": ["=x", " a", ""]})
    )
    with closing(store):
        with pytest.raises(ProjectError, match="onay"):
            generate(request, ExportSpec("csv"), work)
        with pytest.raises(ProjectError, match="null"):
            generate(
                request, ExportSpec("csv", accept_loss=True, null_marker="=1"), work
            )
        view = {
            "filters": [
                {"column_id": column(request, "n"), "operator": "gt", "value": "1"}
            ]
        }
        result = generate(request, ExportSpec("parquet", view=view), work)
        assert result["rows"] == 2 and pl.read_parquet(result["artifact"])[
            "n"
        ].to_list() == [2, 3]
        source = tmp_path / "existing"
        source.write_bytes(b"original")
        with pytest.raises(ProjectError):
            publish(result["artifact"], source, store.root)
        assert source.read_bytes() == b"original"
        link = tmp_path / "link"
        link.symlink_to(source)
        with pytest.raises(ProjectError):
            publish(result["artifact"], link, store.root)
        with pytest.raises(ProjectError):
            publish(result["artifact"], store.root / "out", store.root)
        request["row_count"] = (
            100001  # Admission reads real query, not untrusted count.
        )
        assert (
            generate(request, ExportSpec("xlsx", accept_loss=True), work)["rows"] == 3
        )


def test_null_collision_header_collision_and_xlsx_cell_limit(tmp_path):
    for index, frame, message in (
        (0, pl.DataFrame({"text": ["\\N"]}), "çakış"),
        (1, pl.DataFrame({"=x": ["a"], "'=x": ["b"]}), "çakış"),
        (2, pl.DataFrame({"text": ["x" * 32768]}), "32767"),
    ):
        case = tmp_path / str(index)
        case.mkdir()
        store, request, work = prepare(case, frame)
        with closing(store), pytest.raises(ProjectError, match=message):
            generate(
                request,
                ExportSpec("xlsx" if index == 2 else "csv", accept_loss=True),
                work,
            )


def test_local_html_escape_and_turkish_pdf_pages(tmp_path):
    frame = pl.DataFrame(
        {
            "Ad": [f"İıŞşÇçĞğÖöÜü satır {i}" for i in range(200)],
            "Not": ["<script>alert('x')</script>"] * 200,
        }
    )
    store, request, _ = prepare(tmp_path, frame)
    with closing(store):
        request["report_context"] = {
            "sources": [{"path": '<img src="https://evil.test/x">'}],
            "quality": [
                {
                    "dataset_version": "old",
                    "findings": [{"column": "Ad", "count": 1, "reason": "Örnek bulgu"}],
                }
            ],
            "operations": [{"kind": "trim", "parameters": {"column": "Ad"}}],
        }
        spec = ReportSpec("pdf", title="Çağrı İıŞşÇçĞğÖöÜü <b>", table_rows=200)
        document, images, info = build(request, spec, Control())
        assert 'alt="Veri_Ufku logosu"' in document
        assert any(uri.startswith("data:image/png;base64,") for uri in images)
        assert "<script>" not in document and "&lt;script&gt;" in document
        assert '<img src="https://' not in document
        assert "data:font/ttf;base64," in document and "default-src 'none'" in document
        for title in (
            "Amaç",
            "Kaynak ve köken",
            "Kalite bulguları",
            "Temizleme",
            "Veri tablosu",
            "Grafikler",
            "Yöntemler ve sınırlamalar",
        ):
            assert title in document
        assert info["shown_rows"] == 200
        output = tmp_path / "report.pdf"
        result = write_pdf(document, images, output, Control())
        assert result >= 2
        from PySide6.QtPdf import QPdfDocument

        pdf = QPdfDocument()
        assert pdf.load(str(output)) == QPdfDocument.Error.None_
        full = "".join(pdf.getAllText(i).text() for i in range(pdf.pageCount()))
        assert "İıŞşÇçĞğÖöÜü" in full and "satır 199" in full and "Örnek bulgu" in full
        assert not pdf.render(0, pdf.pagePointSize(0).toSize()).isNull()
        pdf.close()


def race_publish(source, target, project, queue):
    try:
        publish(source, target, project)
        queue.put("published")
    except (ProjectError, FileExistsError):
        queue.put("preserved")


def test_exclusive_two_process_publication_and_cancel(tmp_path):
    import multiprocessing as mp

    from veri_ufku.jobs.workers import Canceled

    ctx = mp.get_context("spawn")
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(b"a" * 100000)
    b.write_bytes(b"b" * 100000)
    project = tmp_path / "project"
    project.mkdir()
    target = tmp_path / "out"
    queue = ctx.Queue()
    processes = [
        ctx.Process(
            target=race_publish, args=(str(source), str(target), str(project), queue)
        )
        for source in (a, b)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(10)
        assert process.exitcode == 0
    assert sorted([queue.get(timeout=2), queue.get(timeout=2)]) == [
        "preserved",
        "published",
    ]
    assert target.read_bytes() in (a.read_bytes(), b.read_bytes())
    cancel = ctx.Event()
    cancel.set()
    with pytest.raises(Canceled):
        publish(a, tmp_path / "cancel", project, Control(cancel))
    assert not (tmp_path / "cancel").exists()
    assert not list(tmp_path.glob(".*.export"))
    queue.close()


@pytest.mark.parametrize("fmt", ["csv", "json", "jsonl", "parquet", "xlsx"])
def test_export_reimports_with_existing_adapter(tmp_path, fmt):
    from veri_ufku.importers.delimited import ImportSettings, capture
    from veri_ufku.importers.native import StructuredSettings
    from veri_ufku.importers.registry import get_adapter

    frame = pl.DataFrame({"Ad": ["Şule", "İpek", "Çağrı"], "n": [-12, 2, None]})
    store, request, work = prepare(tmp_path, frame)
    with closing(store):
        generated = generate(request, ExportSpec(fmt, accept_loss=True), work)
        rework = tmp_path / "reimport"
        rework.mkdir()
        snapshot = capture(generated["artifact"], rework, any_format=True)
        settings = (
            ImportSettings(null_markers=("\\N",), types=("text", "int64"))
            if fmt == "csv"
            else StructuredSettings(adapter_id=fmt)
        )
        result = get_adapter(fmt).import_data(snapshot, settings, rework, Control())
        assert result["accepted"] == 3
        assert pl.read_parquet(result["path"])["Ad"].to_list() == [
            "Şule",
            "İpek",
            "Çağrı",
        ]
        assert pl.read_parquet(result["path"])["n"].to_list() == [-12, 2, None]


def test_sorted_filtered_export_and_report_same_order_as_table(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {"key": [2, 1, 2, None], "name": ["ilk", "önce", "ikinci", "son"]}
        ),
    )
    with closing(store):
        view = {
            "sort_column": column(request, "key"),
            "descending": True,
            "hidden": [column(request, "name")],
        }
        result = generate(request, ExportSpec("parquet", view=view), work)
        assert pl.read_parquet(result["artifact"])["name"].to_list() == [
            "ilk",
            "ikinci",
            "önce",
            "son",
        ]
        document, _, info = build(request, ReportSpec("html", view=view), Control())
        assert (
            document.index("<td>ilk</td>")
            < document.index("<td>ikinci</td>")
            < document.index("<td>önce</td>")
        )
        assert info["view"]["descending"] and "gizli sütunlar dahil" in document
        assert "name" in result["columns"]


def test_xlsx_trailing_all_null_rows_reimported(tmp_path):
    from veri_ufku.importers.delimited import capture
    from veri_ufku.importers.native import StructuredSettings
    from veri_ufku.importers.registry import get_adapter

    store, request, work = prepare(
        tmp_path,
        pl.DataFrame({"a": ["", "Çağrı", None, None], "n": [1, 2, None, None]}),
    )
    with closing(store):
        generated = generate(request, ExportSpec("xlsx", accept_loss=True), work)
        rework = tmp_path / "xlsx-reimport"
        rework.mkdir()
        snapshot = capture(generated["artifact"], rework, any_format=True)
        result = get_adapter("xlsx").import_data(
            snapshot, StructuredSettings(adapter_id="xlsx"), rework, Control()
        )
        assert result["accepted"] == 4
        assert pl.read_parquet(result["path"])["a"].to_list() == [
            "",
            "Çağrı",
            None,
            None,
        ]
