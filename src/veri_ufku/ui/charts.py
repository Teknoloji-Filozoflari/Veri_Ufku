"""Chart jobs, image provider and RowId bridge. Computation and Matplotlib stay off Qt."""

import copy
import json
import multiprocessing as mp
import os
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

from veri_ufku.charts.contracts import COMPOSITION_KINDS, MULTIVARIATE_KINDS, ChartSpec
from veri_ufku.charts.engine import suggest
from veri_ufku.charts.worker import process_entry
from veri_ufku.jobs.admission import start_controller
from veri_ufku.storage.chart_store import publish
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.ui.projects import project_error_text


class ChartImages(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.image = QImage()

    def requestImage(self, identifier, size, requestedSize):
        if size is not None:
            size.setWidth(self.image.width())
            size.setHeight(self.image.height())
        return self.image.copy()


class ChartController(QObject):
    changed = Signal()

    def __init__(self, data, projects, cache, budget, provider, parent=None):
        super().__init__(parent)
        self.data, self.projects, self.cache, self.budget, self.provider = (
            data,
            projects,
            Path(cache),
            budget,
            provider,
        )
        self.result = None
        self.process = self.connection = self.cancel_event = self.future = None
        self.workspace = None
        self.result_workspace = None
        self.binding = None
        self.revision = 0
        self.cancel_time = None
        self._error = ""
        self._message = "Grafik türünü ve alanlarını seçin. Kaynak korunur."
        self._image_url = ""
        self.selection = {}
        self._page = ()
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        data.rowSelected.connect(self.tableSelected)
        data.changed.connect(self.data_changed)
        projects.changed.connect(self.changed)

    busy = Property(
        bool,
        lambda self: self.process is not None or self.future is not None,
        notify=changed,
    )
    message = Property(str, lambda self: self._message, notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    imageUrl = Property(str, lambda self: self._image_url, notify=changed)
    chartResult = Property(
        "QVariantMap",
        lambda self: {
            k: v
            for k, v in (self.result or {}).items()
            if k not in ("points", "paths", "fingerprints")
        },
        notify=changed,
    )
    referenceRows = Property(
        "QVariantList",
        lambda self: [
            f"{p['label']} · x={p['x']} · y={p['y']} · n={p['n']}"
            + (f" · ölçüm={p['z']}" if "z" in p else "")
            + (f" · r={p['coefficient']} · {p['error']}" if "coefficient" in p else "")
            for p in (self.result or {}).get("points", [])[:400]
        ],
        notify=changed,
    )
    methodSummary = Property(str, lambda self: self.method_summary(), notify=changed)

    def method_summary(self):
        if not self.result:
            return ""
        details = self.result["details"]
        spec = self.result["spec"]
        lines = [
            f"Normalizasyon: {details.get('normalization', 'none')} · agregasyon: {details.get('aggregation', spec['aggregation'])}",
            f"Sonlu/kullanılan n: {details.get('included_n', self.result['used_n'])} · dışlanan: {details.get('excluded_rows', 0)} · ağırlık: {spec.get('weight_type', 'none')}",
            f"Eksen: {spec.get('xscale', 'linear')} / {spec.get('yscale', 'linear')} · kırpma: {bool(self.result.get('render', {}).get('view_bounds'))} · DPI: {spec['dpi']}",
        ]
        if details.get("geospatial"):
            geo = details["geospatial"]
            summary = {
                key: geo[key]
                for key in (
                    "authority",
                    "axis_order",
                    "geometry_types",
                    "extent",
                    "invalid_count",
                    "mode",
                    "classification",
                    "thresholds",
                    "value_semantics",
                    "normalization",
                    "window",
                    "band",
                    "nodata_count",
                    "attribution",
                    "cache_policy",
                )
                if key in geo
            }
            lines.append(
                "CRS / geometry / extent / nodata / classification: " + str(summary)
            )
        if spec["kind"] == "histogram":
            lines.append(
                f"Bin: {spec['bins']} · sınırlar: {details.get('bin_edges')} · grup/facet içinde normalizasyon"
            )
        if spec["kind"] == "violin":
            lines.append(
                "Violin genişliği: her grup/facette en yüksek yoğunluk 0.35 yarı genişliğe ölçeklenir; kayıt sayısı değildir."
            )
        if details.get("multivariate_version"):
            lines.append(
                f"Panel önkontrolü: {details['preflight']} · facet ölçeği: {spec['facet_scale']} · örnek: {self.result['scope']} {self.result['used_n']}/{self.result['population_n']}"
            )
            for key in ("bubble", "heatmap", "parallel", "hexbin", "density_2d"):
                if key in details:
                    lines.append(key + ": " + str(details[key]))
        if details.get("composition_version"):
            lines.append("Input şeması: " + details["input_schema"])
            lines.append(
                f"Payda: {details.get('denominator', details.get('denominators', 'pay grafiği değil'))} · eksik kategori: {spec['missing_category']} · {details.get('count_policy', 'strict input schema')}"
            )
            for key in (
                "hierarchy",
                "flow",
                "waterfall",
                "funnel",
                "calendar",
                "radar",
            ):
                if key in details:
                    lines.append(key + ": " + str(details[key]))
        for sample in details.get("samples", []):
            line = f"{sample.get('facet') or 'Tüm veri'} / {sample.get('group') or 'Grupsuz'} / {sample.get('key', '')}: n={sample['n']} · ağırlık toplamı={sample['weight_sum']:g}"
            if "bandwidth" in sample:
                line += f" · bandwidth={sample['bandwidth']:g} ({sample['bandwidth_rule']}, çarpan={spec['bandwidth_factor']:g})"
            if "method" in sample:
                line += f" · {sample['method']} · SD={sample['sd']:g} · SE={sample['se']:g} · df={sample['df']} · güven={sample['confidence']}"
            if "quantile_method" in sample:
                line += " · " + sample["quantile_method"]
            lines.append(line)
        return "\n".join(lines)

    selectionResult = Property(
        "QVariantMap", lambda self: self.selection, notify=changed
    )
    plotMetadata = Property(
        "QVariantMap",
        lambda self: (self.result or {}).get("render", {}),
        notify=changed,
    )
    current = Property(
        bool,
        lambda self: bool(
            self.result
            and self.result["dataset_version"]
            == (self.data.dataset() or {}).get("version_id")
            and self.result["spec"]["view"] == self.data.view.data()
            and self.result["config_revision"] == self.revision
        ),
        notify=changed,
    )
    columns = Property("QVariantList", lambda self: self.column_rows(), notify=changed)
    savedCharts = Property(
        "QVariantList",
        lambda self: [
            dict(
                id=r["id"],
                label=r["chart"]["spec"]["title"] or r["chart"]["spec"]["kind"],
                version=r["chart"]["dataset_version"],
            )
            for r in self.projects.draft["results"]
            if "chart" in r
        ],
        notify=changed,
    )

    def column_rows(self):
        d = self.data.dataset()
        if not d or not self.projects.store:
            return []
        schema = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]["schema"]
        return [
            dict(
                c,
                type=schema[c["name"]],
                role=d.get("semantic_metadata", {}).get(c["id"], {}).get("role", ""),
                unit=d.get("semantic_metadata", {}).get(c["id"], {}).get("unit", ""),
            )
            for c in d["import_metadata"]["columns"]
        ]

    @Slot(str, bool, result="QVariantList")
    def gallery(self, query, advanced=False):
        from veri_ufku.domain.capabilities import CAPABILITIES, availability
        from veri_ufku.learning.catalog import fold

        needle = fold(query)
        rows = []
        for c in CAPABILITIES.values():
            if c.kind != "chart" or c.capability_id == "chart.radar" and not advanced:
                continue
            if needle not in fold(
                " ".join(
                    (
                        c.capability_id,
                        c.deterministic_policy,
                        c.input_schema,
                        *c.help_links,
                    )
                )
            ):
                continue
            ready, reason = availability(c)
            rows.append(
                dict(
                    kind=c.capability_id.removeprefix("chart."),
                    question=c.deterministic_policy,
                    schema=c.input_schema,
                    ready=ready,
                    status="Yerel uygulama · deneysel" if ready else reason,
                )
            )
        return rows

    @Slot(str, result="QVariantList")
    def recommendations(self, purpose):
        from veri_ufku.operations.types import dtype_of

        # Read only the schema already present in the manifest, never dataset values on Qt.
        cols = self.column_rows()
        schema = {c["name"]: dtype_of(c["type"]) for c in cols}
        return (
            suggest(
                cols,
                schema,
                (self.data.dataset() or {}).get("semantic_metadata", {}),
                purpose,
            )
            if cols
            else []
        )

    def current_binding(self):
        return (
            str(self.projects.store.root) if self.projects.store else "",
            (self.data.dataset() or {}).get("version_id"),
            self.revision,
            json.dumps(self.data.view.data(), sort_keys=True),
        )

    def fail(self, error):
        self._error = project_error_text(error)
        self.changed.emit()

    @Slot()
    def invalidate(self):
        self.revision += 1
        self.changed.emit()

    @Slot(str)
    def create(self, spec_json):
        if self.busy or self.projects.busy:
            return self.fail(ProjectError("Devam eden işi bekleyin veya iptal edin."))
        try:
            d = self.data.dataset()
            if not d:
                raise ProjectError("Önce veri içe aktarın.")
            spec = ChartSpec.from_dict(json.loads(spec_json))
            spec.validate(d["import_metadata"]["columns"])
            spec = ChartSpec.from_dict(dict(spec.data(), view=self.data.view.data()))
            fp = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
            request = dict(
                path=str(self.projects.store.path(d["snapshot_uri"])).replace(
                    "/proc/self/", f"/proc/{os.getpid()}/", 1
                ),
                fingerprint={k: fp[k] for k in ("size", "sha256")},
                columns=copy.deepcopy(d["import_metadata"]["columns"]),
                semantic_metadata=copy.deepcopy(d.get("semantic_metadata", {})),
                row_count=d["import_metadata"]["row_count"],
                version_id=d["version_id"],
                source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
                snapshot_uri=d["snapshot_uri"],
                format_metadata=copy.deepcopy(
                    d["import_metadata"]["settings"].get("format_metadata", {})
                ),
                config_revision=self.revision,
            )
            self.start("calculate", request, spec.data())
        except (ValueError, TypeError, KeyError) as error:
            self.fail(error)

    def start(self, action, request, parameters):
        if self.busy or self.projects.busy:
            return self.fail(ProjectError("Devam eden işi bekleyin."))
        try:
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="chart-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, sender = ctx.Pipe(duplex=False)
            self.process = ctx.Process(
                target=process_entry,
                args=(
                    action,
                    copy.deepcopy(request),
                    parameters,
                    self.workspace,
                    self.cancel_event,
                    sender,
                    self.budget,
                ),
            )
            self.action = action
            self.binding = self.current_binding()
            self.started = time.monotonic()
            self.cancel_time = None
            if not start_controller(self, sender):
                return
            sender.close()
            self.projects.dataset_active = True
            self._error = ""
            self._message = "Grafik işi ayrı süreçte çalışıyor…"
            self.projects.changed.emit()
            self.changed.emit()
        except (OSError, ValueError) as error:
            self.release()
            self.fail(error)

    @Slot()
    def cancel(self):
        if self.process:
            self.cancel_event.set()
            self.cancel_time = self.cancel_time or time.monotonic()
            self._message = "İptal isteniyor…"
            self.changed.emit()

    def release(self, keep=False):
        if self.process:
            if self.process.pid is not None:
                self.process.join(0.1)
                if self.process.is_alive():
                    self.process.terminate()
                    self.process.join(0.2)
                if self.process.is_alive():
                    self.process.kill()
                    self.process.join()
                self.process.close()
            self.process = None
        if self.connection:
            self.connection.close()
            self.connection = None
        if self.workspace and not keep:
            shutil.rmtree(self.workspace, ignore_errors=True)
        self.workspace = None
        self.projects.dataset_active = False

    def poll(self):
        if self.future:
            if not self.future.done():
                return
            future, self.future = self.future, None
            try:
                self.projects.draft = future.result()
                self.projects.saved = copy.deepcopy(self.projects.draft)
                self._message = "Grafik tarifi/verisi/üyelikleri ve PNG/SVG atomik proje kaydında saklandı."
            except (ValueError, OSError) as error:
                self.fail(error)
            self.projects.dataset_active = False
            self.projects.changed.emit()
            self.changed.emit()
            return
        if not self.process:
            return
        if time.monotonic() - self.started > self.budget.max_wall_seconds:
            self.cancel()
        if (
            self.cancel_time
            and time.monotonic() - self.cancel_time > self.budget.cancel_grace_ms / 1000
        ):
            self.release()
            self._message = "İptal edildi; son grafik ve dataset korundu."
            self.projects.changed.emit()
            self.changed.emit()
            return
        for _ in range(30):
            if not self.connection.poll():
                break
            try:
                kind, value = self.connection.recv()
            except EOFError:
                break
            if kind == "progress":
                self._message = value.phase
                self.changed.emit()
                continue
            valid = self.binding == self.current_binding()
            canceled = self.cancel_event.is_set()
            workspace = self.workspace
            keep = (
                kind == "result"
                and valid
                and not canceled
                and self.action in ("calculate", "render")
            )
            self.release(keep)
            if self.action == "export" and kind == "result":
                self._message = "Dışa aktarıldı: " + value["exported"]
            elif canceled or kind == "canceled":
                self._message = "İptal edildi; son grafik korundu."
            elif not valid:
                self._message = (
                    "Eski veri/yapılandırma sonucu güncel grafiğe bağlanmadı."
                )
            elif kind == "error":
                self._error = value
            elif self.action == "select":
                self.selection = value
                if "page_row_ids" in value:
                    self.data.selectChartRows(value["page_row_ids"], value["count"])
                self._message = f"Seçim: {value['count']} RowId; {len(value['point_ids'])} görünür nokta. Örneklenmemiş kayıtlar nokta seçimiyle seçilmez."
            elif keep:
                if self.result_workspace:
                    shutil.rmtree(self.result_workspace, ignore_errors=True)
                self.result_workspace = workspace
                self.result = value
                if self.action == "calculate":
                    self.selection = {}
                self.provider.image = QImage(value["paths"]["png"])
                self._image_url = "image://charts/" + uid()
                self._message = (
                    f"Grafik hazır · {value['used_n']}/{value['population_n']} kayıt"
                )
            self.projects.changed.emit()
            self.changed.emit()
            return
        if self.process and not self.process.is_alive() and not self.connection.poll():
            self.release()
            self._error = "Grafik süreci durdu; sonuç kabul edilmedi."
            self.projects.changed.emit()
            self.changed.emit()

    @Slot()
    def save(self):
        if (
            not self.current
            or self.busy
            or self.projects.busy
            or self.projects.readOnly
        ):
            return self.fail(
                ProjectError("Güncel grafik ve yazılabilir proje gerekli.")
            )
        self.future = self.projects.executor.submit(
            publish,
            self.projects.store,
            copy.deepcopy(self.projects.draft),
            copy.deepcopy(self.result),
        )
        self.projects.dataset_active = True
        self.projects.changed.emit()
        self.changed.emit()

    @Slot(str)
    def openSaved(self, ident):
        if self.busy or self.projects.busy:
            return
        try:
            record = next(r for r in self.projects.draft["results"] if r["id"] == ident)
            chart = copy.deepcopy(record["chart"])
            uris = chart["artifact_uris"]
            path = self.projects.store.path(uris["result"])
            from veri_ufku.storage.project_store import file_hash

            for uri in uris.values():
                info = self.projects.store.manifest["artifacts"][uri]
                if file_hash(self.projects.store.path(uri)) != {
                    k: info[k] for k in ("size", "sha256")
                }:
                    raise ProjectError("Kayıtlı grafik artifact değişmiş.")
            result = json.loads(path.read_text())
            result["paths"] = {
                k: str(self.projects.store.path(uri)).replace(
                    "/proc/self/", f"/proc/{os.getpid()}/", 1
                )
                for k, uri in uris.items()
            }
            result["fingerprints"] = {
                k: {
                    f: self.projects.store.manifest["artifacts"][uri][f]
                    for f in ("size", "sha256")
                }
                for k, uri in uris.items()
            }
            self.result = result
            self.revision = result["config_revision"]
            self.provider.image = QImage(result["paths"]["png"])
            self._image_url = "image://charts/" + uid()
            self.selection = {}
            self._message = (
                "Kayıtlı grafik açıldı; eski sürüm güncelmiş gibi gösterilmez."
            )
            self.changed.emit()
        except (ValueError, KeyError, StopIteration, OSError) as error:
            self.fail(error)

    @Slot(str, str)
    def export(self, destination, fmt):
        if not self.current:
            return self.fail(
                ProjectError("Grafik eski veri/filtreye ait; yeniden oluşturun.")
            )
        url = QUrl(destination)
        path = url.toLocalFile() if url.isLocalFile() else destination
        self.start(
            "export",
            self.result,
            dict(
                destination=path, format=fmt, project_root=str(self.projects.store.root)
            ),
        )

    @Slot(float, float, float, float)
    def selectRectangle(self, x0, y0, x1, y1):
        if not self.current or self.busy:
            return
        metadata = self.result["render"]
        w, h = metadata["width"], metadata["height"]
        lo, hi = sorted((x0 * w, x1 * w))
        top, bottom = sorted((y0 * h, y1 * h))
        if hi - lo < 8 and bottom - top < 8:
            distances = [
                ((p["x"] - lo) ** 2 + (p["y"] - top) ** 2, p["point_id"])
                for p in metadata["pixels"]
            ]
            distance, pid = min(distances)
            hits = [
                region["point_id"]
                for region in metadata.get("hit_regions", [])
                if region["left"] <= lo <= region["right"]
                and region["top"] <= top <= region["bottom"]
            ]
            selected = hits[:1] if hits else [pid] if distance <= 25**2 else []
        else:
            selected = [
                p["point_id"]
                for p in metadata["pixels"]
                if lo <= p["x"] <= hi and top <= p["y"] <= bottom
            ]
        page = self.data.model.result or {}
        self.start(
            "select",
            self.result,
            dict(point_ids=selected, page_row_ids=page.get("row_ids", [])),
        )

    @Slot()
    def freezeSelection(self):
        if self.current and not self.busy:
            self.start(
                "render",
                self.result,
                dict(
                    bounds=self.result.get("render", {}).get("view_bounds", []),
                    highlight=self.selection.get("point_ids", []),
                ),
            )

    @Slot(str)
    def tableSelected(self, row_id):
        if self.current and not self.busy and not self.projects.busy:
            self.start("select", self.result, dict(point_ids=[], row_ids=[row_id]))

    @Slot(float, float, float, float)
    def zoomRectangle(self, x0, y0, x1, y1):
        if not self.current or self.busy:
            return
        from veri_ufku.charts.contracts import axis_coordinate

        meta = self.result["render"]
        if (
            meta.get("facets", 1) > 1
            or self.result["spec"]["kind"] in MULTIVARIATE_KINDS + COMPOSITION_KINDS
        ):
            return self.fail(
                ProjectError(
                    "Facet panellerinde sürükleyerek zoom desteklenmiyor; açık veri filtresi seçin."
                )
            )
        left, top, right, bottom = meta["axes_rect"]
        bounds = meta["bounds"]
        w, h = meta["width"], meta["height"]
        spec = ChartSpec.from_dict(self.result["spec"])

        def interpolate(value, low, high, scale):
            first = axis_coordinate(low, scale, spec.linthresh)
            last = axis_coordinate(high, scale, spec.linthresh)
            return axis_coordinate(
                first + value * (last - first), scale, spec.linthresh, inverse=True
            )

        def x(v):
            return interpolate(
                (v * w - left) / (right - left), bounds[0], bounds[1], spec.xscale
            )

        def y(v):
            return interpolate(
                (v * h - top) / (bottom - top), bounds[3], bounds[2], spec.yscale
            )

        xs = sorted((x(x0), x(x1)))
        ys = sorted((y(y0), y(y1)))
        if xs[0] == xs[1] or ys[0] == ys[1]:
            return
        self.start(
            "render",
            self.result,
            dict(bounds=xs + ys, highlight=self.selection.get("point_ids", [])),
        )

    @Slot()
    def reset(self):
        if self.current:
            self.start(
                "render",
                self.result,
                dict(bounds=[], highlight=self.selection.get("point_ids", [])),
            )

    def data_changed(self):
        page = tuple((self.data.model.result or {}).get("row_ids", []))
        if page != self._page:
            self._page = page
            if (
                self.current
                and self.selection.get("point_ids")
                and not self.busy
                and not self.projects.busy
            ):
                self.start(
                    "select",
                    self.result,
                    dict(
                        point_ids=self.selection["point_ids"], page_row_ids=list(page)
                    ),
                )
        self.changed.emit()

    def shutdown(self):
        self.timer.stop()
        self.release()
        if self.future:
            self.future.result()
            self.future = None
        if self.result_workspace:
            shutil.rmtree(self.result_workspace, ignore_errors=True)
