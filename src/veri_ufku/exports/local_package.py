"""Local report package: identity, operations, and HTML. Raw rows stay out."""

import json
import zipfile
from pathlib import Path

from veri_ufku.exports.environment_text import current_environment_text
from veri_ufku.exports.files import publish
from veri_ufku.exports.operation_python import operation_history_python
from veri_ufku.exports.report_statistics import statistics_report_text
from veri_ufku.exports.reports import ReportSpec, build, text
from veri_ufku.exports.seed_text import seed_text
from veri_ufku.exports.source_note import source_license_text
from veri_ufku.importers.delimited import Control
from veri_ufku.storage.project_model import ProjectError

README = """Veri_Ufku yerel paketi.
Bu dosya çevrimdışı bir arşivdir. Sunucuya gönderilmez.
Paylaşım özet veya örneklemdir. Tam veri kopyası yoktur.
Ham satırlar pakette yoktur. Veri kimliği sürüm, satır sayısı ve sütun kimliğidir.
Özet hücre değeri içermez. Örneklem yalnız rapor tablosundaki kişisel olmayan satırlardır.
İşlem dökümü çalıştırılmaz. Parametre değerleri yazılmaz.
"""


def export(request, parameters, workspace, destination, project_root, control=None):
    control = control or Control()
    if parameters.get("format") != "zip" or Path(destination).suffix.lower() != ".zip":
        raise ProjectError("Paket uzantısı zip olmalı.")
    mode = parameters.get("share_mode") or "ozet"
    if mode not in ("ozet", "orneklem"):
        raise ProjectError(
            "Paylaşım özet veya örneklem olmalı. Tam kopya bu pakette yok."
        )
    context = request.get("report_context") or {}
    if mode == "orneklem":
        spec = ReportSpec(
            "html",
            title=parameters.get("title") or "Veri_Ufku veri inceleme raporu",
            purpose=parameters.get("purpose") or "Dosyamı anlamak istiyorum",
            scope=parameters.get("scope") or "view",
            view=parameters.get("view") or {},
            table_rows=parameters.get("table_rows") or 100,
            include_personal=parameters.get("include_personal") is True,
            license_note=parameters.get("license_note") or "",
        )
        document, _images, info = build(request, spec, control)
    else:
        document = _summary(request, context, parameters.get("license_note") or "")
        info = {
            "dataset_version": request.get("version_id"),
            "rows": request.get("row_count"),
        }
    members = {
        "README.txt": README,
        "veri.json": json.dumps(_identity(request, mode), ensure_ascii=False, indent=2),
        "islemler.py": operation_history_python(context.get("operations") or []),
        "tohum.txt": seed_text(
            context.get("project_seed"),
            context.get("operations") or [],
            context.get("result_seeds") or [],
        ),
        "ortam.txt": current_environment_text(),
        "rapor.html": document,
    }
    path = Path(workspace) / "package.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in members.items():
            control.check()
            archive.writestr(name, body)
    info["published"] = publish(path, destination, project_root, control)
    info.update(
        format="zip", raw_included=False, share_mode=mode, offline_resources=True
    )
    return info


def _summary(request, context, license_note):
    identity = _identity(request, "ozet")
    body = "\n".join(
        [
            "Bu özet hücre değeri içermez.",
            "Sürüm: " + str(identity["dataset_version"] or ""),
            "Satır sayısı: " + str(identity["row_count"]),
            "Sütun sayısı: " + str(len(identity["column_ids"])),
            statistics_report_text(context.get("analyses") or []),
            operation_history_python(context.get("operations") or []),
            seed_text(
                context.get("project_seed"),
                context.get("operations") or [],
                context.get("result_seeds") or [],
            ),
            current_environment_text(),
            source_license_text(context.get("sources"), license_note),
        ]
    )
    return "<pre>" + text(body) + "</pre>"


def _identity(request, mode):
    columns = request.get("columns") or []
    return {
        "dataset_version": request.get("version_id"),
        "row_count": request.get("row_count"),
        "column_ids": [
            item.get("id") for item in columns[:200] if isinstance(item, dict)
        ],
        "share_mode": mode,
        "raw_included": False,
    }
