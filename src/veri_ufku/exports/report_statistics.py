"""Saved statistics for a report, kept apart from model metrics."""

CORE_PATHS = frozenset({"independent", "paired", "groups", "categorical", "numeric"})


def split_report_analyses(analyses):
    """Core findings stay. Any other saved record is counted, not quoted."""
    findings = []
    skipped = 0
    for item in analyses or []:
        found = statistics_finding(item)
        if found is None:
            skipped += 1
        else:
            findings.append(found)
    return findings, skipped


def statistics_finding(analysis):
    if not isinstance(analysis, dict):
        return None
    spec = analysis.get("spec") or {}
    if spec.get("path") not in CORE_PATHS:
        return None
    primary = analysis.get("primary") or {}
    effect = primary.get("effect") or {}
    return {
        "question": _clip(spec.get("question")) or "Soru metni yok",
        "method": _clip(analysis.get("method_label") or spec.get("method")),
        "n": analysis.get("n"),
        "excluded": analysis.get("excluded_rows"),
        "statistic": primary.get("statistic"),
        "p_value": primary.get("p_value"),
        "effect_name": _clip(effect.get("name")),
        "effect_value": effect.get("value"),
        "ci_limitation": _clip(effect.get("ci_limitation")),
        "version": _clip(analysis.get("dataset_version")),
    }


def statistics_report_text(analyses):
    findings, skipped = split_report_analyses(analyses)
    parts = [finding_text(item) for item in findings]
    if not findings:
        parts.insert(0, "Kaydedilmiş istatistiksel analiz yok. Sonuç uydurulmaz.")
    if skipped:
        parts.append(
            f"Model kaydı {skipped} adet istatistik bölümüne yazılmadı. "
            "Model metriği uydurulmaz."
        )
    return "\n".join(parts)


def finding_text(found):
    lines = [
        "Soru: " + found["question"],
        "Yöntem: " + found["method"],
        "n: " + _show(found["n"]),
        "dışlanan: " + _show(found["excluded"]),
        "istatistik: " + _show(found["statistic"]),
        "p: " + _show(found["p_value"]),
        (found["effect_name"] or "etki") + ": " + _show(found["effect_value"]),
    ]
    if found["ci_limitation"]:
        lines.append("ci_limitation: " + found["ci_limitation"])
    if found["version"]:
        lines.append("sürüm: " + found["version"])
    return "\n".join(lines)


def _show(value):
    if value is None:
        return "yok"
    return str(value)


def _clip(value):
    return str(value or "").replace("\n", " ").strip()[:500]
