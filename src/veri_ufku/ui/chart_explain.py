"""Chart sentences built only from numbers already in the result."""

import math
from decimal import Decimal

CORE_KINDS = frozenset(
    {"histogram", "box", "bar", "line", "scatter", "missing", "correlation"}
)
RELATION_KINDS = frozenset({"scatter", "correlation", "line"})


def chart_explanation(result):
    """Return four template sentences. Unsupported kinds do not invent a statistic."""
    result = result or {}
    kind = str((result.get("spec") or {}).get("kind") or "")
    used = result.get("used_n")
    points = result.get("points") or []
    if kind not in CORE_KINDS or not isinstance(used, int) or not points:
        return _empty(
            "Bu tür için açıklama şablonu yok. Sayı uydurulmaz."
            if kind
            else "Grafik yok. Açıklama üretilmez."
        )
    details = result.get("details") or {}
    if kind == "histogram":
        text = _histogram(result, points, used, details)
    elif kind == "box":
        text = _box(points, used)
    elif kind == "bar":
        text = _bar(points, used)
    elif kind == "line":
        text = _line(points, used)
    elif kind == "scatter":
        text = _scatter(result, points, used, details)
    elif kind == "missing":
        text = _missing(points, used)
    else:
        text = _correlation(points, used)
    if text is None:
        return _empty("Bu sonuçtaki sayılar şablona uymadı. Sayı uydurulmaz.")
    if kind in RELATION_KINDS and "Nedensellik kanıtlamaz" not in text["caution"]:
        text["caution"] += " Nedensellik kanıtlamaz."
    text["ready"] = True
    return text


def _empty(see):
    return {"ready": False, "see": see, "read": "", "caution": "", "next": ""}


def _fmt(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, float) and math.isfinite(value):
        return f"{value:.4g}"
    return None


def _label(value):
    text = str(value or "").replace("\n", " ").strip()
    return text[:80] or "adsız"


def _peak(points, key):
    usable = [point for point in points if _fmt(point.get(key)) is not None]
    if not usable:
        return None
    return max(usable, key=lambda point: point.get(key))


def _summary_pair(result):
    rows = result.get("summary") or []
    lines = []
    for row in rows[:2]:
        numeric = (row or {}).get("numeric") or {}
        mean = _fmt(numeric.get("mean"))
        if mean is None:
            continue
        name = _label(row.get("column_name") or row.get("name"))
        lines.append(f"{name} ortalama {mean}")
    return lines


def _histogram(result, points, used, details):
    peak = _peak(points, "n")
    if peak is None:
        return None
    excluded = details.get("excluded_rows")
    excluded_text = _fmt(excluded) or "0"
    pair = _summary_pair(result)
    read = (
        "Nasıl yorumlamalıyım? " + " · ".join(pair) + "."
        if pair
        else f"Nasıl yorumlamalıyım? Aralık sayısı {len(points)}."
    )
    return {
        "see": (
            f"Ne görüyorum? {used} kayıt, {len(points)} aralık. "
            f"En yoğun aralık n={_fmt(peak.get('n'))}."
        ),
        "read": read,
        "caution": (
            f"Neye dikkat etmeliyim? Dışlanan kayıt {excluded_text}. "
            "Aralık yüksekliği silme kararı değildir."
        ),
        "next": (
            f"Sonraki adım: aynı {used} kayıtta kutu grafiğine bakın. Veri değişmez."
        ),
    }


def _box(points, used):
    point = points[0]
    q1, mid, q3 = _fmt(point.get("q1")), _fmt(point.get("y")), _fmt(point.get("q3"))
    n = _fmt(point.get("n")) or str(used)
    if not (q1 and mid and q3):
        return None
    width = None
    if isinstance(point.get("q1"), (int, float)) and isinstance(
        point.get("q3"), (int, float)
    ):
        width = _fmt(point["q3"] - point["q1"])
    return {
        "see": f"Ne görüyorum? n={n}. Medyan {mid}, çeyrekler {q1} ve {q3}.",
        "read": (
            f"Nasıl yorumlamalıyım? Çeyrekler arası açıklık {width}."
            if width
            else f"Nasıl yorumlamalıyım? Medyan {mid}."
        ),
        "caution": (
            f"Neye dikkat etmeliyim? Bıyıklar {_fmt(point.get('whislo')) or 'yok'}–"
            f"{_fmt(point.get('whishi')) or 'yok'}. Aday, silme kararı değildir."
        ),
        "next": f"Sonraki adım: aykırı aday Hazırla önizlemesindedir. n={n}.",
    }


