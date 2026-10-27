"""UX10: not / grafik / karar / model bağlamını rapora bağlanabilir özet."""

from __future__ import annotations

from veri_ufku.exports.report_contracts import LIMITATIONS


def build_context(
    *,
    dataset_version: str = "",
    row_count: int | None = None,
    column_count: int | None = None,
    chart_notes: dict | None = None,
    outlier_candidates: dict | None = None,
    model_candidates: dict | None = None,
    scope_note: str = "",
):
    notes = {
        str(k)[:200]: str(v)[:2000]
        for k, v in (chart_notes or {}).items()
        if str(v).strip()
    }
    outliers = outlier_candidates or {}
    models = model_candidates or {}
    return {
        "schema": "UxReportContext/v1",
        "dataset_version": dataset_version or "",
        "row_count": row_count,
        "column_count": column_count,
        "scope_note": scope_note
        or "Kapsam: rapor bağlı DatasetVersion ve kayıtlı artifact'larla sınırlıdır.",
        "chart_notes": notes,
        "chart_note_count": len(notes),
        "outlier_candidates_applied": bool(outliers.get("applied")),
        "outlier_union_n": len(outliers.get("union_row_ids") or []),
        "model_status": models.get("status") or "aday",
        "model_auto_fit": bool(models.get("auto_fit")),
        "model_starter": models.get("starter_model") or "",
        "model_structure": models.get("structure") or "",
        "limitations": list(LIMITATIONS),
        "reopenable": True,
        "provenance_note": (
            "Yeniden açılışta bağlı DatasetVersion kimliği ve kayıt hash'leri "
            "korunur; analiz yeniden hesaplanmaz."
        ),
    }


def context_note_text(context: dict) -> str:
    lines = [
        "UX bağlam özeti (manuel bağ; sayısal bulgu sayılmaz)",
        f"Veri sürümü: {context.get('dataset_version') or 'yok'}",
        f"Satır/sütun: {context.get('row_count')} / {context.get('column_count')}",
        context.get("scope_note") or "",
        f"Grafik yorumu sayısı: {context.get('chart_note_count', 0)}",
        f"Aykırı aday uygulandı mı: {context.get('outlier_candidates_applied')}; birleşik n={context.get('outlier_union_n', 0)}",
        f"Model durumu: {context.get('model_status')} · auto_fit={context.get('model_auto_fit')} · başlangıç={context.get('model_starter')} · yapı={context.get('model_structure')}",
        context.get("provenance_note") or "",
        "Sınırlamalar:",
    ]
    for item in context.get("limitations") or []:
        lines.append("- " + item)
    for key, note in (context.get("chart_notes") or {}).items():
        lines.append(f"Grafik notu [{key}]: {note}")
    return "\n".join(line for line in lines if line is not None)
