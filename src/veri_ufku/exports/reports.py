"""Escaped, self-contained HTML and paged local Qt PDF from bound project context."""

import base64
import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

import polars as pl

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked
from veri_ufku.exports.files import publish
from veri_ufku.exports.query import scoped
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.storage.project_model import ProjectError

ASSETS = Path(__file__).resolve().parents[1] / "assets"


@dataclass(frozen=True)
class ReportSpec:
    format: str
    title: str = "Veri_Ufku veri inceleme raporu"
    purpose: str = "Dosyamı anlamak istiyorum"
    scope: str = "view"
    view: dict = field(default_factory=dict)
    table_rows: int = 100

    def validate(self, columns):
        if self.format not in ("html", "pdf") or self.scope not in ("full", "view"):
            raise ProjectError("Rapor formatı/kapsamı geçersiz.")
        if (
            not isinstance(self.title, str)
            or not 1 <= len(self.title) <= 200
            or not isinstance(self.purpose, str)
            or len(self.purpose) > 2000
        ):
            raise ProjectError(
                "Rapor başlığı 1–200, amaç en fazla 2000 karakter olmalı."
            )
        if type(self.table_rows) is not int or not 1 <= self.table_rows <= 200:
            raise ProjectError("Rapor tablo örneği 1–200 kayıt olmalı.")
        ViewSpec.from_dict(self.view).validate(columns)


def text(value):
    return html.escape(str(value), quote=True)


def described(value):
    return (
        "<pre>"
        + text(json.dumps(value, ensure_ascii=False, indent=2, default=str))
        + "</pre>"
    )


