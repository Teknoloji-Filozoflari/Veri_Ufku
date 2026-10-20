"""Desktop dashboard canvas, linked selection and figure composition controller."""

import copy
import json
import math
import multiprocessing as mp
import os
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from veri_ufku.charts.dashboard import (
    DashboardSpec,
    DashboardWidget,
    FigureSpec,
    save_dashboard,
)
from veri_ufku.charts.dashboard_worker import process_entry
from veri_ufku.jobs.admission import start_controller
from veri_ufku.operations.contracts import active_datasets
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.ui.projects import project_error_text


class DashboardController(QObject):
    changed = Signal()

    def __init__(self, projects, cache, budget, parent=None):
        super().__init__(parent)
        self.projects, self.cache, self.budget = projects, Path(cache), budget
        self.spec = DashboardSpec("Dashboard", ()).data()
        self.result = None
        self.revision = 0
        self.process = self.connection = self.workspace = self.result_workspace = None
        self._error = self._message = ""
        self.root = self.project_root()
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        projects.changed.connect(self.context_changed)

    def project_root(self):
        return str(self.projects.store.root) if self.projects.store else ""

    def context_changed(self):
        root = self.project_root()
        if root != self.root:
            if self.process:
                self.cancel()
            self.root = root
            self.spec = DashboardSpec("Dashboard", ()).data()
            self.result = None
            self.revision += 1
        self.changed.emit()

    busy = Property(bool, lambda self: self.process is not None, notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    message = Property(str, lambda self: self._message, notify=changed)
    viewSpec = Property("QVariantMap", lambda self: self.spec, notify=changed)
    resultData = Property("QVariantMap", lambda self: self.result or {}, notify=changed)
    savedViews = Property(
        "QVariantList",
        lambda self: [
            {"id": r["id"], "name": r["dashboard"]["name"]}
            for r in self.projects.draft["results"]
            if "dashboard" in r
        ],
        notify=changed,
    )
    datasets = Property(
        "QVariantList",
        lambda self: [
            {
                "id": d["version_id"],
                "name": d.get("import_metadata", {}).get(
                    "display_name", d["dataset_id"]
                )
                + " · "
                + d["version_id"][-8:],
                "columns": d.get("import_metadata", {}).get("columns", []),
            }
            for d in self.projects.draft["datasets"]
            if d.get("import_metadata")
        ],
        notify=changed,
    )
    savedCharts = Property(
        "QVariantList",
        lambda self: [
            {
                "id": r["id"],
                "name": r["chart"]["spec"]["title"] or r["chart"]["spec"]["kind"],
                "version": r["chart"]["dataset_version"],
            }
            for r in self.projects.draft["results"]
            if "chart" in r
        ],
        notify=changed,
    )
    widgets = Property(
        "QVariantList", lambda self: self.display_widgets(), notify=changed
    )
    current = Property(
        bool,
        lambda self: bool(self.result and self.result["revision"] == self.revision),
        notify=changed,
    )

    def display_widgets(self):
        results = {w["id"]: w for w in (self.result or {}).get("widgets", [])}
        active = {d["version_id"] for d in active_datasets(self.projects.draft)}
        datasets = {d["version_id"]: d for d in self.projects.draft["datasets"]}
        output = []
        for widget in self.spec["widgets"]:
            w = {**widget, **results.get(widget["id"], {})}
            d = datasets.get(w["dataset_version"], {})
            stale = w["dataset_version"] not in active or self.projects._statuses.get(
                d.get("source_id")
            ) not in ("unchanged", "captured")
            w["freshness"] = "stale" if stale else "current"
            w["status_text"] = (
                "Eski sürüm / kaynak değişmiş · güncel veri değildir"
                if stale
                else "Güncel snapshot"
            )
            if self.result and self.result["revision"] != self.revision:
                w["status_text"] += " · filtre/ayar değişti, yeniden hesaplayın"
            if w.get("image_path"):
                w["image_url"] = QUrl.fromLocalFile(w["image_path"]).toString()
            output.append(w)
        return output

    def fail(self, error):
        self._error = project_error_text(error)
        self.changed.emit()

    def edit(self, candidate):
        if self.busy or self.projects.busy:
            raise ProjectError("Devam eden işi bekleyin veya iptal edin.")
        DashboardSpec(**candidate).validate(
            {d["version_id"]: d for d in self.projects.draft["datasets"]}
        )
        self.spec = candidate
        self.revision += 1
        self._error = ""
        self.changed.emit()

    @Slot()
    def newView(self):
        try:
            self.edit(DashboardSpec("Dashboard", ()).data())
            self.result = None
            self.changed.emit()
        except (ValueError, TypeError) as e:
            self.fail(e)

    @Slot(str)
    def rename(self, name):
        try:
            self.edit({**self.spec, "name": name})
        except (ValueError, TypeError) as e:
            self.fail(e)

    @Slot(str, str, str, str, str)
    def addWidget(self, kind, version, column, chart, text):
        try:
            row = max(
                (w["grid"][0] + w["grid"][2] for w in self.spec["widgets"]), default=0
            )
            widget = DashboardWidget(
                kind,
                version,
                title={
                    "chart": "Grafik",
                    "table": "Tablo",
                    "kpi": "KPI",
                    "note": "Not",
                }[kind],
                column_id=column if kind == "kpi" else "",
                chart_result_id=chart if kind == "chart" else "",
                columns=(column,) if kind == "table" and column else (),
                text=text,
                grid=(row, 0, 4, 6),
            )
            candidate = copy.deepcopy(self.spec)
            candidate["widgets"].append(
                DashboardSpec("x", (widget,)).data()["widgets"][0]
            )
            self.edit(candidate)
        except (ValueError, TypeError, KeyError) as e:
            self.fail(e)

    @Slot(str, str)
    def updateWidget(self, ident, parameters):
        try:
            candidate = copy.deepcopy(self.spec)
            w = next(w for w in candidate["widgets"] if w["id"] == ident)
            changes = json.loads(parameters)
            if set(changes) - {
                "title",
                "text",
                "grid",
                "aggregation",
                "denominator",
                "denominator_mode",
                "denominator_column",
                "previous_period",
                "previous_filters",
                "columns",
            }:
                raise ProjectError("Widget düzenlemesi bilinmeyen alan içeriyor.")
            w.update(changes)
            self.edit(candidate)
        except (ValueError, TypeError, KeyError, StopIteration) as e:
            self.fail(e)

    @Slot(str)
    def removeWidget(self, ident):
        try:
            self.edit(
                {
                    **self.spec,
                    "widgets": [w for w in self.spec["widgets"] if w["id"] != ident],
                    "figure": {},
                }
            )
        except (ValueError, TypeError) as e:
            self.fail(e)

    @Slot(str, str, str, str, str)
    def addFilter(self, widget_id, version, column, operator, value):
        try:
            candidate = copy.deepcopy(self.spec)
            f = {
                "column_id": column,
                "operator": operator,
                "value": value,
                "scope": "local" if widget_id else "global",
                "dataset_version": version,
            }
            if widget_id:
                w = next(w for w in candidate["widgets"] if w["id"] == widget_id)
                if version != w["dataset_version"]:
                    raise ProjectError(
                        "Yerel filtre widget veri sürümüne bağlanmalıdır."
                    )
                w["filters"].append(f)
            else:
                candidate["global_filters"].append(f)
            self.edit(candidate)
        except (ValueError, TypeError, KeyError, StopIteration) as e:
            self.fail(e)

    @Slot()
    def clearFilters(self):
        try:
            candidate = copy.deepcopy(self.spec)
            candidate["global_filters"] = []
            for w in candidate["widgets"]:
                w["filters"] = []
            self.edit(candidate)
        except (ValueError, TypeError) as e:
            self.fail(e)

    @Slot(str, str, str, str)
    def mapColumns(self, source_version, source_column, target_version, target_column):
        try:
            candidate = copy.deepcopy(self.spec)
            candidate["filter_mappings"][
                source_version + "|" + source_column + "|" + target_version
            ] = {
                "source_version": source_version,
                "source_column": source_column,
                "target_version": target_version,
                "target_column": target_column,
            }
            self.edit(candidate)
        except (ValueError, TypeError, KeyError) as e:
            self.fail(e)

    @Slot()
    def clearMappings(self):
        try:
            self.edit({**self.spec, "filter_mappings": {}})
        except (ValueError, TypeError) as e:
            self.fail(e)

    @Slot(str, str)
    def selectRows(self, ident, row_ids):
        try:
            w = next(
                w for w in (self.result or {}).get("widgets", []) if w["id"] == ident
            )
            rows = json.loads(row_ids)
            if not set(rows) <= set(w["row_ids"]):
                raise ProjectError(
                    "Seçim widget filtre kapsamındaki RowId değerleriyle sınırlı."
                )
            self.edit(
                {
                    **self.spec,
                    "selection": {
                        "dataset_version": w["dataset_version"],
                        "row_ids": rows,
                    },
                }
            )
            self.evaluate()
        except (ValueError, TypeError, KeyError, StopIteration) as e:
            self.fail(e)

    @Slot(str, float, float, float, float)
    def brush(self, ident, x1, y1, x2, y2):
        try:
            w = next(
                w for w in (self.result or {}).get("widgets", []) if w["id"] == ident
            )
            metadata = w["chart"]["render"]
            left, right = sorted((x1 * metadata["width"], x2 * metadata["width"]))
            top, bottom = sorted((y1 * metadata["height"], y2 * metadata["height"]))
            if right - left < 10 and bottom - top < 10:
                left -= 6
                right += 6
                top -= 6
                bottom += 6
            points = {
                p["point_id"]
                for p in metadata["pixels"]
                if left <= p["x"] <= right and top <= p["y"] <= bottom
            }
            points.update(
                p["point_id"]
                for p in metadata.get("hit_regions", [])
                if p["left"] <= right
                and p["right"] >= left
                and p["top"] <= bottom
                and p["bottom"] >= top
            )
            rows = sorted(
                {
                    rid
                    for point in points
                    for rid in w["memberships"].get(str(point), [])
                }
            )
            self.selectRows(ident, json.dumps(rows))
        except (ValueError, TypeError, KeyError, StopIteration) as e:
            self.fail(e)

    @Slot(bool)
    def drillDown(self, enabled):
        try:
            self.edit({**self.spec, "drill_down": enabled})
            self.evaluate()
        except (ValueError, TypeError) as e:
            self.fail(e)

    @Slot()
    def clearSelection(self):
        try:
            self.edit({**self.spec, "selection": {}, "drill_down": False})
            self.evaluate()
        except (ValueError, TypeError) as e:
            self.fail(e)

    def request(self):
        if not self.projects.store:
            raise ProjectError("Önce proje oluşturun veya açın.")
        by_version = {d["version_id"]: d for d in self.projects.draft["datasets"]}
        spec = DashboardSpec(**self.spec)
        spec.validate(by_version)
        required = {w["dataset_version"] for w in self.spec["widgets"]}
        required.update(f["dataset_version"] for f in self.spec["global_filters"])
        if self.spec["selection"]:
            required.add(self.spec["selection"]["dataset_version"])
        for m in self.spec["filter_mappings"].values():
            required.update((m["source_version"], m["target_version"]))
        datasets = {}
        for version in required:
            d = by_version[version]
            fp = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
            datasets[version] = {
                **copy.deepcopy(d),
                "source_current": self.projects._statuses.get(d["source_id"])
                in ("unchanged", "captured"),
                "request": {
                    "path": str(self.projects.store.path(d["snapshot_uri"])).replace(
                        "/proc/self/", f"/proc/{os.getpid()}/", 1
                    ),
                    "fingerprint": {k: fp[k] for k in ("size", "sha256")},
                    "columns": copy.deepcopy(d["import_metadata"]["columns"]),
                    "row_count": d["import_metadata"]["row_count"],
                    "version_id": version,
                    "source_snapshot_id": d["import_metadata"]["source_snapshot_id"],
                    "snapshot_uri": d["snapshot_uri"],
                    "semantic_metadata": copy.deepcopy(d.get("semantic_metadata", {})),
                    "format_metadata": copy.deepcopy(
                        d["import_metadata"]["settings"].get("format_metadata", {})
                    ),
                    "config_revision": self.revision,
                },
            }
        return {
            "spec": copy.deepcopy(self.spec),
            "datasets": datasets,
            "charts": {
                r["id"]: copy.deepcopy(r["chart"])
                for r in self.projects.draft["results"]
                if "chart" in r
            },
            "active_versions": [
                d["version_id"] for d in active_datasets(self.projects.draft)
            ],
            "revision": self.revision,
        }

    @Slot()
    def evaluate(self):
        try:
            self.start("evaluate", self.request())
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    @Slot()
    def save(self):
        try:
            if (
                self.busy
                or self.projects.busy
                or self.projects.readOnly
                or not self.projects.opened
            ):
                raise ProjectError("Yazılabilir ve boşta bir proje gerekli.")
            state = copy.deepcopy(self.projects.draft)
            save_dashboard(state, self.spec)
            self.projects.draft = state
            self.projects.changed.emit()
            self.projects.request("save")
            self._message = (
                "Dashboard düzeni ve filtre sözleşmesi atomik proje kaydına gönderildi."
            )
            self.changed.emit()
        except (ValueError, TypeError, KeyError) as e:
            self.fail(e)

    @Slot(str)
    def openSaved(self, ident):
        try:
            r = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident and "dashboard" in r
            )
            self.edit(copy.deepcopy(r["dashboard"]))
            self.evaluate()
        except (ValueError, TypeError, KeyError, StopIteration) as e:
            self.fail(e)

    @Slot(str)
    def setFigure(self, parameters):
        try:
            changes = json.loads(parameters)
            ids = [
                w["chart_result_id"]
                for w in self.spec["widgets"]
                if w["kind"] == "chart"
            ]
            figure = as_figure = {
                **self.spec.get("figure", {}),
                **changes,
                "chart_result_ids": ids,
            }
            FigureSpec(**as_figure).validate()
            self.edit({**self.spec, "figure": figure})
        except (ValueError, TypeError, KeyError) as e:
            self.fail(e)

    @Slot(str, str)
    def export(self, destination, fmt):
        try:
            if not self.current:
                raise ProjectError(
                    "Export için geçerli filtre/ayar hesaplamasını çalıştırın."
                )
            result = copy.deepcopy(self.result)
            dynamic = {w["id"]: w for w in self.display_widgets()}
            charts = []
            for w in result["widgets"]:
                w["freshness"] = dynamic[w["id"]]["freshness"]
                w["status_text"] = dynamic[w["id"]]["status_text"]
                if "chart" in w:
                    chart = copy.deepcopy(w["chart"])
                    raw = next(s for s in self.spec["widgets"] if s["id"] == w["id"])
                    chart["id"] = raw["chart_result_id"]
                    chart["dashboard_context"]["freshness"] = w["freshness"]
                    charts.append(chart)
            n = len(charts)
            figure = self.spec["figure"] or {
                "chart_result_ids": [c["id"] for c in charts],
                "rows": max(1, math.ceil(n / 2)),
                "columns": min(2, max(1, n)),
            }
            self.start(
                "export",
                {
                    "result": result,
                    "charts": charts,
                    "figure": figure,
                    "destination": self.projects.local(destination),
                    "format": fmt,
                    "project_root": self.project_root(),
                },
            )
        except (ValueError, TypeError, KeyError, OSError) as e:
            self.fail(e)

    def start(self, action, request):
        if self.busy or self.projects.busy:
            raise ProjectError("Devam eden işi bekleyin veya iptal edin.")
        self.cache.mkdir(parents=True, exist_ok=True)
        self.workspace = tempfile.mkdtemp(prefix="dashboard-", dir=self.cache)
        ctx = mp.get_context("spawn")
        self.cancel_event = ctx.Event()
        self.connection, sender = ctx.Pipe(duplex=False)
        self.process = ctx.Process(
            target=process_entry,
            args=(
                action,
                request,
                self.workspace,
                self.cancel_event,
                sender,
                self.budget,
            ),
        )
        self.binding = (self.project_root(), self.revision)
        self.action = action
        self.started = time.monotonic()
        self.cancel_time = None
        try:
            if not start_controller(self, sender):
                return
        except (OSError, RuntimeError):
            sender.close()
            self.process.close()
            self.process = None
            self.release()
            raise
        sender.close()
        self.projects.dataset_active = True
        self._error = ""
        self._message = "Dashboard işi ayrı süreçte çalışıyor…"
        self.projects.changed.emit()
        self.changed.emit()

    @Slot()
    def cancel(self):
        if self.process:
            self.cancel_event.set()
            self.cancel_time = self.cancel_time or time.monotonic()

    def release(self, keep=False):
        if self.process:
            self.process.join(0.1)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(0.2)
            if self.process.is_alive():
                self.process.kill()
                self.process.join()
            self.process.close()
        if self.connection:
            self.connection.close()
        if self.workspace and not keep:
            shutil.rmtree(self.workspace, ignore_errors=True)
        self.process = self.connection = self.workspace = None
        self.projects.dataset_active = False

    def poll(self):
        if not self.process:
            return
        if time.monotonic() - self.started > self.budget.max_wall_seconds:
            self.cancel()
        if (
            self.cancel_time
            and time.monotonic() - self.cancel_time > self.budget.cancel_grace_ms / 1000
        ):
            self.release()
            self._message = "İptal edildi; proje korundu."
            self.projects.changed.emit()
            self.changed.emit()
            return
        for _ in range(20):
            if not self.connection.poll():
                break
            try:
                kind, value = self.connection.recv()
            except EOFError:
                break
            if kind == "progress":
                self._message = value
                self.changed.emit()
                continue
            valid = self.binding == (self.project_root(), self.revision)
            canceled = self.cancel_event.is_set()
            workspace = self.workspace
            keep = (
                kind == "result"
                and valid
                and not canceled
                and self.action == "evaluate"
            )
            self.release(keep)
            if canceled or kind == "canceled":
                self._message = "İptal edildi; önceki görünüm korundu."
            elif not valid:
                self._message = "Eski oturum/ayar sonucu güncel görünüme bağlanmadı."
            elif kind == "error":
                self._error = value
            elif self.action == "evaluate":
                if self.result_workspace:
                    shutil.rmtree(self.result_workspace, ignore_errors=True)
                self.result_workspace = workspace
                self.result = value
                self._message = (
                    "Dashboard hazır; her widget kendi sürüm ve filtre kapsamına bağlı."
                )
            else:
                self._message = (
                    "Dışa aktarıldı: "
                    + value["path"]
                    + (
                        " · Statik çıktı etkileşimi korumaz."
                        if not value["interactive"]
                        else " · Yerel ağsız SVG adapter."
                    )
                )
            self.projects.changed.emit()
            self.changed.emit()
            return
        if self.process and not self.process.is_alive() and not self.connection.poll():
            self.release()
            self._error = "Dashboard süreci durdu; sonuç kabul edilmedi."
            self.projects.changed.emit()
            self.changed.emit()

    def shutdown(self):
        self.timer.stop()
        self.release()
        if self.result_workspace:
            shutil.rmtree(self.result_workspace, ignore_errors=True)
