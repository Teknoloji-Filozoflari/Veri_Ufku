"""Closed section-based report recipe. Numerical findings come only from records."""

import copy
import re
from urllib.parse import urlsplit

from veri_ufku.storage.project_model import ProjectError, entity_id

KINDS = (
    "section",
    "note",
    "method",
    "assumption",
    "dictionary",
    "chart",
    "table",
    "model-card",
    "uncertainty",
    "diagnostic",
    "result",
    "bibliography",
)
RECORD_KINDS = (
    "analysis",
    "baseline",
    "scenario",
    "monitoring",
    "learning_lab",
    "profile",
    "quality",
    "time_series",
    "neural",
)
FORMATS = ("md", "html", "pdf", "zip")
LIMITATIONS = [
    "Bulgular seçilen immutable kayıtların değerleridir; bu rapor analiz/modeli yeniden hesaplamaz.",
    "Keşifsel/doğrulayıcı sınıfı kullanıcı beyanıdır; confirmatory seçmek tasarımın geçerliliğini kanıtlamaz.",
    "Kullanıcı notu/yorum/varsayım manuel metindir; doğrulanmış sayısal bulgu veya nedensel etki diye etiketlenmez.",
    "Eksik metrik, belirsizlik veya tanılama üretilmez; not_recorded olarak görünür.",
    "Redaction desen ve açık ColumnId seçimine dayanır; anonimlik veya bütün serbest metindeki sırları bulma garantisi değildir.",
    "Statik grafikte örnekleme/filtre/caption bağlamı korunur; kaynak değişimi eski raporu güncel kanıt yapmaz.",
    "Markdown/HTML/PDF bağımsız dosyada attachment bağlantıları yalnız paketle aynı dizine açıldığında çalışır; ZIP taşınabilir tam teslimdir.",
    "PDF yerel A4 Türkçe font kullanır; HTML/Markdown/PDF düzenleri birebir aynı değildir. DOCX/local LLM/remote service desteklenmiyor.",
]


def text(v, maximum=2000):
    if not isinstance(v, str) or not v.strip() or len(v) > maximum:
        raise ProjectError("Rapor metin alanı boş veya sınırı aşıyor.")


def recipe(raw):
    if not isinstance(raw, dict) or set(raw) != {
        "title",
        "protocol",
        "protocol_note",
        "blocks",
        "masked_columns",
        "allow_graphics",
    }:
        raise ProjectError("ReportSpec/v1 kapalı alanlarını kullanın.")
    v = copy.deepcopy(raw)
    text(v["title"], 200)
    text(v["protocol_note"])
    if (
        v["protocol"] not in ("exploratory", "confirmatory")
        or type(v["allow_graphics"]) is not bool
    ):
        raise ProjectError(
            "Protocol exploratory/confirmatory ve allow_graphics boolean olmalı."
        )
    if (
        not isinstance(v["masked_columns"], list)
        or len(v["masked_columns"]) > 256
        or len(set(v["masked_columns"])) != len(v["masked_columns"])
    ):
        raise ProjectError("Maskelenecek ColumnId listesi geçersiz.")
    for col in v["masked_columns"]:
        entity_id(col, "col")
    if not isinstance(v["blocks"], list) or not 1 <= len(v["blocks"]) <= 32:
        raise ProjectError("Rapor1..32blok içermeli.")
    for b in v["blocks"]:
        if (
            not isinstance(b, dict)
            or not {"kind", "title"} <= set(b)
            or set(b)
            - {
                "kind",
                "title",
                "text",
                "version",
                "record",
                "columns",
                "rows",
                "caption",
                "code_column",
                "references",
            }
        ):
            raise ProjectError("Rapor blok alanları geçersiz.")
        if b["kind"] not in KINDS:
            raise ProjectError("Blok türü desteklenmiyor.")
        text(b["title"], 200)
        kind = b["kind"]
        allowed = {"kind", "title"}
        if kind in ("section", "note", "assumption"):
            allowed.add("text")
            text(b.get("text"))
        elif kind in ("dictionary", "table"):
            allowed.update(("version", "columns"))
            entity_id(b.get("version"), "dv")
            if (
                not isinstance(b.get("columns"), list)
                or not 1 <= len(b["columns"]) <= 16
                or len(set(b["columns"])) != len(b["columns"])
            ):
                raise ProjectError("Tablo/sözlük1..16açık ColumnId seçimi ister.")
            for c in b["columns"]:
                entity_id(c, "col")
            if kind == "table":
                allowed.update(("rows", "caption"))
                if type(b.get("rows")) is not int or not 1 <= b["rows"] <= 100:
                    raise ProjectError(
                        "Tablo önizleme1..100row; açık örnek, tam veri export değil."
                    )
                text(b.get("caption"), 1000)
            if "code_column" in b:
                allowed.add("code_column")
                entity_id(b["code_column"], "col")
                if kind != "dictionary" or b["code_column"] not in b["columns"]:
                    raise ProjectError(
                        "Reference-only script/notebook yalnız dictionary seçili numeric profile kolonu."
                    )
        elif kind == "bibliography":
            allowed.add("references")
            if not isinstance(b.get("references"), list) or len(b["references"]) > 20:
                raise ProjectError("Kaynakça en fazla20açık referans.")
            for ref in b["references"]:
                if not isinstance(ref, dict) or set(ref) != {"title", "url"}:
                    raise ProjectError("Kaynakça title/url ister.")
                text(ref["title"], 200)
                text(ref["url"], 1000)
                u = urlsplit(ref["url"])
                if (
                    u.scheme != "https"
                    or not u.hostname
                    or u.username
                    or u.password
                    or u.query
                    or u.fragment
                    or any(c.isspace() or c in '<>"\\' for c in ref["url"])
                ):
                    raise ProjectError(
                        "Kaynakça yalnız credentials/query/fragment içermeyen HTTPS atfı; ağ açılmaz."
                    )
        else:
            allowed.add("record")
            entity_id(b.get("record"), "result")
            if kind == "chart":
                allowed.add("caption")
                text(b.get("caption"), 1000)
        if set(b) != allowed:
            raise ProjectError("Blok türü için alanlar eksik/uyumsuz.")
    return v


