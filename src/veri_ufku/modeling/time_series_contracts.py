"""Lightweight declarative settings; no model libraries in the GUI."""

from dataclasses import asdict, dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from veri_ufku.storage.project_model import ProjectError


@dataclass(frozen=True)
class TimeSeriesSpec:
    date: str
    measurement: str
    group: str = ""
    frequency: str = "D"
    timezone: str = ""
    resample: bool = False
    aggregation: str = "none"
    horizon: int = 3
    test_periods: int = 6
    folds: int = 3
    seasonal_period: int = 0
    window: int = 3
    model: str = "level"
    advanced: dict | None = None

    @classmethod
    def from_dict(cls, value):
        try:
            if not isinstance(value, dict) or set(value) - set(
                cls.__dataclass_fields__
            ):
                raise ValueError
            spec = cls(**value)
            spec.validate()
            return spec
        except (ValueError, TypeError) as error:
            raise ProjectError("Zaman serisi ayarları geçersiz.") from error

    def data(self):
        data = asdict(self)
        if self.advanced is None:
            data.pop("advanced")
        return data

    def validate(self, columns=None):
        if self.advanced is not None:
            if (
                isinstance(self.advanced, dict)
                and self.advanced.get("family") == "signal"
            ):
                from veri_ufku.modeling.signal_contracts import SignalSpec

                SignalSpec.from_dict(self.advanced, self, columns)
                return
            from veri_ufku.modeling.temporal_contracts import TemporalSpec

            TemporalSpec.from_dict(self.advanced, self, columns)

        if self.frequency not in ("h", "D", "W-MON", "MS") or self.model not in (
            "none",
            "level",
            "trend",
            "seasonal",
        ):
            raise ProjectError("Desteklenmeyen sıklık veya tahmin modeli.")
        if type(self.resample) is not bool or self.aggregation not in (
            "none",
            "sum",
            "mean",
        ):
            raise ProjectError("Yeniden örnekleme/agregasyon seçimini kontrol edin.")
        if self.resample != (self.aggregation != "none"):
            raise ProjectError(
                "Yeniden örnekleme için toplam veya ortalamayı açıkça seçin."
            )
        for key, low, high in (
            ("horizon", 1, 60),
            ("test_periods", 1, 120),
            ("folds", 2, 5),
            ("seasonal_period", 0, 366),
            ("window", 2, 60),
        ):
            v = getattr(self, key)
            if type(v) is not int or not low <= v <= high:
                raise ProjectError(f"{key}: {low}–{high} aralığında tam sayı gerekli.")
        if self.seasonal_period == 1 or self.test_periods < self.horizon:
            raise ProjectError(
                "Mevsim dönemi 0 veya ≥2; final aralık tahmin ufkundan kısa olamaz."
            )
        if self.model == "seasonal" and self.seasonal_period < 2:
            raise ProjectError("Mevsimsel model için dönem ≥2 seçin.")
        if not all(
            isinstance(v, str)
            for v in (self.date, self.measurement, self.group, self.timezone)
        ):
            raise ProjectError("Tarih/ölçüm/grup/saat dilimi seçimi geçersiz.")
        if self.timezone:
            try:
                ZoneInfo(self.timezone)
            except (ZoneInfoNotFoundError, ValueError) as error:
                raise ProjectError(
                    "Geçerli IANA saat dilimi gerekli (ör. Europe/Istanbul)."
                ) from error
        if columns is not None:
            selected = [self.date, self.measurement] + (
                [self.group] if self.group else []
            )
            if len(set(selected)) != len(selected) or not set(selected) <= {
                c["id"] for c in columns
            }:
                raise ProjectError("Farklı tarih, ölçüm ve isteğe bağlı grup seçin.")

    @property
    def minimum_history(self):
        # Deliberate product floor; also exceeds estimated seasonal initialization needs.
        return max(12, 3 * self.seasonal_period, self.window + 1)
