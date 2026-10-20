"""Bounded data-only sharing scanner. Findings never contain original values."""

import re

from veri_ufku.exports.repro import LOCATION, SECRET_KEY, SENSITIVE
from veri_ufku.storage.project_model import ProjectError

EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<![\w-])\+?\d[\d ()]{8,}\d(?![\w-])")
IDENTITY = re.compile(
    r"^(?:(?:row|sr|col|dv|source|snapshot|result|operation):)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
LIMITATIONS = [
    "Yerel aktarım; yayınlama, sunucu, identity/permissions veya ortak yazma hizmeti değildir.",
    "Tarama secret anahtar/desen ve email/telefon/explicit hassas terim kapsamındadır; anonimlik/eksiksiz PII tespiti garantisi yoktur.",
    "Tam kopya yalnız mevcut committed mantıksal proje ve manifest artifact setidir; geçmiş SQLite/ACTIVE/recovery/staging/keyring ve dış dosya yolları taşınmaz.",
    "Tam kopyada taranamayan binary/image/model/archive artifact varsa işlem kapalıdır; binary içeriği taranmış gibi sunulmaz.",
    "Redacted örnek ilk N satırdır; bütün metin/kategori ve seçilmeyen sayısallar maskelenir. RowId/SourceRecordId/ColumnId kökenle birlikte korunur.",
    "Metadata-only ve redacted örnek inceleme içindir; düzenlenebilir özgün proje veya tam yeniden üretim değildir.",
    "Diff hash/kimlik değişimini gösterir; iki farklı kökendeki eşit kimlikler eşdeğer varlık sayılmaz. Otomatik merge/last-write-wins yoktur.",
    "Tam kopya yalnız yeni yerel klasöre ayrı fork olarak açılır; mevcut proje üzerine yazılmaz. Eski yorum özgün subject/hash bağlamında kalır.",
    "Tek yazıcı file lock korunur; unsupported concurrent edit read-only/ret ile karşılanır. Paylaşımlı ağ klasöründeki SQLite çok kullanıcılı DB değildir.",
    "Hash bütünlük içindir; göndericiyi doğrulamaz, yeniden imzalanmış kötü niyetli pakete karşı kimlik/auth kanıtı değildir.",
]


def terms(raw):
    if (
        not isinstance(raw, list)
        or len(raw) > 32
        or any(not isinstance(v, str) or not 1 <= len(v) <= 80 for v in raw)
    ):
        raise ProjectError(
            "Hassas terimler1..80karakter, en fazla32adet; yalnız geçici taramada kullanılır."
        )
    return raw


def reason(value, sensitive=()):
    if not isinstance(value, str) or IDENTITY.fullmatch(value):
        return None
    if SENSITIVE.search(value):
        return "secret-pattern"
    if EMAIL.search(value) or PHONE.search(value):
        return "pii-pattern"
    if any(t and t.casefold() in value.casefold() for t in sensitive):
        return "explicit-sensitive-term"
    return None


def sensitive_key(key, value):
    # This exact closed checklist flag is a boolean decision, never a credential.
    return bool(SECRET_KEY.search(key)) and not (
        key == "secret-pii-reviewed" and type(value) is bool
    )


def sanitize(value, sensitive=(), findings=None, path="metadata"):
    findings = [] if findings is None else findings
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            key = str(k)
            if sensitive_key(key, v) and v not in (None, "", False, [], {}):
                safe = "redacted-field-" + str(len(out))
                findings.append(dict(field=path + "." + safe, reason="secret-key"))
                out[safe] = "[redacted]"
            else:
                safe = (
                    "redacted-label-" + str(len(out))
                    if reason(key, sensitive) or LOCATION.search(key)
                    else key
                )
                if safe != key:
                    findings.append(
                        dict(field=path + "." + safe, reason="sensitive-key")
                    )
                out[safe] = sanitize(v, sensitive, findings, path + "." + safe)
        return out
    if isinstance(value, list):
        return [
            sanitize(v, sensitive, findings, path + "." + str(i))
            for i, v in enumerate(value)
        ]
    why = reason(value, sensitive)
    if isinstance(value, str) and (why or LOCATION.search(value)):
        findings.append(dict(field=path, reason=why or "external-location"))
        return "[redacted]"
    return value


def scan(value, sensitive=(), path="payload"):
    findings = []

    def visit(v, p):
        if len(findings) > 1000:
            raise ProjectError("Tarama1000bulgu sınırı; daha dar kapsam seçin.")
        if isinstance(v, dict):
            for i, (k, x) in enumerate(v.items()):
                # Field paths contain ordinals, never sensitive original keys/values.
                if sensitive_key(str(k), x) and x not in (None, "", False, [], {}):
                    findings.append(
                        dict(field=p + ".field" + str(i), reason="secret-key")
                    )
                if reason(str(k), sensitive):
                    findings.append(
                        dict(field=p + ".field" + str(i), reason="sensitive-key")
                    )
                visit(x, p + ".field" + str(i))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                visit(x, p + "." + str(i))
        elif why := reason(v, sensitive):
            findings.append(dict(field=p, reason=why))
        elif (
            isinstance(v, str)
            and LOCATION.search(v)
            and not re.fullmatch(r"/unresolved-source/[0-9a-f-]{36}", v)
        ):
            findings.append(dict(field=p, reason="external-location"))

    visit(value, path)
    return findings
