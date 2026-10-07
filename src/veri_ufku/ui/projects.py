"""Project actions, dirty tracking and recovery; no implicit source reimport."""

import copy
import errno
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QFileSystemWatcher,
    QObject,
    QTimer,
    QUrl,
    Signal,
    Slot,
)

from veri_ufku.storage.project_model import ProjectError, decode, encode, new_state
from veri_ufku.storage.project_store import ProjectStore


def project_error_text(error):
    """Actionable messages and safe codes, never arbitrary exception contents."""
    if isinstance(error, ProjectError):
        return str(error)
    if isinstance(error, OSError):
        messages = {
            errno.ENOENT: "Proje veya üst klasörü bulunamadı. Klasör seç ile var olan bir konum seçin.",
            errno.ENOTDIR: "Yolun bir bölümü klasör değil. Projeyi bir dizinin içinde oluşturun.",
            errno.EACCES: "Bu konuma yazma izni yok. Kendi kullanıcı klasörünüzde başka bir konum seçin.",
            errno.EPERM: "Bu konuma yazma izni yok. Kendi kullanıcı klasörünüzde başka bir konum seçin.",
            errno.EROFS: "Seçilen konum salt okunur. Yazılabilir bir yerel klasör seçin.",
            errno.ENOSPC: "Seçilen diskte yeterli boş alan yok. Yer açın veya başka bir disk seçin.",
            errno.EDQUOT: "Bu konumun disk kotası dolmuş. Yer açın veya başka bir konum seçin.",
            errno.EEXIST: "Hedef bu sırada oluşturulmuş. Mevcut içerik korunuyor; yeni bir proje adı seçin.",
            errno.ENAMETOOLONG: "Proje yolu çok uzun. Daha kısa bir klasör adı seçin.",
        }
        if error.errno in messages:
            return messages[error.errno]
    if isinstance(error, sqlite3.Error):
        code = getattr(error, "sqlite_errorcode", 0) & 255
        messages = {
            sqlite3.SQLITE_CANTOPEN: "SQLite proje dosyası oluşturulamadı veya açılamadı. Yazılabilir bir yerel klasör seçin.",
            sqlite3.SQLITE_READONLY: "SQLite proje kaydı salt okunur. Yazılabilir bir yerel kopya seçin.",
            sqlite3.SQLITE_FULL: "SQLite kaydı için disk alanı yetersiz. Yer açın veya başka bir disk seçin.",
            sqlite3.SQLITE_BUSY: "SQLite proje kaydı kullanımda. Diğer işlemin tamamlanmasını bekleyin.",
            sqlite3.SQLITE_CORRUPT: "SQLite proje kaydı bozuk. Mevcut dosyalar korundu; sağlam bir kopya açın.",
        }
        if code in messages:
            return messages[code]
    code = type(error).__name__
    return f"Proje işlemi tamamlanamadı (hata türü: {code}). Mevcut dosyalar korundu; bu hata türünü destek için paylaşabilirsiniz."


def project_task(action, store, state, path, source_id, portable):
    """I/O thread returns plain state; never invokes Qt or publishes GUI properties."""
    candidate = None
    try:
        if action == "create":
            candidate = ProjectStore.create(path, state["name"])
        elif action in {"open", "openRecover"}:
            candidate = ProjectStore.open(path, recover_lock=action == "openRecover")
        elif action == "recover":
            candidate = ProjectStore.open(store.root, recover_lock=True)
        else:
            if store is None:
                raise ProjectError("Önce proje oluşturun veya açın.")
            store.state = state
            if action == "save":
                store.save()
            elif action == "autosave":
                store.save(autosave=True)
            elif action == "saveAs":
                candidate = store.save_as(path)
            elif action == "addSource":
                store.stage_source(path, portable)
            elif action == "relink":
                store.relink(source_id, path)
            elif action == "restore":
                store.restore_autosave()
            elif action != "refresh":
                raise ProjectError("Bilinmeyen proje eylemi.")
        result = candidate or store
        return result, copy.deepcopy(result.state), result.source_statuses()
    except BaseException:
        if candidate:
            candidate.close()
        raise


