"""Data-only recipes and persistent branch cursors; no executable expressions."""

import copy
from dataclasses import asdict, dataclass

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.storage.project_model import ProjectError, entity_id, uid

# Future kinds have a lineage contract, but are deliberately not executable.
LINEAGE = {
    "rename": "preserve RowId/SourceRecordId/ColumnId; change display name",
    "drop": "preserve RowId/SourceRecordId; remove selected ColumnId",
    "filter": "preserve surviving RowId/SourceRecordId and immutable input order",
    "sort": "preserve RowId/SourceRecordId; ties use immutable input order then RowId",
    "join": "new RowId per left/right/occurrence tuple; absent side has no source",
    "explode": "new RowId per parent/list-path/occurrence; equal elements stay distinct",
    "aggregate": "new RowId per group; lazy membership references immutable input/spec",
    "dedup": "retain first/last stable RowId; persist duplicate-group membership separately",
}
IMPLEMENTED = {"rename", "drop", "filter", "roles"}


def heads(state):
    result = {d["dataset_id"]: d["version_id"] for d in state["datasets"]}
    result.update(state.get("workflow", {}).get("heads", {}))
    return result


def active_datasets(state):
    current = heads(state)
    return [d for d in state["datasets"] if current[d["dataset_id"]] == d["version_id"]]


def workflow(state):
    return state.setdefault("workflow", {"heads": {}, "redo": {}})


def activate(state, dataset):
    w = workflow(state)
    w["heads"][dataset["dataset_id"]] = dataset["version_id"]
    # A new branch clears the redo cursor, never the old versions or results.
    w["redo"][dataset["dataset_id"]] = []


def move(state, dataset_id, direction):
    current = next(
        (d for d in active_datasets(state) if d["dataset_id"] == dataset_id), None
    )
    if not current:
        raise ProjectError("Dataset bulunamadı.")
    w = workflow(state)
    redo = w["redo"].setdefault(dataset_id, [])
    if direction == "undo":
        parents = current.get("parent_version_ids", [])
        if not parents:
            raise ProjectError("Kaynak sürümünden önce geri alınamaz.")
        redo.append(current["version_id"])
        target = parents[0]
    elif direction == "redo":
        if not redo:
            raise ProjectError("Yinelenecek adım yok.")
        target = redo.pop()
    else:
        raise ProjectError("Geçmiş eylemi bilinmiyor.")
    w["heads"][dataset_id] = target
    return target


@dataclass(frozen=True)
class OperationSpec:
    id: str
    kind: str
    input_version_id: str
    column_ids: tuple
    parameters: dict
    output_schema: tuple
    schema_version: int = 1
    method_version: int = 1
    learned_scope: str = "none"

    def data(self):
        data = asdict(self)
        data["column_ids"] = list(self.column_ids)
        data["output_schema"] = list(self.output_schema)
        return data

    @classmethod
    def from_dict(cls, value):
        try:
            spec = cls(**value)
            entity_id(spec.id, "op")
            entity_id(spec.input_version_id, "dv")
            if (
                type(spec.schema_version) is not int
                or spec.schema_version != 1
                or type(spec.method_version) is not int
                or spec.method_version != 1
                or spec.learned_scope != "none"
                or spec.kind not in IMPLEMENTED
                or not isinstance(spec.column_ids, (list, tuple))
                or len(set(spec.column_ids)) != len(spec.column_ids)
                or not isinstance(spec.parameters, dict)
                or not isinstance(spec.output_schema, (list, tuple))
            ):
                raise ProjectError("İşlem türü/sürümü/alanları desteklenmiyor.")
            for col in spec.column_ids:
                entity_id(col, "col")
            return spec
        except (TypeError, KeyError) as error:
            raise ProjectError("Tipli işlem alanları geçersiz.") from error


