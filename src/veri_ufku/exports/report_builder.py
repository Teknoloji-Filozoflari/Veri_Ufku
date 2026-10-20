"""Offline bounded rendering of pinned records, never an analysis engine."""

import base64
import csv
import html
import io
import json
import zipfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from veri_ufku.domain.contracts import Provenance
from veri_ufku.exports.report_contracts import LIMITATIONS, recipe, redact
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, encode, uid
from veri_ufku.storage.project_store import file_hash

# Closed fields only: user narrative cannot introduce machine-verified findings.
FIELDS = (
    "method",
    "spec",
    "parameters",
    "metrics",
    "summary",
    "statistics",
    "result",
    "estimates",
    "coefficients",
    "model_card",
    "diagnostics",
    "warnings",
    "limitations",
    "uncertainty",
    "interval",
    "confidence_interval",
    "protocol",
    "split",
    "validation",
    "selection",
    "test_use",
    "fit_scope",
    "status",
    "n",
    "rows",
    "sample",
    "excluded",
    "counts",
    "value",
    "outputs",
    "cv_summary",
    "plan",
    "evaluations",
    "decision",
    "data_access_at",
    "evaluated_at",
    "details",
)


def findings(data, record_id):
    """Verbatim numeric field values with native paths, no estimated conclusions."""
    out = []

    def visit(value, path):
        if isinstance(value, dict):
            for k, item in value.items():
                visit(item, path + "/" + str(k))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                visit(item, path + "/" + str(i))
        elif type(value) in (int, float) and len(out) < 40:
            out.append(
                "Kayıtlı bulgu: "
                + path
                + " = "
                + str(value)
                + " · kaynak "
                + record_id
                + "/"
                + path
            )

    for k in (
        "metrics",
        "cv_summary",
        "statistics",
        "estimates",
        "coefficients",
        "counts",
        "n",
    ):
        if k in data:
            visit(data[k], k)
    return out or [
        "Bu blokta şablonun desteklediği sayısal alan yok; kayıtlı ayrıntılara bakın. Yeni metrik hesaplanmadı."
    ]


def public_report(value):
    return {k: v for k, v in value.items() if k not in ("files", "experiment_capture")}


