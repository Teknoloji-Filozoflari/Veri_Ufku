"""Real offline exports and immutable run/artifact references, not mocked renderers."""

import base64
import copy
import io
import zipfile
from contextlib import closing

import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.exports.report_builder import calculate
from veri_ufku.exports.report_contracts import recipe, redact, template
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage import report_builder_store as storage
from veri_ufku.storage.project_model import ProjectError


def fixture(tmp_path):
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            {
                "isim": ["Çağrı İıŞşÇçĞğÖöÜü", "a@example.org", "=1+1"],
                "değer": [1.0, 2.0, 3.0],
            }
        ),
    )
    spec = template()
    spec["blocks"] += [
        dict(
            kind="dictionary",
            title="Sözlük",
            version=request["version_id"],
            columns=[column(request, "değer")],
        ),
        dict(
            kind="table",
            title="Tablo",
            version=request["version_id"],
            columns=[c["id"] for c in request["columns"]],
            rows=2,
            caption="İlk iki satır.",
        ),
    ]
    spec["blocks"][2]["references"] = [
        dict(title="Qt PDF", url="https://doc.qt.io/qt-6/qpdfwriter.html")
    ]
    return store, spec, work


def test_real_turkish_pdf_html_markdown_tables_bundle(tmp_path):
    store, spec, work = fixture(tmp_path)
    with closing(store):
        req = storage.request_for(store, store.state, spec)
        before = {v: open(r["path"], "rb").read() for v, r in req["sources"].items()}
        out = calculate(req, spec, work)
        files = {k: base64.b64decode(v) for k, v in out["files"].items()}
        from PySide6.QtPdf import QPdfDocument

        pdf = QPdfDocument()
        assert pdf.load(str(work / "report.pdf")) == QPdfDocument.Error.None_
        text = "\n".join(pdf.getAllText(i).text() for i in range(pdf.pageCount()))
        assert "Çağrı" in text and "ŞşÇçĞğÖöÜü" in text and "Qt PDF" in text
        assert pdf.pagePointSize(0).width() == pytest.approx(595, abs=2)
        assert "a@example.org" not in files["report.md"].decode()
        assert "qpdfwriter.html" in files["report.md"].decode()
        assert "data:font/ttf;base64," in files["report.html"].decode()
        with zipfile.ZipFile(io.BytesIO(files["report-package.zip"])) as z:
            assert z.testzip() is None and z.read("table-4.csv") == files["table-4.csv"]
        tab = pl.read_parquet(io.BytesIO(files["table-4.parquet"]))
        assert tab["değer"].to_list() == [1.0, 2.0] and tab["isim"][1] == "[redacted]"
        state = storage.publish(store, store.state, out)
        r = state["results"][-1]
        assert storage.load(store, r)["review_hash"] == out["review_hash"]
        dest = tmp_path / "final.zip"
        storage.export_file(
            store, state, r["id"], "report-package.zip", dest, out["review_hash"]
        )
        assert dest.read_bytes() == files["report-package.zip"]
        with pytest.raises(ProjectError):
            storage.export_file(
                store, state, r["id"], "report-package.zip", dest, out["review_hash"]
            )
        assert all(
            open(req["sources"][v]["path"], "rb").read() == raw
            for v, raw in before.items()
        )
        target = store.path(r["scientific_report"]["file_refs"]["report.md"]["uri"])
        target.write_bytes(b"corrupt")
        with pytest.raises(ProjectError, match="hash"):
            storage.load(store, r)


def test_closed_recipe_secret_preview_no_unreviewed_publish(tmp_path):
    store, spec, work = fixture(tmp_path)
    with closing(store):
        spec["blocks"][0]["text"] = "password=DO_NOT_EXPORT"
        with pytest.raises(ProjectError, match="secret"):
            storage.request_for(store, store.state, spec)
        clean, reasons = redact(spec)
        assert reasons and "DO_NOT_EXPORT" not in str(clean)
        out = calculate(storage.request_for(store, store.state, clean), clean, work)
        assert "DO_NOT_EXPORT" not in str(out)
        damaged = copy.deepcopy(out)
        damaged["files"]["report.md"] = base64.b64encode(b"wrong").decode()
        with pytest.raises(ProjectError, match="hash"):
            storage.publish(store, store.state, damaged)
        bad = copy.deepcopy(spec)
        bad["blocks"][0]["metric"] = 999
        with pytest.raises(ProjectError):
            recipe(bad)
        prior = store.commit_id
        import threading

        cancel = threading.Event()
        cancel.set()
        with pytest.raises(Canceled):
            calculate(
                storage.request_for(store, store.state, clean),
                clean,
                work,
                Control(cancel),
            )
        assert store.commit_id == prior


