"""Version-bound dashboard and publication figure contracts.

The module is deliberately data-only: a saved view never owns rows or silently
rebinds to the active dataset. Selection transfer across sources requires an
explicit column mapping chosen by the caller.
"""

from dataclasses import dataclass, field

from veri_ufku.storage.project_model import ProjectError, entity_id, uid

WIDGET_TYPES = ("chart", "table", "kpi", "note")
FILTER_OPS = ("eq", "in", "gte", "lte", "contains", "is-null")


@dataclass(frozen=True)
class DashboardFilter:
    column_id: str
    operator: str
    value: object = None
    scope: str = "global"
    dataset_version: str = ""

    def validate(self):
        if (
            not self.column_id
            or self.operator not in FILTER_OPS
            or self.scope not in ("global", "local")
        ):
            raise ProjectError("Dashboard filtresi sütun/işlem/kapsamı geçersiz.")
        if self.operator == "in" and (
            not isinstance(self.value, list) or len(self.value) > 1000
        ):
            raise ProjectError("IN filtresi en fazla1000 açık değer içerebilir.")


@dataclass(frozen=True)
class DashboardWidget:
    kind: str
    dataset_version: str
    title: str = ""
    chart_result_id: str = ""
    filters: tuple = ()
    grid: tuple = (0, 0, 4, 3)  # row, column, row span, column span
    text: str = ""
    column_id: str = ""
    aggregation: str = "count"
    denominator: str = "included rows"
    previous_period: str = "none"
    id: str = field(default_factory=lambda: "widget:" + uid())
    columns: tuple = ()
    denominator_mode: str = "none"
    denominator_column: str = ""
    previous_filters: tuple = ()

    def validate(self):
        entity_id(self.id, "widget")
        if self.kind not in WIDGET_TYPES or not self.dataset_version:
            raise ProjectError("Widget türü ve veri sürümü zorunludur.")
        if (
            len(self.grid) != 4
            or any(type(x) is not int for x in self.grid)
            or self.grid[0] < 0
            or self.grid[1] < 0
            or min(self.grid[2:]) < 1
            or self.grid[0] + self.grid[2] > 48
            or self.grid[1] + self.grid[3] > 12
        ):
            raise ProjectError("Widget grid konumu geçersiz.")
        if self.kind == "kpi" and (
            not self.aggregation or not self.denominator or not self.previous_period
        ):
            raise ProjectError(
                "KPI agregasyon, payda ve önceki dönem tanımını göstermelidir."
            )
        if self.kind == "chart" and not self.chart_result_id:
            raise ProjectError("Grafik widget kayıtlı grafik sonucuna bağlanmalıdır.")
        if self.aggregation not in (
            "count",
            "sum",
            "mean",
            "min",
            "max",
        ) or self.denominator_mode not in ("none", "rows", "non-null", "column-sum"):
            raise ProjectError("KPI agregasyonu/payda türü geçersiz.")
        if self.denominator_mode == "column-sum" and not self.denominator_column:
            raise ProjectError("Kolon toplamı paydası için açık ColumnId seçin.")
        if self.previous_period != "none" and not self.previous_filters:
            raise ProjectError("Önceki dönem tanımı için açık filtre seçin.")
        if any(
            not isinstance(t, str) or len(t) > 2000
            for t in (self.title, self.text, self.denominator, self.previous_period)
        ):
            raise ProjectError("Widget metni sınırı aşıldı.")
        if len(self.filters) + len(self.previous_filters) > 100:
            raise ProjectError("Widget filtre sayısı en fazla100 olmalı.")
        for f in (*self.filters, *self.previous_filters):
            item = f if isinstance(f, DashboardFilter) else DashboardFilter(**f)
            item.validate()
            if item.scope != "local" or item.dataset_version not in (
                "",
                self.dataset_version,
            ):
                raise ProjectError(
                    "Yerel/dönem filtresi yalnız widget veri sürümüne bağlanmalıdır."
                )


