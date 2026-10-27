"""Model-open leakage notice from operations already on the active version."""

from veri_ufku.modeling.history import audit
from veri_ufku.storage.project_model import ProjectError


def model_leakage_notice(state, version_id):
    """Warn only when a dataset-learned transform sits on this version's history."""
    if not version_id:
        return {"warning": False, "count": 0, "text": ""}
    if not isinstance(state, dict) or "datasets" not in state:
        return _unread()
    try:
        report = audit(state, version_id, version_id, "raw")
    except (ProjectError, KeyError):
        return _unread()
    hits = [
        item
        for item in report.get("findings") or []
        if item.get("risk") == "dataset_learned"
        and item.get("resolution") == "unresolved"
    ]
    if not hits:
        return {"warning": False, "count": 0, "text": ""}
    kinds = ", ".join(sorted({str(item.get("kind") or "") for item in hits}))
    count = len(hits)
    return {
        "warning": True,
        "count": count,
        "text": (
            f"Veri sızıntısı uyarısı: {count} işlem tüm veriye uygulanmış "
            f"öğrenilen dönüşüm ({kinds}). "
            "Bu istatistikler sonraki doğrulama kayıtlarını da görmüş olabilir. "
            "Model için plan, dönüşümü yalnız eğitim katında öğrenir. "
            "Bu uyarı bir ölçüm değildir."
        ),
    }


def _unread():
    return {
        "warning": False,
        "count": 0,
        "text": "Sürüm geçmişi okunamadı. Sızıntı uyarısı uydurulmaz.",
    }
