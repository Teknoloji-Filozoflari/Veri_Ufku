"""Read-only bounded page model, explicit profile scope and semantic version edits."""

import copy
import json
import multiprocessing as mp
import os
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QAbstractTableModel,
    QModelIndex,
    QObject,
    Qt,
    QTimer,
    Signal,
    Slot,
)

from veri_ufku.analytics.cache import PageCache, page_key
from veri_ufku.analytics.contracts import ViewSpec, metadata_version
from veri_ufku.analytics.worker import process_entry
from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.jobs.admission import start_controller
from veri_ufku.storage.project_model import ProjectError, decode, encode, uid
from veri_ufku.ui.projects import project_error_text


class DatasetTableModel(QAbstractTableModel):
    columnsChanged = Signal()
    RowIdRole = Qt.UserRole + 1
    SourceIdRole = Qt.UserRole + 2
    MissingRole = Qt.UserRole + 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        self._null_cells = set()

    def roleNames(self):
        return {
            Qt.DisplayRole: b"display",
            self.RowIdRole: b"rowId",
            self.SourceIdRole: b"sourceRecordId",
            self.MissingRole: b"missing",
        }

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or not self.result else len(self.result["rows"])

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or not self.result else len(self.result["columns"])

    def data(self, index, role=Qt.DisplayRole):
        if (
            not self.result
            or not index.isValid()
            or not 0 <= index.row() < self.rowCount()
            or not 0 <= index.column() < self.columnCount()
        ):
            return None
        if role == self.MissingRole:
            return (index.row(), index.column()) in self._null_cells
        if role == Qt.DisplayRole:
            return self.result["rows"][index.row()][index.column()]
        if role == self.RowIdRole:
            return self.result["row_ids"][index.row()]
        if role == self.SourceIdRole:
            return self.result["source_record_ids"][index.row()]

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        count = self.columnCount() if orientation == Qt.Horizontal else self.rowCount()
        if not 0 <= section < count:
            return None
        if role == Qt.DisplayRole and self.result:
            if orientation != Qt.Horizontal:
                return str(self.result["offset"] + section + 1)
            column = self.result["columns"][section]
            parts = [
                column["name"],
                column.get("type") or column.get("physical_type", ""),
            ]
            role_label = column.get("role_label") or ""
            if role_label:
                parts.append(role_label)
            description = (column.get("description") or "").strip()
            if description:
                parts.append(description[:48] + ("…" if len(description) > 48 else ""))
            return " · ".join(part for part in parts if part)

    def flags(self, index):
        return (
            Qt.ItemIsEnabled | Qt.ItemIsSelectable
            if index.isValid()
            else Qt.NoItemFlags
        )

    def replace(self, result=None):
        old_columns = (self.result or {}).get("columns", [])
        new_columns = (result or {}).get("columns", [])
        self.beginResetModel()
        self.result = result
        self._null_cells = {
            tuple(cell) for cell in (result or {}).get("null_cells", ())
        }
        self.endResetModel()
        if old_columns != new_columns:
            self.columnsChanged.emit()