def calculate(request, spec, workspace, control=None):
    control = control or Control()
    spec = recipe(spec)
    if spec != request["spec"]:
        raise ProjectError("Rapor tarifi envelope ile aynı olmalı.")
    work = Path(workspace)
    work.mkdir(parents=True, exist_ok=True)
    files, blocks, changes = {}, [], []
    for ref in [*request["sources"].values(), *request["artifacts"].values()]:
        control.check()
        if file_hash(Path(ref["path"])) != ref["fingerprint"]:
            raise ProjectError("Rapor girdisinin hash değeri değişmiş.")
    for i, block in enumerate(spec["blocks"]):
        control.check()
        b = dict(kind=block["kind"], title=block["title"])
        kind = b["kind"]
        if kind in ("section", "note", "assumption"):
            b.update(
                text=block["text"],
                evidence="Kullanıcı metni; doğrulanmış hesap değildir.",
            )
        elif kind == "bibliography":
            b["references"] = block["references"]
        elif kind in ("dictionary", "table"):
            ref = request["sources"][block["version"]]
            columns = {c["id"]: c for c in ref["columns"]}
            selected = [columns[c] for c in block["columns"]]
            b["dataset_version"] = block["version"]
            if kind == "dictionary":
                # Metadata is recorded, never inferred from names/values.
                b["data"] = dict(
                    columns=selected,
                    semantic_metadata={
                        k: v
                        for k, v in ref.get("semantic_metadata", {}).items()
                        if k in block["columns"]
                    },
                )
                if block.get("code_column"):
                    from veri_ufku.exports.code_bridge import CodeRecipe, bundle

                    name = f"profile-code-{i}.zip"
                    code_work = work / ("code-" + uid())
                    code_work.mkdir(mode=0o700)
                    bundle(
                        ref,
                        CodeRecipe(column_id=block["code_column"], sample=False).data(),
                        "notebook",
                        code_work,
                        code_work / name,
                        work / "unrelated-project",
                        control,
                    )
                    files[name] = (code_work / name).read_bytes()
                    b["attachments"] = [name]
                    b["code_scope"] = (
                        "Yalnız tam numeric profile; raporun bütün analizlerini yeniden üretmez."
                    )
            else:
                import pyarrow as pa
                import pyarrow.parquet as pq

                # iter_batches bounds row materialization; never read the entire tensor/table.
                pf = pq.ParquetFile(ref["path"])
                names = [c["name"] for c in selected]
                if any(redact(n)[0] != n for n in names):
                    raise ProjectError(
                        "Tablo başlığında hassas/path/secret deseni; rapordan önce açık kolon adı düzenlemesi gerekli."
                    )
                batch = next(
                    pf.iter_batches(batch_size=block["rows"], columns=names), None
                )
                rows = batch.to_pylist() if batch is not None else []
                for row in rows:
                    for c in selected:
                        name = c["name"]
                        if c["id"] in spec["masked_columns"]:
                            row[name] = "[redacted]"
                        elif isinstance(row[name], str):
                            row[name], reasons = redact(row[name])
                            changes.extend(
                                dict(field=f"block.{i}.cell", reason=r["reason"])
                                for r in reasons
                            )
                b.update(
                    data=json.loads(json.dumps(rows, default=str, allow_nan=False)),
                    caption=block["caption"],
                    n=len(rows),
                    total_n=ref["row_count"],
                    selection="İlk N immutable satır; rastgele veya tam veri değildir.",
                    csv_policy="Null boş hücre; spreadsheet formül öneklerine apostrof eklenir. Parquet null/type korur; maskeli kolon string olur.",
                )
                csv_out = io.StringIO(newline="")
                writer = csv.writer(csv_out)
                writer.writerow(
                    [
                        "'" + n if n.lstrip().startswith(("=", "+", "-", "@")) else n
                        for n in names
                    ]
                )
                for row in rows:
                    writer.writerow(
                        [
                            ("'" + row[n])
                            if isinstance(row[n], str)
                            and row[n].lstrip().startswith(("=", "+", "-", "@"))
                            else row[n]
                            for n in names
                        ]
                    )
                csv_name, parquet_name = f"table-{i}.csv", f"table-{i}.parquet"
                files[csv_name] = csv_out.getvalue().encode("utf-8-sig")
                # Preserve original Arrow schema except columns explicitly masked.
                table = pa.Table.from_pylist(
                    rows,
                    schema=pa.schema(
                        [
                            pa.field(
                                c["name"],
                                pa.string()
                                if c["id"] in spec["masked_columns"]
                                else pf.schema_arrow.field(c["name"]).type,
                            )
                            for c in selected
                        ]
                    ),
                )
                pq.write_table(table, work / parquet_name)
                pq.read_table(work / parquet_name)  # Real format readback.
                files[parquet_name] = (work / parquet_name).read_bytes()
                b["attachments"] = [csv_name, parquet_name]
        else:
            r = request["records"][block["record"]]
            from veri_ufku.storage.report_builder_store import result_value

            _, value = result_value(r)
            b.update(
                record_id=r["id"],
                capability_id=r.get("capability_id"),
                dataset_versions=r["dataset_version_ids"],
                run_id=value.get("run_id", "not_recorded"),
                evidence="Kayıtlı alan projeksiyonu; yeni hesap veya otomatik yorum değildir.",
            )
            fields = (
                ("model_card",)
                if kind == "model-card"
                else (
                    ("diagnostics", "warnings", "limitations")
                    if kind == "diagnostic"
                    else (
                        (
                            "uncertainty",
                            "interval",
                            "confidence_interval",
                            "limitations",
                        )
                        if kind == "uncertainty"
                        else FIELDS
                    )
                )
            )
            b["data"] = {k: value[k] for k in fields if k in value} or {
                "status": "not_recorded"
            }
            b["narrative"] = findings(b["data"], r["id"])
            b["narrative_scope"] = (
                "İlk40 numeric alanın birebir değeri; bütün kayıtlı ayrıntılar data alanında. İstatistiksel yorum/hesap yapılmaz."
            )
            # Metrics remain numerical and carry exact native field paths.
            b["field_references"] = {k: r["id"] + "/" + k for k in b["data"]}
            if kind == "chart":
                b["data"] = dict(
                    spec=value["spec"],
                    **{
                        k: value[k]
                        for k in (
                            "warnings",
                            "details",
                            "dataset_n",
                            "population_n",
                            "used_n",
                            "scope",
                            "filters",
                            "summary",
                            "render",
                        )
                        if k in value
                    },
                )
                b["field_references"] = {k: r["id"] + "/" + k for k in b["data"]}
                b["caption"] = block["caption"]
                for fmt in ("png", "svg", "pdf"):
                    name = f"figure-{i}.{fmt}"
                    files[name] = Path(
                        request["artifacts"][r["id"] + ":" + fmt]["path"]
                    ).read_bytes()
                b["image"] = f"figure-{i}.png"
                b["attachments"] = [f"figure-{i}.svg", f"figure-{i}.pdf"]
        # References were structurally checked; preserve HTTPS citation text without fetching it.
        refs = b.pop("references", None)
        b, reasons = redact(b, request["masked_names"])
        changes.extend(
            dict(field=f"block.{i}." + r["field"], reason=r["reason"]) for r in reasons
        )
        if refs is not None:
            b["references"] = refs
        # Bound arbitrary legacy payload size; no silent truncation of results.
        if len(encode(b)) > 128 * 1024:
            raise ProjectError("Blok128KiB sınırı; daha dar kayıt/kolon seçin.")
        blocks.append(b)
        control.disk(work)
    value = dict(
        schema="ScientificReport/v1",
        status="completed",
        run_id="run:" + uid(),
        spec=spec,
        blocks=blocks,
        redactions=changes,
        stale=request["stale"],
        limitations=LIMITATIONS,
        source_refs=request["source_refs"],
        record_refs=request["record_refs"],
        test_uses=request["test_uses"],
        prior_test_use_ids=request["prior_test_use_ids"],
        experiment_capture=request["experiment_capture"],
        compute_budget=asdict(control.budget),
        provenance=asdict(
            Provenance(
                provenance_id="provenance:" + uid(),
                dataset_versions=tuple(request["source_refs"]),
                config_revision=0,
                capability_id="report.builder",
                parameters_hash=digest(spec),
                environment=tuple(request["experiment_capture"]["environment"].items()),
                created_at=datetime.now(UTC).isoformat(),
                scope="Pinned recorded results; first-N table; no recompute; native RowId lineage stays in referenced records",
                seed_reason="No random draw or model fitting; render layout platform bounded",
                source_snapshot_ids=tuple(
                    r["source_snapshot_id"] for r in request["source_refs"].values()
                ),
            )
        ),
    )
    # The report contains a safe environment lock, not runtime paths or environment variables.
    files["environment.lock.json"] = encode(
        request["experiment_capture"]["environment"]
    )
    md, doc = render(value, files)
    files["report.md"] = md.encode()
    # PDF resolves local images first; portable HTML embeds those same bytes.
    files["report.html"] = doc.encode()
    from veri_ufku.exports.reports import write_pdf

    images = {name: raw for name, raw in files.items() if name.endswith(".png")}
    value["pdf_pages"] = write_pdf(doc, images, work / "report.pdf", control)
    files["report.pdf"] = (work / "report.pdf").read_bytes()
    for name, raw in images.items():
        doc = doc.replace(
            'src="' + name + '"',
            'src="data:image/png;base64,' + base64.b64encode(raw).decode() + '"',
        )
    files["report.html"] = doc.encode()
    hashes = {
        n: dict(size=len(raw), sha256=__import__("hashlib").sha256(raw).hexdigest())
        for n, raw in files.items()
    }
    manifest = dict(
        schema="ReportPackage/v1",
        files=hashes,
        source_refs=value["source_refs"],
        record_refs=value["record_refs"],
        redactions=changes,
        protocol=spec["protocol"],
        limitations=LIMITATIONS,
    )
    files["manifest.json"] = encode(manifest)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, raw in files.items():
            control.check()
            z.writestr(name, raw)
    with zipfile.ZipFile(io.BytesIO(out.getvalue())) as z:
        if z.testzip() is not None:
            raise ProjectError("Rapor paket doğrulaması başarısız.")
    files["report-package.zip"] = out.getvalue()
    value["file_hashes"] = {
        n: dict(size=len(raw), sha256=__import__("hashlib").sha256(raw).hexdigest())
        for n, raw in files.items()
    }
    value["review_hash"] = digest(value)
    if sum(len(v) for v in files.values()) > 32 * 1024**2:
        raise ProjectError("Rapor32MiB bütçesini aşıyor.")
    value["files"] = {
        n: base64.b64encode(raw).decode("ascii") for n, raw in files.items()
    }
    control.check()
    return value


