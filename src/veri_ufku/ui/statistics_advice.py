"""Recommendation card from a finished preflight or analysis. No invented counts."""

from veri_ufku.statistics.contracts import LABELS

PATHS = frozenset({"independent", "paired", "groups", "categorical", "numeric"})


def statistics_advice(result):
    """Plain-language card. Independence is recorded, never tested here."""
    result = result or {}
    spec = result.get("spec") or {}
    path = spec.get("path")
    used = result.get("used_rows")
    if path not in PATHS or not isinstance(used, int):
        return _empty("Önkontrol yok. Öneri uydurulmaz.")
    if path == "independent":
        body = _independent(result, used)
    elif path == "paired":
        body = _paired(result, used)
    elif path == "groups":
        body = _groups(result, used)
    elif path == "categorical":
        body = _categorical(result, used)
    else:
        body = _numeric(used)
    if body is None:
        return _empty("Bu önkontrol şablona uymadı. Öneri uydurulmaz.")
    question = _clip(spec.get("question")) or "Soru metni yok"
    body["ready"] = True
    body["question"] = f"Soru: {question}. Kullanılan kayıt {used}."
    body["selection"] = _selection(spec, used)
    return body


def _empty(text):
    return {
        "ready": False,
        "question": text,
        "structure": "",
        "suggestion": "",
        "assumption": "",
        "selection": "",
    }


def _clip(value):
    return str(value or "").replace("\n", " ").strip()[:200]


def _counts(result):
    raw = result.get("n")
    if not isinstance(raw, list) or not raw:
        return None
    if not all(isinstance(item, int) for item in raw):
        return None
    return raw


def _selection(spec, used):
    method = spec.get("method") or ""
    label = LABELS.get(method, method or "yöntem seçilmedi")
    mark = "işaretli" if spec.get("independent") else "işaretsiz"
    return (
        f"Seçiminiz: {label}. Bağımsızlık kutusu {mark}. "
        f"Kullanılan kayıt {used}. Bağımsızlık otomatik test edilmedi."
    )


def _independent(result, used):
    counts = _counts(result)
    if counts is None or len(counts) != 2:
        return None
    small = min(counts)
    extra = ""
    if small < 30:
        extra = (
            f" Küçük grup n={small}. Mann-Whitney ayrıca düşünülür; "
            "Welch yerine geçmez."
        )
    listed = " ve ".join(str(item) for item in counts)
    return {
        "structure": f"İki grup. n={listed}. Kullanılan kayıt {used}.",
        "suggestion": (
            "Ortalama sorusu için Welch t-testi önerilir. "
            "Mann-Whitney farklı sorudur: dağılımların sıra karşılaştırması. "
            f"Yöntem p değeriyle seçilmedi.{extra}"
        ),
        "assumption": (
            f"Bağımsızlık otomatik test edilmedi. Kullanılan kayıt {used}. "
            "Varyans eşitliği Welch için şart değildir."
        ),
    }


def _paired(result, used):
    diff = result.get("difference_summary") or {}
    n = diff.get("n")
    if not isinstance(n, int):
        n = used
    return {
        "structure": f"Eş sayısı {n}. Kullanılan kayıt {used}.",
        "suggestion": (
            "Aynı kayıtların tekrarı tasarım sorusudur. Eşleştirilmiş t ortalama "
            f"değişimini sorar. Wilcoxon farklı sorudur. Eş sayısı {n}."
        ),
        "assumption": (f"Bağımsızlık otomatik test edilmedi. Kullanılan kayıt {used}."),
    }


def _groups(result, used):
    counts = _counts(result)
    if counts is None or len(counts) < 3:
        return None
    listed = ", ".join(str(item) for item in counts)
    return {
        "structure": (
            f"Grup sayısı {len(counts)}. n={listed}. Kullanılan kayıt {used}."
        ),
        "suggestion": (
            "ANOVA, Welch ANOVA ve Kruskal-Wallis tek p değerine göre seçilmez. "
            f"Grup karşılaştırmaları ayrıdır. Grup sayısı {len(counts)}."
        ),
        "assumption": (f"Bağımsızlık otomatik test edilmedi. Kullanılan kayıt {used}."),
    }


def _categorical(result, used):
    expected = result.get("expected")
    flat = _flat(expected)
    if not flat:
        return None
    rows = len(expected)
    cols = len(expected[0])
    lowest = min(flat)
    lowest_text = f"{lowest:.4g}" if isinstance(lowest, float) else str(lowest)
    if rows == 2 and cols == 2 and lowest < 5:
        suggestion = (
            f"En küçük beklenen {lowest_text}. 2×2 tabloda Fisher önerilir. "
            "Ki-kare önkoşulu sağlanmıyor."
        )
    elif rows == 2 and cols == 2:
        suggestion = (
            f"En küçük beklenen {lowest_text}. 2×2 tabloda ki-kare beklenen "
            "frekans önkoşulu tutuluyor. Fisher ayrıca durur."
        )
    elif lowest < 5:
        suggestion = (
            f"En küçük beklenen {lowest_text}. {rows}×{cols} tabloda ki-kare "
            "önkoşulu sağlanmıyor. Kesin ve Monte Carlo bu sürümde hesaplanmaz."
        )
    else:
        suggestion = (
            f"En küçük beklenen {lowest_text}. {rows}×{cols} tablo. "
            "Yöntem p değeriyle seçilmedi."
        )
    return {
        "structure": (
            f"Tablo {rows}×{cols}. En küçük beklenen {lowest_text}. "
            f"Kullanılan kayıt {used}."
        ),
        "suggestion": suggestion,
        "assumption": (f"Bağımsızlık otomatik test edilmedi. Kullanılan kayıt {used}."),
    }


def _numeric(used):
    return {
        "structure": f"İki sayısal ölçüm. Kullanılan kayıt {used}.",
        "suggestion": (
            "Pearson doğrusal ilişkiyi, Spearman sıra ilişkisini sorar. "
            f"İlişki nedensellik değildir. Kullanılan kayıt {used}."
        ),
        "assumption": (f"Bağımsızlık otomatik test edilmedi. Kullanılan kayıt {used}."),
    }


def _flat(expected):
    if not isinstance(expected, list) or not expected:
        return None
    values = []
    width = None
    for row in expected:
        if not isinstance(row, list) or not row:
            return None
        if width is None:
            width = len(row)
        if len(row) != width:
            return None
        for item in row:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                return None
            values.append(item)
    return values
