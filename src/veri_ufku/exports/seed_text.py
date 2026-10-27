"""Recorded randomness seeds. Missing seeds stay missing."""


def seed_text(project_seed, operations, results):
    lines = ["Proje tohumu: " + _label(project_seed)]
    found = _label(project_seed) not in ("kayıtlı değil", "geçersiz")
    for index, op in enumerate(list(operations or [])[:100], start=1):
        if not isinstance(op, dict):
            lines.append(f"{index}. işlem okunamadı")
            continue
        spec = op.get("spec") if isinstance(op.get("spec"), dict) else {}
        kind = _clip(spec.get("kind") or op.get("id") or "işlem")
        label = _label(op.get("seed"))
        lines.append(f"{index}. {kind} · tohum {label}")
        found = found or label not in ("kayıtlı değil", "geçersiz")
    for index, result in enumerate(list(results or [])[:100], start=1):
        if not isinstance(result, dict):
            continue
        label = _label(result.get("seed"))
        lines.append(
            f"Sonuç {index}. {_clip(result.get('id') or 'kayıt')} · tohum {label}"
        )
        found = found or label not in ("kayıtlı değil", "geçersiz")
    if not found:
        lines.append("Kayıtlı rastgele tohum yok. Tohum uydurulmaz.")
    return "\n".join(lines)


def _label(value):
    if type(value) is int and 0 <= value < 2**32:
        return str(value)
    if value is None:
        return "kayıtlı değil"
    return "geçersiz"


def _clip(value):
    raw = str(value or "").replace("\n", " ").strip()
    return raw[:80] or "kayıt"
