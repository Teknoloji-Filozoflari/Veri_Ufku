"""Explicit study design and hypotheses; no automatic method selection."""

from dataclasses import asdict, dataclass, field

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.storage.project_model import ProjectError

METHODS = {
    "independent": ("welch_t", "mann_whitney"),
    "paired": ("paired_t", "wilcoxon"),
    "groups": ("anova", "welch_anova", "kruskal"),
    "categorical": ("chi2", "fisher"),
    "numeric": ("pearson", "spearman"),
}
LABELS = {
    "welch_t": "Welch t — bağımsız grup ortalamaları",
    "mann_whitney": "Mann–Whitney — dağılımların sıra üstünlüğü",
    "paired_t": "Eşleştirilmiş t — kişi içi ortalama değişim",
    "wilcoxon": "Wilcoxon — simetrik kişi içi farkların merkezi",
    "anova": "ANOVA — eşit varyanslı grup ortalamaları",
    "welch_anova": "Welch ANOVA — farklı varyanslı grup ortalamaları",
    "kruskal": "Kruskal–Wallis — grup dağılımlarının sıraları",
    "chi2": "Ki-kare — kategorilerin bağımsızlığı",
    "fisher": "Fisher exact — 2×2 kategorik ilişki",
    "pearson": "Pearson — doğrusal sayısal ilişki",
    "spearman": "Spearman — monoton sıra ilişkisi",
}

ADVANCED_METHODS = (
    "missing_patterns",
    "missing_indicators",
    "mi_mean",
    "mi_ols",
    "sample_random",
    "sample_stratified",
    "sample_cluster",
    "weighted_mean",
    "weighted_ols",
    "weighted_fit",
    "survey_mean",
)
LABELS.update(
    dict(
        zip(
            ADVANCED_METHODS,
            (
                "Eksiklik desenleri",
                "Eksiklik göstergeleri",
                "Çoklu imputasyon — ortalama",
                "Çoklu imputasyon — OLS katsayıları",
                "Basit rastgele örnekleme",
                "Stratified — her stratada sabit adet",
                "Cluster — seçili kümelerin tüm satırları",
                "Frekans/analitik ağırlıklı ortalama",
                "Analitik ağırlıklı WLS",
                "sample_weight — doğrusal fit, çıkarım yok",
                "Survey ortalaması — strata/PSU Taylor SE/CI",
            ),
        )
    )
)


