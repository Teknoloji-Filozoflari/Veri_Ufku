"""CSV/TSV workflow with a virtual preview model and isolated, cancelable I/O."""

import copy
import json
import multiprocessing as mp
import shutil
import tempfile
import time
from dataclasses import replace
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

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.importers.advanced import ADVANCED_FORMATS
from veri_ufku.importers.arrays import ARRAY_FORMATS
from veri_ufku.importers.connector_contracts import CONNECTORS, ConnectorSpec
from veri_ufku.importers.delimited import TYPES, ImportSettings
from veri_ufku.importers.registry import FORMATS, default_settings, settings_from_dict
from veri_ufku.importers.worker import process_entry
from veri_ufku.jobs.admission import start_controller
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.ui.projects import project_error_text


class PreviewModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows, self.names = [], []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.names)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.isValid():
            return self.rows[index.row()][index.column()]

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return (
                self.names[section]
                if orientation == Qt.Horizontal
                else str(section + 1)
            )

    def replace(self, result=None):
        self.beginResetModel()
        self.rows = result["rows"][:20] if result else []
        self.names = result["schema"]["names"] if result else []
        self.endResetModel()


def publish(project, state, result, portable, cancel):
    previous = copy.deepcopy(project.state)
    project.state = state
    irreversible = False

    def checkpoint(point):
        nonlocal irreversible
        if point == "pointer_replaced":
            irreversible = True
        if not irreversible and cancel.is_set():
            raise Canceled()

    try:
        project.publish_import(result, portable=portable, checkpoint=checkpoint)
        return copy.deepcopy(project.state), project.source_statuses()
    except BaseException:
        # Service reconciles ACTIVE itself; preserve a durable publication if present.
        if project.state == state:
            project.state = previous
        raise