def build(request, spec, control):
    spec.validate(request["columns"])
    checked(request, control)
    query, schema, view = scoped(request, spec)
    count = query.select(pl.len()).collect(engine="streaming").item()
    context = request.get("report_context", {})
    columns = [c["name"] for c in request["columns"]][:20]
    frame = query.select(columns).head(spec.table_rows).collect(engine="streaming")
    frame = frame.with_columns(
        pl.col(n).cast(pl.String) for n in columns if schema[n].is_temporal()
    )
    sections = []

    def section(title, content):
        sections.append(
            "<section><h2>" + text(title) + "</h2>" + content + "</section>"
        )

    section("Amaç", "<p>" + text(spec.purpose) + "</p>")
    section(
        "Veri sürümü ve kapsam",
        described(
            dict(
                dataset_version=request["version_id"],
                dataset_n=request["row_count"],
                scope=spec.scope,
                filtered_n=count,
                filters=list(view.filters),
                view=view.data(),
                snapshot=request["fingerprint"],
            )
        ),
    )
    section(
        "Kaynak ve köken (provenance)",
        described(context.get("sources", []))
        + described(context.get("dataset_provenance", {})),
    )
    quality = context.get("quality", [])
    section(
        "Kalite bulguları",
        "".join(
            "<h3>"
            + text("Tarama sürümü: " + str(q.get("dataset_version", "bilinmiyor")))
            + "</h3><ul>"
            + "".join(
                "<li>"
                + text(
                    f"{f.get('column', '')}: {f.get('count', 0)} kayıt · {f.get('reason', '')}"
                )
                + "</li>"
                for f in q.get("findings", [])
            )
            + "</ul>"
            + described(
                {
                    k: q[k]
                    for k in (
                        "scope",
                        "used_n",
                        "population_n",
                        "methods",
                        "parameters",
                        "warnings",
                    )
                    if k in q
                }
            )
            for q in quality
        )
        if quality
        else "<p>Kaydedilmiş kalite taraması yok. Sorunsuz veri olduğu iddia edilmez.</p>",
    )
    operations = context.get("operations", [])
    section(
        "Temizleme ve işlem geçmişi",
        "<p>Seçilen sürümün işlem zinciri aşağıdadır; geri alınan farklı dallar güncel veriye uygulanmış sayılmaz.</p>"
        + described(operations)
        if operations
        else "<p>Bu veri sürümüne uygulanmış kayıtlı işlem yok.</p>",
    )
    profiles = context.get("profiles", [])
    section(
        "Profil ve yöntemler",
        "".join(
            "<p>"
            + text(
                f"{p.get('column_name', p.get('column_id', 'Sütun'))}: ortalama {p.get('numeric', {}).get('mean', 'hesaplanmadı')}, medyan {p.get('numeric', {}).get('median', 'hesaplanmadı')}; sürüm {p.get('dataset_version', 'grafik sürümü')}"
            )
            + "</p>"
            + described(
                {
                    k: p[k]
                    for k in (
                        "physical_type",
                        "role",
                        "unit",
                        "scope",
                        "used_n",
                        "population_n",
                        "counts",
                        "numeric",
                        "warnings",
                    )
                    if k in p
                }
            )
            for p in profiles
        )
        if profiles
        else "<p>Kaydedilmiş profil özeti yok. Rapor sayısal özet uydurmaz.</p>",
    )
    table = (
        "<p>"
        + text(
            f"İlk {frame.height}/{count} kayıt, ilk {len(columns)}/{len(request['columns'])} sütun (gizli sütunlar dahil); hücre metni ilk 500 karakter. Bu tablo açık görüntü örneğidir."
        )
        + "</p><table><thead><tr>"
        + "".join("<th>" + text(n) + "</th>" for n in columns)
        + "</tr></thead><tbody>"
    )
    for row in frame.iter_rows():
        table += (
            "<tr>"
            + "".join(
                "<td>"
                + text(
                    "∅ (null)"
                    if v is None
                    else str(v)[:500] + ("…" if len(str(v)) > 500 else "")
                )
                + "</td>"
                for v in row
            )
            + "</tr>"
        )
    section("Veri tablosu", table + "</tbody></table>")
    logo = (ASSETS / "branding/icon-128.png").read_bytes()
    logo_uri = "data:image/png;base64," + base64.b64encode(logo).decode()
    images = {logo_uri: logo}
    chart_sections = []
    charts = context.get("charts", [])
    for index, chart in enumerate(charts[:10]):
        control.check()
        path = Path(chart["path"])
        if path.is_symlink() or hash_artifact(path, control) != chart["fingerprint"]:
            raise ProjectError("Rapor grafiği değişmiş; yeniden oluşturun/açın.")
        data = path.read_bytes()
        if len(data) > 10 * 1024**2:
            raise ProjectError("Rapor grafiği 10MiB sınırını aşıyor.")
        uri = "data:image/png;base64," + base64.b64encode(data).decode()
        images[uri] = data
        chart_sections.append(
            "<h3>"
            + text(chart.get("title", "Grafik"))
            + "</h3><p>"
            + text(chart.get("context", ""))
            + '</p><img width="650" height="423" src="'
            + uri
            + '">'
            + described(chart.get("metadata", {}))
        )
    section(
        "Grafikler",
        "<p>"
        + text(
            f"{min(10, len(charts))}/{len(charts)} kayıtlı/güncel grafik. Her grafiğin kendi sürüm/filtre/kapsamı ayrıca gösterilir."
        )
        + "</p>"
        + "".join(chart_sections)
        if charts
        else "<p>Grafik eklenmedi; rapor için grafik zorunlu değildir.</p>",
    )
    section(
        "İstatistiksel analizler",
        "".join(
            "<h3>"
            + text(a["spec"]["question"])
            + "</h3>"
            + described({k: v for k, v in a.items() if k != "artifact_uris"})
            for a in context.get("analyses", [])
        )
        or "<p>Kaydedilmiş istatistiksel analiz yok; sonuç uydurulmaz.</p>",
    )
    limitations = "Bu sürüm deneysel veri inceleme/temizlik/grafik/istatistik/rapor aracıdır. Bu eski rapor şablonu model kartı içermez; model sonuçlarını bilimsel rapor oluşturucuda açıkça bağlayın. Korelasyon nedensellik değildir. Küçük p kesinlik veya pratik önem göstermez. Tablolar sınırlı görüntü örneğidir; grafik örnekleme/gruplama ve null politikaları kendi kayıtlarında görünür. Kalite/profil/analiz bulgusunun veri sürümü farklıysa güncel kanıt sayılmaz. Genel veri bağımlı temizleme gelecekte model doğrulamasında sızıntı incelemesi gerektirir. "
    section(
        "Yöntemler ve sınırlamalar",
        '<p class="warning">'
        + text(limitations)
        + "</p>"
        + described(context.get("environment", {})),
    )
    font = base64.b64encode((ASSETS / "fonts/DejaVuSans.ttf").read_bytes()).decode()
    css = (
        '@font-face{font-family:"DejaVu Sans";src:url(data:font/ttf;base64,'
        + font
        + ")}\n"
        + (ASSETS / "reports/report.css").read_text()
    )
    document = Template((ASSETS / "reports/report.html").read_text()).substitute(
        title=text(spec.title),
        css=css,
        body='<p><img width="48" height="48" alt="Veri_Ufku logosu" src="'
        + logo_uri
        + '"> Veri_Ufku</p><h1>'
        + text(spec.title)
        + "</h1>"
        + "".join(sections),
    )
    if len(document.encode()) > 16 * 1024**2:
        raise ProjectError("Rapor 16MiB sınırını aşıyor; daha az grafik/ayrıntı seçin.")
    return (
        document,
        images,
        dict(
            dataset_version=request["version_id"],
            lineage_record_ids=context.get("lineage_record_ids", []),
            lineage_context_version=context.get("lineage_context_version"),
            scope=spec.scope,
            filters=list(view.filters),
            view=view.data(),
            rows=count,
            shown_rows=frame.height,
            shown_columns=len(columns),
            charts_shown=min(10, len(charts)),
            title=spec.title,
            purpose=spec.purpose,
            limitations=limitations,
        ),
    )