@dataclass(frozen=True)
class AnalysisSpec:
    path: str
    method: str
    x: str
    y: str = ""
    group: str = ""
    key: str = ""
    before: str = "önce"
    after: str = "sonra"
    pair_policy: str = "reject"
    question: str = ""
    hypothesis: str = ""
    unit: str = ""
    observation_unit: str = ""
    independent: bool = False
    measurement_confirmed: bool = False
    assumptions_confirmed: bool = False
    alternative: str = "two-sided"
    confidence: float = 0.95
    scope: str = "view"
    view: dict = field(default_factory=dict)
    precision: str = "reject"
    posthoc: str = "none"
    correction: str = "holm"
    features: list = field(default_factory=list)
    weight_type: str = "none"
    weight: str = ""
    strata: str = ""
    psu: str = ""
    seed: int = 42
    sample_size: int = 10
    imputations: int = 5
    iterations: int = 10
    deltas: list = field(default_factory=lambda: [-1.0, 0.0, 1.0])
    missing_assumption: str = "MAR"

    references: dict = field(default_factory=dict)
    interactions: list = field(default_factory=list)
    covariance: str = "nonrobust"
    offset: str = ""
    exposure: str = ""
    cluster: str = ""
    random_slopes: list = field(default_factory=list)
    within: list = field(default_factory=list)
    quantile: float = 0.5
    nb_alpha: float = 1.0
    reml: bool = True
    max_iterations: int = 1000
    missing_policy: str = "reject"

    resampling_unit: str = "observation"
    dependence: str = "independent"
    time_column: str = ""
    block_length: int = 5
    resamples: int = 1000
    statistic: str = "mean"
    trim_fraction: float = 0.2
    null_value: float = 0.0
    exchangeability_confirmed: bool = False
    symmetry_confirmed: bool = False
    outlier_policy: str = "keep"
    family_name: str = ""
    family_ids: list = field(default_factory=list)
    family_dependence: str = "arbitrary"
    scenarios: list = field(default_factory=list)
    experiment_plan: dict = field(default_factory=dict)
    dimension_plan: dict = field(default_factory=dict)
    survival_plan: dict = field(default_factory=dict)
    causal_plan: dict = field(default_factory=dict)
    bayes_plan: dict = field(default_factory=dict)
    bayes_feature_units: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data):
        try:
            return cls(**data)
        except (TypeError, ValueError):
            raise ProjectError("Analiz tarifi alanları geçersiz.") from None

    def data(self):
        return asdict(self)

    def validate(self, columns, run=False):
        for name in (
            "path",
            "method",
            "x",
            "y",
            "group",
            "key",
            "alternative",
            "scope",
            "precision",
            "pair_policy",
            "posthoc",
            "correction",
        ):
            if not isinstance(getattr(self, name), str):
                raise ProjectError("Analiz seçimi/sütun kimliği metin olmalı.")
        if self.path != "dimensions" and self.dimension_plan:
            raise ProjectError("Dimension plan başka analizde sessizce yok sayılamaz.")
        if self.path == "dimensions":
            from veri_ufku.statistics.dimension_contracts import validate

            validate(self, columns, run)
            return
        if self.path != "survival" and self.survival_plan:
            raise ProjectError("Sağkalım planı başka yöntemde sessizce yok sayılamaz.")
        if self.path == "survival":
            from veri_ufku.statistics.survival_contracts import validate

            validate(self, columns, run)
            return
        if self.path != "causal" and self.causal_plan:
            raise ProjectError("Nedensel plan başka analizde sessizce yok sayılamaz.")
        if self.path == "causal":
            from veri_ufku.statistics.causal_contracts import validate

            validate(self, columns, run)
            return
        if self.path == "bayes":
            from veri_ufku.statistics.bayes_contracts import validate

            validate(self, columns, run)
            return
        if self.path == "experiments":
            from veri_ufku.statistics.experiment_contracts import validate

            validate(self, columns, run)
            return
        if self.path == "resampling":
            from veri_ufku.statistics.resampling_contracts import validate

            validate(self, columns, run)
            return
        if self.path == "models":
            from veri_ufku.statistics.model_contracts import validate

            validate(self, columns, run)
            return
        if self.path == "advanced":
            from veri_ufku.statistics.missing_contracts import validate

            validate(self, columns, run)
            return
        if self.weight_type != "none" or self.weight or self.strata or self.psu:
            raise ProjectError(
                "Bu yöntem seçilen ağırlık/tasarımı desteklemiyor; ağırlık sessizce yok sayılmaz."
            )
        if self.path not in METHODS or self.method not in METHODS[self.path]:
            raise ProjectError("Soru yolu ve istatistik yöntemi uyuşmuyor.")
        for name in ("question", "hypothesis", "unit", "observation_unit"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or len(value) > 1000:
                raise ProjectError(
                    "Soru, hipotez, ölçüm birimi ve gözlem birimini yazın."
                )
        for name in ("independent", "measurement_confirmed", "assumptions_confirmed"):
            if type(getattr(self, name)) is not bool:
                raise ProjectError("Ölçüm/bağımsızlık onayı geçersiz.")
        if not self.independent or not self.measurement_confirmed:
            raise ProjectError(
                "Ölçüm/kategori rolünü ve bağımsız gözlem birimlerini onaylayın."
            )
        if run and not self.assumptions_confirmed:
            raise ProjectError(
                "Önkontrolü, dağılımı ve seçilen hipotezin varsayımlarını inceleyip onaylayın."
            )
        if (
            self.alternative not in ("two-sided", "less", "greater")
            or self.method in ("anova", "welch_anova", "kruskal", "chi2")
            and self.alternative != "two-sided"
        ):
            raise ProjectError("Bu yöntemde seçilen yönlü hipotez desteklenmiyor.")
        if (
            type(self.confidence) not in (float, int)
            or not 0.8 <= self.confidence <= 0.99
            or self.scope not in ("view", "full")
            or self.precision not in ("reject", "approximate")
            or self.pair_policy not in ("reject", "complete")
            or self.posthoc not in ("none", "pairwise")
            or self.posthoc == "pairwise"
            and self.path != "groups"
            or self.correction not in ("none", "holm", "bonferroni", "bh")
        ):
            raise ProjectError("Güven/kapsam/eşleştirme/çoklu test seçimi geçersiz.")
        ids = {c["id"] for c in columns}
        required = [self.x]
        if self.path in ("numeric", "categorical"):
            required += [self.y]
        if self.path in ("independent", "paired", "groups"):
            required += [self.group]
        if self.path == "paired":
            required += [self.key]
            if (
                not isinstance(self.before, str)
                or not isinstance(self.after, str)
                or not self.before
                or not self.after
                or self.before == self.after
                or max(len(self.before), len(self.after)) > 256
            ):
                raise ProjectError("Önce ve sonra için farklı, açık etiketler girin.")
        if not set(required) <= ids or len(set(required)) != len(required):
            raise ProjectError("Farklı ve mevcut ölçüm/grup/kişi sütunlarını seçin.")
        ViewSpec.from_dict(self.view).validate(columns)


def validate_saved(record, versions):
    result = record["analysis"]
    if result["provenance"]["schema"] != "AnalysisResult/v1":
        raise ProjectError("İstatistik sonuç şeması desteklenmiyor.")
    version = result["dataset_version"]
    if record["dataset_version_ids"] != [version] or version not in versions:
        raise ProjectError("İstatistik sonuç veri sürümü bağı geçersiz.")
    spec = AnalysisSpec.from_dict(result["spec"])
    spec.validate(versions[version]["import_metadata"]["columns"], run=True)
    from veri_ufku.domain.capabilities import CAPABILITIES

    if record["capability_id"] in CAPABILITIES and record[
        "capability_id"
    ] != "statistics." + spec.method.replace("_", "-"):
        raise ProjectError("İstatistik capability bağı geçersiz.")
    if set(result["artifact_uris"]) != (
        {"result", "members", "details", "diagnostic_png"}
        if spec.path in ("survival", "dimensions")
        else {"result", "members", "details", "chains", "diagnostic_png"}
        if spec.path == "bayes"
        else {"result", "members", "diagnostic", "diagnostic_png"}
        if spec.path == "models"
        else {"result", "members", "details"}
        if spec.path in ("advanced", "resampling", "experiments", "causal", "survival")
        else {"result", "members"}
    ):
        raise ProjectError("İstatistik artifact bağları eksik.")
    if result["method"] != spec.method or result["primary"]["method"] != spec.method:
        raise ProjectError("Kayıtlı istatistik yöntemi tarifle uyuşmuyor.")
    p = result["primary"]["p_value"]
    if not (
        spec.path
        in (
            "advanced",
            "models",
            "resampling",
            "experiments",
            "bayes",
            "causal",
            "survival",
            "dimensions",
        )
        and p is None
    ) and (type(p) not in (int, float) or not 0 <= p <= 1):
        raise ProjectError("Kayıtlı p-değeri geçersiz.")
    if record["result_version"] != result["result_version"]:
        raise ProjectError("İstatistik sonuç sürümü uyuşmuyor.")