class InspectionTableModel(QAbstractTableModel):
    """Virtualized summary cells; these are statistics, never source RowIds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers, self.rows = [], []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.isValid():
            value = self.rows[index.row()][index.column()]
            if value is None:
                return "—"
            return str(value)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return (
                self.headers[section]
                if orientation == Qt.Horizontal
                else str(section + 1)
            )

    def replace(self, headers=(), rows=()):
        self.beginResetModel()
        self.headers, self.rows = list(headers), list(rows)
        self.endResetModel()


def latest_datasets(state):
    from veri_ufku.operations.contracts import active_datasets

    return [d for d in active_datasets(state) if d.get("import_metadata")]


class DatasetController(QObject):
    changed = Signal()
    rowSelected = Signal(str)

    def __init__(self, projects, cache, budget=ComputeBudget(), parent=None):
        super().__init__(parent)
        self.projects = projects
        self.cache = Path(cache)
        self.budget = budget
        self.model = DatasetTableModel(self)
        self.info_model = InspectionTableModel(self)
        self.describe_model = InspectionTableModel(self)
        self.page_cache = PageCache()
        self.cache_key = None
        self.context = mp.get_context("spawn")
        self.process = self.connection = self.cancel_event = None
        self.workspace = None
        self.signature = None
        self.dataset_id = ""
        self.column_id = ""
        self.view = ViewSpec()
        self.offset = 0
        self.total = 0
        self.revision = 0
        self.quality_result = None
        self.profile_result = None
        self.inventory_result = None
        self.describe_result = None
        self.suggestions = {}
        self._error = ""
        self._message = "Dataset seçin; tablo salt okunurdur."
        self._column_search = ""
        self._selection = ""
        self._selected_ids = []
        self.cancel_time = None
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        projects.changed.connect(self.project_changed)
        self.project_changed()

    busy = Property(bool, lambda self: self.process is not None, notify=changed)
    tableModel = Property(QObject, lambda self: self.model, constant=True)
    infoModel = Property(QObject, lambda self: self.info_model, constant=True)
    describeModel = Property(QObject, lambda self: self.describe_model, constant=True)
    datasets = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=d["dataset_id"],
                version=d["version_id"],
                label=f"Veri {i + 1} · {d['import_metadata']['row_count']} kayıt · {d['version_id'][-8:]}",
            )
            for i, d in enumerate(latest_datasets(self.projects.draft))
        ],
        notify=changed,
    )
    selectedDataset = Property(str, lambda self: self.dataset_id, notify=changed)
    selectedColumn = Property(str, lambda self: self.column_id, notify=changed)
    pageOffset = Property(int, lambda self: self.offset, notify=changed)
    pageRowCount = Property(int, lambda self: self.model.rowCount(), notify=changed)
    totalRows = Property(int, lambda self: self.total, notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    message = Property(str, lambda self: self._message, notify=changed)
    selectionText = Property(str, lambda self: self._selection, notify=changed)
    selectedRowIds = Property(
        "QVariantList", lambda self: self._selected_ids, notify=changed
    )
    profileResult = Property(
        "QVariantMap", lambda self: self.profile_result or {}, notify=changed
    )
    qualityResult = Property(
        "QVariantMap", lambda self: self.quality_result or {}, notify=changed
    )
    inventoryResult = Property(
        "QVariantMap", lambda self: self.inventory_result or {}, notify=changed
    )
    describeResult = Property(
        "QVariantMap", lambda self: self.describe_result or {}, notify=changed
    )
    filters = Property(
        "QVariantList", lambda self: list(self.view.filters), notify=changed
    )
    viewSummary = Property(str, lambda self: self._view_summary(), notify=changed)
    datasetColumns = Property(
        "QVariantList",
        lambda self: (
            self.dataset()["import_metadata"]["columns"] if self.dataset() else []
        ),
        notify=changed,
    )
    columns = Property("QVariantList", lambda self: self._columns(), notify=changed)
    columnDetails = Property(
        "QVariantMap", lambda self: self._details(), notify=changed
    )
    dataContent = Property("QVariantMap", lambda self: self._content(), notify=changed)
    dataDictionary = Property(
        "QVariantList", lambda self: self._dictionary(), notify=changed
    )

    def _content(self):
        d = self.dataset()
        if not d:
            return {}
        source = next(
            (s for s in self.projects.draft["sources"] if s["id"] == d["source_id"]),
            {},
        )
        return dict(
            rows=d["import_metadata"]["row_count"],
            columns=len(d["import_metadata"]["columns"]),
            source=Path(source.get("path", "")).name,
            version=d["version_id"],
            analysis_unit=d.get("analysis_unit", ""),
        )

    def _dictionary(self):
        d = self.dataset()
        if not d:
            return []
        roles = dict(
            identifier="Kimlik",
            category="Kategori",
            measurement="Ölçüm",
            time="Tarih / zaman",
            text="Metin",
            ordinal="Sıralı kategori",
            ignored="Analizde dışarıda",
        )
        values = []
        for c in d["import_metadata"]["columns"]:
            semantics = d.get("semantic_metadata", {}).get(c["id"], {})
            values.append(
                dict(
                    id=c["id"],
                    name=c["name"],
                    physical_type=c["type"],
                    role=roles.get(semantics.get("role"), "Rol henüz onaylanmadı"),
                    unit=semantics.get("unit", ""),
                    description=semantics.get("description", ""),
                )
            )
        return values

    def dataset(self):
        return next(
            (
                d
                for d in latest_datasets(self.projects.draft)
                if d["dataset_id"] == self.dataset_id
            ),
            None,
        )

    def saved_quality(self):
        d = self.dataset()
        if not d:
            return None
        return next(
            (
                copy.deepcopy(r["quality"])
                for r in reversed(self.projects.draft["results"])
                if r.get("capability_id") == "dataset.quality"
                and r.get("quality", {}).get("dataset_version") == d["version_id"]
            ),
            None,
        )

    def _columns(self):
        d = self.dataset()
        if not d:
            return []
        roles = dict(
            identifier="Kimlik",
            category="Kategori",
            measurement="Ölçüm",
            time="Tarih / zaman",
            text="Metin",
            ordinal="Sıralı kategori",
            ignored="Analizde dışarıda",
        )
        return [
            dict(
                c,
                physical_type=self.suggestions.get(c["id"], {}).get(
                    "physical_type", c["type"]
                ),
                role=roles.get(
                    (d.get("semantic_metadata", {}).get(c["id"], {}) or {}).get("role"),
                    "Rol henüz onaylanmadı",
                ),
                description=(d.get("semantic_metadata", {}).get(c["id"], {}) or {}).get(
                    "description", ""
                ),
                hidden=c["id"] in self.view.hidden,
                selected=c["id"] == self.column_id,
            )
            for c in d["import_metadata"]["columns"]
            if self._column_search.casefold() in c["name"].casefold()
        ]

    def _details(self):
        d = self.dataset()
        if not d:
            return {}
        c = next(
            (c for c in d["import_metadata"]["columns"] if c["id"] == self.column_id),
            None,
        )
        if not c:
            return {}
        semantics = d.get("semantic_metadata", {}).get(c["id"])
        proposal = self.suggestions.get(
            c["id"],
            dict(
                role="text",
                reason="Profil/sınırlı örnek hesaplandıktan sonra öneri güncellenir.",
            ),
        )
        return dict(
            c,
            role=semantics["role"] if semantics else proposal["role"],
            confirmed=semantics.get("confirmed", False) if semantics else False,
            unit=semantics["unit"] if semantics else "",
            ordinal_order=semantics["ordinal_order"] if semantics else [],
            analysis_unit=d.get("analysis_unit", ""),
            description=semantics.get("description", "") if semantics else "",
            measurement_level=semantics.get("measurement_level", "unknown")
            if semantics
            else "unknown",
            physical_type=self.projects.store.manifest["artifacts"][d["snapshot_uri"]][
                "schema"
            ].get(c["name"], c["type"]),
            proposal=proposal["role"],
            reason=proposal["reason"],
        )

    def _view_summary(self):
        d = self.dataset()
        if not d:
            return "Tablo için önce dosya içe aktarın."
        filters = "; ".join(
            f"{next(c['name'] for c in d['import_metadata']['columns'] if c['id'] == f['column_id'])} {f['operator']} {f['value']}"
            for f in self.view.filters
        )
        return f"Salt okunur · Görünüm: {'filtreli alt küme' if self.view.filters else 'tüm veri'} · {self.total} / {d['import_metadata']['row_count']} kayıt · {len(d['import_metadata']['columns'])} sütun\nVeri sürümü: {d['version_id']}\nAktif filtreler: {filters or 'yok'}. Gizli sütun: {len(self.view.hidden)}. Görünüm filtreleri analiz dataset’ini değiştirmez; profil kapsamını ayrıca seçin."

    def project_changed(self):
        signature = (
            str(self.projects.store.root) if self.projects.store else "",
            tuple(
                (d["dataset_id"], d["version_id"])
                for d in latest_datasets(self.projects.draft)
            ),
        )
        if signature == self.signature:
            return self.changed.emit()
        self.signature = signature
        self.abort()
        ds = latest_datasets(self.projects.draft)
        self.dataset_id = (
            self.dataset_id
            if any(d["dataset_id"] == self.dataset_id for d in ds)
            else ds[-1]["dataset_id"]
            if ds
            else ""
        )
        d = self.dataset()
        self.column_id = d["import_metadata"]["columns"][0]["id"] if d else ""
        self.view = ViewSpec()
        self.offset = self.total = 0
        self.quality_result = self.saved_quality()
        self.profile_result = None
        self.suggestions = {}
        self.inventory_result = self.describe_result = None
        self.info_model.replace()
        self.describe_model.replace()
        self.model.replace()
        self._selection = ""
        self._selected_ids = []
        self.revision += 1
        self.changed.emit()

    def fail(self, error):
        self._error = project_error_text(error)
        self.changed.emit()

    @Slot(str)
    def selectDataset(self, value):
        if self.busy:
            return
        if any(d["dataset_id"] == value for d in latest_datasets(self.projects.draft)):
            self.dataset_id = value
            self.column_id = self.dataset()["import_metadata"]["columns"][0]["id"]
            self.view = ViewSpec()
            self.quality_result = self.saved_quality()
            self.profile_result = None
            self.inventory_result = self.describe_result = None
            self.info_model.replace()
            self.describe_model.replace()
            self.offset = 0
            self.revision += 1
            self.refresh()

    @Slot(str)
    def selectColumn(self, value):
        d = self.dataset()
        if d and any(c["id"] == value for c in d["import_metadata"]["columns"]):
            self.column_id = value
            self.quality_result = None
            self.profile_result = None
            self.changed.emit()

    @Slot(str)
    def searchColumns(self, value):
        self._column_search = value[:200]
        self.changed.emit()

    @Slot(str, bool)
    def hideColumn(self, value, hidden):
        if self.busy or not self.dataset():
            return
        values = set(self.view.hidden)
        if hidden:
            values.add(value)
        else:
            values.discard(value)
        data = self.view.data()
        data["hidden"] = list(values)
        try:
            view = ViewSpec.from_dict(data)
            view.validate(self.dataset()["import_metadata"]["columns"])
            self.view = view
            self.revision += 1
            self.refresh()
        except (ValueError, TypeError) as error:
            self.fail(error)

    @Slot(str, bool)
    def sort(self, value, descending):
        if self.busy:
            return
        data = self.view.data()
        data.update(sort_column=value, descending=descending)
        self.change_view(data)

    def change_view(self, data):
        try:
            view = ViewSpec.from_dict(data)
            view.validate(self.dataset()["import_metadata"]["columns"])
            self.view = view
            self.offset = 0
            self.quality_result = None
            self.profile_result = None
            self.revision += 1
            self.model.replace()
            self._selection = ""
            self._selected_ids = []
            self.refresh()
        except (ValueError, TypeError, AttributeError) as error:
            self.fail(error)

    @Slot(str, str, str)
    def addFilter(self, column_id, operator, value):
        if self.busy:
            return
        data = self.view.data()
        data["filters"].append(
            dict(column_id=column_id, operator=operator, value=value)
        )
        self.change_view(data)

    @Slot()
    def clearFilters(self):
        if not self.busy:
            data = self.view.data()
            data["filters"] = []
            self.change_view(data)

    @Slot()
    def refresh(self):
        self.start("page", dict(view=self.view.data(), offset=self.offset))

    @Slot(int)
    def goPage(self, offset):
        if self.busy or offset < 0:
            return
        self.offset = offset
        self.refresh()

    @Slot(bool, str, str, str, str)
    def computeQuality(self, sample, target, purpose, duplicate_columns, rules):
        try:
            import json

            parameters = dict(
                view=self.view.data(),
                sample=sample,
                target=target,
                purpose=purpose,
                duplicate_columns=json.loads(duplicate_columns),
                rules=json.loads(rules),
            )
            from veri_ufku.analytics.quality import validate

            validate(parameters, self.dataset()["import_metadata"]["columns"])
            self.quality_result = None
            self.start("quality", parameters)
        except (ValueError, TypeError, AttributeError) as error:
            self.fail(error)

    @Slot()
    def saveQuality(self):
        if not self.quality_result or self.projects.readOnly or self.projects.busy:
            return
        d = self.dataset()
        if self.quality_result["dataset_version"] != d["version_id"]:
            return self.fail(ProjectError("Kalite raporu eski veri sürümüne ait."))
        self.projects.draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[d["version_id"]],
                seed=None,
                capability_id="dataset.quality",
                quality=decode(encode(self.quality_result)),
            )
        )
        self.projects.changed.emit()
        self._message = "Kalite raporu taslağa eklendi; Projeyi kaydet ile kalıcı olur."
        self.changed.emit()

    @Slot(bool, str, int)
    def computeProfile(self, sample=True, target="dataset", ddof=1):
        self.start(
            "profile",
            dict(
                view=self.view.data(),
                column_id=self.column_id,
                sample=sample,
                target=target,
                ddof=ddof,
            ),
        )

    @Slot(bool, bool)
    def inspectColumns(self, sample=True, describe=False):
        self.start(
            "describe" if describe else "inventory",
            dict(view=ViewSpec().data(), sample=sample),
        )

    @Slot(bool, int, str)
    def inspectValues(self, sample=True, offset=0, query=""):
        self.start(
            "profile",
            dict(
                view=ViewSpec().data(),
                column_id=self.column_id,
                sample=sample,
                target="dataset",
                ddof=1,
                unique_offset=offset,
                unique_query=query,
            ),
        )

    @Slot(int, int, bool)
    def selectInspectionCell(self, row, column, descriptive=False):
        result = self.describe_result if descriptive else self.inventory_result
        if not result:
            return
        columns = (
            [c for c in result["columns"] if c.get("numeric")]
            if descriptive
            else result["columns"]
        )
        index = column - 1 if descriptive else row
        if 0 <= index < len(columns):
            self.selectColumn(columns[index]["id"])

    def publish_inspection(self, value, descriptive):
        columns = value["columns"]
        if not descriptive:
            self.info_model.replace(
                ["Sütun", "Veri türü", "Dolu", "Null", "NaN"],
                [
                    [
                        c["name"],
                        c["physical_type"],
                        c["non_null"],
                        c["null"],
                        c["nan"],
                    ]
                    for c in columns
                ],
            )
            return
        numeric = [c for c in columns if c.get("numeric")]
        keys = [
            ("Sonlu değer sayısı", "finite_n"),
            ("Ortalama", "mean"),
            ("Standart sapma (ddof=1)", "std"),
            ("En küçük", "minimum"),
            ("%25", "0.25"),
            ("Medyan (%50)", "0.5"),
            ("%75", "0.75"),
            ("En büyük", "maximum"),
        ]
        rows = []
        for label, key in keys:
            row = [label]
            for c in numeric:
                n = c["numeric"]
                value = (
                    None
                    if n["suppressed"]
                    else n["quantiles"].get(key)
                    if key.startswith("0.")
                    else n.get(key)
                )
                row.append(value)
            rows.append(row)
        self.describe_model.replace(["İstatistik"] + [c["name"] for c in numeric], rows)

    @Slot(str, str, str, str)
    @Slot(str, str, str, str, str)
    def applyRole(
        self,
        role,
        unit,
        order,
        analysis_unit,
        description=None,
        *,
        confirm=True,
        ordinal_order=None,
    ):
        if self.busy or self.projects.busy or self.projects.readOnly:
            return self.fail(
                ProjectError("Rol değişikliği için yazılabilir ve boşta proje gerekli.")
            )
        try:
            d = self.dataset()
            if not d or not self.column_id:
                raise ProjectError("Sütun seçin.")
            result = metadata_version(
                d,
                self.column_id,
                role,
                unit,
                ordinal_order
                if ordinal_order is not None
                else order.split("|")
                if order
                else [],
                analysis_unit,
                description,
            )
            result["semantic_metadata"][self.column_id]["confirmed"] = confirm
            from veri_ufku.operations.contracts import activate, build

            spec = build(
                dict(
                    columns=d["import_metadata"]["columns"], version_id=d["version_id"]
                ),
                "roles",
                [self.column_id],
                dict(
                    semantic_metadata=result["semantic_metadata"],
                    analysis_unit=analysis_unit,
                ),
            )
            artifact = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
            result.update(operation_id=spec.id, output_schema=artifact["schema"])
            self.projects.draft["datasets"].append(result)
            self.projects.draft["operations"].append(
                dict(
                    id=spec.id,
                    dataset_version_ids=[d["version_id"], result["version_id"]],
                    seed=None,
                    capability_id="dataset.roles",
                    spec=spec.data(),
                    output_version_id=result["version_id"],
                    status="succeeded",
                    applicability={"applicable": True},
                    validation={"valid": True},
                    impact={
                        "scope": "full",
                        "changed_rows": 0,
                        "changed_columns": 1,
                        "changed_cells": 0,
                    },
                )
            )
            activate(self.projects.draft, result)
            chosen = self.column_id
            self.projects.changed.emit()
            self.column_id = chosen
            self._message = "Rol metadata sürümü oluşturuldu; fiziksel tür ve RowId değişmedi. Görünüm filtreleri sıfırlandı. Kalıcı kayıt için Projeyi kaydet seçin."
            self.changed.emit()
        except (ValueError, TypeError) as error:
            self.fail(error)

    @Slot(str, result=bool)
    def applyDescription(self, description):
        d = self.dataset()
        if not d or not self.column_id:
            self.fail(ProjectError("Açıklama eklemek için bir sütun seçin."))
            return False
        from veri_ufku.analytics.dataset import suggest_role
        from veri_ufku.operations.types import dtype_of

        previous = d.get("semantic_metadata", {}).get(self.column_id, {})
        c = next(
            c for c in d["import_metadata"]["columns"] if c["id"] == self.column_id
        )
        role = (
            previous.get("role") or suggest_role(c["name"], dtype_of(c["type"]), [])[0]
        )
        version = d["version_id"]
        self.applyRole(
            role,
            previous.get("unit", ""),
            "",
            d.get("analysis_unit", ""),
            description,
            confirm=previous.get("confirmed", False),
            ordinal_order=previous.get("ordinal_order", []),
        )
        return self.dataset()["version_id"] != version

    @Slot()
    def saveProfile(self):
        if not self.profile_result or self.projects.readOnly or self.projects.busy:
            return
        d = self.dataset()
        if self.profile_result["dataset_version"] != d["version_id"]:
            return self.fail(
                ProjectError("Profil eski veri sürümüne ait. Yeniden hesaplayın.")
            )
        result = decode(encode(self.profile_result))
        self.projects.draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[d["version_id"]],
                seed=None,
                capability_id="dataset.profile",
                profile=result,
            )
        )
        self.projects.changed.emit()
        self._message = "Profil, kapsamı ve yöntemleriyle proje taslağına eklendi; Projeyi kaydet ile kalıcı olur."
        self.changed.emit()

    @Slot(int)
    def selectRow(self, index):
        if self.model.result and 0 <= index < self.model.rowCount():
            result = self.model.result
            self._selected_ids = [result["row_ids"][index]]
            self.rowSelected.emit(result["row_ids"][index])
            source_id = result["source_record_ids"][index]
            origin = (
                "SourceRecordId " + source_id
                if source_id
                else "Tek bir kaynak kayıt kimliği yok; bu satırın tüm girdileri işlem kökeni Parquet'inde kayıtlı."
            )
            self._selection = f"Görüntü sırası {result['offset'] + index + 1} · RowId {result['row_ids'][index]} · {origin}"
            self.changed.emit()

    @Slot(result=bool)
    def copyVisibleSelection(self):
        """Explicit clipboard action; bounded displayed values, never a full read."""
        from PySide6.QtGui import QGuiApplication

        result = self.model.result
        if not result:
            return False
        selected = set(self._selected_ids)
        rows = [
            dict(row_id=row_id, displayed_values=result["rows"][index])
            for index, row_id in enumerate(result["row_ids"])
            if row_id in selected
        ]
        if not rows:
            return False
        QGuiApplication.clipboard().setText(
            json.dumps(
                dict(columns=[c["name"] for c in result["columns"]], rows=rows),
                ensure_ascii=False,
                indent=2,
            )
        )
        self._message = "Bu sayfada seçili satırların görünen metni JSON olarak kopyalandı; kısaltılmış hücreler tam veri değildir."
        self.changed.emit()
        return True

    def selectChartRows(self, row_ids, count):
        self._selected_ids = list(row_ids)
        self._selection = f"Grafik seçimi: {count} gerçek RowId; bu sayfada {len(row_ids)} eşleşme. Toplulaştırılmış nokta tüm üyelerini seçer."
        self.changed.emit()

    def start(self, action, parameters):
        if self.busy or self.projects.busy:
            return self.fail(ProjectError("Devam eden işi bekleyin veya iptal edin."))
        try:
            d = self.dataset()
            if not d:
                raise ProjectError("Önce dataset içe aktarın.")
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="view-", dir=self.cache)
            artifact = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
            request = dict(
                path=str(self.projects.store.path(d["snapshot_uri"])).replace(
                    "/proc/self/", f"/proc/{os.getpid()}/", 1
                ),
                fingerprint={k: artifact[k] for k in ("sha256", "size")},
                columns=copy.deepcopy(d["import_metadata"]["columns"]),
                row_count=d["import_metadata"]["row_count"],
                import_bad_count=d["import_metadata"].get("bad_count", 0),
                import_settings=copy.deepcopy(d["import_metadata"].get("settings", {})),
                version_id=d["version_id"],
                snapshot_uri=d["snapshot_uri"],
                source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
                semantic_metadata=copy.deepcopy(d.get("semantic_metadata", {})),
                config_revision=self.revision,
            )
            self.binding = (
                self.signature,
                d["version_id"],
                self.revision,
                self.column_id,
            )
            self.action = action
            if action == "page":
                self.cache_key = page_key(request, parameters)
                cached = self.page_cache.get(self.cache_key)
                if cached is not None:
                    parameters = dict(parameters, cached_page=cached)
            self.started = time.monotonic()
            self.cancel_time = None
            self.cancel_event = self.context.Event()
            self.connection, sender = self.context.Pipe(duplex=False)
            self.process = self.context.Process(
                target=process_entry,
                args=(
                    action,
                    request,
                    parameters,
                    self.workspace,
                    self.cancel_event,
                    sender,
                    self.budget,
                ),
            )
            if not start_controller(self, sender):
                return
            sender.close()
            self.projects.dataset_active = True
            self.projects.changed.emit()
            self._error = ""
            self._message = "Dataset değiştirilmeden sorgulanıyor…"
            self.changed.emit()
        except (ValueError, OSError, KeyError) as error:
            self.abort()
            self.fail(error)

    @Slot()
    def cancel(self):
        if self.busy:
            self.cancel_event.set()
            self.cancel_time = self.cancel_time or time.monotonic()
            self._message = "İptal isteniyor…"
            self.changed.emit()

    def release(self):
        if self.process:
            if self.process.pid is not None:
                self.process.join(timeout=0.1)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=0.2)
            if self.process.is_alive():
                self.process.kill()
                self.process.join()
            self.process.close()
            self.process = None
        if self.connection:
            self.connection.close()
            self.connection = None
        if self.workspace:
            shutil.rmtree(self.workspace)
            self.workspace = None
        self.projects.dataset_active = False

    def abort(self):
        self.release()

    def poll(self):
        if not self.busy:
            return
        if time.monotonic() - self.started > self.budget.max_wall_seconds:
            self.cancel()
        if (
            self.cancel_time
            and time.monotonic() - self.cancel_time > self.budget.cancel_grace_ms / 1000
        ):
            self.release()
            self._message = "İptal edildi; dataset değişmedi."
            self.projects.changed.emit()
            self.changed.emit()
            return
        for _ in range(30):
            if not self.connection.poll():
                break
            try:
                kind, value = self.connection.recv()
            except EOFError:
                break
            if kind == "progress":
                self._message = f"{value.phase}: {value.done} / {value.total if value.total is not None else '?'}"
                self.changed.emit()
                continue
            canceled = self.cancel_event.is_set()
            valid = self.binding == (
                self.signature,
                self.dataset()["version_id"] if self.dataset() else "",
                self.revision,
                self.column_id,
            )
            self.release()
            if canceled or kind == "canceled":
                self._message = "İptal edildi; dataset değişmedi."
            elif not valid:
                self._message = (
                    "Eski veri/yapılandırma sonucu güncel panele bağlanmadı."
                )
            elif kind == "error":
                self._error = value
            elif self.action == "page":
                self.page_cache.put(self.cache_key, value)
                roles = dict(
                    identifier="Kimlik",
                    category="Kategori",
                    measurement="Ölçüm",
                    time="Tarih / zaman",
                    text="Metin",
                    ordinal="Sıralı kategori",
                    ignored="Analizde dışarıda",
                )
                dataset = self.dataset() or {}
                semantics = dataset.get("semantic_metadata", {})
                annotated = []
                for column in value["columns"]:
                    meta = semantics.get(column["id"], {})
                    annotated.append(
                        dict(
                            column,
                            role_label=roles.get(meta.get("role"), ""),
                            description=meta.get("description", ""),
                        )
                    )
                value = dict(value, columns=annotated)
                self.model.replace(value)
                self.total = value["total"]
                self.suggestions = copy.deepcopy(value["suggestions"])
                self._message = (
                    f"Sayfa: {value['offset'] + 1 if value['rows'] else 0}–"
                    f"{value['offset'] + len(value['rows'])} / {value['total']} "
                    f"(görünen sayfa; tam veri değil). Model en fazla200 kayıt taşır."
                )
            elif self.action == "quality":
                self.quality_result = value
                self._message = f"Kalite taraması: {value['scope']} · {value['used_n']}/{value['population_n']} kayıt; veri değiştirilmedi."
            elif self.action in {"inventory", "describe"}:
                self.publish_inspection(value, self.action == "describe")
                if self.action == "inventory":
                    self.inventory_result = value
                else:
                    self.describe_result = value
                self._message = f"Sütun özeti: {value['scope']} · {value['used_n']}/{value['population_n']} kayıt; veri değiştirilmedi."
            else:
                self.profile_result = value
                self.suggestions[value["column_id"]] = dict(
                    role=value["role_proposal"],
                    reason=value["role_reason"],
                    physical_type=value["physical_type"],
                )
                self._message = f"Profil: {value['scope']} · kullanılan {value['used_n']} / {value['population_n']} · veri sürümü {value['dataset_version']}"
            self.projects.changed.emit()
            self.changed.emit()
            return
        if self.process and not self.process.is_alive() and not self.connection.poll():
            self.release()
            self._error = "Tablo/profil süreci durdu; sonuç kabul edilmedi."
            self.projects.changed.emit()
            self.changed.emit()

    def shutdown(self):
        self.timer.stop()
        self.abort()