def build(request, kind, column_ids=(), parameters=None):
    columns = copy.deepcopy(request["columns"])
    ids = {c["id"] for c in columns}
    parameters = copy.deepcopy(parameters or {})
    if not set(column_ids) <= ids or len(set(column_ids)) != len(column_ids):
        raise ProjectError("İşlem bilinmeyen/tekrarlanan ColumnId içeriyor.")
    if kind == "rename":
        name = parameters.get("name")
        if (
            set(parameters) != {"name"}
            or len(column_ids) != 1
            or not isinstance(name, str)
            or not name.strip()
            or len(name) > 200
            or name.startswith("__vu_")
            or "\x00" in name
            or any(c["name"] == name and c["id"] != column_ids[0] for c in columns)
        ):
            raise ProjectError(
                "Yeni sütun adı boş, ayrılmış veya başka sütunla aynı olamaz."
            )
        next(c for c in columns if c["id"] == column_ids[0])["name"] = name
    elif kind == "drop":
        if parameters or not column_ids or len(column_ids) == len(columns):
            raise ProjectError("En az bir sütun korunmalı; çıkarılacak sütun seçin.")
        columns = [c for c in columns if c["id"] not in column_ids]
    elif kind == "filter":
        if set(parameters) != {"filters"} or not parameters["filters"]:
            raise ProjectError("Kalıcı filtre için en az bir koşul seçin.")
        filters = parameters["filters"]
        view_items = []
        for f in filters:
            if not isinstance(f, dict) or set(f) != {
                "column_id",
                "operator",
                "literal",
            }:
                raise ProjectError("Tipli filtre alanları geçersiz.")
            value = f["literal"]
            if not isinstance(value, dict) or set(value) != {"dtype", "text"}:
                raise ProjectError("Filtre literal fiziksel tür ve metin taşımalı.")
            col = next((c for c in columns if c["id"] == f["column_id"]), None)
            if not col or value["dtype"] != col["type"]:
                raise ProjectError("Filtre literal türü ColumnId ile uyuşmuyor.")
            view_items.append(
                dict(
                    column_id=f["column_id"],
                    operator=f["operator"],
                    value=value["text"],
                )
            )
        ViewSpec(filters=tuple(view_items)).validate(columns)
        if set(column_ids) != {f["column_id"] for f in filters}:
            raise ProjectError("Filtre kolon bağı koşullarla uyuşmuyor.")
    elif kind == "roles":
        from veri_ufku.analytics.contracts import validate_semantics

        if (
            set(parameters) != {"semantic_metadata", "analysis_unit"}
            or len(column_ids) != 1
        ):
            raise ProjectError("Rol işlemi alanları geçersiz.")
        validate_semantics(dict(import_metadata={"columns": columns}, **parameters))
    else:
        raise ProjectError(
            "Bu işlem henüz mevcut değil; yalnız köken sözleşmesi tanımlı."
        )
    return OperationSpec(
        "op:" + uid(),
        kind,
        request["version_id"],
        tuple(column_ids),
        parameters,
        tuple(columns),
    )


def validate(spec, request):
    spec = OperationSpec.from_dict(
        spec.data() if isinstance(spec, OperationSpec) else spec
    )
    if spec.input_version_id != request["version_id"]:
        raise ProjectError("İşlem eski giriş sürümüne bağlı; tekrar önizleyin.")
    expected = build(request, spec.kind, spec.column_ids, spec.parameters)
    if list(spec.output_schema) != list(expected.output_schema):
        raise ProjectError("İşlem çıktı şeması tarifle uyuşmuyor.")
    return spec


def filter_view(spec):
    return ViewSpec(
        filters=tuple(
            dict(
                column_id=f["column_id"],
                operator=f["operator"],
                value=f["literal"]["text"],
            )
            for f in spec.parameters["filters"]
        )
    )


def validate_workflow(state):
    w = state.get("workflow", {"heads": {}, "redo": {}})
    if (
        not isinstance(w, dict)
        or set(w) != {"heads", "redo"}
        or any(not isinstance(w[k], dict) for k in w)
    ):
        raise ProjectError("İşlem geçmişi alanları geçersiz.")
    versions = {d["version_id"]: d for d in state["datasets"]}
    for key, version in w["heads"].items():
        if version not in versions or versions[version]["dataset_id"] != key:
            raise ProjectError("Aktif işlem geçmişi sürümü bulunamadı.")
    for key, stack in w["redo"].items():
        if not isinstance(stack, list) or len(stack) > 10000 or key not in heads(state):
            raise ProjectError("Yineleme zinciri geçersiz.")
        parent = heads(state)[key]
        for version in reversed(stack):
            d = versions.get(version)
            if (
                not d
                or d["dataset_id"] != key
                or d.get("parent_version_ids") != [parent]
            ):
                raise ProjectError("Yineleme zinciri parent bağı geçersiz.")
            parent = version


@dataclass(frozen=True)
class RowLineageSpec:
    """Bounded policy descriptor; future relation artifacts do not expand UUID lists in JSON."""

    kind: str
    input_version_ids: tuple
    identity_policy: str
    relation_format: str
    method_version: int = 1

    def validate(self):
        policies = {
            "filter": ("preserve", "output_rowid_projection"),
            "sort": ("preserve", "ordered_output_rowids"),
            "join": ("new_per_match_occurrence", "parquet_left_right_occurrence"),
            "explode": ("new_per_item_occurrence", "parquet_parent_path_occurrence"),
            "aggregate": ("new_per_group", "lazy_immutable_membership"),
            "dedup": ("retain_stable_survivor", "parquet_duplicate_groups"),
        }
        if (
            self.kind not in policies
            or (self.identity_policy, self.relation_format) != policies[self.kind]
            or type(self.method_version) is not int
            or self.method_version != 1
        ):
            raise ProjectError("Satır kökeni yöntem/kimlik politikası geçersiz.")
        if len(self.input_version_ids) != (2 if self.kind == "join" else 1):
            raise ProjectError("Satır kökeni giriş sayısı geçersiz.")
        for version in self.input_version_ids:
            entity_id(version, "dv")
        return self
