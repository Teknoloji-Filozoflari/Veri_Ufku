"""Phase53 bounded data-only extensions of TimeSeriesSpec, no second registry."""

from dataclasses import asdict, dataclass, field

from veri_ufku.storage.project_model import ProjectError

DIAGNOSTICS = ("decomposition", "stl", "acf", "pacf", "stationarity", "change-point")
FORECASTERS = (
    "naive",
    "seasonal-naive",
    "arima",
    "sarima",
    "sarimax",
    "var",
    "global-ridge",
    "croston",
)


@dataclass(frozen=True)
class TemporalSpec:
    task: str = "forecast"
    method: str = "arima"
    diagnostics: list[str] = field(default_factory=lambda: ["acf", "stationarity"])
    order: list[int] = field(default_factory=lambda: [1, 0, 0])
    seasonal_order: list[int] = field(default_factory=lambda: [1, 0, 0])
    gap: int = 0
    embargo: int = 0
    lags: int = 4
    difference: int = 0
    known_future: list[str] = field(default_factory=list)
    past_covariates: list[str] = field(default_factory=list)
    availability: dict[str, str] = field(default_factory=dict)
    var_columns: list[str] = field(default_factory=list)
    var_assumption: str = ""
    hierarchy: list[list[str]] = field(default_factory=list)
    training_series: list[str] = field(default_factory=list)
    validation_series: list[str] = field(default_factory=list)
    label: str = ""
    clusters: int = 2
    seed: int = 53
    alpha: float = 0.2
    croston_alpha: float = 0.1
    change_penalty: float = 3.0

    def data(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data, base=None, columns=None):
        if not isinstance(data, dict) or set(data) - set(cls.__dataclass_fields__):
            raise ProjectError("TemporalSpec declarative alanları geçersiz.")
        try:
            result = cls(**data)
            result.validate(base, columns)
            return result
        except (TypeError, ValueError, KeyError) as error:
            raise ProjectError("TemporalSpec ayar/tür/kapsam geçersiz.") from error

    def validate(self, base=None, columns=None):
        if (
            self.task not in ("forecast", "diagnostics", "classification", "clustering")
            or self.method not in FORECASTERS
        ):
            raise ProjectError("Temporal task/method desteklenmiyor.")
        for name, low, high in (
            ("gap", 0, 30),
            ("embargo", 0, 30),
            ("lags", 1, 12),
            ("difference", 0, 1),
            ("clusters", 2, 4),
            ("seed", 0, 2**32 - 1),
        ):
            v = getattr(self, name)
            if type(v) is not int or not low <= v <= high:
                raise ProjectError("Temporal tam sayı sınırı: " + name)
        for values in (self.order, self.seasonal_order):
            if (
                not isinstance(values, list)
                or len(values) != 3
                or any(type(v) is not int or not 0 <= v <= 2 for v in values)
                or values[1] > 1
            ):
                raise ProjectError("ARIMA order p/q≤2,d≤1; seasonal P/Q≤2,D≤1.")
        for name in ("alpha", "croston_alpha", "change_penalty"):
            value = getattr(self, name)
            bounds = (
                (0.05, 0.5)
                if name == "alpha"
                else (0.01, 0.5)
                if name == "croston_alpha"
                else (1.0, 20.0)
            )
            if type(value) not in (int, float) or not bounds[0] <= value <= bounds[1]:
                raise ProjectError("Temporal numeric param sınırı: " + name)
        for name in (
            "known_future",
            "past_covariates",
            "var_columns",
            "training_series",
            "validation_series",
            "diagnostics",
        ):
            v = getattr(self, name)
            if (
                not isinstance(v, list)
                or len(v) > 20
                or any(not isinstance(i, str) or not 0 < len(i) <= 200 for i in v)
                or len(set(v)) != len(v)
            ):
                raise ProjectError("Benzersiz bounded temporal liste gerekli: " + name)
        if not set(self.diagnostics) <= set(DIAGNOSTICS):
            raise ProjectError("Bilinmeyen diagnostic.")
        if (
            set(self.known_future) & set(self.past_covariates)
            or len(self.known_future + self.past_covariates) > 4
        ):
            raise ProjectError("Covariate rolleri ayrı ve en çok4 kolon olmalı.")
        if (
            not isinstance(self.availability, dict)
            or set(self.availability) != set(self.known_future + self.past_covariates)
            or any(
                not isinstance(v, str) or not 3 <= len(v) <= 500
                for v in self.availability.values()
            )
        ):
            raise ProjectError("Her covariate için açık erişim gerekçesi gerekir.")
        if self.method != "sarimax" and (self.known_future or self.past_covariates):
            raise ProjectError("Bu bounded yol covariate yalnız SARIMAX ile destekler.")
        if self.method == "sarimax" and not self.known_future + self.past_covariates:
            raise ProjectError("SARIMAX için explicit covariate rolü seçin.")
        if self.method == "var" and (
            not 1 <= len(self.var_columns) <= 3
            or not isinstance(self.var_assumption, str)
            or len(self.var_assumption.strip()) < 5
        ):
            raise ProjectError(
                "VAR 2–4 jointly observed numeric değişken ve stationarity gerekçesi ister; test tek başına kanıt değildir."
            )
        if self.method != "var" and self.difference:
            raise ProjectError(
                "difference yalnız VAR; ARIMA/SARIMA d/D order alanında seçilir."
            )
        if self.method != "var" and self.var_columns:
            raise ProjectError("var_columns yalnız VAR içindir.")
        if self.task != "forecast" and self.hierarchy:
            raise ProjectError("Reconciliation yalnız forecast alt yeteneğidir.")
        if (
            not isinstance(self.hierarchy, list)
            or len(self.hierarchy) > 32
            or any(
                not isinstance(e, list)
                or len(e) != 2
                or any(not isinstance(i, str) or not 0 < len(i) <= 200 for i in e)
                for e in self.hierarchy
            )
        ):
            raise ProjectError("Hierarchy parent/child token çiftleri gerekli.")
        if not isinstance(self.label, str) or not isinstance(self.var_assumption, str):
            raise ProjectError("Label/assumption türü geçersiz.")
        if self.task == "classification" and (
            not self.label
            or not self.training_series
            or not self.validation_series
            or set(self.training_series) & set(self.validation_series)
        ):
            raise ProjectError(
                "Whole-series train/validation kimlikleri ve label kolonu seçin; parçalı tabular split yok."
            )
        if base:
            if base.resample:
                raise ProjectError(
                    "Advanced covariate/panel yolunda resample kapalı; ayrı açık hazırlık işlemi kullanın."
                )
            if (
                self.method in ("sarima", "sarimax", "seasonal-naive")
                or set(self.diagnostics) & {"decomposition", "stl"}
            ) and not 2 <= base.seasonal_period <= 24:
                raise ProjectError("Bu seasonal dilim period2–24 ister.")
            if (
                self.past_covariates
                and self.lags
                < max(base.horizon, base.test_periods) + self.gap + self.embargo
            ):
                raise ProjectError(
                    "Geçmiş covariate lagı max(horizon,test_periods)+gap+embargo kadar olmalı; eval covariate erişimi kapalı."
                )
        if columns and base:
            selected = (
                self.known_future
                + self.past_covariates
                + self.var_columns
                + ([self.label] if self.label else [])
            )
            ids = {c["id"] for c in columns}
            if not set(selected) <= ids or set(selected) & {
                base.date,
                base.measurement,
                base.group,
            }:
                raise ProjectError(
                    "Covariate/VAR/label kolonları temel rollerden ayrı olmalı."
                )