@dataclass(frozen=True)
class DashboardSpec:
    name: str
    widgets: tuple
    global_filters: tuple = ()
    # dataset-version -> source column -> target dataset-version/column
    filter_mappings: dict = field(default_factory=dict)
    schema_version: int = 1
    id: str = field(default_factory=lambda: "dashboard:" + uid())
    selection: dict = field(default_factory=dict)
    drill_down: bool = False
    figure: dict = field(default_factory=dict)

    def validate(self, versions):
        entity_id(self.id, "dashboard")
        if (
            self.schema_version != 1
            or not self.name.strip()
            or len(self.name) > 2000
            or len(self.widgets) > 100
            or len(self.global_filters) > 100
        ):
            raise ProjectError("Dashboard adı/şeması/widget sayısı geçersiz.")
        for raw_widget in self.widgets:
            widget = (
                raw_widget
                if isinstance(raw_widget, DashboardWidget)
                else DashboardWidget(**raw_widget)
            )
            widget.validate()
            if widget.dataset_version not in versions:
                raise ProjectError("Dashboard widget veri sürümü projede bulunmuyor.")
            if isinstance(versions, dict):
                columns = {
                    c["id"]
                    for c in versions[widget.dataset_version]
                    .get("import_metadata", {})
                    .get("columns", [])
                }
                chosen = {
                    x
                    for x in (
                        *widget.columns,
                        widget.column_id,
                        widget.denominator_column,
                    )
                    if x
                }
                chosen.update(
                    (f if isinstance(f, dict) else f.__dict__)["column_id"]
                    for f in (*widget.filters, *widget.previous_filters)
                )
                if not chosen <= columns:
                    raise ProjectError(
                        "Widget filtresi/KPI/tablo sütunu veri sürümüyle uyuşmuyor."
                    )
        if len(
            {
                (w.id if isinstance(w, DashboardWidget) else w["id"])
                for w in self.widgets
            }
        ) != len(self.widgets):
            raise ProjectError("Widget kimlikleri farklı olmalı.")
        if type(self.drill_down) is not bool or not isinstance(self.selection, dict):
            raise ProjectError("Dashboard seçim sözleşmesi geçersiz.")
        if self.selection and (
            set(self.selection) != {"dataset_version", "row_ids"}
            or self.selection["dataset_version"] not in versions
            or not isinstance(self.selection["row_ids"], list)
            or len(self.selection["row_ids"]) > 10000
            or any(not isinstance(r, str) for r in self.selection["row_ids"])
        ):
            raise ProjectError("Seçim sürüm/RowId bağı geçersiz.")
        if self.figure:
            FigureSpec(**self.figure).validate()
        for f in self.global_filters:
            item = f if isinstance(f, DashboardFilter) else DashboardFilter(**f)
            item.validate()
            if item.scope != "global":
                raise ProjectError("Global filtre global kapsam taşımalıdır.")
            if isinstance(versions, dict):
                raw = f if isinstance(f, dict) else f.__dict__
                source = versions.get(raw.get("dataset_version"))
                if not source or raw["column_id"] not in {
                    c["id"]
                    for c in source.get("import_metadata", {}).get("columns", [])
                }:
                    raise ProjectError(
                        "Global filtre açık kaynak dataset sürümü/ColumnId ister."
                    )
        # Only explicit mappings are accepted; no name or position matching.
        if not isinstance(self.filter_mappings, dict):
            raise ProjectError("Kaynaklar arası filtre eşlemesi açık sözlük olmalıdır.")
        for mapping in self.filter_mappings.values():
            if not isinstance(mapping, dict) or set(mapping) not in (
                {"target_version", "target_column"},
                {"source_version", "source_column", "target_version", "target_column"},
            ):
                raise ProjectError("Filtre eşlemesi hedef sürüm ve ColumnId ister.")
            if (
                mapping["target_version"] not in versions
                or not mapping["target_column"]
            ):
                raise ProjectError("Filtre eşlemesinin hedefi geçersiz.")
            if (
                "source_version" in mapping
                and mapping["source_version"] not in versions
            ):
                raise ProjectError("Filtre eşlemesinin kaynak sürümü projede yok.")
            if isinstance(versions, dict):
                if "source_version" not in mapping:
                    raise ProjectError(
                        "Kaynak eşlemesi açık kaynak sürümü ve sütunu ister."
                    )
                for prefix in ("source", "target"):
                    if prefix + "_version" in mapping:
                        d = versions[mapping[prefix + "_version"]]
                        if mapping[prefix + "_column"] not in {
                            c["id"]
                            for c in d.get("import_metadata", {}).get("columns", [])
                        }:
                            raise ProjectError(
                                "Filtre eşlemesinin ColumnId bağı geçersiz."
                            )

    def bound_versions(self):
        data = self.data()
        versions = {w["dataset_version"] for w in data["widgets"]}
        versions.update(
            f["dataset_version"]
            for f in data["global_filters"]
            if f.get("dataset_version")
        )
        for mapping in self.filter_mappings.values():
            versions.update(
                mapping[key]
                for key in ("source_version", "target_version")
                if key in mapping
            )
        if self.selection:
            versions.add(self.selection["dataset_version"])
        return versions

    def data(self):
        def primitive(value):
            if hasattr(value, "__dataclass_fields__"):
                return {
                    name: primitive(getattr(value, name))
                    for name in value.__dataclass_fields__
                }
            if isinstance(value, tuple):
                return [primitive(x) for x in value]
            if isinstance(value, dict):
                return {k: primitive(v) for k, v in value.items()}
            return value

        return primitive(self)


def filter_row_ids(rows, filters, columns):
    """Apply filters to {RowId: {ColumnId: value}} without positional joins."""
    selected = set(rows)
    for raw in filters:
        f = raw if isinstance(raw, DashboardFilter) else DashboardFilter(**raw)
        f.validate()
        if f.column_id not in columns:
            raise ProjectError("Filtre ColumnId seçilen dataset sürümünde yok.")

        def matches(value):
            if f.operator == "is-null":
                return value is None
            if f.operator == "eq":
                return value == f.value
            if f.operator == "in":
                return value in f.value
            if f.operator == "contains":
                return f.value in str(value) if value is not None else False
            if value is None:
                return False
            if f.operator == "gte":
                return value >= f.value
            if f.operator == "lte":
                return value <= f.value
            return False

        selected = {rid for rid in selected if matches(rows[rid].get(f.column_id))}
    return selected