def md_literal(value):
    value = html.escape(value)
    for char in "\\[]*_`#":
        value = value.replace(char, "\\" + char)
    return value


def render(value, files):
    spec = value["spec"]
    lines = [
        "# " + md_literal(spec["title"]),
        "",
        "Protokol: " + spec["protocol"],
        md_literal(spec["protocol_note"]),
        "",
        "Güncellik: "
        + (
            "STALE · " + json.dumps(value["stale"], ensure_ascii=False)
            if value["stale"]
            else "Seçilen dataset/run için daha yeni kayıt bulunmadı; dış kaynağın canlı tazeliği doğrulanmadı."
        ),
        "",
        "Test kullanım defteri: " + json.dumps(value["test_uses"], ensure_ascii=False),
        "Model seçim protokolü: kayıtlı method/model-card alanlarına bakın; alan yoksa not_recorded.",
    ]
    parts = ["<h1>" + html.escape(spec["title"]) + "</h1>"]
    for line in lines[2:]:
        parts.append("<p>" + html.escape(line) + "</p>")
    for b in value["blocks"]:
        lines.extend(["", "## " + md_literal(b["title"]), ""])
        parts.append("<h2>" + html.escape(b["title"]) + "</h2>")
        if b["kind"] == "table" and b.get("data"):
            rows = b["data"]
            names = list(rows[0])

            def cell(v):
                return "null" if v is None else str(v)

            def md_cell(v):
                return html.escape(cell(v)).replace("|", "\\|").replace("\n", " ")

            lines.extend(
                [
                    "| " + " | ".join(md_cell(n) for n in names) + " |",
                    "| " + " | ".join("---" for n in names) + " |",
                ]
            )
            lines.extend(
                "| " + " | ".join(md_cell(row[n]) for n in names) + " |" for row in rows
            )
            parts.append(
                '<table border="1" cellspacing="0" cellpadding="4"><tr>'
                + "".join("<th>" + html.escape(n) + "</th>" for n in names)
                + "</tr>"
                + "".join(
                    "<tr>"
                    + "".join(
                        "<td>" + html.escape(cell(row[n])) + "</td>" for n in names
                    )
                    + "</tr>"
                    for row in rows
                )
                + "</table>"
            )
        for k, item in b.items():
            if k in ("title", "kind", "image", "attachments", "references") or (
                b["kind"] == "table" and k == "data"
            ):
                continue
            text = (
                item
                if isinstance(item, str)
                else json.dumps(
                    item, ensure_ascii=False, indent=2, default=str, allow_nan=False
                )
            )
            # Markdown escapes HTML; embedded user markup is displayed literally.
            lines.extend(
                ["**" + k + "**", "", "```text", text.replace("```", "'''"), "```"]
            )
            parts.append(
                "<p><b>"
                + html.escape(k)
                + "</b></p><pre>"
                + html.escape(text)
                + "</pre>"
            )
        if "image" in b:
            name = b["image"]
            lines.append("![" + b["title"].replace("]", "") + "](" + name + ")")
            parts.append(
                '<img width="620" src="'
                + name
                + '" alt="'
                + html.escape(b["title"], quote=True)
                + '">'
            )
        for name in b.get("attachments", []):
            lines.append("[" + name + "](" + name + ")")
            parts.append('<p><a href="' + name + '">' + name + "</a></p>")
        for ref in b.get("references", []):
            lines.append(
                "["
                + md_literal(ref["title"])
                + "]("
                + __import__("urllib.parse", fromlist=["quote"]).quote(
                    ref["url"], safe="/:@%+-_.~"
                )
                + ")"
            )
            parts.append(
                "<p>"
                + html.escape(ref["title"])
                + " — "
                + html.escape(ref["url"])
                + "</p>"
            )
    lines.extend(["", "## Sınırlamalar", *LIMITATIONS])
    parts.append(
        "<h2>Sınırlamalar</h2>"
        + "".join("<p>" + html.escape(s) + "</p>" for s in LIMITATIONS)
    )
    doc = (
        '<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\' data:; font-src data:"><title>'
        + html.escape(spec["title"])
        + "</title><style>body{font-family:DejaVu Sans,sans-serif;font-size:10pt;max-width:190mm;margin:15mm}pre{white-space:pre-wrap;word-wrap:break-word;font-size:8pt}h2{page-break-after:avoid}img{max-width:100%}</style></head><body>"
        + "".join(parts)
        + "</body></html>"
    )
    # The PDF renderer resolves only explicitly provided images; HTML is self-contained.
    from veri_ufku.exports.reports import ASSETS

    FONT = ASSETS / "fonts/DejaVuSans.ttf"
    font = base64.b64encode(FONT.read_bytes()).decode()
    doc = doc.replace(
        "<style>",
        "<style>@font-face{font-family:ReportTurkish;src:url(data:font/ttf;base64,"
        + font
        + ")}body{font-family:ReportTurkish,DejaVu Sans,sans-serif}",
    )
    return "\n".join(lines) + "\n", doc