def write_pdf(document, images, path, control):
    # A disposable worker owns its own Qt GUI runtime, never the application's objects.
    from PySide6.QtCore import QMarginsF, QSizeF
    from PySide6.QtGui import (
        QFont,
        QFontDatabase,
        QGuiApplication,
        QImage,
        QPageSize,
        QPdfWriter,
        QTextDocument,
    )
    from PySide6.QtPdf import QPdfDocument

    app = QGuiApplication.instance() or QGuiApplication(["veri-ufku-report"])
    font_id = QFontDatabase.addApplicationFont(str(ASSETS / "fonts/DejaVuSans.ttf"))
    if font_id < 0:
        raise ProjectError("Paket rapor fontu yüklenemedi.")

    class LocalDocument(QTextDocument):
        def loadResource(self, kind, name):
            data = images.get(name.toString())
            return QImage.fromData(data) if data else None

    writer = QPdfWriter(str(path))
    writer.setResolution(96)
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageMargins(QMarginsF(15, 15, 15, 15))
    writer.setTitle("Veri_Ufku raporu")
    writer.setCreator("Veri_Ufku — yerel çevrimdışı rapor")
    doc = LocalDocument()
    doc.setDefaultFont(QFont("DejaVu Sans", 10))
    doc.setPageSize(QSizeF(writer.width(), writer.height()))
    doc.setHtml(document)
    control.check()
    doc.print_(writer)
    del writer
    control.check()
    verify = QPdfDocument()
    if verify.load(str(path)) != QPdfDocument.Error.None_ or verify.pageCount() < 1:
        raise ProjectError("PDF yeniden açma/sayfa doğrulaması başarısız.")
    count = verify.pageCount()
    if not verify.getAllText(0).text():
        raise ProjectError("PDF metin/font doğrulaması başarısız.")
    verify.close()
    app.processEvents()
    return count


def export(request, parameters, workspace, destination, project_root, control=None):
    control = control or Control()
    spec = (
        parameters if isinstance(parameters, ReportSpec) else ReportSpec(**parameters)
    )
    spec.validate(request["columns"])
    if Path(destination).suffix.lower() != "." + spec.format:
        raise ProjectError("Rapor uzantısı formatla eşleşmeli.")
    document, images, info = build(request, spec, control)
    path = Path(workspace) / ("report." + spec.format)
    if spec.format == "html":
        path.write_text(document, encoding="utf-8")
        if path.read_text(encoding="utf-8") != document:
            raise ProjectError("HTML metin doğrulaması başarısız.")
    else:
        info["pages"] = write_pdf(document, images, path, control)
    checked(request, control)
    control.disk(Path(workspace))
    info["published"] = publish(path, destination, project_root, control)
    info.update(format=spec.format, offline_resources=True)
    return info
