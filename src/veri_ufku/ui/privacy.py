"""Explicit local privacy actions; no automatic scan, deletion or key generation."""

import copy
import json
import threading
import time

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.domain.json import parse
from veri_ufku.exports.privacy_contracts import LIMITATIONS
from veri_ufku.exports.privacy_worker import worker
from veri_ufku.importers.delimited import Control
from veri_ufku.storage import privacy_store as storage
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.ui.monitoring import MonitoringController


def dump(v):
    return json.dumps(v, ensure_ascii=False, indent=2, default=str)


class PrivacyController(MonitoringController):
    privacyChanged = Signal()
    storage = storage
    worker = staticmethod(worker)
    result_kind = "privacy_event"
    public_report = staticmethod(lambda v: v)

    def __init__(self, *args):
        self._preview = {}
        self._scan = {}
        self._cleanup = {}
        self._io = False
        super().__init__(*args)
        self.changed.connect(self.privacyChanged.emit)

    models = Property("QVariantList", lambda s: [], notify=privacyChanged)
    currentRoute = Property("QVariantMap", lambda s: {}, notify=privacyChanged)
    saved = Property(
        "QVariantList",
        lambda s: [
            dict(id=r["id"], label=r["id"], event=r["privacy_event"])
            for r in s.projects.draft["results"]
            if r.get("privacy_event", {}).get("kind") == "review"
        ],
        notify=privacyChanged,
    )
    outputText = Property(str, lambda s: dump(s.result), notify=privacyChanged)
    previewText = Property(str, lambda s: dump(s._preview), notify=privacyChanged)
    limitations = Property(str, lambda s: "\n".join(LIMITATIONS), constant=True)
    dependenciesText = Property(
        str,
        lambda s: dump(storage.dependencies(s.projects.draft)),
        notify=privacyChanged,
    )

    @Slot(str)
    def scan(self, version):
        self.run(dump(dict(action="scan", version=version)))

    @Slot(result=str)
    def template(self):
        return dump(
            dict(
                version=self._scan.get("version", ""),
                rules=[
                    dict(column=c["id"], classification="uncertain", strategy="mask")
                    for c in self._scan.get("columns", [])[:16]
                ],
                reviewer="Yerel inceleyen",
                rationale="Kolonlar ve linkage riski incelendi",
                key_ref="",
            )
        )

    @Slot(str, bool)
    def savePolicy(self, text, confirmed):
        try:
            self.ready()
            if confirmed is not True:
                raise ProjectError("Kolon kararları için açık insan onayı gerekli.")
            self.future = self.projects.executor.submit(
                storage.review,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                parse(text),
            )
            self.projects.dataset_active = True
            self._error = ""
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    @Slot(str)
    def preview(self, review):
        self.run(dump(dict(action="preview", review_id=review)))

    @Slot(str, str, str, str, bool)
    def exportData(self, review, destination, fmt, keyref, confirmed):
        self.run(
            dump(
                dict(
                    action="export",
                    review_id=review,
                    destination=destination,
                    format=fmt,
                    encryption_key_ref=keyref,
                    preview_hash=self._preview.get("preview_hash", ""),
                    reviewed=confirmed,
                )
            )
        )

    @Slot(str, str)
    def inspectSealed(self, path, keyref):
        self.run(dump(dict(action="inspect", archive=path, encryption_key_ref=keyref)))

    def io(self, fn, *args):
        self.ready()
        self._io = True
        self.cancel_event = threading.Event()
        self.started = time.monotonic()
        self.future = self.projects.executor.submit(
            fn, *args, Control(cancel=self.cancel_event, budget=self.budget)
        )
        self.projects.dataset_active = True
        self._error = ""
        self.projects.changed.emit()
        self.changed.emit()

    @Slot(str, str)
    def generateKey(self, purpose, ref):
        self.run(dump(dict(action="generate-key", purpose=purpose, key_ref=ref)))

    @Slot(int)
    def retention(self, days):
        try:
            self.ready()
            self.future = self.projects.executor.submit(
                storage.retention,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                days,
            )
            self.projects.dataset_active = True
            self._error = ""
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    @Slot(int)
    def cleanupPreview(self, days):
        try:
            from veri_ufku.exports.privacy_cleanup import preview

            self.io(
                preview,
                self.cache,
                self.projects.store.root if self.projects.store else "",
                days,
            )
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    @Slot(bool)
    def cleanup(self, confirmed):
        try:
            if not self._cleanup:
                raise ProjectError("Önce cleanup scope önizlemesi gerekli.")
            self.io(
                storage.cleanup,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                self.cache,
                copy.deepcopy(self._cleanup),
                confirmed,
            )
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    def project_changed(self):
        root = str(self.projects.store.root) if self.projects.store else None
        if root != self._root and not self.busy:
            self._preview = {}
            self._scan = {}
            self._cleanup = {}
        super().project_changed()

    @Slot()
    def cancel(self):
        if self._io and self.cancel_event:
            self.cancel_event.set()
        else:
            super().cancel()

    def poll(self):
        if self._io:
            if time.monotonic() - self.started > self.budget.max_wall_seconds:
                self.cancel_event.set()
            if not self.future or not self.future.done():
                return
            f, self.future = self.future, None
            self._io = False
            try:
                value = f.result()
                if isinstance(value, tuple):
                    self.projects.draft, value = value
                    self.projects.saved = copy.deepcopy(self.projects.draft)
                self.result = value
                if self.result.get("schema") == "PrivacyCleanup/v1":
                    self._cleanup = self.result
            except Exception as e:
                self.fail(e)
            self.projects.dataset_active = False
            self.projects.changed.emit()
            self.changed.emit()
            return
        old = self.result
        super().poll()
        if self.result is not old:
            if self.result.get("action") == "preview":
                self._preview = self.result
            if self.result.get("action") == "scan":
                self._scan = self.result
            self.changed.emit()
