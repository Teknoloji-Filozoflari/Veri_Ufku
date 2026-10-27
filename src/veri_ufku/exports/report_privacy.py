"""Report-table privacy preview. Findings name a column, never a cell value."""

import re

from veri_ufku.exports.repro import SECRET_KEY
from veri_ufku.exports.share_privacy import reason

PERSONAL_NAME = re.compile(
    r"e-?mail|e-?posta|eposta|telefon|phone|gsm|adres|address|soyad|"
    r"tc.?kimlik|kimlik.?no|iban",
    re.I,
)


def column_findings(names, values, limit=20):
    """Classify columns from names and a bounded sample. Matched text is dropped."""
    findings = []
    for name in names:
        why = _name_reason(name)
        if not why:
            for value in list(values.get(name) or [])[:limit]:
                why = reason(value if isinstance(value, str) else "")
                if why:
                    break
        if why:
            findings.append({"name": str(name), "reason": why})
    return findings


def privacy_note(findings, include):
    if not findings:
        return (
            "Kişisel sütun adayı yok. Tarama e-posta, telefon ve gizli anahtar "
            "deseniyle sınırlıdır. Eksiksiz tespit değildir. Değer yazılmaz."
        )
    listed = ", ".join(f"{item['name']} ({item['reason']})" for item in findings)
    if include:
        return (
            "Kişisel sütunlar açık seçimle rapora alındı: "
            + listed
            + ". Bu bir anonimlik garantisi değildir."
        )
    return "Kişisel sütunlar rapora alınmadı: " + listed + ". Hücre değeri yazılmadı."


def _name_reason(name):
    if SECRET_KEY.search(str(name)) or PERSONAL_NAME.search(str(name)):
        return "sensitive-name"
    return None
