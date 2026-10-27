"""Sample catalog + Verilerim — thin UI over ProjectStore import path."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from veri_ufku.storage import user_library as library


def examples_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "examples"


def load_sample_catalog() -> list[dict]:
    path = examples_dir() / "catalog.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    samples = []
    for sample in payload.get("samples", []):
        file_name = sample.get("file") or sample.get("csv_file")
        file_path = examples_dir() / file_name
        rows = columns = size = None
        column_names = []
        if file_path.suffix.lower() == ".csv" and file_path.is_file():
            text = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if text:
                column_names = [part.strip() for part in text[0].split(",")]
                rows = max(0, len(text) - 1)
                columns = len(column_names)
            size = file_path.stat().st_size
        elif file_path.is_file():
            size = file_path.stat().st_size
        samples.append(
            dict(
                sample,
                path=str(file_path),
                rows=rows,
                columns=columns,
                size_bytes=size,
                column_names=column_names,
                available=file_path.is_file(),
            )
        )
    return samples


class DataLibraryController(QObject):
    changed = Signal()

    def __init__(self, paths, projects, imports, guide, parent=None):
        super().__init__(parent)
        self.paths = paths
        self.projects = projects
        self.imports = imports
        self.guide = guide
        self._message = ""
        self._error = ""
        self._pending_delete = ""
        self._samples = load_sample_catalog()

    def _data_home(self) -> Path:
        return self.paths.data

    def _entries(self):
        try:
            return library.load_index(self._data_home())["entries"]
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self._error = str(error)
            return []

    @Property("QVariantList", notify=changed)
    def samples(self):
        return self._samples

    @Property("QVariantList", notify=changed)
    def entries(self):
        return self._entries()

    @Property(str, notify=changed)
    def message(self):
        return self._message

    @Property(str, notify=changed)
    def errorText(self):
        return self._error

    @Property(int, notify=changed)
    def diskUsageBytes(self):
        try:
            return library.disk_usage_bytes(self._data_home())
        except OSError:
            return 0

    @Property(str, notify=changed)
    def diskUsageLabel(self):
        value = self.diskUsageBytes
        if value < 1024:
            return f"{value} B"
        if value < 1024 * 1024:
            return f"{value / 1024:.1f} KiB"
        return f"{value / (1024 * 1024):.1f} MiB"

    @Slot(str, str)
    def openSampleAsProject(self, sample_id, directory):
        self._error = ""
        sample = next((s for s in self._samples if s["id"] == sample_id), None)
        if not sample or not sample.get("available"):
            self._error = "Örnek katalog kaydı bulunamadı veya dosya eksik."
            self.changed.emit()
            return
        kind = sample.get("kind")
        if kind in ("sales", "problem"):
            self.guide.createExample(kind, directory)
            self._message = (
                "Örnek yeni proje olarak açılıyor (çevrimdışı paket dosyası)."
            )
            self.changed.emit()
            return
        self._open_file_sample(sample, directory)

    def _open_file_sample(self, sample, directory):
        from PySide6.QtCore import QUrl

        from veri_ufku.domain.contracts import uid

        if self.guide.pending or self.projects.busy:
            return
        if self.projects.store:
            self._error = "Önce mevcut projeyi kapatın."
            self.changed.emit()
            return
        url = QUrl(directory)
        parent = Path(url.toLocalFile() if url.isLocalFile() else directory)
        target = parent / ("Veri_Ufku_" + sample["kind"] + "_" + uid()[:8])
        self._pending_sample = sample
        self.projects.request("create", str(target))
        self._message = f"Örnek proje oluşturuluyor: {sample['name']}"
        self.changed.emit()
        # Poll via timer attachment from app — use projects.changed
        self.projects.changed.connect(self._continue_sample_import)

    def _continue_sample_import(self):
        sample = getattr(self, "_pending_sample", None)
        if not sample:
            return
        if self.projects.busy or self.imports.busy:
            return
        if self.projects.errorText:
            self._error = self.projects.errorText
            self._pending_sample = None
            self.projects.changed.disconnect(self._continue_sample_import)
            self.changed.emit()
            return
        if not self.projects.store:
            return
        self.projects.draft["name"] = sample["name"]
        self.imports.choose(sample["path"])
        self.imports.importData()
        self._pending_sample = None
        try:
            self.projects.changed.disconnect(self._continue_sample_import)
        except (RuntimeError, TypeError):
            pass
        self._message = (
            "Örnek projeye aktarıldı. Kaynak paket içi dosyadır; internet kullanılmadı."
        )
        self.changed.emit()

    @Slot(str)
    def useLibraryEntry(self, entry_id):
        self._error = ""
        entry = library.find_entry(self._data_home(), entry_id)
        if not entry:
            self._error = "Verilerim kaydı bulunamadı."
            self.changed.emit()
            return
        if not self.projects.opened:
            self._error = "Önce bir proje oluşturun veya açın."
            self.changed.emit()
            return
        path = entry.get("stored_path", "")
        if not Path(path).is_file():
            self._error = "Kayıtlı dosya diskte yok; giriş bozulmuş olabilir."
            self.changed.emit()
            return
        self.imports.choose(path)
        self._message = (
            f"«{entry.get('name', '')}» önizlemeye alındı. "
            "İçe aktarın; proje kendi DatasetVersion’ını oluşturur. "
            "Kütüphane girdisi kaynak olarak bağlanır; girdi silinse mevcut proje bozulmaz."
        )
        self.changed.emit()

    @Slot(str, str, str, str)
    def addPathToLibrary(self, path, name, description, tags_csv):
        self._error = ""
        try:
            tags = [
                part.strip() for part in (tags_csv or "").split(",") if part.strip()
            ]
            entry = library.add_file_entry(
                self._data_home(),
                Path(path),
                name=name,
                description=description,
                tags=tags,
            )
            self._message = (
                f"Verilerim’e kaydedildi: {entry['name']} "
                f"({self.diskUsageLabel} disk). "
                "Kişisel/hassas veri içerebilir; kaynak dosya değiştirilmedi."
            )
        except (OSError, ValueError) as error:
            self._error = str(error)
        self.changed.emit()

    @Slot()
    def addCurrentImportSource(self):
        path = getattr(self.imports, "sourcePath", "") or ""
        if not path:
            self._error = "Önce bir dosya seçip önizleyin."
            self.changed.emit()
            return
        name = Path(path).stem
        self.addPathToLibrary(path, name, "", "")

    @Slot(str)
    def requestDelete(self, entry_id):
        self._pending_delete = entry_id
        self._message = (
            "Silme onayı bekleniyor. Onaylarsanız yalnız Verilerim kopyası silinir; "
            "mevcut projeler etkilenmez."
        )
        self.changed.emit()

    @Slot()
    def confirmDelete(self):
        entry_id = self._pending_delete
        self._pending_delete = ""
        if not entry_id:
            return
        try:
            ok = library.remove_entry(self._data_home(), entry_id)
            self._message = "Verilerim kaydı silindi." if ok else "Kayıt bulunamadı."
            if not ok:
                self._error = "Silinecek kayıt yok."
        except (OSError, ValueError) as error:
            self._error = str(error)
        self.changed.emit()

    @Slot()
    def cancelDelete(self):
        self._pending_delete = ""
        self._message = "Silme iptal edildi."
        self.changed.emit()

    @Property(str, notify=changed)
    def pendingDeleteId(self):
        return self._pending_delete