def _bar(points, used):
    peak = _peak(points, "y") or _peak(points, "n")
    if peak is None:
        return None
    return {
        "see": (
            f"Ne görüyorum? {len(points)} sütun. En yüksek {_label(peak.get('label'))}: "
            f"y={_fmt(peak.get('y')) or _fmt(peak.get('n'))}, n={_fmt(peak.get('n'))}."
        ),
        "read": f"Nasıl yorumlamalıyım? Karşılaştırılan sütun sayısı {len(points)}.",
        "caution": (
            f"Neye dikkat etmeliyim? Yükseklik bu {used} kaydın özetidir, "
            "nedensel etki değildir."
        ),
        "next": f"Sonraki adım: grup farkı İstatistik bölümündedir. Kayıt {used}.",
    }


def _line(points, used):
    first, last = points[0], points[-1]
    start, end = _fmt(first.get("y")), _fmt(last.get("y"))
    if start is None or end is None:
        return None
    delta = None
    if isinstance(first.get("y"), (int, float)) and isinstance(
        last.get("y"), (int, float)
    ):
        delta = _fmt(last["y"] - first["y"])
    return {
        "see": (
            f"Ne görüyorum? {len(points)} nokta. İlk {_label(first.get('label'))} y={start}, "
            f"son {_label(last.get('label'))} y={end}."
        ),
        "read": (
            f"Nasıl yorumlamalıyım? İlk ve son değer farkı {delta}."
            if delta
            else f"Nasıl yorumlamalıyım? Nokta sayısı {len(points)}."
        ),
        "caution": f"Neye dikkat etmeliyim? Nedensellik kanıtlamaz. Kullanılan kayıt {used}.",
        "next": f"Sonraki adım: bulguyu nota ekleyin. Nokta sayısı {len(points)}.",
    }


def _scatter(result, points, used, details):
    pair = _summary_pair(result)
    omitted = _fmt(details.get("omitted_rows"))
    caution = f"Neye dikkat etmeliyim? Nedensellik kanıtlamaz. Kullanılan kayıt {used}."
    if omitted is not None:
        caution += f" Dışarıda kalan {omitted}."
    return {
        "see": f"Ne görüyorum? {len(points)} nokta, kullanılan kayıt {used}.",
        "read": (
            "Nasıl yorumlamalıyım? " + " · ".join(pair) + "."
            if pair
            else f"Nasıl yorumlamalıyım? Çizilen nokta sayısı {len(points)}."
        ),
        "caution": caution,
        "next": f"Sonraki adım: ilişki metni nedensellik kanıtlamaz. Nokta {len(points)}.",
    }


def _missing(points, used):
    peak = _peak(points, "y")
    if peak is None:
        return None
    nulls = _fmt(peak.get("null_count")) or "0"
    return {
        "see": (
            f"Ne görüyorum? {len(points)} sütun. En yüksek eksik {_label(peak.get('label'))}: "
            f"null={nulls}, oran={_fmt(peak.get('y'))}."
        ),
        "read": f"Nasıl yorumlamalıyım? Oran {used} kayıt içindedir.",
        "caution": (
            f"Neye dikkat etmeliyim? {used} kayıtta boş metin null sayılmaz. "
            "Oran silme kararı değildir."
        ),
        "next": f"Sonraki adım: Hazırla önizlemesi. Null sayısı {nulls}.",
    }


def _correlation(points, used):
    pairs = [
        point
        for point in points
        if _fmt(point.get("coefficient")) is not None
        and point.get("x") != point.get("y")
    ]
    if pairs:
        best = max(pairs, key=lambda point: abs(point["coefficient"]))
        see = (
            f"Ne görüyorum? {_label(best.get('label'))} katsayı="
            f"{_fmt(best.get('coefficient'))}, n={_fmt(best.get('n')) or used}."
        )
    else:
        see = (
            f"Ne görüyorum? {len(points)} hücre. Tanımlı katsayı yok. "
            f"Kullanılan kayıt {used}."
        )
    return {
        "see": see,
        "read": f"Nasıl yorumlamalıyım? Hücre sayısı {len(points)}.",
        "caution": f"Neye dikkat etmeliyim? Nedensellik kanıtlamaz. Kullanılan kayıt {used}.",
        "next": f"Sonraki adım: katsayıyı nota yazın. Hücre {len(points)}.",
    }
