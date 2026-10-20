"""Explicit local review/share UI; no server, implicit merge or common project writer."""

import copy
import json
import threading

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.domain.json import parse
from veri_ufku.exports.share_privacy import LIMITATIONS
from veri_ufku.exports.share_worker import worker
from veri_ufku.importers.delimited import Control
from veri_ufku.storage import review_store as storage
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.ui.monitoring import MonitoringController


def dump(v):
    return json.dumps(v, ensure_ascii=False, indent=2, default=str)


class SharingController(MonitoringController):
    shareChanged = Signal()
    storage = storage
    worker = staticmethod(worker)
    result_kind = "review_event"
    public_report = staticmethod(lambda v: v)

    def __init__(self, *args):
        self._preview = {}
        self._opened = {}
        self._spec = None
        self._io = False
        super().__init__(*args)
        self.changed.connect(self.shareChanged.emit)

    currentRoute = Property("QVariantMap", lambda s: {}, notify=shareChanged)
    models = Property("QVariantList", lambda s: [], notify=shareChanged)
    saved = Property(
        "QVariantList",
        lambda s: (
            [
                dict(
                    id=r["id"],
                    event=r["review_event"],
                    binding=storage.binding_status(
                        r["review_event"], s.projects.draft, s.projects.store.manifest
                    ),
                )
                for r in s.projects.draft["results"]
                if "review_event" in r
            ]
            if s.projects.store
            else []
        ),
        notify=shareChanged,
    )
    outputText = Property(str, lambda s: dump(s.result), notify=shareChanged)
    previewText = Property(str, lambda s: dump(s._preview), notify=shareChanged)
    limitations = Property(str, lambda s: "\n".join(LIMITATIONS), constant=True)
    reviewTargets = Property(
        "QVariantList",
        lambda s: [
            dict(id=k, label=v["kind"] + " · " + v["id"])
            for k, v in s.projection().get("entities", {}).items()
        ],
        notify=shareChanged,
    )
    commentsText = Property(str, lambda s: dump(s.saved), notify=shareChanged)
    errorText = Property(
        str, lambda s: s._error.replace("Monitoring", "Paylaşım"), notify=shareChanged
    )

    def projection(self):
        return self._opened.get("projection") or self._preview.get("projection") or {}

    @Slot(str, result=str)
    def template(self, mode):
        if mode not in ("metadata-only", "redacted-sample", "full-copy"):
            mode = "metadata-only"
        datasets = self.projects.draft["datasets"]
        return dump(
            dict(
                mode=mode,
                version=datasets[-1]["version_id"] if datasets else "",
                rows=10,
                keep_numeric=[],
                sensitive_terms=[],
            )
        )

    @Slot(str)
    def inspect(self, text):
        try:
            value = parse(text)
            self._spec = copy.deepcopy(value)
            self._opened = {}
            self.run(dump(dict(action="preview", spec=value)))
        except (ValueError, TypeError, KeyError) as e:
            self.fail(e)

    @Slot(str, bool, bool)
    def exportBundle(self, destination, reviewed, allow_pii):
        if not self._preview or self._spec is None:
            self.fail(ProjectError("Önce inclusion/redaction önizlemesi oluşturun."))
            return
        self.run(
            dump(
                dict(
                    action="bundle",
                    spec=self._spec,
                    destination=destination,
                    preview_hash=self._preview["preview_hash"],
                    reviewed=reviewed,
                    allow_pii=allow_pii,
                )
            )
        )

    @Slot(str)
    def openBundle(self, path):
        self.run(dump(dict(action="open", archive=path)))

    @Slot(str, str)
    def compareBundles(self, left, right):
        self.run(dump(dict(action="diff", left=left, right=right)))

    @Slot(str, str, str, str, str)
    def saveReview(self, target, author, note, checks, decision):
        try:
            self.ready()
            if not self.projection():
                raise ProjectError("Önce hedef paket veya yerel preview açın.")
            bound = storage.subject(
                self.projection(), target, self._opened.get("fingerprint")
            )
            self.future = self.projects.executor.submit(
                storage.append_review,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                bound,
                author,
                note,
                parse(checks),
                decision,
            )
            self.projects.dataset_active = True
            self._error = ""
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    @Slot(str, str, bool)
    def restoreCopy(self, archive, destination, reviewed):
        try:
            self.ready()
            if not reviewed or not self._opened:
                raise ProjectError(
                    "Önce paketi hash kontrolüyle açıp inclusion onayı verin."
                )
            self.cancel_event = threading.Event()
            self._io = True
            self.future = self.projects.executor.submit(
                storage.restore,
                archive,
                destination,
                self._opened["fingerprint"],
                Control(cancel=self.cancel_event, budget=self.budget),
            )
            self.projects.dataset_active = True
            self._error = ""
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    @Slot()
    def cancel(self):
        if self._io and self.cancel_event:
            self.cancel_event.set()
        else:
            super().cancel()

    def project_changed(self):
        root = str(self.projects.store.root) if self.projects.store else None
        if root != self._root and not self.busy:
            self._preview = {}
            self._opened = {}
            self._spec = None
        super().project_changed()

    def poll(self):
        if self._io:
            if not self.future or not self.future.done():
                return
            future, self.future = self.future, None
            self._io = False
            try:
                self.result = future.result()
            except Exception as e:
                self.fail(e)
            self.projects.dataset_active = False
            self.projects.changed.emit()
            self.changed.emit()
            return
        old = self.result
        budget_error = (
            self._error
            if self.cancel_time and ("bütçe" in self._error or "bellek" in self._error)
            else ""
        )
        super().poll()
        if budget_error and not self.busy:
            self._error = budget_error
            self.changed.emit()
        if self.result is not old:
            if self.result.get("action") == "preview":
                self._preview = self.result
            if self.result.get("action") == "open":
                self._opened = self.result
            self.changed.emit()
