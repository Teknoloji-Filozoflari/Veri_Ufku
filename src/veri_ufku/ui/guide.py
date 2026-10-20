"""Optional purpose path and explicit synthetic project creation."""

from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from veri_ufku.storage.project_model import uid


class GuideController(QObject):
    changed = Signal()
    navigate = Signal(int, int)

    def __init__(self, projects, imports, data, parent=None):
        super().__init__(parent)
        self.projects, self.imports, self.data = projects, imports, data
        self._active = False
        self._step = 0
        self._message = "Her adımı atlayabilir, istediğiniz ekrana dönebilirsiniz. Veriye kendiliğinden işlem uygulanmaz."
        self.pending = None
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    active = Property(bool, lambda self: self._active, notify=changed)
    step = Property(int, lambda self: self._step, notify=changed)
    message = Property(str, lambda self: self._message, notify=changed)
    busy = Property(bool, lambda self: self.pending is not None, notify=changed)

    @Slot(int)
    def go(self, step):
        if not 0 <= step <= 5:
            return
        self._active, self._step = True, step
        section, tab = [(1, 1), (1, 0), (1, 2), (2, 0), (3, 0), (6, 0)][step]
        self.navigate.emit(section, tab)
        self.changed.emit()

    @Slot()
    def close(self):
        self._active = False
        self.changed.emit()

    @Slot(str, str)
    def createExample(self, kind, directory):
        if self.pending or self.projects.busy or kind not in ("sales", "problem"):
            return
        if self.projects.store:
            self._message = "Örnek ayrı proje açar. Mevcut projeyi kaydedip kapatın; hiçbir taslak otomatik değiştirilmez."
            self.changed.emit()
            return
        url = QUrl(directory)
        parent = Path(url.toLocalFile() if url.isLocalFile() else directory)
        target = parent / ("Veri_Ufku_" + kind + "_" + uid()[:8])
        self.pending = ("project", kind)
        self.projects.request("create", str(target))
        self._message = (
            "Ayrı sentetik örnek projesi oluşturuluyor. CC0; gerçek kişi/satış içermez."
        )
        self.changed.emit()

    def poll(self):
        if not self.pending:
            return
        stage, kind = self.pending
        if self.projects.busy or self.imports.busy:
            return
        error = self.projects.errorText or (
            self.imports.errorText if stage != "project" else ""
        )
        if error:
            self._message = error
            self.pending = None
            self.changed.emit()
            return
        if stage == "project":
            if not self.projects.store:
                self.pending = None
                return
            self.projects.draft["name"] = (
                "Sentetik satış örneği"
                if kind == "sales"
                else "Sentetik problemli veri örneği"
            )
            self.imports.choose(
                str(
                    Path(__file__).resolve().parents[1]
                    / "assets/examples"
                    / (kind + ".parquet")
                )
            )
            self.pending = ("preview", kind)
        elif stage == "preview":
            self.imports.importData()
            self.pending = ("import", kind)
        else:
            self.pending = None
            if not self.data.datasets:
                self._message = "Örnek içe aktarılmadı. Veri ekranında önizlemeyi yenileyip yeniden deneyebilirsiniz."
                self.changed.emit()
                return
            self._message = "Örnek ayrı projede açıldı. Önce bir sütun seçip profili hesaplayın; kalite, seçtiğiniz temizlik, grafik ve rapora geçebilirsiniz."
            self.go(1)
        self.changed.emit()

    def shutdown(self):
        self.timer.stop()