def test_real_chart_script_links_and_newer_run_stale(tmp_path):
    from veri_ufku.charts.contracts import ChartSpec
    from veri_ufku.charts.engine import calculate as chart
    from veri_ufku.charts.plot import render
    from veri_ufku.storage.chart_store import publish as publish_chart
    from veri_ufku.storage.lineage import graph

    store, spec, work = fixture(tmp_path)
    with closing(store):
        from veri_ufku.operations.workflow import references

        ref = next(iter(references(store, store.state).values()))
        result = chart(
            ref, ChartSpec("histogram", x=column(ref, "değer"), bins=2), work
        )
        result.update(render(result, work))
        state = publish_chart(store, store.state, result)
        record = state["results"][-1]
        spec["allow_graphics"] = True
        spec["blocks"] += [
            dict(
                kind="chart",
                title="Dağılım",
                record=record["id"],
                caption="İki bin; üç gözlem.",
            )
        ]
        spec["blocks"][3]["code_column"] = column(ref, "değer")
        req = storage.request_for(store, state, spec)
        out = calculate(req, spec, work)
        assert out["blocks"][-1]["data"]["summary"] == record["chart"]["summary"]
        assert out["blocks"][-1]["data"]["used_n"] == record["chart"]["used_n"]
        assert (
            out["blocks"][-1]["data"]["details"]
            == redact(record["chart"]["details"])[0]
        )
        files = {k: base64.b64decode(v) for k, v in out["files"].items()}
        assert b"data:image/png;base64," in files["report.html"]
        assert (
            files["figure-5.svg"]
            == store.path(record["chart"]["artifact_uris"]["svg"]).read_bytes()
        )
        with zipfile.ZipFile(io.BytesIO(files["profile-code-3.zip"])) as z:
            import json

            notebook = json.loads(z.read("analysis.ipynb"))
            assert all(not c.get("outputs") for c in notebook["cells"])
            assert {"run.py", "query.sql", "dataset-reference.json"} <= set(
                z.namelist()
            )
        state = storage.publish(store, state, out)
        report = state["results"][-1]
        lineage = graph(state, store.manifest)
        assert any(
            n["id"] == report["id"] and n["kind"] == "report" for n in lineage["nodes"]
        )
        result = chart(
            ref, ChartSpec("histogram", x=column(ref, "değer"), bins=3), work
        )
        result.update(render(result, work))
        state = publish_chart(store, state, result)
        assert storage.freshness(state, spec)[0]["kind"] == "newer_same_capability_run"
        with pytest.raises(ProjectError, match="güncellik"):
            storage.export_file(
                store,
                state,
                report["id"],
                "report.md",
                tmp_path / "old.md",
                out["review_hash"],
            )
        changed = calculate(storage.request_for(store, state, spec), spec, work)
        assert (
            changed["stale"]
            and "STALE" in base64.b64decode(changed["files"]["report.md"]).decode()
        )
        spec["masked_columns"] = [column(ref, "değer")]
        with pytest.raises(ProjectError, match="Maskeli"):
            storage.request_for(store, state, spec)


