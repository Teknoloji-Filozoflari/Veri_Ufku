"""Read-only bounded page model, explicit profile scope and semantic version edits."""

import copy
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

from veri_ufku.analytics.contracts import ViewSpec, metadata_version
from veri_ufku.analytics.worker import process_entry
from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.storage.project_model import ProjectError, decode, encode, uid
from veri_ufku.ui.projects import project_error_text


class DatasetTableModel(QAbstractTableModel):
    RowIdRole = Qt.UserRole + 1
    SourceIdRole = Qt.UserRole + 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None

    def roleNames(self):
        return {
            Qt.DisplayRole: b"display",
            self.RowIdRole: b"rowId",
            self.SourceIdRole: b"sourceRecordId",
        }

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or not self.result else len(self.result["rows"])

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or not self.result else len(self.result["columns"])

    def data(self, index, role=Qt.DisplayRole):
        if not self.result or not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self.result["rows"][index.row()][index.column()]
        if role == self.RowIdRole:
            return self.result["row_ids"][index.row()]
        if role == self.SourceIdRole:
            return self.result["source_record_ids"][index.row()]

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and self.result:
            return (
                self.result["columns"][section]["name"]
                if orientation == Qt.Horizontal
                else str(self.result["offset"] + section + 1)
            )

    def flags(self, index):
        return (
            Qt.ItemIsEnabled | Qt.ItemIsSelectable
            if index.isValid()
            else Qt.NoItemFlags
        )

    def replace(self, result=None):
        self.beginResetModel()
        self.result = result
        self.endResetModel()


def latest_datasets(state):
    from veri_ufku.operations.contracts import active_datasets

    return [d for d in active_datasets(state) if d.get("import_metadata")]


class DatasetController(QObject):
    changed = Signal()

    def __init__(self, projects, cache, budget=ComputeBudget(), parent=None):
        super().__init__(parent)
        self.projects = projects
        self.cache = Path(cache)
        self.budget = budget
        self.model = DatasetTableModel(self)
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
        self.suggestions = {}
        self._error = ""
        self._message = "Dataset seçin; tablo salt okunurdur."
        self._column_search = ""
        self._selection = ""
        self.cancel_time = None
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        projects.changed.connect(self.project_changed)
        self.project_changed()

    busy = Property(bool, lambda self: self.process is not None, notify=changed)
    tableModel = Property(QObject, lambda self: self.model, constant=True)
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
    totalRows = Property(int, lambda self: self.total, notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    message = Property(str, lambda self: self._message, notify=changed)
    selectionText = Property(str, lambda self: self._selection, notify=changed)
    profileResult = Property(
        "QVariantMap", lambda self: self.profile_result or {}, notify=changed
    )
    qualityResult = Property(
        "QVariantMap", lambda self: self.quality_result or {}, notify=changed
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
        return [
            dict(
                c,
                physical_type=self.suggestions.get(c["id"], {}).get(
                    "physical_type", c["type"]
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
            confirmed=bool(semantics),
            unit=semantics["unit"] if semantics else "",
            ordinal_order=semantics["ordinal_order"] if semantics else [],
            analysis_unit=d.get("analysis_unit", ""),
            physical_type=proposal.get("physical_type", c["type"]),
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
        self.model.replace()
        self._selection = ""
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

    @Slot(str, str, str, str)
    def applyRole(self, role, unit, order, analysis_unit):
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
                order.split("|") if order else [],
                analysis_unit,
            )
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
            source_id = result["source_record_ids"][index]
            origin = (
                "SourceRecordId " + source_id
                if source_id
                else "Tek bir kaynak kayıt kimliği yok; bu satırın tüm girdileri işlem kökeni Parquet'inde kayıtlı."
            )
            self._selection = f"Görüntü sırası {result['offset'] + index + 1} · RowId {result['row_ids'][index]} · {origin}"
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
            self.started = time.monotonic()
            self.cancel_time = None
            self.cancel_event = self.context.Event()
            self.connection, sender = self.context.Pipe(duplex=False)
            os.environ.setdefault("POLARS_MAX_THREADS", str(self.budget.cpu_threads))
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
            self.process.start()
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
                self.model.replace(value)
                self.total = value["total"]
                self.suggestions = value["suggestions"]
                self._message = f"Sayfa: {value['offset'] + 1 if value['rows'] else 0}–{value['offset'] + len(value['rows'])}; model en fazla200 kayıt taşır."
            elif self.action == "quality":
                self.quality_result = value
                self._message = f"Kalite taraması: {value['scope']} · {value['used_n']}/{value['population_n']} kayıt; veri değiştirilmedi."
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