class ImportController(QObject):
    changed = Signal()

    def __init__(self, projects, cache, budget=ComputeBudget(), parent=None):
        super().__init__(parent)
        self.projects, self.cache, self.budget = projects, Path(cache), budget
        self.model = PreviewModel(self)
        self.context = mp.get_context("spawn")
        self.process = self.connection = self.cancel_event = self.future = None
        self.workspace = None
        self.snapshot = self.result = None
        self._settings = ImportSettings()
        self._message, self._error, self._path = (
            "CSV/TSV, JSON/JSONL, XLSX veya Parquet seçin veya buraya bırakın.",
            "",
            "",
        )
        self.valid = False
        self._choices = {}
        self.revision = 0
        self.cancel_time = None
        self.started = 0
        self.portable = False
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        projects.changed.connect(self.changed.emit)

    busy = Property(
        bool,
        lambda self: self.process is not None or self.future is not None,
        notify=changed,
    )
    ready = Property(
        bool,
        lambda self: (
            self.valid
            and not self.busy
            and self.projects.opened
            and not self.projects.readOnly
        ),
        notify=changed,
    )
    message = Property(str, lambda self: self._message, notify=changed)

    @Property(str, notify=changed)
    def statusText(self):
        if self.busy:
            return "Dosyan işleniyor…"
        if self.errorText:
            return "Okuma ayarlarını Gelişmiş bölümünden düzenleyebilirsin."
        if self.valid and self.result:
            return (
                f"Önizleme: {self.model.rowCount()} kayıt · "
                f"{len(self.result['schema']['names'])} sütun. "
                "Bu sınırlı örnektir; içe aktarmada dosyanın tamamı doğrulanır."
            )
        if self._message.startswith(("İçe aktarma kaydedildi:", "İptal")):
            return self._message.split(" Veri sürümü:")[0]
        if self.sourcePath:
            return "Ayarları düzenledikten sonra önizlemeyi güncelle."
        return ""

    @Property(str, notify=changed)
    def previewWarnings(self):
        if not self.result or self.busy:
            return ""
        if not self.valid and self.result.get("settings") != {
            k: list(v) if isinstance(v, tuple) else v
            for k, v in self._settings.__dict__.items()
        }:
            return ""
        warnings = list(self.result["schema"]["warnings"])
        if self.result["bad"]:
            warnings.append(
                f"Önizlemede {len(self.result['bad'])} bozuk kayıt var. "
                "Bu kayıtlar veriden ayrı tutulacak; ayrıntılar Gelişmiş bölümünde."
            )
        return "\n".join(warnings)

    errorText = Property(str, lambda self: self._error, notify=changed)
    sourcePath = Property(str, lambda self: self._path, notify=changed)
    settings = Property(
        "QVariantMap",
        lambda self: {
            k: list(v) if isinstance(v, tuple) else v
            for k, v in self._settings.__dict__.items()
        },
        notify=changed,
    )
    previewModel = Property(QObject, lambda self: self.model, constant=True)
    columns = Property(
        "QVariantList",
        lambda self: (
            [
                dict(name=n, type=t, suggestion=s)
                for n, t, s in zip(
                    self.result["schema"]["names"],
                    self._settings.types
                    or (
                        ["auto"] * len(self.result["schema"]["names"])
                        if hasattr(self._settings, "adapter_id")
                        else self.result["schema"]["types"]
                    ),
                    self.result.get("suggestions", self.result["schema"]["types"]),
                    strict=True,
                )
            ]
            if self.result
            else []
        ),
        notify=changed,
    )
    choices = Property("QVariantMap", lambda self: self._choices, notify=changed)
    formatId = Property(
        str,
        lambda self: self.snapshot.get("adapter_id", "csv") if self.snapshot else "csv",
        notify=changed,
    )

    formats = Property("QVariantList", lambda self: list(FORMATS), constant=True)
    connectorKinds = Property(
        "QVariantList", lambda self: list(CONNECTORS), constant=True
    )
    connectorTables = Property(
        "QVariantList",
        lambda self: getattr(self, "_connector_tables", []),
        notify=changed,
    )

    @Slot()
    def connectionEdited(self):
        if not self.busy and self.snapshot and self.snapshot.get("connector"):
            self.valid = False
            self._message = "Bağlantı ayarları değişti. Yeni açık okuma ile yeniden snapshot önizleyin."
            self.changed.emit()

    @Slot(str, str)
    def saveCredential(self, reference, secret):
        from veri_ufku.importers.credentials import store

        if self.busy:
            return
        try:
            store(reference, secret)
            self._message, self._error = (
                "Credential sistem keyring'inde; projede yalnız referans saklanır.",
                "",
            )
            self.changed.emit()
        except (ValueError, OSError) as error:
            self.fail(error)

    @Slot(str)
    def connectSource(self, data):
        self._connect(data, "connector")

    @Slot(str)
    def listTables(self, data):
        self._connect(data, "connector_tables")

    def _connect(self, data, action):
        if (
            self.busy
            or self.projects.busy
            or (self.projects.opened and self.projects.readOnly)
        ):
            return self.fail(
                ProjectError("Devam eden işi bekleyin; yazılabilir proje gerekli.")
            )
        try:
            spec = ConnectorSpec.from_dict(json.loads(data))
            if not spec.terms_acknowledged:
                raise ProjectError("Bağlantı/servis koşullarını onaylayın.")
            self.cache.mkdir(parents=True, exist_ok=True)
            self.clear_workspace()
            self.workspace = tempfile.mkdtemp(prefix="connector-", dir=self.cache)
            self.snapshot = self.result = None
            self.valid = False
            self.model.replace()
            self._connector_tables = []
            self._path = spec.endpoint or ("S3 · " + spec.bucket)
            self.revision += 1
            self.start(action, spec.data())
        except (OSError, ValueError, TypeError) as error:
            self.fail(error)

    @Property(str, notify=changed)
    def formatMetadata(self):
        import json

        metadata = getattr(self._settings, "format_metadata", {})
        if not metadata and self.snapshot and self.snapshot.get("connector"):
            metadata = {"connector": self.snapshot["connector"]}
        display = copy.deepcopy(metadata)
        for part in display.get("parts", []):
            part.pop("arrow_schema_base64", None)
        return json.dumps(display, ensure_ascii=False, indent=2) if metadata else ""

    @Slot(str)
    def setFormat(self, adapter_id):
        if (
            self.busy
            or adapter_id not in FORMATS
            or (self.snapshot and self.snapshot.get("connector"))
        ):
            return
        self._settings = default_settings(adapter_id)
        if isinstance(self._settings, ImportSettings):
            self._settings = replace(self._settings, infer_types=True)
        if self.snapshot:
            self.snapshot["adapter_id"] = adapter_id
        self._choices = {}
        self.valid = False
        self.result = None
        self.model.replace()
        self.changed.emit()

    @Slot()
    def resetTypes(self):
        if self.busy:
            return
        data = dict(self._settings.__dict__)
        data["types"] = ()
        if "column_names" in data:
            data["column_names"] = ()
        self._settings = settings_from_dict(data)
        self.valid = False
        self.changed.emit()

    datasetSummary = Property(
        str,
        lambda self: (
            "\n".join(
                f"{d['dataset_id']} · Sürüm {d['version_id']} · {d.get('import_metadata', {}).get('row_count', '?')} kayıt · {d.get('import_metadata', {}).get('bad_count', 0)} karantina"
                for d in self.projects.draft["datasets"]
            )
            or "İçe aktarılmış dataset yok."
        ),
        notify=changed,
    )

    def fail(self, error):
        self._error = project_error_text(error)
        self.changed.emit()

    def clear_workspace(self):
        if self.workspace:
            shutil.rmtree(self.workspace)
            self.workspace = None

    @Slot(str)
    def choose(self, value):
        if self.busy or self.projects.busy:
            return self.fail(
                ProjectError("Devam eden işlemin tamamlanmasını bekleyin.")
            )
        try:
            if self.projects.opened and self.projects.readOnly:
                raise ProjectError("Önce yazılabilir bir proje oluşturun veya açın.")
            source = self.projects.local(value)
            if self.projects.opened and source.resolve().is_relative_to(
                self.projects.store.root
            ):
                raise ProjectError("Proje içindeki dosya kaynak olarak seçilemez.")
            self.cache.mkdir(parents=True, exist_ok=True)
            self.clear_workspace()
            self.workspace = tempfile.mkdtemp(prefix="csv-", dir=self.cache)
            self._path = str(source)
            self.snapshot = self.result = None
            self.model.replace()
            self.valid = False
            self.start("capture", source)
        except (OSError, ValueError) as error:
            self.fail(error)

    @Slot("QVariantList")
    def dropFiles(self, values):
        if len(values) != 1:
            return self.fail(ProjectError("Tek bir yerel veri dosyası bırakın."))
        self.choose(str(values[0]))

    @Slot(str, "QVariant")
    def setOption(self, key, value):
        if self.busy:
            return
        try:
            data = dict(self._settings.__dict__)
            if key not in data or key == "types":
                raise ProjectError("Bilinmeyen içe aktarma ayarı.")
            if key in {"null_markers", "expand_lists"}:
                value = tuple(value.split("|")) if value else ()
            if key == "column_names":
                value = tuple(str(value).split("|")) if value else ()
            if key == "widths":
                value = tuple(
                    int(w.strip()) for w in str(value).split(",") if w.strip()
                )
            if key == "geo_window" and isinstance(value, str):
                value = json.loads(value)
            if key == "array_slice" and isinstance(value, str):
                value = json.loads(value or "{}")
            if key == "array_coordinates" and isinstance(value, str):
                value = tuple(n.strip() for n in value.split("|") if n.strip())
            if key in {"delimiter", "encoding", "header_row"}:
                data["types"] = ()
            data[key] = value
            self._settings = settings_from_dict(data)
            self.revision += 1
            self.valid = False
            self._error = ""
            self._message = "Ayar değişti. Aynı kopyayı yeniden önizleyin; içe aktarma bu ayarlarla yapılacak."
            self.changed.emit()
        except (ValueError, TypeError) as error:
            self.valid = False
            self.fail(error)

    @Slot(int, str)
    def setType(self, index, kind):
        if self.busy or not self.result:
            return
        if (
            self.formatId
            in ("parquet", "ipc", "ipc_stream")
            + CONNECTORS
            + ARRAY_FORMATS
            + tuple(n for n in ADVANCED_FORMATS if n not in ("xml", "fixed_width"))
            or kind not in TYPES + ("auto",)
            or not 0 <= index < len(self.result["schema"]["names"])
        ):
            return
        data = dict(self._settings.__dict__)
        types = list(
            self._settings.types
            or (
                ["auto"] * len(self.result["schema"]["names"])
                if hasattr(self._settings, "adapter_id")
                else self.result["schema"]["types"]
            )
        )
        types[index] = kind
        data["types"] = types
        if "column_names" in data:
            data["column_names"] = self.result["schema"].get(
                "input_names", self.result["schema"]["original_headers"]
            )
        self._settings = settings_from_dict(data)
        self.revision += 1
        self.valid = False
        self.changed.emit()

    @Slot()
    def refreshPreview(self):
        if self.snapshot and not self.busy and not self.projects.busy:
            try:
                self.start("preview")
            except (OSError, ValueError) as error:
                self.fail(error)

    @Slot(bool)
    def importData(self, portable=False):
        if not self.ready or self.projects.busy:
            return self.fail(
                ProjectError("Geçerli önizleme ve yazılabilir proje gerekli.")
            )
        self.portable = portable
        try:
            self.start("import")
        except (OSError, ValueError) as error:
            self.fail(error)

    def start(self, action, source=None):
        if action == "import":
            # These files are private worker copies, never linked project artifacts.
            for path in Path(self.workspace).glob("*.parquet"):
                if not self.snapshot or str(path) != self.snapshot["path"]:
                    path.unlink()
        self.action = action
        self.submitted_revision = self.revision
        self.started = time.monotonic()
        self.cancel_time = None
        self.cancel_event = self.context.Event()
        self.connection, sender = self.context.Pipe(duplex=False)
        self.process = self.context.Process(
            target=process_entry,
            args=(
                action,
                source,
                self.snapshot,
                dict(self._settings.__dict__),
                self.workspace,
                self.cancel_event,
                sender,
                self.budget,
            ),
        )
        try:
            if not start_controller(self, sender):
                return
        except BaseException:
            sender.close()
            self.connection.close()
            self.connection = None
            self.process.close()
            self.process = None
            raise
        sender.close()
        self.projects.import_active = True
        self.projects.changed.emit()
        self._error = ""
        self._message = "Doğrulama sürüyor; dataset henüz kaydedilmedi."
        self.changed.emit()

    @Slot()
    def cancel(self):
        if self.busy:
            self.cancel_event.set()
            if self.cancel_time is None:
                self.cancel_time = time.monotonic()
            self._message = "İptal isteniyor…"
            self.changed.emit()

    def release_process(self):
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

    def finish(self):
        self.projects.import_active = False
        self.projects.changed.emit()
        self.changed.emit()

    def poll(self):
        if self.future is not None:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                state, statuses = future.result()
                self.projects.draft = self.projects.store.state = state
                self.projects.saved = copy.deepcopy(state)
                self.projects._statuses = statuses
                self.projects._watch_sources()
                self._message = f"İçe aktarma kaydedildi: {self.import_result['accepted']} kayıt; {self.import_result['bad_count']} bozuk kayıt karantinada. Veri sürümü: {state['datasets'][-1]['version_id']}."
                self.valid = False
            except Canceled:
                self._message = "İptal edildi. Dataset kaydedilmedi."
                self.clear_workspace()
                self.valid = False
            except Exception as error:
                self.fail(error)
                self.projects.draft = self.projects.store.state
            self.finish()
            return
        if not self.process:
            return
        if (
            self.cancel_time is None
            and time.monotonic() - self.started > self.budget.max_wall_seconds
        ):
            self.cancel()
            self._error = "İçe aktarma süre bütçesi aşıldı."
        if (
            self.cancel_time
            and time.monotonic() - self.cancel_time > self.budget.cancel_grace_ms / 1000
        ):
            self.release_process()
            self._message = "İptal edildi. Kaynak ve proje korunuyor."
            self.clear_workspace()
            self.valid = False
            self.finish()
            return
        # Drain only a bounded number per Qt tick.
        for _ in range(30):
            if not self.connection.poll():
                break
            try:
                kind, value = self.connection.recv()
            except EOFError:
                break
            if kind == "captured":
                self.snapshot = value[0]
                self._settings = settings_from_dict(value[1])
                self.changed.emit()
                continue
            if kind == "inspected":
                self._choices = value
                self.changed.emit()
                continue
            if kind == "progress":
                phase, done, total = value.phase, value.done, value.total
                self._message = f"{phase}: {done}" + (
                    f" / {total}" if total is not None else " · toplam henüz bilinmiyor"
                )
                self.changed.emit()
                continue
            if kind == "tables":
                self.release_process()
                self._connector_tables = value["tables"]
                self._message = (
                    "Tablo/şema listesini inceleyin; veri okuması ayrı açık eylemdir."
                )
                self.finish()
                return
            self.release_process()
            if self.cancel_event.is_set() or kind == "canceled":
                self._message = "İptal edildi. Dataset kaydedilmedi."
                self.clear_workspace()
                self.valid = False
            elif kind == "error":
                self._error = value
                self.valid = False
            elif self.action == "import":
                value["config_revision"] = self.submitted_revision
                self.import_result = value
                self.future = self.projects.executor.submit(
                    publish,
                    self.projects.store,
                    copy.deepcopy(self.projects.draft),
                    value,
                    self.portable,
                    self.cancel_event,
                )
                self._message = "Doğrulandı; Parquet, SQLite ve manifest atomik olarak yayımlanıyor…"
                self.changed.emit()
                return
            else:
                self.result, self.snapshot = value, value["capture"]
                self._settings = settings_from_dict(value["settings"])
                self.model.replace(value)
                self.valid = bool(value["examined"]) and value.get("importable", True)
                self._message = f"Ekranda ilk 20 kayıt gösterilir; önkontrolde incelenen {value['examined']}, bozuk {len(value['bad'])}. Tür önerileri kesin değildir. CSV otomatik türleri tam dosyada doğrulanır; yapılandırılmış veride tam dosya tür doğrulaması; Parquet türleri korunur.\nDeğişmez kopya: {self.snapshot['captured_at']} · SHA256 {self.snapshot['fingerprint']['sha256']}. İçe aktarma bu kopyadan yapılır; güncel kaynağı almak için dosyayı yeniden seçin."
                if value["schema"]["warnings"]:
                    self._message += "\n" + "\n".join(value["schema"]["warnings"])
                if value["bad"]:
                    self._message += "\n" + "\n".join(
                        f"Satır {b['start_line']}–{b['end_line']}: {b['reason']}"
                        for b in value["bad"][:10]
                    )
            self.finish()
            return
        if self.process and not self.process.is_alive():
            if self.connection.poll():
                return
            self.release_process()
            self._error = (
                "İçe aktarma işlemi beklenmedik biçimde durdu; dataset kaydedilmedi."
            )
            self.valid = False
            self.clear_workspace()
            self.finish()

    def shutdown(self):
        self.timer.stop()
        if self.cancel_event:
            self.cancel_event.set()
        self.release_process()
        if self.future:
            try:
                self.future.result()
            except Exception:
                pass
            self.future = None
        self.projects.import_active = False
        self.clear_workspace()
