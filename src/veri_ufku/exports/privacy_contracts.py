"""Closed, human-reviewed export policies; no automatic anonymous-data claims."""

import copy
import re

from veri_ufku.exports.share_privacy import scan
from veri_ufku.storage.project_model import ProjectError, entity_id

LIMITATIONS = [
    "PII bulguları adaydır; kolon adı/desen taraması bütün hassas veriyi bulmaz. Kullanıcı doğrulaması ground truth veya hukuki uygunluk kanıtı değildir.",
    "Masking/pseudonymization anonimlik garantisi değildir. Quasi-identifier, nadir kombinasyon, dış veri ve kaynak referansları yeniden tanımlama/linkage riski taşır.",
    "HMAC-SHA256 standart keyed pseudonymization; aynı proje/ColumnId/key ile aynı değer eşleşir. Frekans/linkage korunur; key sahibi sözlük saldırısı yapabilir.",
    "Kaynak dataset, geçmiş snapshot, model ve rapor değişmez. Bu çıktı yalnız seçili kolonların tam bounded satır projeksiyonudur; internal RowId/SourceRecordId dışa aktarılmaz.",
    "Canlı ProjectStore/SQLite/cache şifreli değildir. Fernet yalnız explicit küçük export paketini şifreler; RAM, açık oturum, swap, backup veya plaintext kaynak kopyasını korumaz.",
    "Keys yalnız Linux Secret Service keyring; dosya/env/plaintext fallback yok. Key kaybı encrypted export açmayı ve aynı pseudonymi üretmeyi engeller; uygulamada escrow/backdoor yok. Key oluşturma servis işlemi iptalden önce tamamlanmış olabilir; tekrar üzerine yazılmaz.",
    "Yerel application history/append-only kuralı güçlü nonrepudiation veya değiştirilemez audit değildir; aynı kullanıcı dosyaları değiştirebilir.",
    "Retention süre dolması otomatik silme değildir. Referanslı/current/historical artifact ve dış kaynaklar korunur; physical project purge/secure erase desteklenmiyor.",
    "Cache cleanup yalnız idle, sahiplik işaretli privacy scratch dosyaları; önizleme/hash onayı gerekir. SSD/snapshot/backup üzerinde güvenli silme garantisi yoktur.",
    "Differential privacy mevcut değil: doğrulanmış mechanism/sensitivity ve toplam budget accountant yok; noise veya hash DP sayılmaz.",
]
STRATEGIES = ("mask", "drop", "pseudonym", "keep")
CLASSES = ("pii", "not-pii", "uncertain")


def reference(v):
    if not isinstance(v, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,79}", v):
        raise ProjectError(
            "Keyring referansı1..80harf/rakam/_.-; anahtar değeri kabul edilmez."
        )
    return v


def policy(raw):
    if not isinstance(raw, dict) or set(raw) != {
        "version",
        "rules",
        "reviewer",
        "rationale",
        "key_ref",
    }:
        raise ProjectError(
            "PrivacyPolicy/v1 version/rules/reviewer/rationale/key_ref alanları gerekli."
        )
    entity_id(raw["version"], "dv")
    for k, maximum in (("reviewer", 100), ("rationale", 1000)):
        if (
            not isinstance(raw[k], str)
            or not 1 <= len(raw[k]) <= maximum
            or scan(raw[k])
        ):
            raise ProjectError(
                "İnceleyen/gerekçe boş, uzun veya hassas desen içeriyor; maskeleyin."
            )
    if not isinstance(raw["key_ref"], str):
        raise ProjectError("Key referansı metin olmalı.")
    if raw["key_ref"]:
        reference(raw["key_ref"])
    rules = raw["rules"]
    if (
        not isinstance(rules, list)
        or not 1 <= len(rules) <= 16
        or any(
            not isinstance(r, dict) or not isinstance(r.get("column"), str)
            for r in rules
        )
        or len({r.get("column") for r in rules}) != len(rules)
    ):
        raise ProjectError("Privacy1..16unique ColumnId kuralı gerekli.")
    for r in rules:
        if (
            not isinstance(r, dict)
            or set(r) != {"column", "classification", "strategy"}
            or r["classification"] not in CLASSES
            or r["strategy"] not in STRATEGIES
        ):
            raise ProjectError("Her kolon classification ve strategy kararı ister.")
        entity_id(r["column"], "col")
        if r["strategy"] == "keep" and r["classification"] != "not-pii":
            raise ProjectError(
                "PII/uncertain kolon keep olamaz; mask/drop/pseudonym seçin veya yanlış pozitifi gerekçelendirin."
            )
    if all(r["strategy"] == "drop" for r in rules):
        raise ProjectError("Bütün kolonları drop eden export desteklenmiyor.")
    if any(r["strategy"] == "pseudonym" for r in rules) and not raw["key_ref"]:
        raise ProjectError("Pseudonym için Secret Service key referansı gerekli.")
    return copy.deepcopy(raw)
