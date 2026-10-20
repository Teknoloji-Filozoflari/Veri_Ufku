"""Closed local monitoring recipe. No executable callbacks, URLs or auth values."""

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime

from veri_ufku.storage.project_model import ProjectError

LIMITATIONS = [
    "Data drift, concept drift veya performans düşüşü kanıtı değildir; labels yoksa başarı metriği yok.",
    "KS bağımsız sürekli örneklem varsayar; ties/bağımlılıkta p sunulmaz. Büyük n küçük farkı anlamlı gösterebilir.",
    "Çok kolon/tekrarlı pencere false-positive yaratır; Bonferroni yalnız bu rapordaki geçerli KS testlerine uygulanır.",
    "PSI referans quantile binleri ve smoothing'e bağlı betimsel eşiktir; evrensel anlamlılık testi değildir.",
    "Wasserstein kaynak birimindedir; kategoride JS distance [0,1] destek üzerinde hesaplanır.",
    "Brier/log-loss yalnız kalibrasyonu ölçmez. Reliability binleri ve n birlikte okunmalı; küçük n güvenilmezdir.",
    "Gecikmeli label alt kümesi temsil yanlılığı taşıyabilir; shadow skor gerçek kullanıcı faydası veya nedensellik değildir.",
    "Alarm yeniden eğitim/deploy yapmaz. Yeni eğitim ayrı açık run; rollback yalnız yerel model referansını değiştirir.",
]


def instant(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ProjectError("UTC offset içeren ISO timestamp gerekli.")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError()
        return dt.timestamp()
    except (ValueError, OverflowError):
        raise ProjectError("Timezone içeren geçerli ISO timestamp gerekli.") from None


@dataclass(frozen=True)
class MonitorSpec:
    reference: str
    window: str
    features: list[dict] = field(default_factory=list)
    champion: str = ""
    challenger: str = ""
    use_champion_route: bool = False
    reference_mapping: dict = field(default_factory=dict)
    window_mapping: dict = field(default_factory=dict)
    # Explicit business key + namespace; RowId from another source is never guessed.
    labels: str = ""
    reference_key: str = ""
    window_key: str = ""
    label_key: str = ""
    label_value: str = ""
    label_arrived: str = ""
    key_namespace: str = ""
    event_time: str = ""
    window_start: str = ""
    window_end: str = ""
    as_of: str = ""
    independent: bool = False
    bins: int = 10
    min_n: int = 20
    psi_threshold: float = 0.2
    ks_effect_threshold: float = 0.1
    alpha: float = 0.05
    js_threshold: float = 0.1
    wasserstein_threshold: float = 1.0
    missing_threshold: float = 0.05
    label_delay_seconds: float = 86400.0
    performance_delta: float = 0.05
    calibration_delta: float = 0.05

    @classmethod
    def from_dict(cls, value):
        try:
            if not isinstance(value, dict):
                raise TypeError()
            s = cls(**value)
        except (TypeError, ValueError):
            raise ProjectError("Monitoring recipe şeması geçersiz.") from None
        for name in (
            "reference",
            "window",
            "champion",
            "challenger",
            "labels",
            "reference_key",
            "window_key",
            "label_key",
            "label_value",
            "label_arrived",
            "event_time",
            "key_namespace",
        ):
            v = getattr(s, name)
            if (
                not isinstance(v, str)
                or len(v) > 160
                or any(c in v for c in ("/", "\\", "\n", "\r"))
            ):
                raise ProjectError(
                    "Recipe kimliği/namespace geçersiz; URL/path/secret kabul edilmez."
                )
        if (
            not s.reference
            or not s.window
            or s.reference == s.window
            or type(s.independent) is not bool
        ):
            raise ProjectError("Ayrı referans ve pencere dataset sürümü gerekli.")
        if not isinstance(s.features, list) or not 1 <= len(s.features) <= 32:
            raise ProjectError("1..32 açık feature eşlemesi gerekli.")
        for f in s.features:
            if (
                not isinstance(f, dict)
                or set(f) != {"reference", "window", "kind", "continuous"}
                or f["kind"] not in ("numeric", "categorical")
                or type(f["continuous"]) is not bool
                or not all(
                    isinstance(f[k], str) and f[k] for k in ("reference", "window")
                )
            ):
                raise ProjectError("Feature ColumnId/kind/continuous şeması geçersiz.")
        for side in ("reference", "window"):
            if len({f[side] for f in s.features}) != len(s.features):
                raise ProjectError("Tekrarlı feature eşlemesi reddedildi.")
        for m in (s.reference_mapping, s.window_mapping):
            if (
                not isinstance(m, dict)
                or len(m) > 256
                or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in m.items()
                )
            ):
                raise ProjectError("Model ColumnId eşlemesi geçersiz.")
        if (
            type(s.use_champion_route) is not bool
            or s.use_champion_route
            and s.champion
        ):
            raise ProjectError(
                "Route seçimi bool ve explicit champion ile ayrı olmalı."
            )
        if s.challenger and (
            not (s.champion or s.use_champion_route) or s.challenger == s.champion
        ):
            raise ProjectError("Shadow için farklı champion/challenger gerekli.")
        if s.labels and (
            not (s.champion or s.use_champion_route)
            or not all(
                (
                    s.window_key,
                    s.label_key,
                    s.label_value,
                    s.label_arrived,
                    s.key_namespace,
                )
            )
        ):
            raise ProjectError(
                "Labels için model, açık namespace/key/value/arrival gerekli."
            )
        if not s.labels and any((s.label_key, s.label_value, s.label_arrived)):
            raise ProjectError("Labels dataset seçilmedi.")
        if (
            type(s.bins) is not int
            or not 2 <= s.bins <= 20
            or type(s.min_n) is not int
            or not 2 <= s.min_n <= 10000
        ):
            raise ProjectError("Bin2..20 ve min_n2..10000 gerekli.")
        for name in (
            "psi_threshold",
            "ks_effect_threshold",
            "alpha",
            "js_threshold",
            "wasserstein_threshold",
            "missing_threshold",
            "label_delay_seconds",
            "performance_delta",
            "calibration_delta",
        ):
            v = getattr(s, name)
            if type(v) not in (float, int) or not math.isfinite(v) or v <= 0:
                raise ProjectError("Pozitif sonlu monitoring threshold gerekli.")
        if not 0 < s.alpha < 1 or any(
            getattr(s, n) > 1
            for n in ("ks_effect_threshold", "js_threshold", "missing_threshold")
        ):
            raise ProjectError("Oran threshold [0,1] dışında.")
        if not instant(s.window_start) < instant(s.window_end) <= instant(s.as_of):
            raise ProjectError("Pencere [start,end) ve end≤as_of gerekli.")
        return s

    def data(self):
        return asdict(self)
