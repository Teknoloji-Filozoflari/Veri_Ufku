"""Explicit preview/apply and persisted history, with compute off the GUI thread."""

import copy
import json
import multiprocessing as mp
import os
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from veri_ufku.jobs.admission import start_controller
from veri_ufku.operations.contracts import activate, active_datasets, build, move
from veri_ufku.operations.worker import process_entry
from veri_ufku.storage.project_model import ProjectError, decode, uid
from veri_ufku.ui.dataset import DatasetTableModel
from veri_ufku.ui.projects import project_error_text


def publish(store, state, result=None):
    previous = store.state
    store.state = state
    try:
        if result:
            store.publish_operation(result)
        else:
            store.save()
        return copy.deepcopy(store.state)
    except BaseException:
        # publish_operation reconciles a post-ACTIVE durability failure itself.
        if not result:
            pointer = decode(store._read("ACTIVE", 4096))
            if pointer["commit_id"] != store.commit_id:
                store._load("ACTIVE")
            else:
                store.state = previous
        raise


class OperationsController(QObject):
    changed = Signal()

    def __init__(self, data, projects, cache, budget, parent=None):
        super().__init__(parent)
        self.data, self.projects = data, projects
        self.cache, self.budget = Path(cache), budget
        self.before = DatasetTableModel(self)
        self.after = DatasetTableModel(self)
        self.process = self.connection = self.cancel_event = self.future = None
        self.workspace = None
        self.preview = None
        self.binding = None
        self.signature = None
        self._message = "Kaynak korunur. Önizleme tüm veriyi hesaplar; tablolar ilk200 kaydı gösterir."
        self._error = ""
        self._state = "idle"
        self.cancel_time = None
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        projects.changed.connect(self.project_changed)
        data.changed.connect(self.changed)

    busy = Property(
        bool,
        lambda self: self.process is not None or self.future is not None,
        notify=changed,
    )
    message = Property(str, lambda self: self._message, notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    state = Property(str, lambda self: self._state, notify=changed)
    beforeModel = Property(QObject, lambda self: self.before, constant=True)
    afterModel = Property(QObject, lambda self: self.after, constant=True)
    canApply = Property(
        bool,
        lambda self: bool(
            self.preview
            and self.preview.get("diagnostics", {}).get("publication_allowed", True)
            and not self.busy
            and not self.projects.busy
            and not self.projects.readOnly
            and self.binding == self.current_binding()
        ),
        notify=changed,
    )
    previewResult = Property(
        "QVariantMap",
        lambda self: {
            k: v
            for k, v in (self.preview or {}).items()
            if k not in ("before", "after", "path")
        },
        notify=changed,
    )
    history = Property("QVariantList", lambda self: self.history_rows(), notify=changed)
    resultStatuses = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label=r.get("capability_id", "Sonuç"),
                current=r["current"],
                versions=", ".join(r["dataset_version_ids"]),
            )
            for r in self.projects._result_statuses()
        ],
        notify=changed,
    )

    leakageHistory = Property(
        "QVariantList",
        lambda self: [
            dict(
                kind=o.get("spec", {}).get("kind", ""),
                input_version=o.get("spec", {}).get("input_version_id", ""),
                method=o.get("spec", {}).get("parameters", {}).get("method", ""),
                scope=o.get("spec", {}).get("learned_scope", ""),
                output_version=o.get("output_version_id", ""),
            )
            for o in self.projects.draft["operations"]
            if o.get("leakage_review_required")
        ],
        notify=changed,
    )

    def native_columns(self, d):
        if not d or not self.projects.store:
            return []
        schema = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]["schema"]
        return [
            dict(c, type=schema[c["name"]]) for c in d["import_metadata"]["columns"]
        ]

    transformColumns = Property(
        "QVariantList",
        lambda self: self.native_columns(self.data.dataset()),
        notify=changed,
    )

    secondaryDatasets = Property(
        "QVariantList",
        lambda self: [
            dict(
                version_id=d["version_id"],
                label=Path(
                    next(
                        (
                            s["path"]
                            for s in self.projects.draft["sources"]
                            if s["id"] == d["source_id"]
                        ),
                        "Dataset",
                    )
                ).name
                + " · "
                + str(d["import_metadata"]["row_count"])
                + " kayıt · "
                + d["version_id"][-8:],
                columns=self.native_columns(d),
            )
            for d in active_datasets(self.projects.draft)
        ],
        notify=changed,
    )

    contractRecipe = Property(
        "QVariantMap", lambda self: self.contract_recipe(), notify=changed
    )
    contractReport = Property(
        "QVariantMap", lambda self: self.contract_report(), notify=changed
    )

    def contract_report(self):
        if self.preview and self.preview.get("diagnostics", {}).get("contract_report"):
            return dict(
                report=copy.deepcopy(self.preview["diagnostics"]["contract_report"]),
                policy=self.preview["diagnostics"]["policy"],
                output_version=self.preview["version_id"],
                current=True,
                saved=False,
            )
        d = self.data.dataset() or {}
        reference = d.get("schema_contract", {}).get("report_operation")
        op = next(
            (o for o in self.projects.draft["operations"] if o["id"] == reference), None
        )
        if not op:
            return {}
        return dict(
            report=copy.deepcopy(op.get("diagnostics", {}).get("contract_report", {})),
            policy=op["spec"]["parameters"]["policy"],
            output_version=op["output_version_id"],
            current=op["output_version_id"] == d.get("version_id"),
            saved=True,
        )

    identityJournal = Property(
        "QVariantList", lambda self: self.identity_journal(), notify=changed
    )

    def contract_recipe(self):
        d = self.data.dataset()
        if not d:
            return {}
        return dict(
            contract=copy.deepcopy(
                d.get("schema_contract", {}).get(
                    "definition", {"schema_version": 1, "rules": []}
                )
            ),
            semantic_metadata=copy.deepcopy(d.get("semantic_metadata", {})),
            analysis_unit=d.get("analysis_unit", ""),
        )

    def identity_journal(self):
        records = []
        for op in self.projects.draft["operations"]:
            if op.get("spec", {}).get("kind") not in ("entity_merge", "category_map"):
                continue
            versions = op["dataset_version_ids"]
            descendants = set(versions)
            for d in self.projects.draft["datasets"]:
                if any(
                    v in descendants
                    for v in d.get("parent_version_ids", [])
                    + d.get("input_version_ids", [])
                    + (
                        [d["derived_analysis"]["source_version"]]
                        if d.get("derived_analysis")
                        else []
                    )
                    + (
                        [d["forked_from_version_id"]]
                        if d.get("forked_from_version_id")
                        else []
                    )
                ):
                    descendants.add(d["version_id"])
            linked = [
                dict(id=r["id"], versions=r.get("dataset_version_ids", []))
                for r in self.projects.draft["results"]
                if descendants.intersection(r.get("dataset_version_ids", []))
            ]
            records.append(
                dict(
                    operation=op["id"],
                    input=op["spec"]["input_version_id"],
                    output=op["output_version_id"],
                    approval=op["spec"]["parameters"]["approval"],
                    decisions=op.get("diagnostics", {}).get("decisions", []),
                    mapping=op.get("diagnostics", {}).get("mapping", {}),
                    related_versions=sorted(descendants),
                    inverse_artifact=op.get("lineage", {}).get("relation_uri", ""),
                    related_results=linked,
                    current=op["output_version_id"]
                    == (self.data.dataset() or {}).get("version_id"),
                )
            )
        return records

    @Slot(str)
    def previewSchemaContract(self, recipe):
        self.previewCleaning("schema_contract", "[]", recipe, "chain")

    @Slot(str, str)
    def previewContractCheck(self, definition, policy):
        try:
            parameters = dict(contract=json.loads(definition), policy=policy)
            self.start_preview(
                "contract_check", cleaning_columns=[], cleaning_parameters=parameters
            )
        except (TypeError, ValueError) as error:
            self.fail(error)

    @Slot(str, str, float)
    def previewIdentityCandidates(self, name_column, block_column, threshold):
        self.start_preview(
            "entity_candidates",
            cleaning_columns=[],
            cleaning_parameters=dict(
                name_column=name_column, block_column=block_column, threshold=threshold
            ),
        )

    @Slot(str, float)
    def previewCategoryCandidates(self, column, threshold):
        self.start_preview(
            "category_candidates",
            cleaning_columns=[column],
            cleaning_parameters=dict(threshold=threshold),
        )

    @Slot(str, str, str, str)
    def approveIdentityPair(self, left, right, reviewer, reason):
        from datetime import UTC, datetime

        if (
            not self.preview
            or self.preview["spec"]["kind"] != "entity_candidates"
            or self.binding != self.current_binding()
        ):
            return self.fail(ProjectError("Güncel aday listesinden çift seçin."))
        d = self.data.dataset()
        p = copy.deepcopy(self.preview["spec"]["parameters"])
        p.update(
            pairs=[[left, right]],
            canonical_column=d.get("entity_resolution", {}).get(
                "canonical_column", "col:" + uid()
            ),
            approval=dict(
                approved=True,
                reviewer=reviewer,
                reason=reason,
                at=datetime.now(UTC).isoformat(),
            ),
        )
        self.start_preview("entity_merge", cleaning_columns=[], cleaning_parameters=p)

    @Slot(str, str, str, str, str)
    def approveCategoryPair(self, column, source, target, reviewer, reason):
        from datetime import UTC, datetime

        if (
            not self.preview
            or self.preview["spec"]["kind"] != "category_candidates"
            or self.binding != self.current_binding()
            or list(self.preview["spec"]["column_ids"]) != [column]
            or not any(
                {source, target} == {c["left_value"], c["right_value"]}
                for c in self.preview["diagnostics"].get("category_candidates", [])
            )
        ):
            return self.fail(ProjectError("Güncel kategori adayından eşleme seçin."))
        self.start_preview(
            "category_map",
            cleaning_columns=[column],
            cleaning_parameters=dict(
                mapping={source: target},
                approval=dict(
                    approved=True,
                    reviewer=reviewer,
                    reason=reason,
                    at=datetime.now(UTC).isoformat(),
                ),
            ),
        )

    @Slot(str, str)
    def exportContractRecipe(self, path, recipe):
        from PySide6.QtCore import QIODevice, QSaveFile, QUrl

        from veri_ufku.operations.data_contracts import parameters

        try:
            d = self.data.dataset()
            if not d:
                raise ProjectError("Dataset seçin.")
            value = json.loads(recipe)
            parameters(
                {},
                "schema_contract",
                [],
                value,
                copy.deepcopy(d["import_metadata"]["columns"]),
            )
            target = QUrl(path).toLocalFile() if path.startswith("file:") else path
            protected = [
                Path(s["path"]).resolve()
                for s in self.projects.draft["sources"]
                if "://" not in s["path"]
            ]
            if Path(target).resolve() in protected or Path(
                target
            ).resolve().is_relative_to(self.projects.store.root):
                raise ProjectError(
                    "Kaynak veya proje iç dosyası üzerine tarif yazılamaz; ayrı çıktı yolu seçin."
                )
            if not Path(target).is_absolute() or Path(target).suffix != ".json":
                raise ProjectError("Mutlak .json tarif yolu gerekli.")
            file = QSaveFile(target)
            file.setDirectWriteFallback(False)
            payload = json.dumps(
                dict(
                    schema_version=1,
                    bound_dataset_version=d["version_id"],
                    columns=d["import_metadata"]["columns"],
                    recipe=value,
                ),
                ensure_ascii=False,
                indent=2,
            ).encode()
            if (
                not file.open(QIODevice.WriteOnly)
                or file.write(payload) != len(payload)
                or not file.commit()
            ):
                raise ProjectError("Tarif atomik dışa yazılamadı.")
            self._message = "Taşınabilir tarif yazıldı; başka dataset için ColumnId ve referans sürümü açıkça yeniden bağlanmalı."
            self.changed.emit()
        except (TypeError, ValueError) as error:
            self.fail(error)

    @Slot(str, str, str, str)
    def previewTransform(self, kind, column_ids_json, parameters_json, destination):
        self.previewCleaning(kind, column_ids_json, parameters_json, destination)

    def current_binding(self):
        d = self.data.dataset()
        return (
            str(self.projects.store.root) if self.projects.store else "",
            d["version_id"] if d else "",
            self.data.revision,
        )

    def project_changed(self):
        binding = self.current_binding()
        if self.signature != binding:
            self.signature = binding
            if self.process:
                self.cancel()
            if not self.future:
                self.clear_preview()
        self.changed.emit()

    @Slot()
    def discardPreview(self):
        if not self.busy:
            self.clear_preview()
            self.changed.emit()

    def clear_preview(self):
        self.preview = None
        self.before.replace()
        self.after.replace()
        if self.workspace and not self.process:
            shutil.rmtree(self.workspace, ignore_errors=True)
            self.workspace = None

    def history_rows(self):
        d = self.data.dataset()
        if not d:
            return []
        versions = {v["version_id"]: v for v in self.projects.draft["datasets"]}
        chain, cursor = set(), d
        while cursor:
            chain.add(cursor["version_id"])
            cursor = versions.get(next(iter(cursor.get("parent_version_ids", [])), ""))
        return [
            dict(
                id=v["version_id"],
                label=f"{i + 1}. {next((o.get('spec', {}).get('kind', o.get('capability_id', 'metadata')) for o in self.projects.draft['operations'] if o.get('output_version_id') == v['version_id']), 'Kaynak / metadata')} · {v['version_id'][-8:]}",
                current=v["version_id"] == d["version_id"],
                onBranch=v["version_id"] in chain,
                parent=next(iter(v.get("parent_version_ids", [])), ""),
            )
            for i, v in enumerate(self.projects.draft["datasets"])
            if v["dataset_id"] == d["dataset_id"]
        ]

    def fail(self, error):
        self._error = project_error_text(error)
        self._state = "failed"
        self.changed.emit()

    @Slot(result=str)
    def newColumnId(self):
        return "col:" + uid()

    @Slot(str, str, str)
    def previewOperation(self, kind, column_id="", name=""):
        self.start_preview(kind, column_id, name)

    @Slot(str, str, str, str)
    def previewCleaning(self, kind, column_ids_json, parameters_json, destination):
        try:
            columns = json.loads(column_ids_json)
            parameters = json.loads(parameters_json)
            self.start_preview(kind, "", "", columns, parameters, destination)
        except (ValueError, TypeError):
            self.fail(
                ProjectError("Temizlik seçimleri geçersiz; parametreleri kontrol edin.")
            )

    @Slot(str)
    def previewChartSelection(self, text):
        try:
            selection = json.loads(text)
            rows = selection.get("dataset_row_ids", [])
            if (
                selection.get("dataset_version") != self.data.dataset()["version_id"]
                or len(rows) != selection.get("count")
                or not rows
            ):
                raise ProjectError(
                    "Güncel ve tam seçim gerekli; grafik filtresi en fazla10000 kayıt destekler."
                )
            self.start_preview(
                "filter",
                cleaning_columns=[],
                cleaning_parameters={
                    "row_ids": rows,
                    "chart_result_id": selection["chart_result_id"],
                },
                destination="copy",
            )
        except (TypeError, ValueError, KeyError, ProjectError) as error:
            self.fail(ProjectError(str(error)))

    def start_preview(
        self,
        kind,
        column_id="",
        name="",
        cleaning_columns=None,
        cleaning_parameters=None,
        destination="chain",
    ):
        if self.busy or self.projects.busy or self.projects.readOnly:
            return self.fail(
                ProjectError("Devam eden işi bekleyin; proje yazılabilir olmalı.")
            )
        try:
            d = self.data.dataset()
            if not d:
                raise ProjectError("Önce dataset içe aktarın.")
            self.clear_preview()
            artifact = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
            request = dict(
                path=str(self.projects.store.path(d["snapshot_uri"])).replace(
                    "/proc/self/", f"/proc/{os.getpid()}/", 1
                ),
                fingerprint={k: artifact[k] for k in ("sha256", "size")},
                columns=copy.deepcopy(d["import_metadata"]["columns"]),
                row_count=d["import_metadata"]["row_count"],
                version_id=d["version_id"],
                source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
                config_revision=self.data.revision,
                semantic_metadata=copy.deepcopy(d.get("semantic_metadata", {})),
                entity_resolution=copy.deepcopy(d.get("entity_resolution", {})),
                format_metadata=copy.deepcopy(
                    d["import_metadata"]["settings"].get("format_metadata", {})
                ),
            )
            if (
                kind in ("join", "append", "geo_join")
                or kind == "contract_check"
                and any(
                    r["kind"] == "foreign_key"
                    for r in (cleaning_parameters or {})
                    .get("contract", {})
                    .get("rules", [])
                )
            ) and cleaning_parameters:
                if kind == "contract_check":
                    secondary_version = next(
                        r["parameters"]["version_id"]
                        for r in cleaning_parameters["contract"]["rules"]
                        if r["kind"] == "foreign_key"
                    )
                else:
                    secondary_version = cleaning_parameters.get("secondary_version_id")
                other = next(
                    (
                        item
                        for item in active_datasets(self.projects.draft)
                        if item["version_id"] == secondary_version
                    ),
                    None,
                )
                if not other:
                    raise ProjectError("İkinci dataset sürümünü seçin.")
                info = self.projects.store.manifest["artifacts"][other["snapshot_uri"]]
                request["secondary"] = dict(
                    path=str(self.projects.store.path(other["snapshot_uri"])).replace(
                        "/proc/self/", f"/proc/{os.getpid()}/", 1
                    ),
                    fingerprint={k: info[k] for k in ("sha256", "size")},
                    columns=copy.deepcopy(other["import_metadata"]["columns"]),
                    row_count=other["import_metadata"]["row_count"],
                    version_id=other["version_id"],
                    source_snapshot_id=other["import_metadata"]["source_snapshot_id"],
                    format_metadata=copy.deepcopy(
                        other["import_metadata"]["settings"].get("format_metadata", {})
                    ),
                )
            if cleaning_columns is not None:
                spec = build(
                    request, kind, cleaning_columns, cleaning_parameters, destination
                )
            elif kind == "filter":
                cols = {c["id"]: c for c in request["columns"]}
                filters = [
                    dict(
                        column_id=f["column_id"],
                        operator=f["operator"],
                        literal={
                            "dtype": cols[f["column_id"]]["type"],
                            "text": f["value"],
                        },
                    )
                    for f in self.data.view.filters
                ]
                spec = build(
                    request,
                    kind,
                    list(dict.fromkeys(f["column_id"] for f in filters)),
                    {"filters": filters},
                )
            else:
                spec = build(
                    request,
                    kind,
                    [column_id],
                    {"name": name} if kind == "rename" else {},
                )
            self.binding = self.current_binding()
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="operation-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, sender = ctx.Pipe(duplex=False)
            self.process = ctx.Process(
                target=process_entry,
                args=(
                    request,
                    spec.data(),
                    self.workspace,
                    self.cancel_event,
                    sender,
                    self.budget,
                ),
            )
            if not start_controller(self, sender):
                return
            sender.close()
            self.started = time.monotonic()
            self.cancel_time = None
            self.projects.dataset_active = True
            self._error = ""
            self._state = "running"
            self._message = "Önizleme hesaplanıyor… Eski dataset korunuyor."
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, OSError, KeyError, TypeError) as error:
            self.release()
            self.clear_preview()
            self.fail(error)

    @Slot()
    def cancel(self):
        if self.process:
            self.cancel_event.set()
            self.cancel_time = self.cancel_time or time.monotonic()
            self._state = "cancel_requested"
            self.changed.emit()

    def release(self):
        if self.process:
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
        self.projects.dataset_active = False

    @Slot()
    def apply(self):
        if not self.canApply:
            return self.fail(ProjectError("Geçerli önizleme yok; yeniden önizleyin."))
        self.submit(copy.deepcopy(self.projects.draft), self.preview)

    def submit(self, state, result=None):
        self.publication_commit = self.projects.store.commit_id
        self.future = self.projects.executor.submit(
            publish, self.projects.store, state, result
        )
        self.projects.dataset_active = True
        self._state = "publishing"
        self._message = (
            "İşlem ve geçmiş atomik kaydediliyor… Bu eylem proje taslağını da kaydeder."
        )
        self.projects.changed.emit()
        self.changed.emit()

    @Slot(str)
    def historyAction(self, direction):
        if self.busy or self.projects.busy or self.projects.readOnly:
            return
        try:
            state = copy.deepcopy(self.projects.draft)
            move(state, self.data.dataset_id, direction)
            self.submit(state)
        except (ValueError, TypeError) as error:
            self.fail(error)

    @Slot(str)
    def checkout(self, version):
        if self.busy or self.projects.busy or self.projects.readOnly:
            return
        state = copy.deepcopy(self.projects.draft)
        d = next(
            (
                v
                for v in state["datasets"]
                if v["dataset_id"] == self.data.dataset_id
                and v["version_id"] == version
            ),
            None,
        )
        if d:
            activate(state, d)
            self.submit(state)

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                state = future.result()
                self.projects.draft = state
                self.projects.saved = copy.deepcopy(state)
                self.projects.store.state = state
                if self.preview and self.preview["spec"].get("destination") == "copy":
                    output = next(
                        d
                        for d in state["datasets"]
                        if d["version_id"] == self.preview["version_id"]
                    )
                    self.data.dataset_id = output["dataset_id"]
                self._state = "succeeded"
                self._message = (
                    "İşlem/geçmiş kaydedildi. Eski sonuçların sürüm bağları korunur."
                )
            except Exception as error:
                if self.projects.store.commit_id != self.publication_commit:
                    self.projects.draft = copy.deepcopy(self.projects.store.state)
                    self.projects.saved = copy.deepcopy(self.projects.store.state)
                self.fail(error)
            self.projects.dataset_active = False
            self.clear_preview()
            self.projects.changed.emit()
            self.changed.emit()
            return
        if not self.process:
            return
        if time.monotonic() - self.started > self.budget.max_wall_seconds:
            self.cancel()
        if (
            self.cancel_time
            and time.monotonic() - self.cancel_time > self.budget.cancel_grace_ms / 1000
        ):
            self.release()
            self.clear_preview()
            self._state = "canceled"
            self._message = "İptal edildi; eski dataset korundu."
            self.projects.changed.emit()
            self.changed.emit()
            return
        while self.connection.poll():
            try:
                kind, value = self.connection.recv()
            except EOFError:
                break
            if kind == "progress":
                self._message = value.phase
                self.changed.emit()
                continue
            valid = self.binding == self.current_binding()
            canceled = self.cancel_event.is_set()
            self.release()
            if kind == "result" and valid and not canceled:
                self.preview = value
                self.before.replace(value["before"])
                self.after.replace(value["after"])
                self._state = "previewed"
                self._message = "Tam veri etki sayımı hazır. Karşılaştırma tabloları ilk200 kaydı gösterir. Uygula proje taslağını da kaydeder."
            else:
                self.clear_preview()
                if kind == "error":
                    self.fail(ProjectError(value))
                else:
                    self._state = "canceled"
                    self._message = (
                        "İptal/eski sürüm: sonuç uygulanmadı; dataset korundu."
                    )
            self.projects.changed.emit()
            self.changed.emit()
            return
        if not self.process.is_alive() and not self.connection.poll():
            self.release()
            self.clear_preview()
            self.fail(ProjectError("İşlem süreci durdu; eski dataset korundu."))
            self.projects.changed.emit()

    def shutdown(self):
        self.timer.stop()
        if self.future:
            self.future.result()
            self.poll()
        self.release()
        self.clear_preview()
