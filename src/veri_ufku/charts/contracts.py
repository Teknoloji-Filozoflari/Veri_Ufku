"""Data-only ChartSpec/v1; column identities, display settings and scope are explicit."""

import math
from dataclasses import asdict, dataclass, field

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.storage.project_model import ProjectError, entity_id

GEO_KINDS = ("map-point", "map-choropleth", "map-density", "map-raster")

ARRAY_KINDS = ("array-heatmap", "array-profile")
DISTRIBUTION_KINDS = (
    "violin",
    "kde",
    "ecdf",
    "rug",
    "strip",
    "swarm",
    "qq",
    "pp",
    "error-bar",
    "ci-band",
    "missing-pattern",
)
MULTIVARIATE_KINDS = (
    "pair",
    "hexbin",
    "density-2d",
    "bubble",
    "grouped-heatmap",
    "clustered-heatmap",
    "parallel",
    "facets",
    "conditional",
)

COMPOSITION_KINDS = (
    "stacked-bar",
    "percent-bar",
    "stacked-area",
    "percent-area",
    "dot",
    "lollipop",
    "waterfall",
    "pareto",
    "treemap",
    "sunburst",
    "sankey",
    "alluvial",
    "funnel",
    "calendar",
    "pie",
    "donut",
    "radar",
)

COMPOSITION_SCHEMAS = {
    "stacked-bar": "X category + group series + Y nonnegative additive value; sum/count; per-X denominator",
    "percent-bar": "X category + group series + Y nonnegative additive value; sum/count; per-X denominator",
    "stacked-area": "X numeric/date ordered coordinate + group series + Y nonnegative additive value; common complete grid",
    "percent-area": "X numeric/date ordered coordinate + group series + Y nonnegative additive value; common complete grid",
    "dot": "X category + Y numeric value; explicit sum/count/mean/median/min/max",
    "lollipop": "X category + Y numeric value; explicit sum/count/mean/median/min/max",
    "waterfall": "X unique ordered label + Y signed amount + waterfall_role start/change/end; verified endpoint",
    "pareto": "X category + Y nonnegative additive amount; sum/count; cumulative share of included total",
    "treemap": "X unique node ID string + parent nullable node ID + Y leaf amount; internal amount must be zero",
    "sunburst": "X unique node ID string + parent nullable node ID + Y leaf amount; internal amount must be zero",
    "sankey": "X source ID string + target ID string + Y nonnegative edge amount; balanced DAG",
    "alluvial": "X source ID string + target ID string + Y nonnegative adjacent-stage edge amount; balanced DAG",
    "funnel": "X stage + explicit stage order; people: entity ID and nested cohort, events: row counts",
    "calendar": "X Date or timezone-aware/naive Datetime (local calendar day) + Y numeric amount; explicit sum/count/mean",
    "pie": "X at most6 categories + Y nonnegative additive amount; included mutually exclusive parts; positive total",
    "donut": "X at most6 categories + Y nonnegative additive amount; included mutually exclusive parts; positive total",
    "radar": "advanced opt-in;3–6 numeric columns; per-column minmax normalization; optional group mean",
}

WEIGHT_KINDS = ("histogram", "box", "violin", "kde", "ecdf")

KINDS = ("histogram", "box", "bar", "line", "scatter", "correlation", "missing")