def map_selection(
    source_rows, target_rows, selected_row_ids, source_column, target_column
):
    """Transfer a brush only through an explicitly chosen key-column mapping."""
    if not source_column or not target_column:
        raise ProjectError("Kaynaklar arası seçim için kullanıcı eşlemesi gerekli.")
    keys = {
        source_rows[rid].get(source_column)
        for rid in selected_row_ids
        if rid in source_rows
    }
    keys.discard(None)
    return {rid for rid, row in target_rows.items() if row.get(target_column) in keys}


def kpi_value(rows, column_id, aggregation, denominator, previous_period):
    """Return value and the displayed definition so KPI arithmetic is auditable."""
    vals = [
        row.get(column_id) for row in rows.values() if row.get(column_id) is not None
    ]
    if aggregation == "count":
        value = len(vals)
    elif aggregation == "sum":
        value = sum(vals)
    elif aggregation == "mean":
        value = sum(vals) / len(vals) if vals else None
    elif aggregation == "min":
        value = min(vals) if vals else None
    elif aggregation == "max":
        value = max(vals) if vals else None
    else:
        raise ProjectError("KPI agregasyonu count/sum/mean/min/max olmalıdır.")
    return {
        "value": value,
        "aggregation": aggregation,
        "denominator": denominator,
        "previous_period": previous_period,
        "included_n": len(rows),
        "non_null_n": len(vals),
    }


def freshness(widget_version, active_version):
    return "current" if widget_version == active_version else "stale"


def save_dashboard(state, spec):
    """Persist a named layout in the project's immutable result journal."""
    versions = {d["version_id"]: d for d in state["datasets"]}
    spec = spec if isinstance(spec, DashboardSpec) else DashboardSpec(**spec)
    spec.validate(versions)
    charts = {r["id"]: r["chart"] for r in state["results"] if "chart" in r}
    for raw in spec.widgets:
        w = raw if isinstance(raw, DashboardWidget) else DashboardWidget(**raw)
        if w.kind == "chart" and (
            w.chart_result_id not in charts
            or charts[w.chart_result_id]["dataset_version"] != w.dataset_version
        ):
            raise ProjectError("Kaydedilmiş grafik widget veri sürümüyle uyuşmuyor.")
    record = {
        "id": "result:" + uid(),
        "dataset_version_ids": sorted(spec.bound_versions()),
        "seed": None,
        "dashboard": spec.data(),
    }
    state["results"].append(record)
    return record["id"]


def open_dashboard(state, result_id, active_versions):
    """Reopen layout exactly as saved and identify widgets from old versions."""
    record = next(
        (r for r in state["results"] if r["id"] == result_id and "dashboard" in r), None
    )
    if record is None:
        raise ProjectError("Kaydedilmiş dashboard bulunamadı.")
    saved = record["dashboard"]
    return {
        "spec": saved,
        "widgets": [
            {
                **widget,
                "freshness": freshness(
                    widget["dataset_version"],
                    active_versions.get(widget["dataset_version"], ""),
                ),
            }
            for widget in saved["widgets"]
        ],
    }


@dataclass(frozen=True)
class FigureSpec:
    chart_result_ids: tuple
    rows: int = 1
    columns: int = 1
    shared_legend: bool = True
    palette: str = "accessible"
    font: str = "DejaVu Sans"
    font_size: int = 11
    width: int = 12
    height: int = 7
    caption: str = ""
    unit: str = ""
    source: str = ""

    def validate(self):
        if (
            not self.chart_result_ids
            or self.rows < 1
            or self.columns < 1
            or len(self.chart_result_ids) > self.rows * self.columns
            or self.rows * self.columns > 16
        ):
            raise ProjectError(
                "Figure subplot ızgarası seçili grafik sayısını kapsamıyor."
            )
        if (
            self.palette not in ("accessible", "colorblind", "grayscale")
            or not 6 <= self.font_size <= 48
        ):
            raise ProjectError("Figure renk/typography preset geçersiz.")
        if not (2 <= self.width <= 40 and 2 <= self.height <= 40):
            raise ProjectError("Figure boyutu 2–40 inç aralığında olmalı.")
        if (
            self.font not in ("DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono")
            or type(self.shared_legend) is not bool
        ):
            raise ProjectError("Figure font/ortak legend seçimi geçersiz.")


def validate_axis_policy(spec):
    """Require a warning and legend whenever a chart declares dual axes."""
    dual = bool(spec.get("dual_axis"))
    if dual and (not spec.get("axis_warning") or not spec.get("legend")):
        raise ProjectError("Çift eksen açık uyarı ve legend gerektirir.")
    if spec.get("automatic_axis_truncation"):
        raise ProjectError("Yanıltıcı otomatik eksen kırpma kabul edilmez.")
    return True
