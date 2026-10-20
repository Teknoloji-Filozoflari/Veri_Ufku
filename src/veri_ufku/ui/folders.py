"""Bounded directory browsing and explicit new-folder creation outside the GUI thread; literal URL paths."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot


def directory_rows(path):
    rows = []
    with os.scandir(path) as entries:
        for index, entry in enumerate(entries):
            if index >= 100000 or len(rows) >= 10000:
                raise ValueError(
                    "Klasörde çok fazla öğe var; daha küçük bir alt klasör seçin."
                )
            try:
                if entry.is_dir():
                    rows.append(
                        dict(
                            name=entry.name,
                            url=QUrl.fromLocalFile(entry.path).toString(),
                        )
                    )
            except OSError:
                continue
    return sorted(rows, key=lambda row: (row["name"].casefold(), row["name"]))


class FolderController(QObject):
    changed = Signal()
    folderCreated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="folder-list"
        )
        self.future = None
        self.pending = None
        self._rows = []
        self.query = ""
        self.hidden = False
        self._error = ""
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    busy = Property(bool, lambda self: self.future is not None, notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    rows = Property(
        "QVariantList",
        lambda self: [
            row
            for row in self._rows
            if (self.hidden or not row["name"].startswith("."))
            and self.query.casefold() in row["name"].casefold()
        ],
        notify=changed,
    )

    @Slot(str)
    def load(self, value):
        if self.future:
            self.pending = value
            return
        url = QUrl(value)
        if not url.isLocalFile() or url.host():
            self._error = "Yalnız yerel klasörler seçilebilir."
            self.changed.emit()
            return
        self._rows = []
        self._error = ""
        self.future = self.executor.submit(directory_rows, Path(url.toLocalFile()))
        self.changed.emit()

    @Slot(str, str)
    def createFolder(self, value, name):
        if self.future:
            return
        url = QUrl(value)
        if (
            not url.isLocalFile()
            or url.host()
            or not name.strip()
            or name in (".", "..")
            or "/" in name
            or "\\" in name
            or "\x00" in name
        ):
            self._error = "Tek bir yerel klasör adı yazın; yol veya üst klasör ifadesi kullanmayın."
            self.changed.emit()
            return
        self._error = ""
        self.future = self.executor.submit(
            create_directory, Path(url.toLocalFile()), name
        )
        self.changed.emit()

    @Slot(str)
    def search(self, value):
        self.query = value
        self.changed.emit()

    @Slot(bool)
    def showHidden(self, value):
        self.hidden = value
        self.changed.emit()

    def poll(self):
        if not self.future or not self.future.done():
            return
        future, self.future = self.future, None
        if self.pending is not None:
            pending, self.pending = self.pending, None
            self.load(pending)
            return
        try:
            value = future.result()
            if isinstance(value, dict):
                self._rows = value["rows"]
                self.folderCreated.emit(value["url"])
            else:
                self._rows = value
        except FileExistsError:
            self._error = (
                "Bu isimde bir klasör veya dosya zaten var; farklı bir ad seçin."
            )
        except OSError:
            self._error = "Klasör okunamadı veya oluşturulamadı. Erişim iznini veya konumu kontrol edin."
        except ValueError as error:
            self._error = str(error)
        self.changed.emit()

    def shutdown(self):
        self.timer.stop()
        self.executor.shutdown(wait=True, cancel_futures=True)


def create_directory(parent, name):
    destination = parent / name
    destination.mkdir()
    return dict(
        rows=directory_rows(destination),
        url=QUrl.fromLocalFile(str(destination)).toString(),
    )
