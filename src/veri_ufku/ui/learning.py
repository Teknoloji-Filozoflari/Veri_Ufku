"""Qt presentation of offline articles and optional local reading marks."""

import json
import uuid
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QFileDevice,
    QIODevice,
    QObject,
    QSaveFile,
    Signal,
    Slot,
)

from veri_ufku.learning.catalog import SCREEN_CONTEXTS, Catalog


class LearningController(QObject):
    changed = Signal()
    resultsChanged = Signal()
    exampleRequested = Signal()

    def __init__(self, config_path: Path, parent=None, *, sandbox=False, catalog=None):
        super().__init__(parent)
        self.catalog = catalog or Catalog()
        self.path = config_path / "learning-marks.json"
        self._article_id = "learn"
        self._query = ""
        self._category = "Tümü"
        self._glossary = False
        self._depth = 0
        self._enabled = False
        self._read = set()
        self._bookmarks = set()
        self._error = ""
        self._writable = True
        self._sandbox = sandbox
        self._project_id = ""
        self._example = None
        if not sandbox:
            self._load_marks()
            self._example = LearningController(
                config_path, self, sandbox=True, catalog=self.catalog
            )

    def _load_marks(self):
        try:
            if not self.path.exists():
                return
            if self.path.stat().st_size > 64_000:
                raise ValueError("Reading marks too large")
            data = json.loads(self.path.read_text())
            if not isinstance(data, dict) or set(data) != {
                "schema_version",
                "enabled",
                "read",
                "bookmarks",
            }:
                raise ValueError("Invalid reading marks")
            if (
                type(data["schema_version"]) is not int
                or data["schema_version"] != 1
                or type(data["enabled"]) is not bool
            ):
                raise ValueError("Unsupported reading marks")
            for field in ("read", "bookmarks"):
                if not isinstance(data[field], list) or any(
                    not isinstance(key, str) or key not in self.catalog.articles
                    for key in data[field]
                ):
                    raise ValueError("Invalid article marks")
            self._enabled, self._read, self._bookmarks = (
                data["enabled"],
                set(data["read"]),
                set(data["bookmarks"]),
            )
        except (OSError, ValueError, TypeError):
            self._writable = False
            self._error = "Okuma tercihleri okunamadı. Mevcut dosya korundu; yardım okumaya devam edebilirsin."

    def _save_marks(self, enabled, read, bookmarks):
        if self._sandbox or not self._writable:
            return False
        data = json.dumps(
            dict(
                schema_version=1,
                enabled=enabled,
                read=sorted(read),
                bookmarks=sorted(bookmarks),
            )
        ).encode()
        file = QSaveFile(str(self.path))
        file.setDirectWriteFallback(False)
        if (
            not file.open(QIODevice.OpenModeFlag.WriteOnly)
            or not file.setPermissions(
                QFileDevice.Permission.ReadOwner | QFileDevice.Permission.WriteOwner
            )
            or file.write(data) != len(data)
            or not file.commit()
        ):
            file.cancelWriting()
            self._error = "Okuma tercihleri kaydedilemedi. Önceki kayıt korundu."
            self.changed.emit()
            return False
        self._enabled, self._read, self._bookmarks = enabled, read, bookmarks
        self.resultsChanged.emit()
        self._error = ""
        self.changed.emit()
        return True

    @Property("QVariantList", notify=resultsChanged)
    def results(self):
        return [
            dict(
                id=a["id"],
                title=a["title"],
                summary=a["summary"],
                category=a["category"],
                read=a["id"] in self._read,
                bookmarked=a["id"] in self._bookmarks,
            )
            for a in self.catalog.search(self._query, self._category, self._glossary)
        ]

    @Property("QVariantMap", notify=changed)
    def article(self):
        return dict(self.catalog.articles[self._article_id])

    @Property("QVariantList", notify=changed)
    def relatedArticles(self):
        return [
            dict(id=key, title=self.catalog.articles[key]["title"])
            for key in self.article["related"]
        ]

    @Property(str, notify=changed)
    def articleContexts(self):
        labels = dict(
            zip(
                SCREEN_CONTEXTS,
                (
                    "Başlangıç",
                    "Veri",
                    "Hazırla",
                    "İncele",
                    "Karşılaştır",
                    "Model",
                    "Rapor",
                    "Öğren",
                ),
            )
        )
        labels.update(
            {
                "demo.cpu": "CPU denemesi",
                "demo.io": "I/O denemesi",
                "demo.unknown": "Belirsiz ilerleme",
                "demo.failure": "Hata denemesi",
                "learn.search": "Yardım araması",
                "learn.example": "Örnek öğrenme projesi",
            }
        )
        return ", ".join(
            labels.get(context, context) for context in self.article["contexts"]
        )

    @Property("QStringList", constant=True)
    def screenContexts(self):
        return list(SCREEN_CONTEXTS)

    @Property("QStringList", constant=True)
    def categories(self):
        return ["Tümü"] + list(
            dict.fromkeys(a["category"] for a in self.catalog.articles.values())
        )

    @Property(str, notify=changed)
    def query(self):
        return self._query

    @Property(str, notify=changed)
    def category(self):
        return self._category

    @Property(bool, notify=changed)
    def glossary(self):
        return self._glossary

    @Property(int, notify=changed)
    def depth(self):
        return self._depth

    @Property(bool, notify=changed)
    def marksEnabled(self):
        return self._enabled

    @Property(bool, notify=changed)
    def isRead(self):
        return self._article_id in self._read

    @Property(bool, notify=changed)
    def isBookmarked(self):
        return self._article_id in self._bookmarks

    @Property(str, notify=changed)
    def errorText(self):
        return self._error

    @Property(bool, constant=True)
    def sandbox(self):
        return self._sandbox

    @Property(str, notify=changed)
    def projectId(self):
        return self._project_id

    @Property(QObject, constant=True)
    def exampleLibrary(self):
        return self._example

    @Slot(str)
    def setQuery(self, value):
        self._query = value[:200]
        self.resultsChanged.emit()
        self.changed.emit()

    @Slot(str)
    def setCategory(self, value):
        if value in self.categories:
            self._category = value
            self.resultsChanged.emit()
            self.changed.emit()

    @Slot(bool)
    def setGlossary(self, value):
        self._glossary = value
        self.resultsChanged.emit()
        self.changed.emit()

    @Slot(int)
    def setDepth(self, value):
        if value in (0, 1, 2):
            self._depth = value
            self.changed.emit()

    @Slot(str, result=bool)
    def openArticle(self, article_id):
        if article_id not in self.catalog.articles:
            self._error = "Bu yardım kaydı bulunamadı."
            self.changed.emit()
            return False
        self._article_id = article_id
        if self._writable:
            self._error = ""
        self.changed.emit()
        return True

    @Slot(str, result=bool)
    def openContext(self, context):
        try:
            return self.openArticle(self.catalog.article_for(context))
        except ValueError:
            self._error = "Bu ekran veya işlem için yardım kaydı bulunamadı."
            self.changed.emit()
            return False

    @Slot(bool)
    def setMarksEnabled(self, value):
        # Opt out clears marks in the same atomic publication.
        self._save_marks(
            value, self._read if value else set(), self._bookmarks if value else set()
        )

    @Slot()
    def toggleRead(self):
        if self._enabled:
            read = self._read ^ {self._article_id}
            self._save_marks(True, read, self._bookmarks)

    @Slot()
    def toggleBookmark(self):
        if self._enabled:
            bookmarks = self._bookmarks ^ {self._article_id}
            self._save_marks(True, self._read, bookmarks)

    @Slot()
    def tryExample(self):
        if self.article["try_action"] != "learn.example" or self._sandbox:
            return
        example = self._example
        example._project_id = "learning-example:" + str(uuid.uuid4())
        example._article_id = "mean-median"
        example._query = "medyan"
        example._category = "Tümü"
        example._glossary = False
        example._depth = 1
        example.resultsChanged.emit()
        example.changed.emit()
        self.exampleRequested.emit()