def template(name="scientific"):
    if name not in ("scientific", "brief"):
        raise ProjectError("Report preset mevcut değil.")
    return dict(
        title="Veri_Ufku · Bilimsel rapor",
        protocol="exploratory",
        protocol_note="Keşifsel inceleme; analiz birimi, seçim ve test kullanımını kayıtlı sonuçlarla değerlendirin.",
        blocks=[
            dict(
                kind="section",
                title="Araştırma sorusu",
                text="Soruyu ve analiz birimini kullanıcı olarak açıklayın.",
            ),
            dict(
                kind="note",
                title="Yorum ve sınırlamalar",
                text="Bulguyu yorumdan ayırın; nedensel çıkarım varsayımlarını açıkça yazın.",
            ),
            dict(kind="bibliography", title="Kaynakça", references=[]),
        ][: 3 if name == "scientific" else 2],
        masked_columns=[],
        allow_graphics=False,
    )


def redact(value, masked_names=()):
    """Data-only projection with visible reasons; never returns original secrets."""
    from veri_ufku.exports.repro import LOCATION, SECRET_KEY, SENSITIVE

    changes = []

    def clean(v, path):
        if isinstance(v, dict):
            out = {}
            for key, item in v.items():
                label = str(key)
                if SECRET_KEY.search(label) or LOCATION.search(label):
                    safe_key = "redacted-field-" + str(len(out))
                    changes.append(
                        dict(field=path + "." + safe_key, reason="secret/location key")
                    )
                    out[safe_key] = "[redacted]"
                else:
                    out[label] = clean(item, path + "." + label)
            return out
        if isinstance(v, (list, tuple)):
            return [clean(x, path + "." + str(i)) for i, x in enumerate(v)]
        if isinstance(v, str):
            if (
                SENSITIVE.search(v)
                or (
                    LOCATION.search(v)
                    and not (
                        path.endswith(".url")
                        and v.startswith("https://")
                        and not urlsplit(v).query
                        and not urlsplit(v).username
                    )
                )
                or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", v)
                or any(
                    n and re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", v)
                    for n in masked_names
                )
            ):
                changes.append(
                    dict(
                        field=path,
                        reason="secret/location/personal pattern or selected sensitive name",
                    )
                )
                return "[redacted]"
        return v

    return clean(value, "report"), changes
