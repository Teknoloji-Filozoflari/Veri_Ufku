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
from veri_ufku.learning.curriculum import Curriculum
from veri_ufku.learning.taxonomy import CONTEXT_ONLY, learning_tree


class LearningController(QObject):
    changed = Signal()
    resultsChanged = Signal()
    exampleRequested = Signal()
    articleOpened = Signal()

    def __init__(self, config_path: Path, parent=None, *, sandbox=False, catalog=None):
        super().__init__(parent)
        self.catalog = catalog or Catalog()
        self.curriculum = Curriculum(self.catalog)
        self._lesson_id = "mean-median"
        self._lesson_path = "data"
        self._lesson_progress = {}
        self._lesson_feedback = ""
        self._favorites_only = False
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
            if not isinstance(data, dict) or set(data) not in (
                {"schema_version", "enabled", "read", "bookmarks"},
                {"schema_version", "enabled", "read", "bookmarks", "lessons"},
            ):
                raise ValueError("Invalid reading marks")
            if (
                type(data["schema_version"]) is not int
                or data["schema_version"] not in (1, 2)
                or type(data["enabled"]) is not bool
            ):
                raise ValueError("Unsupported reading marks")
            for field in ("read", "bookmarks"):
                if not isinstance(data[field], list) or any(
                    not isinstance(key, str) or key not in self.catalog.articles
                    for key in data[field]
                ):
                    raise ValueError("Invalid article marks")
            progress = data.get("lessons", {})
            if (
                data["schema_version"] == 2
                and "lessons" not in data
                or data["schema_version"] == 1
                and "lessons" in data
                or not isinstance(progress, dict)
                or any(
                    k not in self.curriculum.lessons or type(v) is not int or v < 1
                    for k, v in progress.items()
                )
            ):
                raise ValueError("Invalid lesson progress")
            self._lesson_progress = progress if data["enabled"] else {}
            self._enabled, self._read, self._bookmarks = (
                data["enabled"],
                set(data["read"]),
                set(data["bookmarks"]),
            )
        except (OSError, ValueError, TypeError):
            self._writable = False
            self._error = "Okuma tercihleri okunamadı. Mevcut dosya korundu; yardım okumaya devam edebilirsin."

    def _save_marks(self, enabled, read, bookmarks, lessons=None):
        if self._sandbox or not self._writable:
            return False
        data = json.dumps(
            dict(
                schema_version=2,
                enabled=enabled,
                read=sorted(read),
                bookmarks=sorted(bookmarks),
                lessons=(self._lesson_progress if lessons is None else lessons)
                if enabled
                else {},
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
        self._lesson_progress = (
            (self._lesson_progress if lessons is None else lessons) if enabled else {}
        )
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
            if a["id"] not in CONTEXT_ONLY
        ]

    @Property("QVariantList", notify=resultsChanged)
    def tree(self):
        return learning_tree(
            self.results,
            include_empty=not (
                self._query or self._category != "Tümü" or self._glossary
            ),
        )

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
        self.articleOpened.emit()
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

    lesson = Property(
        "QVariantMap", lambda s: s.curriculum.lessons[s._lesson_id], notify=changed
    )
    lessonPaths = Property(
        "QVariantList", lambda s: s.curriculum.data["paths"], constant=True
    )
    lessonPath = Property(str, lambda s: s._lesson_path, notify=changed)
    lessonFeedback = Property(str, lambda s: s._lesson_feedback, notify=changed)
    lessonCompleted = Property(
        bool,
        lambda s: s._lesson_progress.get(s._lesson_id) == s.lesson["version"],
        notify=changed,
    )
    lessonProgressText = Property(
        str,
        lambda s: (
            "Bu sürüm tamamlandı işaretli"
            if s.lessonCompleted
            else "Önceki sürümde işaretli; yeni sürüm okunmuş sayılmaz"
            if s._lesson_id in s._lesson_progress
            else "Tamamlandı işareti yok; araç kullanımını engellemez"
        ),
        notify=changed,
    )
    lessonPrerequisites = Property(
        "QVariantList",
        lambda s: [
            dict(id=k, title=s.curriculum.lessons[k]["title"])
            for k in s.lesson["prerequisites"]
        ],
        notify=changed,
    )
    lessons = Property(
        "QVariantList",
        lambda s: (
            s.curriculum.search(
                s._query, s._lesson_path, s._bookmarks if s._favorites_only else ()
            )
            if not s._favorites_only or s._bookmarks
            else []
        ),
        notify=changed,
    )
    favoriteLessonsOnly = Property(bool, lambda s: s._favorites_only, notify=changed)
    conceptEdges = Property(
        "QVariantList",
        lambda s: [
            dict(
                source=p,
                target=v["id"],
                label=s.curriculum.lessons[p]["title"] + " → " + v["title"],
            )
            for v in s.curriculum.data["lessons"]
            for p in v["prerequisites"]
        ],
        constant=True,
    )

    @Property("QVariantList", notify=changed)
    def moduleArticles(self):
        ids = list(
            dict.fromkeys(
                a
                for row in self.curriculum.coverage()
                if row["path"] == self._lesson_path
                for a in row["articles"]
            )
        )
        return [
            dict(
                id=k,
                title=self.catalog.articles[k]["title"],
                coverage="Makale bağlantısı; her modüle ayrı interaktif lab iddiası yok",
            )
            for k in ids
        ]

    @Slot(str)
    def setLessonPath(self, ident):
        if ident in self.curriculum.paths:
            self._lesson_path = ident
            self.changed.emit()

    @Slot(bool)
    def setFavoriteLessonsOnly(self, value):
        self._favorites_only = value
        self.changed.emit()

    @Slot(str, result=bool)
    def openLesson(self, ident):
        if ident not in self.curriculum.lessons:
            return False
        self._lesson_id = ident
        self._lesson_path = self.lesson["path"]
        self._lesson_feedback = ""
        self.openArticle(self.lesson["article_id"])
        self.changed.emit()
        return True

    @Slot(int)
    def answerLesson(self, index):
        check = self.lesson["check"]
        if 0 <= index < len(check["options"]):
            self._lesson_feedback = (
                ("Uygun yorum. " if index == check["correct"] else "Tekrar düşün. ")
                + check["feedback"][index]
                + " Puan/sertifika verilmez; devam edebilirsin."
            )
            self.changed.emit()

    @Slot()
    def completeLesson(self):
        if self._enabled:
            self._save_marks(
                True,
                self._read,
                self._bookmarks,
                dict(
                    self._lesson_progress, **{self._lesson_id: self.lesson["version"]}
                ),
            )
