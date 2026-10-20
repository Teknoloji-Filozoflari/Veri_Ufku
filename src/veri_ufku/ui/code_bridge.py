"""Opt-in code workspace; project opening never launches a kernel or executes a cell."""

import copy
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from veri_ufku.exports.code_bridge import SCRIPT, SQL, CodeRecipe, bundle
from veri_ufku.modeling.code_kernel import Kernel
from veri_ufku.modeling.code_workspace import cell_hash, kernel_environment, record
from veri_ufku.storage.experiment_store import capture
from veri_ufku.storage.neural_store import load, publish
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.validation_store import prior_uses
from veri_ufku.ui.projects import project_error_text


class CodeController(QObject):
    changed = Signal()
    selectCode = Signal()

    def __init__(self, data, projects, exports, cache, budget, parent=None):
        super().__init__(parent)
        self.data, self.projects, self.exports, self.cache, self.budget = (
            data,
            projects,
            exports,
            Path(cache),
            budget,
        )
        self.process = self.kernel = self.future = None
        self.workspace = None
        self.stage = None
        self.source = 'print("Veri_Ufku: explicit local code action")\n'
        self.revision = 0
        self.previous_hash = None
        self._cell_invalid = False
        self.active = None
        self.receipt = {}
        self._output = ""
        self._error = ""
        self._message = "Kod çalışma alanı kapalı; yeni süreç yalnız açık Çalıştır eyleminde başlar."
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        projects.changed.connect(self.project_changed)
        data.changed.connect(self.changed)
        self._root = None

    @Slot()
    def project_changed(self):
        root = str(self.projects.store.root) if self.projects.store else None
        if root != self._root and not self.busy:
            self._root = root
            self.active = None
            self.receipt = {}
            self._output = ""
            self.previous_hash = None
        self.changed.emit()

    busy = Property(
        bool,
        lambda self: self.process is not None or self.future is not None,
        notify=changed,
    )
    canCancel = Property(
        bool,
        lambda self: self.kernel is not None or self.stage == "launch",
        notify=changed,
    )
    canAct = Property(
        bool,
        lambda self: bool(
            self.data.dataset()
            and self.projects.store
            and not self.projects.readOnly
            and not self.projects.busy
            and not self.data.busy
            and not self.busy
        ),
        notify=changed,
    )
    errorText = Property(str, lambda self: self._error, notify=changed)
    message = Property(str, lambda self: self._message, notify=changed)
    outputText = Property(str, lambda self: self._output, notify=changed)
    pythonPreview = Property(str, lambda self: SCRIPT, constant=True)
    sqlPreview = Property(str, lambda self: SQL, constant=True)
    codeHash = Property(str, lambda self: cell_hash(self.source), notify=changed)
    codeRevision = Property(int, lambda self: self.revision, notify=changed)
    environmentInfo = Property(
        "QVariantMap", lambda self: kernel_environment(), constant=True
    )
    report = Property("QVariantMap", lambda self: self.active or {}, notify=changed)
    exportReceipt = Property("QVariantMap", lambda self: self.receipt, notify=changed)
    savedRuns = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label=r["neural"]["status"]
                + " · "
                + r["neural"]["code_recipe"]["cell_hash"][:12],
            )
            for r in self.projects.draft["results"]
            if r.get("neural", {}).get("schema") == "CodeRun/v1"
        ],
        notify=changed,
    )

    def fail(self, error):
        self._error = project_error_text(error)
        self.changed.emit()

    @Slot(str)
    def setCode(self, source):
        if self.busy:
            return
        try:
            cell_hash(source)
            self._cell_invalid = False
            if source != self.source:
                self.previous_hash = cell_hash(self.source)
                self.source = source
                self.revision += 1
                self.active = None
                self._output = ""
                self._error = ""
            self.changed.emit()
        except (ValueError, TypeError) as e:
            self._cell_invalid = True
            self.fail(e)

    def ready(self):
        if not self.canAct:
            raise ProjectError(
                "Yazılabilir proje ve seçili dataset gerekir; başka işin bitmesini bekleyin."
            )
        self.cache.mkdir(parents=True, exist_ok=True)

    def publish_record(self, value, stage):
        self.stage = stage
        self.projects.dataset_active = True
        self.future = self.projects.executor.submit(
            publish,
            self.projects.store,
            copy.deepcopy(self.projects.draft),
            copy.deepcopy(value),
        )
        self.changed.emit()

    def create_record(self, timeout, action):
        if self._cell_invalid:
            raise ProjectError(
                "Geçersiz editor hücresi; eski geçerli hücre sessiz çalıştırılmaz."
            )
        request = self.exports.request()
        request.update(
            run_id="run:" + uid(),
            prior_test_use_ids=prior_uses(self.projects.draft),
            experiment_capture=capture(
                dict(
                    code_recipe=dict(
                        cell_hash=cell_hash(self.source), revision=self.revision
                    )
                )
            ),
        )
        return record(
            request,
            cell_hash(self.source),
            self.revision,
            timeout,
            action,
            self.previous_hash,
        )

    @Slot()
    def saveHash(self):
        try:
            self.ready()
            self.active = self.create_record(1, "save_hash")
            self.publish_record(self.active, "saved")
        except (ValueError, KeyError, TypeError, OSError) as e:
            self.fail(e)

    @Slot(bool, float)
    def execute(self, consent, timeout):
        try:
            self.ready()
            if consent is not True:
                raise ProjectError(
                    "Arbitrary code aynı kullanıcı haklarıyla çalışır; ayrı süreç güvenli sandbox değildir. Açık etkinleştirme gerekli."
                )
            if not 0 < timeout <= min(600, self.budget.max_wall_seconds):
                raise ProjectError("Kernel timeout bütçe dışında.")
            self._error = ""
            self._output = ""
            self._cancel_before_launch = False
            self._timeout = timeout
            self.active = self.create_record(timeout, "execute")
            # Durable hash/config provenance BEFORE executing any user code.
            self.publish_record(self.active, "launch")
        except (ValueError, KeyError, TypeError, OSError) as e:
            self.fail(e)

    @Slot(str, str)
    def exportCode(self, fmt, destination):
        try:
            self.ready()
            p = self.data.profile_result
            d = self.data.dataset()
            if (
                not p
                or p["dataset_version"] != d["version_id"]
                or p["target"] != "dataset"
                or p["filters"]
                or p["role"] != "measurement"
                or p["numeric"]["suppressed"]
            ):
                raise ProjectError(
                    "Önce seçili dataset için numeric measurement sütun profilini hesaplayın. View/filter veya diğer GUI analizleri kod köprüsünde desteklenmez."
                )
            if p["column_id"] != self.data.column_id or (
                p["scope"] == "sample" and p["used_n"] > 10000
            ):
                raise ProjectError(
                    "Seçili kolonun güncel profili gerekir; code export sample üst sınırı10000. Sessiz kısaltma yapılmaz."
                )
            r = CodeRecipe(
                p["column_id"],
                sample=p["scope"] == "sample",
                ddof=p["numeric"]["ddof"],
                sample_limit=min(10000, self.budget.sample_limit_rows),
            )
            self.workspace = tempfile.mkdtemp(prefix="code-export-", dir=self.cache)
            self.stage = "export"
            self.projects.dataset_active = True
            self._error = ""
            self.future = self.projects.executor.submit(
                bundle,
                self.exports.request(),
                r.data(),
                fmt,
                self.workspace,
                destination,
                str(self.projects.store.root),
            )
            self.changed.emit()
        except (ValueError, KeyError, TypeError, OSError) as e:
            self.fail(e)

    @Slot(str)
    def openRecord(self, ident):
        if self.busy or self.projects.busy:
            return
        try:
            r = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident
                and r.get("neural", {}).get("schema") == "CodeRun/v1"
            )
            self.active = load(self.projects.store, r)
            self._output = ""
            self._error = ""
            self._message = "Hash-only kayıt açıldı; hücre kaynak/çıktısı yüklenmedi, kod çalıştırılmadı."
            self.changed.emit()
        except (ValueError, KeyError, OSError, StopIteration) as e:
            self.fail(e)

    @Slot()
    def cancel(self):
        if self.kernel:
            self.kernel.cancel()
        else:
            self._cancel_before_launch = True
        self.changed.emit()

    def cleanup(self):
        if self.kernel:
            self.kernel.close()
        self.kernel = None
        self.process = None
        if self.workspace:
            shutil.rmtree(self.workspace, ignore_errors=True)
        self.workspace = None

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                value = future.result()
                if self.stage == "export":
                    self.receipt = value
                    self.cleanup()
                    self.projects.dataset_active = False
                    self._message = "Referans ve lock içeren kod paketi oluşturuldu; veri/secret/hücre çıktısı gömülmedi."
                else:
                    self.projects.draft = value
                    self.projects.saved = copy.deepcopy(value)
                    if self.stage == "launch" and not self._cancel_before_launch:
                        self.workspace = tempfile.mkdtemp(
                            prefix="code-cell-", dir=self.cache
                        )
                        self.kernel = Kernel(
                            self.source, self.workspace, self.budget, self._timeout
                        )
                        self.process = self.kernel.process
                        self.active["kernel_pid"] = self.process.pid
                        self.stage = "running"
                        self._message = (
                            "Ayrı yerel süreç çalışıyor; güvenli OS sandbox değildir."
                        )
                    elif self.stage == "launch":
                        self.active["status"] = "canceled"
                        self.publish_record(self.active, "terminal")
                        return
                    else:
                        self.projects.dataset_active = False
                        self.stage = None
                        self._message = "Hash-only code kaydı hazır; kaynak/çıktı yalnız bu oturumda."
                self.projects.changed.emit()
                self.changed.emit()
            except (ValueError, TypeError, KeyError, OSError) as e:
                self.cleanup()
                self.projects.dataset_active = False
                self.stage = None
                self.fail(e)
            return
        if not self.kernel:
            return
        done = self.kernel.poll()
        self._output = self.kernel.display
        if done:
            self.active.update(
                status=self.kernel.status,
                output_bytes=self.kernel.raw_bytes,
                exit_code=self.process.returncode,
                elapsed_seconds=time.monotonic() - self.kernel.started,
            )
            self.cleanup()
            self.publish_record(self.active, "terminal")
        self.changed.emit()

    def shutdown(self):
        if self.future:
            try:
                self.future.result(timeout=20)
            except (ValueError, OSError, TimeoutError):
                pass
        self.cleanup()