class ProjectController(QObject):
    changed = Signal()
    saveFinished = Signal(bool)

    def __init__(self, config, learning, parent=None):
        super().__init__(parent)
        self.config = Path(config)
        self.learning = learning
        self.executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="project-io"
        )
        self.future = None
        self.import_active = False
        self.dataset_active = False
        self._statuses = {}
        self._refresh_pending = False
        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._source_changed)
        self.watcher.directoryChanged.connect(self._source_changed)
        self.poller = QTimer(self)
        self.poller.setInterval(25)
        self.poller.timeout.connect(self._poll)
        self.poller.start()
        self.store = None
        self.draft = new_state()
        self.saved = copy.deepcopy(self.draft)
        self._error = ""
        self._message = "Metadata açılışı kaynak veriyi yeniden işlemez."
        self._recent = []
        self._recent_writable = True
        try:
            path = self.config / "recent-projects.json"
            if path.exists():
                raw = path.read_bytes()
                data = decode(raw)
                if (
                    not isinstance(data, list)
                    or len(data) > 20
                    or any(
                        not isinstance(p, str) or not p.startswith("/") or len(p) > 4096
                        for p in data
                    )
                ):
                    raise ProjectError("Son projeler kaydı geçersiz.")
                self._recent = data
        except (OSError, ValueError):
            self._recent_writable = False
            self._error = "Son projeler okunamadı; mevcut liste dosyası korundu."
        self.timer = QTimer(self)
        self.timer.setInterval(60000)
        self.timer.timeout.connect(self._scheduled)
        self.timer.start()
        learning.changed.connect(self._help_changed)

    def _help_changed(self):
        if self.store and not self.store.read_only and not self.busy:
            value = dict(self.draft["help_preferences"], depth=self.learning.depth)
            if self.draft["help_preferences"] != value:
                self.draft["help_preferences"] = value
                self.changed.emit()

    @staticmethod
    def local(value):
        if value.startswith("file:"):
            url = QUrl(value)
            if not url.isLocalFile() or url.host():
                raise ProjectError("Yalnız yerel dosya yolları desteklenir.")
            value = url.toLocalFile()
        if not value:
            raise ProjectError("Proje yolu boş olamaz.")
        return Path(value).expanduser().absolute()

    @Slot(str, result=str)
    def newProjectPath(self, folder):
        return str(self.local(folder) / "Yeni_Proje")

    def _run(self, action):
        try:
            if self.busy:
                raise ProjectError("Devam eden proje/içe aktarma işlemini bekleyin.")
            action()
            self._error = ""
            return True
        except (OSError, ValueError, TypeError, sqlite3.Error) as error:
            self._error = project_error_text(error)
            return False
        finally:
            self.changed.emit()

    def _remember(self):
        path = str(self.store.root)
        self._recent = [path] + [p for p in self._recent if p != path][:19]
        if not self._recent_writable:
            self._message += " Son projeler dosyası yazılamıyor."
            return
        try:
            from PySide6.QtCore import QIODevice, QSaveFile

            file = QSaveFile(str(self.config / "recent-projects.json"))
            file.setDirectWriteFallback(False)
            raw = encode(self._recent)
            if (
                not file.open(QIODevice.WriteOnly)
                or file.write(raw) != len(raw)
                or not file.commit()
            ):
                raise OSError("Recent list write failed")
        except OSError:
            self._message += (
                " Son projeler listesi kaydedilemedi; proje kaydı tamamlandı."
            )

    def _adopt(self, store, statuses=None):
        previous = self.store
        self.store = store
        self.draft = store.state
        self._statuses = statuses if statuses is not None else store.source_statuses()
        self._watch_sources()
        self.saved = copy.deepcopy(self.draft)
        self.learning.setDepth(self.draft["help_preferences"].get("depth", 0))
        self._message = (
            store.notice or "Metadata açıldı. Kaynak veriler yeniden işlenmedi."
        )
        if store.path("AUTOSAVE").exists():
            self._message += " Ayrı otomatik kayıt var; Kurtarma kaydını yükle ile inceleyebilirsiniz."
        if previous:
            previous.close()
        self._remember()

    @Property(bool, notify=changed)
    def busy(self):
        return self.future is not None or self.import_active or self.dataset_active

    @Property(bool, notify=changed)
    def dirty(self):
        return self.draft != self.saved

    @Property(bool, notify=changed)
    def opened(self):
        return self.store is not None

    @Property(bool, notify=changed)
    def readOnly(self):
        return self.store is not None and self.store.read_only

    @Property(str, notify=changed)
    def name(self):
        return self.draft["name"]

    @Property(str, notify=changed)
    def seedText(self):
        return "" if self.draft["seed"] is None else str(self.draft["seed"])

    @Property(str, notify=changed)
    def context(self):
        if not self.store:
            return "Proje açık değil · Veri yüklenmedi"
        return f"{self.name} · {'Salt okunur' if self.readOnly else ('Kaydedilmemiş değişiklikler' if self.dirty else 'Kaydedildi')} · Kayıt {self.store.commit_id[:8]}"

    @Property(str, notify=changed)
    def errorText(self):
        return self._error

    @Property(str, notify=changed)
    def message(self):
        return self._message

    @Property("QStringList", notify=changed)
    def recent(self):
        return self._recent

    @Property("QVariantList", notify=changed)
    def sources(self):
        return self.draft["sources"]

    @Property(str, notify=changed)
    def sourceSummary(self):
        if not self.store:
            return "Kaynak bağlı değil."
        labels = {
            "unchanged": "aynı veri",
            "missing": "kaynak eksik — yeniden bağlayın",
            "changed": "kaynak değişmiş — eski sonuçlar güncel değil",
            "unavailable": "kaynak doğrulanamadı",
        }
        statuses = self._statuses
        return (
            "\n".join(
                f"{s['path']} · {labels[statuses.get(s['id'], 'unavailable')]}"
                for s in self.sources
            )
            or "Kaynak bağlı değil. CSV/TSV dosyasını Veri ekranında içe aktarın."
        )

    @Property(str, notify=changed)
    def resultSummary(self):
        if not self.store:
            return "Sonuç yok."
        return (
            "\n".join(
                f"{r['id']} · Veri sürümü: {', '.join(r['dataset_version_ids'])} · {'kaynakla uyumlu' if r['current'] else 'eski veri / güncel değil'}"
                for r in self._result_statuses()
            )
            or "Sonuç yok; analiz motoru henüz mevcut değil."
        )

    @Slot(str)
    def setName(self, value):
        if not self.busy and not self.readOnly and 1 <= len(value) <= 200:
            self.draft["name"] = value
            self.changed.emit()

    @Slot(str)
    def setSeed(self, value):
        def change():
            if self.readOnly or self.busy:
                raise ProjectError("Salt okunur projede seed değiştirilemez.")
            seed = int(value) if value.strip() else None
            if seed is not None and not 0 <= seed < 2**32:
                raise ProjectError("Seed 0–4294967295 aralığında olmalı.")
            self.draft["seed"] = seed

        self._run(change)

    def _clean_transition(self):
        if self.dirty or self.busy:
            raise ProjectError(
                "Önce değişiklikleri kaydedin veya Değişiklikleri bırak ile kapatın."
            )

    @Slot(str, result=bool)
    def create(self, path):
        def action():
            self._clean_transition()
            self._adopt(ProjectStore.create(self.local(path), self.name))

        return self._run(action)

    @Slot(str, result=bool)
    def open(self, path):
        def action():
            self._clean_transition()
            self._adopt(ProjectStore.open(self.local(path)))

        return self._run(action)

    @Slot(result=bool)
    def save(self):
        def action():
            if not self.store:
                raise ProjectError("Önce yeni bir proje oluşturun.")
            self.store.save()
            self.saved = copy.deepcopy(self.draft)
            self._message = "Proje kaydedildi."

        return self._run(action)

    @Slot(str, result=bool)
    def saveAs(self, path):
        def action():
            if not self.store:
                raise ProjectError("Önce proje oluşturun veya açın.")
            self._adopt(self.store.save_as(self.local(path)))

        return self._run(action)

    @Slot(str, bool, result=bool)
    def addSource(self, path, portable):
        def action():
            if not self.store:
                raise ProjectError("Önce proje oluşturun.")
            self.store.stage_source(self.local(path), portable)
            self._message = "Kaynak bağı eklendi; henüz veri içe aktarılmadı."

        return self._run(action)

    @Slot(str, str, result=bool)
    def relink(self, source_id, path):
        return self._run(lambda: self.store.relink(source_id, self.local(path)))

    @Slot()
    def refreshSources(self):
        self.request("refresh")

    @Slot(result=bool)
    def recoverLock(self):
        def action():
            if not self.store or not self.readOnly:
                raise ProjectError("Kurtarılacak salt okunur proje yok.")
            root = self.store.root
            self._adopt(ProjectStore.open(root, recover_lock=True))

        return self._run(action)

    @Slot(result=bool)
    def restoreAutosave(self):
        def action():
            self.store.restore_autosave()
            self.draft = self.store.state
            self.learning.setDepth(self.draft["help_preferences"].get("depth", 0))
            self._message = "Kurtarma kaydı yüklendi. Manuel kayıt değişmedi; inceleyip Kaydet seçin."

        return self._run(action)

    @Slot()
    def autosave(self):
        if self.store and self.dirty and not self.readOnly:
            self._run(lambda: self.store.save(autosave=True))

    @Slot(bool, result=bool)
    def closeProject(self, discard=False):
        def action():
            if self.busy or (self.dirty and not discard):
                raise ProjectError("Kaydedilmemiş değişiklikler var.")
            if self.store:
                self.store.close()
            self.store = None
            self.draft = new_state()
            self.saved = copy.deepcopy(self.draft)

        return self._run(action)

    def _result_statuses(self):
        versions = {d["version_id"]: d for d in self.draft["datasets"]}
        from veri_ufku.operations.contracts import heads

        latest = heads(self.draft)
        return [
            dict(
                r,
                current=all(
                    self._statuses.get(versions[v]["source_id"]) == "unchanged"
                    and latest[versions[v]["dataset_id"]] == v
                    for v in r["dataset_version_ids"]
                ),
            )
            for r in self.draft["results"]
        ]

    def _watch_sources(self):
        current = self.watcher.files() + self.watcher.directories()
        if current:
            self.watcher.removePaths(current)
        paths = set()
        for source in self.draft["sources"]:
            path = Path(source["path"])
            if path.is_file():
                paths.add(str(path))
            if path.parent.is_dir():
                paths.add(str(path.parent))
        if paths:
            self.watcher.addPaths(sorted(paths))

    def _source_changed(self, path):
        self._statuses = {s["id"]: "unavailable" for s in self.draft["sources"]}
        self._refresh_pending = True
        self.changed.emit()
        if not self.busy:
            self._refresh_pending = False
            self.request("refresh")

    def _scheduled(self):
        if self.store and not self.busy:
            self.request("autosave" if self.dirty and not self.readOnly else "refresh")

    @Slot(str)
    @Slot(str, str)
    @Slot(str, str, str)
    @Slot(str, str, str, bool)
    def request(self, action, value="", source_id="", portable=False):
        if self.busy:
            self._error = "Proje işlemi devam ediyor. Tamamlanmasını bekleyin."
            self.changed.emit()
            return
        try:
            if action in {"create", "open", "openRecover", "recover"}:
                self._clean_transition()
            path = (
                self.local(value)
                if action
                in {"create", "open", "openRecover", "saveAs", "addSource", "relink"}
                else None
            )
            self._action = action
            self._submitted = copy.deepcopy(self.draft)
            self.future = self.executor.submit(
                project_task,
                action,
                self.store,
                self._submitted,
                path,
                source_id,
                portable,
            )
            self._error = ""
            self._message = "Proje işlemi sürüyor… Kaynak dosyana yazılmıyor."
        except (OSError, ValueError) as error:
            self._error = project_error_text(error)
        self.changed.emit()

    def _poll(self):
        if self.future is None or not self.future.done():
            return
        future, action = self.future, self._action
        self.future = None
        success = False
        try:
            result, state, statuses = future.result()
            if action in {"create", "open", "openRecover", "saveAs", "recover"}:
                self._adopt(result, statuses)
            else:
                self._statuses = (
                    {s["id"]: "unavailable" for s in state["sources"]}
                    if self._refresh_pending
                    else statuses
                )
                if action in {"addSource", "relink", "restore"}:
                    self.draft = state
                    self._watch_sources()
                self.store.state = self.draft
                if action == "save":
                    self.saved = self._submitted
                if action == "restore":
                    self.learning.setDepth(state["help_preferences"].get("depth", 0))
                self._message = {
                    "save": "Proje kaydedildi.",
                    "autosave": "Ayrı kurtarma kaydı güncellendi; manuel kayıt korunuyor.",
                    "restore": "Kurtarma kaydı yüklendi; inceleyip Kaydet seçin.",
                    "addSource": "Kaynak bağı eklendi; veri içe aktarılmadı.",
                    "relink": "Aynı veri kaynağı yeniden bağlandı.",
                }.get(action, "Kaynak kontrolü tamamlandı; veri yeniden işlenmedi.")
            self._error = ""
            success = True
        except Exception as error:
            self._error = project_error_text(error)
            if self.store:
                self.store.state = self.draft
        self.changed.emit()
        if action == "save":
            self.saveFinished.emit(success)
        if self._refresh_pending and self.store:
            self._refresh_pending = False
            self.request("refresh")

    def shutdown(self):
        self.timer.stop()
        self.poller.stop()
        self._refresh_pending = False
        self.executor.shutdown(wait=True)
        if self.future:
            self._poll()
        if self.store:
            self.store.close()
