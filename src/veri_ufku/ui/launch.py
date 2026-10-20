"""Desktop file requests wait for an explicitly opened writable project."""

from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, Signal, Slot


class LaunchRequests(QObject):
    navigate = Signal(int, int)

    def __init__(self, projects, imports, parent=None):
        super().__init__(parent)
        self.projects, self.imports = projects, imports
        self.pending = None
        projects.changed.connect(self.deliver)

    def queue(self, value):
        if urlsplit(value).scheme not in {"", "file"}:
            raise ValueError("Only local files are supported")
        path = self.projects.local(value)
        if not Path(path).is_file():
            raise ValueError("Choose an existing local data file")
        self.pending = str(path)
        self.navigate.emit(1, 0)
        self.projects._message = "Dosya açmak için bir proje oluşturun veya açın; ardından import önizlemesi gösterilecek."
        self.projects.changed.emit()

    @Slot()
    def deliver(self):
        if (
            self.pending
            and self.projects.opened
            and not self.projects.readOnly
            and not self.projects.busy
        ):
            path, self.pending = self.pending, None
            self.imports.choose(path)
            self.navigate.emit(1, 1)
