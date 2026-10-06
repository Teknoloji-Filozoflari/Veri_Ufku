"""Data-only views and semantic metadata keyed by immutable column identity."""

import copy
from dataclasses import dataclass, field

from veri_ufku.storage.project_model import ProjectError, entity_id, uid

ROLES = ("identifier", "category", "measurement", "time", "text", "ordinal", "ignored")
OPERATORS = (
    "eq",
    "ne",
    "gt",
    "ge",
    "lt",
    "le",
    "contains",
    "is_null",
    "not_null",
    "is_nan",
    "is_inf",
)


def validate_semantics(dataset):
    semantics = dataset.get("semantic_metadata", {})
    columns = {c["id"] for c in dataset.get("import_metadata", {}).get("columns", [])}
    if not isinstance(semantics, dict) or not set(semantics) <= columns:
        raise ProjectError("Rol metadata bilinmeyen ColumnId içeriyor.")
    if (
        not isinstance(dataset.get("analysis_unit", ""), str)
        or len(dataset.get("analysis_unit", "")) > 200
    ):
        raise ProjectError("Analiz birimi en fazla 200 karakter olmalı.")
    parents = dataset.get("parent_version_ids", [])
    if not isinstance(parents, list) or len(parents) > 1:
        raise ProjectError("Metadata sürümünün parent bağı geçersiz.")
    for parent in parents:
        entity_id(parent, "dv")
    for value in semantics.values():
        if not isinstance(value, dict) or set(value) != {
            "role",
            "unit",
            "ordinal_order",
            "confirmed",
        }:
            raise ProjectError("Sütun rolü alanları geçersiz.")
        if value["role"] not in ROLES or type(value["confirmed"]) is not bool:
            raise ProjectError("Sütun rolü/onay geçersiz.")
        if not isinstance(value["unit"], str) or len(value["unit"]) > 200:
            raise ProjectError("Ölçüm birimi en fazla 200 karakter olmalı.")
        order = value["ordinal_order"]
        if (
            not isinstance(order, list)
            or len(order) > 1000
            or any(not isinstance(v, str) or len(v) > 256 for v in order)
            or len(set(order)) != len(order)
        ):
            raise ProjectError(
                "Ordinal sıra en fazla1000 benzersiz metin değeri içermeli."
            )
        if value["role"] == "ordinal" and not order:
            raise ProjectError("Ordinal kategori için açık sıralama girin.")
        if value["role"] != "ordinal" and order:
            raise ProjectError("Kategori sırası yalnız ordinal rolde kullanılabilir.")


def metadata_version(dataset, column_id, role, unit, order, analysis_unit):
    result = copy.deepcopy(dataset)
    result["version_id"] = "dv:" + uid()
    result["parent_version_ids"] = [dataset["version_id"]]
    result["analysis_unit"] = analysis_unit
    result.setdefault("semantic_metadata", {})[column_id] = dict(
        role=role, unit=unit, ordinal_order=list(order), confirmed=True
    )
    validate_semantics(result)
    return result


@dataclass(frozen=True)
class ViewSpec:
    filters: tuple = ()
    sort_column: str = ""
    descending: bool = False
    hidden: tuple = ()

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) - {
            "filters",
            "sort_column",
            "descending",
            "hidden",
        }:
            raise ProjectError("Görünüm alanları geçersiz.")
        return cls(
            tuple(data.get("filters", ())),
            data.get("sort_column", ""),
            data.get("descending", False),
            tuple(data.get("hidden", ())),
        )

    def validate(self, columns):
        ids = {c["id"] for c in columns}
        if (
            type(self.descending) is not bool
            or self.sort_column
            and self.sort_column not in ids
            or not set(self.hidden) <= ids
            or len(set(self.hidden)) != len(self.hidden)
            or len(self.filters) > 8
        ):
            raise ProjectError("Sıralama/gizleme/filtre ColumnId bağı geçersiz.")
        for item in self.filters:
            if (
                not isinstance(item, dict)
                or set(item) != {"column_id", "operator", "value"}
                or item["column_id"] not in ids
                or item["operator"] not in OPERATORS
                or not isinstance(item["value"], str)
                or len(item["value"]) > 4096
            ):
                raise ProjectError("Filtre alanı/türü/değeri geçersiz.")

    def data(self):
        return dict(
            filters=list(self.filters),
            sort_column=self.sort_column,
            descending=self.descending,
            hidden=list(self.hidden),
        )


@dataclass(frozen=True)
class ProfileSpec:
    column_id: str
    sample: bool = True
    target: str = "dataset"
    ddof: int = 1
    view: ViewSpec = field(default_factory=ViewSpec)

    def validate(self, columns):
        if (
            self.column_id not in {c["id"] for c in columns}
            or type(self.sample) is not bool
            or self.target not in ("dataset", "view")
            or type(self.ddof) is not int
            or self.ddof not in (0, 1)
        ):
            raise ProjectError("Profil kapsamı/sütunu/ddof geçersiz.")
        self.view.validate(columns)