def test_actual_model_card_metrics_protocol_and_dataset_stale(tmp_path):
    from test_monitoring import trained_fixture

    from veri_ufku.analytics.contracts import metadata_version

    store, r, w, work, monitor = trained_fixture(tmp_path)
    with closing(store):
        rec = next(x for x in store.state["results"] if "baseline" in x)
        s = template()
        s["protocol"] = "confirmatory"
        s["protocol_note"] = (
            "Önceden belirlenen geliştirme protokolü; test defterine bakın."
        )
        s["blocks"] = [
            dict(kind=k, title=k, record=rec["id"])
            for k in ("method", "model-card", "result", "uncertainty", "diagnostic")
        ]
        req = storage.request_for(store, store.state, s)
        out = calculate(req, s, work)
        assert (
            out["blocks"][1]["data"]["model_card"]
            == redact(rec["baseline"]["model_card"])[0]
        )
        assert out["blocks"][2]["data"]["cv_summary"] == rec["baseline"]["cv_summary"]
        assert "plan" in out["blocks"][0]["data"]
        assert any(
            "cv_summary/" in text and rec["id"] in text
            for text in out["blocks"][2]["narrative"]
        )
        assert (
            out["blocks"][3]["data"].get("status") == "not_recorded"
            or "limitations" in out["blocks"][3]["data"]
        )
        state = storage.publish(store, store.state, out)
        version = rec["dataset_version_ids"][0]
        d = next(d for d in state["datasets"] if d["version_id"] == version)
        c = d["import_metadata"]["columns"][0]["id"]
        new = metadata_version(d, c, "identifier", "", [], "yeni metadata")
        store.state["datasets"].append(new)
        store.save()
        assert any(
            i["kind"] == "dataset_stale" for i in storage.freshness(store.state, s)
        )
        assert out["source_refs"] == req["source_refs"]


def test_html_markdown_injection_and_disk_fail(tmp_path):
    from dataclasses import replace

    from veri_ufku.domain.contracts import ComputeBudget

    store, ref, work = prepare(tmp_path, pl.DataFrame({"değer": [1.0]}))
    with closing(store):
        s = template()
        s["title"] = "<script>alert(1)</script>"
        s["protocol_note"] = "<img src=x onerror=alert(1)>"
        s["blocks"].append(
            dict(
                kind="table",
                title="Küçük tablo",
                version=ref["version_id"],
                columns=[column(ref, "değer")],
                rows=5,
                caption="Bir satır.",
            )
        )
        r = storage.request_for(store, store.state, s)
        with pytest.raises(ProjectError, match="disk"):
            calculate(
                r,
                s,
                work,
                Control(budget=replace(ComputeBudget(), temp_disk_bytes=1)),
            )
        out = calculate(r, s, work)
        assert out["blocks"][-1]["n"] == 1
        doc = base64.b64decode(out["files"]["report.html"]).decode()
        md = base64.b64decode(out["files"]["report.md"]).decode()
        assert "<script>" not in doc + md and "<img src=x" not in doc + md
        assert (
            pl.read_parquet(
                io.BytesIO(base64.b64decode(out["files"]["table-3.parquet"]))
            ).height
            == 1
        )
        for url in (
            "https://user:pass@example.org/x",
            "https://example.org/x?token=secret",
            "javascript:alert(1)",
            "https://example.org/\nunsafe",
        ):
            bad = copy.deepcopy(s)
            bad["blocks"][2]["references"] = [dict(title="unsafe", url=url)]
            with pytest.raises(ProjectError):
                recipe(bad)


def test_explicit_numeric_column_mask_keeps_protocol_and_parquet_string(tmp_path):
    store, ref, work = prepare(tmp_path, pl.DataFrame({"x": [17.25, 91.5]}))
    with closing(store):
        s = template()
        s["masked_columns"] = [column(ref, "x")]
        s["blocks"].append(
            dict(
                kind="table",
                title="Maskeli tablo",
                version=ref["version_id"],
                columns=s["masked_columns"],
                rows=2,
                caption="Değerler paylaşılmaz.",
            )
        )
        req = storage.request_for(store, store.state, s)
        assert req["spec"]["protocol"] == "exploratory"
        out = calculate(req, s, work)
        values = pl.read_parquet(
            io.BytesIO(base64.b64decode(out["files"]["table-3.parquet"]))
        )
        assert values["x"].to_list() == ["[redacted]", "[redacted]"]
        assert values.schema["x"] == pl.String
        assert "17.25" not in base64.b64decode(out["files"]["report.md"]).decode()
