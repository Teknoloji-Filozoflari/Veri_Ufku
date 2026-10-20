"""Manifest-only discovery and explicit trusted plugin invocation."""

import json

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.domain.json import parse
from veri_ufku.plugins.discovery import inspect
from veri_ufku.plugins.runtime import worker
from veri_ufku.storage import plugin_store as storage
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.ui.monitoring import MonitoringController


def dump(v):
    return json.dumps(v, ensure_ascii=False, indent=2, default=str)


class PluginController(MonitoringController):
    pluginChanged = Signal()
    storage = storage
    worker = staticmethod(worker)
    result_kind = "plugin_result"
    public_report = staticmethod(lambda v: v)

    def __init__(self, *args):
        self._inspection = {}
        self._path = ""
        super().__init__(*args)
        self.changed.connect(self.pluginChanged.emit)

    models = Property("QVariantList", lambda s: [], notify=pluginChanged)
    currentRoute = Property("QVariantMap", lambda s: {}, notify=pluginChanged)
    saved = Property(
        "QVariantList",
        lambda s: [
            dict(id=r["id"], label=r["plugin_result"]["plugin_id"] + " · " + r["id"])
            for r in s.projects.draft["results"]
            if "plugin_result" in r
        ],
        notify=pluginChanged,
    )
    outputText = Property(str, lambda s: dump(s.result), notify=pluginChanged)
    inspectionText = Property(str, lambda s: dump(s._inspection), notify=pluginChanged)
    pluginHelp = Property(
        str,
        lambda s: dump(
            s.result.get("manifest", s._inspection.get("manifest", {})).get(
                "learning", {}
            )
        ),
        notify=pluginChanged,
    )

    @Slot(str)
    def inspectManifest(self, path):
        try:
            self.ready()
            self._inspection = {}
            self._path = ""
            self._inspection, _ = inspect(path)
            self._path = path
            self._error = ""
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    @Slot(str, result=str)
    def template(self, version):
        try:
            d = next(
                d for d in self.projects.draft["datasets"] if d["version_id"] == version
            )
            cols = d["import_metadata"]["columns"]
            return dump(
                dict(
                    version=version,
                    columns=[cols[0]["id"]] if cols else [],
                    params={
                        k: v["default"]
                        for k, v in self._inspection.get("manifest", {})
                        .get("capability", {})
                        .get("parameters", {})
                        .items()
                    },
                    seed=0,
                )
            )
        except (KeyError, StopIteration):
            return "{}"

    @Slot(str, bool, bool)
    def execute(self, text, trusted, network):
        try:
            p = parse(text)
            if not isinstance(p, dict) or set(p) != {
                "version",
                "columns",
                "params",
                "seed",
            }:
                raise ProjectError("Plugin recipe version/columns/params/seed gerekli.")
            p.update(
                manifest_path=self._path,
                inspection_hash=self._inspection.get("inspection_hash", ""),
                trusted=trusted,
                network_confirmed=network,
            )
            self.run(dump(p))
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    @Slot(str)
    def openReport(self, ident):
        try:
            if not self.projects.store or self.busy or self.projects.busy:
                raise ProjectError("Kayıtlı sonuç için açık ve boşta proje gerekli.")
            record = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident and "plugin_result" in r
            )
            self.result = storage.load(self.projects.store, record)
            self._error = ""
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError, StopIteration) as e:
            self.fail(e)

    def project_changed(self):
        root = str(self.projects.store.root) if self.projects.store else None
        if root != self._root and not self.busy:
            self._inspection = {}
            self._path = ""
        super().project_changed()