@dataclass(frozen=True)
class ChartSpec:
    kind: str
    geometry: str = ""
    geo_crs: str = ""
    geo_measure: str = ""
    geo_denominator: str = ""
    geo_measure_mode: str = "count"
    geo_classification: str = "equal"
    geo_thresholds: tuple = ()
    x: str = ""
    y: str = ""
    group: str = ""
    columns: tuple = ()
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    xunit: str = ""
    yunit: str = ""
    legend: bool = True
    bins: int = 20
    top_n: int = 20
    aggregation: str = "count"
    correlation: str = "pearson"
    scatter_mode: str = "systematic"
    point_limit: int = 10000
    grid_bins: int = 40
    scope: str = "view"
    sample_rows: int = 10000
    precision: str = "reject"
    purpose: str = "distribution"
    null_policy: str = "exclude_nonfinite; category_null_separate; missing_null_only"
    view: dict = field(default_factory=dict)
    bounds: tuple = ()
    width: int = 1000
    height: int = 650
    dpi: int = 120
    schema_version: int = 1
    parent: str = ""
    target: str = ""
    entity: str = ""
    waterfall_role: str = ""
    missing_category: str = "include"
    funnel_unit: str = "people"
    advanced: bool = False
    radar_scale: str = "minmax"
    size: str = ""
    bubble_encoding: str = "area"
    facet_scale: str = "shared"
    heatmap_scale: str = "raw"
    heatmap_order: str = "input"
    cluster_method: str = "average"
    facet: str = ""
    weight: str = ""
    weight_type: str = "none"
    normalization: str = "count"
    bandwidth: str = "scott"
    bandwidth_factor: float = 1.0
    uncertainty: str = "ci"
    confidence: float = 0.95
    xscale: str = "linear"
    yscale: str = "linear"
    linthresh: float = 1.0
    category_order: tuple = ()
    palette: str = "accessible"
    font: str = "DejaVu Sans"
    font_size: int = 11
    annotation: str = ""

    @classmethod
    def from_dict(cls, data):
        try:
            value = dict(data)
            value["columns"] = tuple(value.get("columns", ()))
            value["bounds"] = tuple(value.get("bounds", ()))
            value["category_order"] = tuple(value.get("category_order", ()))
            return cls(**value)
        except (TypeError, ValueError) as error:
            raise ProjectError("Grafik tarifi alanları geçersiz.") from error

    def data(self):
        value = asdict(self)
        value["columns"] = list(self.columns)
        value["bounds"] = list(self.bounds)
        return value

    def validate(self, columns):
        ids = {c["id"] for c in columns}
        if (
            self.schema_version != 1
            or self.kind
            not in KINDS
            + ARRAY_KINDS
            + DISTRIBUTION_KINDS
            + MULTIVARIATE_KINDS
            + COMPOSITION_KINDS
            + GEO_KINDS
        ):
            raise ProjectError("Grafik türü veya şema sürümü desteklenmiyor.")
        if self.kind in GEO_KINDS:
            if (
                self.weight
                or self.facet
                or self.group
                or self.size
                or self.xscale != "linear"
                or self.yscale != "linear"
            ):
                raise ProjectError(
                    "Harita linear/singlepanel; facet/weight/size desteklenmez."
                )
            if (
                not isinstance(self.geo_crs, str)
                or len(self.geo_crs) > 4096
                or self.geo_measure_mode not in ("count", "rate")
                or self.geo_classification not in ("equal", "quantile", "manual")
            ):
                raise ProjectError("Harita CRS/ölçüm/classification seçimi geçersiz.")
            if not self.geometry and (not self.x or not self.y):
                raise ProjectError("Harita geometri veya x/y koordinatları ister.")
            if self.kind in ("map-choropleth", "map-raster") and not self.geo_measure:
                raise ProjectError("Harita ölçüm alanı seçin.")
            if self.kind == "map-choropleth" and (
                not self.geometry
                or self.geo_measure_mode == "rate"
                and not self.geo_denominator
            ):
                raise ProjectError("Choropleth polygon ve oran için payda ister.")

            if (
                not isinstance(self.geo_thresholds, (list, tuple))
                or len(self.geo_thresholds) > 9
                or any(
                    type(x) not in (int, float) or not math.isfinite(x)
                    for x in self.geo_thresholds
                )
                or list(self.geo_thresholds) != sorted(set(self.geo_thresholds))
            ):
                raise ProjectError(
                    "Eşikler artan farklı sonlu sayılar olmalı; en fazla9."
                )
            if (
                self.kind == "map-choropleth"
                and self.geo_classification == "manual"
                and not self.geo_thresholds
            ):
                raise ProjectError("Manual sınıflar açık eşik ister.")
            if self.kind == "map-choropleth" and not 2 <= self.bins <= 10:
                raise ProjectError("Choropleth2–10sınıf ister.")
        if self.kind == "array-heatmap" and len(self.columns) != 3:
            raise ProjectError("Isı haritası iki koordinat ve ölçüm sütunu ister.")
        if self.kind == "array-profile" and (not self.x or not self.y):
            raise ProjectError("Profil için boyut koordinatı ve ölçüm seçin.")
        for value in (
            self.x,
            self.y,
            self.group,
            self.facet,
            self.weight,
            self.size,
            self.parent,
            self.target,
            self.entity,
            self.waterfall_role,
            self.geometry,
            self.geo_measure,
            self.geo_denominator,
            *self.columns,
        ):
            if value and value not in ids:
                raise ProjectError("Grafik bilinmeyen ColumnId içeriyor.")
        if len(self.columns) > 20 or len(set(self.columns)) != len(self.columns):
            raise ProjectError("En fazla20 farklı sütun seçin.")
        if self.kind in ("histogram", "box", "bar", "line", "scatter") and not self.x:
            raise ProjectError("Grafik için X sütunu seçin.")
        if self.kind in ("line", "scatter") and not self.y:
            raise ProjectError("Grafik için Y ölçüm sütunu seçin.")
        if self.kind in ("correlation", "missing") and not self.columns:
            raise ProjectError("Grafik sütunlarını açıkça seçin.")
        if self.kind == "correlation" and len(self.columns) < 2:
            raise ProjectError("Korelasyon için en az iki ölçüm seçin.")
        if self.kind == "bar" and self.aggregation != "count" and not self.y:
            raise ProjectError("Toplulaştırma için Y ölçümü seçin.")
        if (
            self.kind in DISTRIBUTION_KINDS
            and self.kind != "missing-pattern"
            and not self.x
        ):
            raise ProjectError("Dağılım grafiği için X seçin.")
        if self.kind in ("error-bar", "ci-band") and not self.y:
            raise ProjectError("Belirsizlik grafiği Y ölçümü ister.")
        if self.kind in ("error-bar", "ci-band") and self.aggregation != "mean":
            raise ProjectError(
                "SD/SE/CI grafiği ortalama (mean) hesabı ister; başka agregasyon sessizce uygulanmaz."
            )
        if self.kind == "missing-pattern" and not self.columns:
            raise ProjectError("Eksiklik deseni sütunlarını seçin.")
        if self.facet and self.kind not in DISTRIBUTION_KINDS + MULTIVARIATE_KINDS + (
            "histogram",
            "box",
        ):
            raise ProjectError("Bu grafik facet desteklemiyor.")
        if self.kind in MULTIVARIATE_KINDS:
            if self.kind in (
                "pair",
                "parallel",
                "grouped-heatmap",
                "clustered-heatmap",
            ):
                if not 2 <= len(self.columns) <= 6:
                    raise ProjectError(
                        "Panel önkontrolü: 2–6 sütun seçin; pair en fazla36 panel."
                    )
            elif not self.x or not self.y:
                raise ProjectError("İlişki grafiği X ve Y ölçümü ister.")
            if self.kind == "bubble" and not self.size:
                raise ProjectError("Bubble boyut ölçümü seçin.")
            if (
                self.kind in ("grouped-heatmap", "clustered-heatmap", "conditional")
                and not self.group
            ):
                raise ProjectError("Grup/koşul sütunu seçin.")
            if self.kind == "facets" and not self.facet:
                raise ProjectError("Small multiples için facet sütunu seçin.")
            if self.xscale != "linear" or self.yscale != "linear":
                raise ProjectError(
                    "Çok değişkenli koordinatlar şu anda linear; dönüşüm sessiz uygulanmaz."
                )
            if self.bounds:
                raise ProjectError(
                    "Çok panel/kategorik grafik yakınlaştırması için açık veri filtresi kullanın."
                )
        if self.kind in MULTIVARIATE_KINDS and self.facet and self.kind != "facets":
            raise ProjectError(
                "Bu çok değişkenli tür ayrı facet kullanmaz; facets türünü seçin."
            )
        if self.kind in ("hexbin", "density-2d") and self.group:
            raise ProjectError(
                "CPU hücre aggregation tüm seçili satırlarda; grup için açık filtre veya facet seçin."
            )
        if (
            self.bubble_encoding not in ("area", "radius")
            or self.facet_scale not in ("shared", "independent")
            or self.heatmap_scale not in ("raw", "column-zscore")
            or self.heatmap_order not in ("input", "alphabetical")
            or self.cluster_method not in ("average", "complete", "ward")
        ):
            raise ProjectError("Boyut/facet/heatmap yöntemi geçersiz.")
        if self.kind in COMPOSITION_KINDS:
            if (
                self.facet
                or self.weight
                or self.size
                or self.xscale != "linear"
                or self.yscale != "linear"
                or self.bounds
            ):
                raise ProjectError(
                    "Kompozisyon grafiği linear ve tek panel; facet/ağırlık/zoom desteklenmez."
                )
            if self.group and self.kind not in (
                "stacked-bar",
                "percent-bar",
                "stacked-area",
                "percent-area",
                "radar",
            ):
                raise ProjectError(
                    "Bu input şeması grup/seri desteklemiyor; açık filtre seçin."
                )
            required_aggregation = (
                "mean"
                if self.kind == "radar"
                else "count"
                if self.kind == "funnel"
                else "sum"
                if self.kind
                in ("treemap", "sunburst", "sankey", "alluvial", "waterfall")
                else None
            )
            if required_aggregation and self.aggregation != required_aggregation:
                raise ProjectError(
                    "Input şeması için agregasyon gerekli: " + required_aggregation
                )
            if self.kind == "radar":
                if (
                    not self.advanced
                    or not 3 <= len(self.columns) <= 6
                    or self.radar_scale != "minmax"
                ):
                    raise ProjectError(
                        "Radar advanced onayı ve3–6 sayısal sütun/minmax ister; dot/parallel alternatifini inceleyin."
                    )
            elif not self.x or (self.kind != "funnel" and not self.y):
                raise ProjectError(
                    "Grafik input şeması X ve Y ölçümü ister: "
                    + COMPOSITION_SCHEMAS[self.kind]
                )
            if (
                self.kind
                in ("stacked-bar", "percent-bar", "stacked-area", "percent-area")
                and not self.group
            ):
                raise ProjectError("Stacked grafik seri/grup sütunu ister.")
            for kinds, name in (
                (("treemap", "sunburst"), "parent"),
                (("sankey", "alluvial"), "target"),
                (("waterfall",), "waterfall_role"),
            ):
                if self.kind in kinds and not getattr(self, name):
                    raise ProjectError("Grafik alanı gerekli: " + name)
            if self.kind == "funnel" and (
                not self.category_order
                or self.funnel_unit == "people"
                and not self.entity
            ):
                raise ProjectError(
                    "Funnel açık aşama sırası ve people için kişi kimliği ister."
                )
            if self.kind not in (
                "radar",
                "funnel",
                "waterfall",
            ) and self.aggregation not in (
                ("sum", "count", "mean", "median", "min", "max")
                if self.kind in ("dot", "lollipop", "calendar")
                else ("sum", "count")
            ):
                raise ProjectError(
                    "Bu grafik açık additive sum/count ister; dot/calendar için ölçüm agregasyonu da seçilebilir."
                )
        if (
            self.missing_category not in ("include", "exclude")
            or self.funnel_unit not in ("people", "events")
            or type(self.advanced) is not bool
            or self.radar_scale != "minmax"
        ):
            raise ProjectError("Eksik kategori/funnel/radar politikası geçersiz.")
        if self.weight_type not in ("none", "frequency", "analytic") or bool(
            self.weight
        ) != (self.weight_type != "none"):
            raise ProjectError(
                "Ağırlık sütunu ve desteklenen türünü birlikte seçin; survey/sample_weight desteklenmez."
            )
        if self.weight and self.kind not in WEIGHT_KINDS:
            raise ProjectError("Bu grafik ağırlık desteklemiyor.")
        if (
            self.normalization not in ("count", "probability", "density", "percent")
            or self.bandwidth not in ("scott", "silverman")
            or self.uncertainty not in ("sd", "se", "ci")
        ):
            raise ProjectError("Normalizasyon/bandwidth/belirsizlik seçimi geçersiz.")
        for name, low, high in (
            ("bandwidth_factor", 0.05, 10),
            ("confidence", 0.8, 0.99),
            ("linthresh", 1e-12, 1e12),
        ):
            v = getattr(self, name)
            if (
                type(v) not in (int, float)
                or not math.isfinite(v)
                or not low <= v <= high
            ):
                raise ProjectError("Grafik sayısal ayarı geçersiz: " + name)
        if self.xscale not in ("linear", "log", "symlog") or self.yscale not in (
            "linear",
            "log",
            "symlog",
        ):
            raise ProjectError("Eksen ölçeği geçersiz.")
        if self.palette not in (
            "accessible",
            "viridis",
            "grayscale",
        ) or self.font not in ("DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono"):
            raise ProjectError("Palet/font desteklenmiyor.")
        if (
            type(self.font_size) is not int
            or not 8 <= self.font_size <= 20
            or not isinstance(self.annotation, str)
            or len(self.annotation) > 200
        ):
            raise ProjectError("Font boyutu/annotation geçersiz.")
        if (
            len(self.category_order) > 100
            or any(not isinstance(v, str) or len(v) > 200 for v in self.category_order)
            or len(set(self.category_order)) != len(self.category_order)
        ):
            raise ProjectError("Kategorik sıra farklı etiketlerden oluşmalı.")
        for name in ("title", "xlabel", "ylabel", "xunit", "yunit"):
            if (
                not isinstance(getattr(self, name), str)
                or len(getattr(self, name)) > 200
            ):
                raise ProjectError("Grafik metinleri en fazla200 karakter olmalı.")
        if type(self.legend) is not bool:
            raise ProjectError("Legend tercihi geçersiz.")
        for name, low, high in (
            ("bins", 1, 200),
            ("top_n", 1, 100),
            ("point_limit", 1, 10000),
            ("grid_bins", 2, 80),
            ("sample_rows", 1, 100000),
            ("width", 400, 2000),
            ("height", 300, 1400),
            ("dpi", 72, 600),
        ):
            v = getattr(self, name)
            if type(v) is not int or not low <= v <= high:
                raise ProjectError(f"Grafik {name} sınırı: {low}–{high}.")
        if (
            self.aggregation
            not in ("count", "sum", "mean", "median", "min", "max", "reject")
            or self.correlation not in ("pearson", "spearman")
            or self.scatter_mode not in ("systematic", "grid", "full")
            or self.scope not in ("full", "view", "sample")
            or self.precision not in ("reject", "approximate")
            or self.purpose
            not in ("distribution", "compare", "relationship", "time", "quality")
        ):
            raise ProjectError("Grafik yöntem/kapsam politikası geçersiz.")
        if (
            self.null_policy
            != "exclude_nonfinite; category_null_separate; missing_null_only"
        ):
            raise ProjectError("Null/NaN/sonsuz politikası desteklenmiyor.")
        ViewSpec.from_dict(self.view).validate(columns)
        if self.bounds and (
            len(self.bounds) != 4
            or any(
                type(v) not in (int, float) or not math.isfinite(v) for v in self.bounds
            )
            or self.bounds[0] >= self.bounds[1]
            or self.bounds[2] >= self.bounds[3]
        ):
            raise ProjectError("Yakınlaştırma sınırları geçersiz.")


def validate_saved(record, versions):
    chart = record["chart"]
    version = record["dataset_version_ids"][0]
    entity_id(version, "dv")
    if chart.get("dataset_version") != version or version not in versions:
        raise ProjectError("Grafik sonuç sürümü geçersiz.")
    spec = ChartSpec.from_dict(chart["spec"])
    spec.validate(versions[version]["import_metadata"]["columns"])
    if set(chart["artifact_uris"]) not in (
        {"data", "members", "png", "svg", "result"},
        {"data", "members", "png", "svg", "pdf", "result"},
    ):
        raise ProjectError("Grafik artifact bağı eksik.")


def axis_coordinate(value, scale, threshold=1.0, inverse=False):
    """Matplotlib base10/default linscale geometry, independent of analytical values."""
    if scale == "linear":
        return value
    if scale == "log":
        return 10**value if inverse else math.log10(value)
    adjusted = 1 / (1 - 0.1)
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    if inverse:
        return (
            value / adjusted
            if magnitude <= threshold * adjusted
            else sign * threshold * 10 ** (magnitude / threshold - adjusted)
        )
    return (
        value * adjusted
        if magnitude <= threshold
        else sign * threshold * (adjusted + math.log10(magnitude / threshold))
    )
