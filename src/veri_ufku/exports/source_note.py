"""Source identity and an explicit license note. Paths stay out."""

from veri_ufku.exports.repro import LOCATION, SECRET_KEY
from veri_ufku.exports.share_privacy import reason


def source_note(sources):
    if not sources:
        return "Kaynak kaydı yok. Kaynak uydurulmaz."
    lines = []
    for source in list(sources)[:20]:
        if not isinstance(source, dict):
            lines.append("Kaynak okunamadı.")
            continue
        lines.append("Kaynak: " + (_clip(source.get("id")) or "kimlik yok"))
        fingerprint = source.get("fingerprint")
        digest = fingerprint.get("sha256") if isinstance(fingerprint, dict) else ""
        if isinstance(digest, str) and len(digest) == 64 and digest.isalnum():
            lines.append("Parmak izi: " + digest)
        else:
            lines.append("Parmak izi: kayıtlı değil")
    lines.append("Kaynak kimliği ve parmak izi yazılır.")
    return "\n".join(lines)


def source_license_text(sources, note):
    lines = [source_note(sources), _license(note)]
    return "\n".join(lines)


def _license(note):
    raw = _clip(note)
    if not raw:
        return "Lisans notu kayıtlı değil. Lisans uydurulmaz."
    if SECRET_KEY.search(raw) or LOCATION.search(raw) or reason(raw):
        return "Lisans notu geçersiz. Not uydurulmaz."
    return "Lisans notu: " + raw


def _clip(value):
    return str(value or "").replace("\n", " ").strip()[:500]
