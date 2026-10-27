"""Explicit report composition and reviewed file export; no automatic recompute."""

import copy
import json

from PySide6.QtCore import Property, Signal, Slot

from veri_ufku.domain.json import parse
from veri_ufku.exports.report_builder import public_report
from veri_ufku.exports.report_contracts import (
    KINDS,
    LIMITATIONS,
    recipe,
    redact,
    template,
)
from veri_ufku.exports.report_worker import worker
from veri_ufku.importers.delimited import Control
from veri_ufku.storage import report_builder_store as storage
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.ui.monitoring import MonitoringController


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


class ReportBuilderController(MonitoringController):
    builderChanged = Signal()
    storage = storage
    worker = staticmethod(worker)
    result_kind = "scientific_report"
    public_report = staticmethod(public_report)

    def __init__(self, *args):
        self.exporting = False
        self._review = ""
        super().__init__(*args)
        self.changed.connect(self.builderChanged.emit)

    saved = Property(
        "QVariantList",
        lambda s: [
            dict(id=r["id"], label=r["scientific_report"]["spec"]["title"])
            for r in s.projects.draft["results"]
            if "scientific_report" in r
        ],
        notify=builderChanged,
    )
    records = Property(
        "QVariantList",
        lambda s: [
            dict(id=r["id"], label=r.get("capability_id", r["id"]))
            for r in s.projects.draft["results"]
            if storage.result_value(r)
        ],
        notify=builderChanged,
    )
    kinds = Property("QVariantList", lambda s: list(KINDS), constant=True)
    limitations = Property("QVariantList", lambda s: list(LIMITATIONS), constant=True)
    preview = Property(
        str, lambda s: dump(s.result) if s.result else s._review, notify=builderChanged
    )
    currentRoute = Property("QVariantMap", lambda s: {}, notify=builderChanged)
    models = Property("QVariantList", lambda s: [], notify=builderChanged)
    freshnessText = Property(str, lambda s: s.freshness_text(), notify=builderChanged)
    errorText = Property(
        str, lambda s: s._error.replace("Monitoring", "Rapor"), notify=builderChanged
    )

    def freshness_text(self):
        if not self.result:
            return "Rapor henüz oluşturulmadı."
        try:
            issues = storage.freshness(self.projects.draft, self.result["spec"])
            return (
                "STALE · " + dump(issues)
                if issues
                else "Dataset/run kayıtlarında daha yeni bağ bulunmadı. Dış canlı kaynak tazeliği doğrulanmadı."
            )
        except (KeyError, ValueError):
            return "STALE · kaynak/run artık bulunamıyor."

    @Slot(str, result=str)
    def template(self, name):
        return dump(template(name))

    def _record_for(self, *want):
        for r in self.projects.draft["results"]:
            found = storage.result_value(r)
            if not found:
                continue
            kind, _ = found
            if kind in want:
                return r["id"]
        return ""

    @Slot(str, str, str, result=str)
    def composeLayout(self, title, protocol, sections_json):
        """Layout A: selected journey sections → recipe; no recompute."""
        try:
            selected = parse(sections_json) if sections_json else []
            if not isinstance(selected, list):
                selected = []
            indexes = {int(x) for x in selected}
            raw = template("scientific")
            if isinstance(title, str) and title.strip():
                raw["title"] = title.strip()[:200]
            if protocol in ("exploratory", "confirmatory"):
                raw["protocol"] = protocol
            blocks = []
            if 1 in indexes:
                blocks.append(
                    dict(
                        kind="section",
                        title="Rapor özeti",
                        text="Bu rapor seçilen immutable kayıtlardan birleştirilir; analiz/model yeniden hesaplanmaz.",
                    )
                )
                blocks.append(
                    dict(
                        kind="note",
                        title="Protokol",
                        text=raw["protocol_note"],
                    )
                )
            if 2 in indexes:
                datasets = self.projects.draft.get("datasets") or []
                if datasets:
                    d = datasets[-1]
                    cols = [c["id"] for c in d["import_metadata"]["columns"][:16]]
                    blocks.append(
                        dict(
                            kind="dictionary",
                            title="Veri sözlüğü",
                            version=d["version_id"],
                            columns=cols or [d["import_metadata"]["columns"][0]["id"]],
                        )
                    )
                else:
                    blocks.append(
                        dict(
                            kind="note",
                            title="Veri",
                            text="Bu sürümde bağlı dataset yok; veri bölümü boş bırakıldı.",
                        )
                    )
            if 3 in indexes:
                rid = self._record_for("quality", "profile")
                if rid:
                    blocks.append(
                        dict(kind="result", title="İncele bulguları", record=rid)
                    )
                else:
                    blocks.append(
                        dict(
                            kind="note",
                            title="İncele",
                            text="Bağlı kalite/profil kaydı yok; bulgu uydurulmaz.",
                        )
                    )
            if 4 in indexes:
                rid = self._record_for("analysis")  # charts may be under different keys
                # Prefer chart-capable: scan capability_id
                chart_id = ""
                for r in self.projects.draft["results"]:
                    cap = str(r.get("capability_id") or "")
                    if "chart" in cap or cap.startswith("charts."):
                        if storage.result_value(r):
                            chart_id = r["id"]
                            break
                if chart_id:
                    blocks.append(
                        dict(
                            kind="chart",
                            title="Görselleştir",
                            record=chart_id,
                            caption="Kayıtlı grafik; örnekleme/filtre bağlamı korunur.",
                        )
                    )
                elif rid:
                    blocks.append(
                        dict(kind="result", title="Görselleştir (kayıt)", record=rid)
                    )
                else:
                    blocks.append(
                        dict(
                            kind="note",
                            title="Görselleştir",
                            text="Bağlı grafik kaydı yok; çizim uydurulmaz.",
                        )
                    )
            if 5 in indexes:
                prep_id = ""
                for r in self.projects.draft["results"]:
                    cap = str(r.get("capability_id") or "")
                    if "clean" in cap or "prepar" in cap or "operation" in cap:
                        if storage.result_value(r):
                            prep_id = r["id"]
                            break
                if prep_id:
                    blocks.append(dict(kind="result", title="Hazırla", record=prep_id))
                else:
                    blocks.append(
                        dict(
                            kind="note",
                            title="Hazırla",
                            text="Bağlı hazırlama/temizlik kaydı yok.",
                        )
                    )
            if 6 in indexes:
                rid = self._record_for("analysis")
                if rid:
                    blocks.append(dict(kind="result", title="İstatistik", record=rid))
                else:
                    blocks.append(
                        dict(
                            kind="note",
                            title="İstatistik",
                            text="Bağlı analiz kaydı yok; p/etki uydurulmaz.",
                        )
                    )
            if 7 in indexes:
                model_id = ""
                for r in self.projects.draft["results"]:
                    cap = str(r.get("capability_id") or "")
                    found = storage.result_value(r)
                    if not found:
                        continue
                    kind, _ = found
                    if (
                        kind in ("baseline", "analysis")
                        or "model" in cap
                        or cap.startswith("statistics.")
                    ):
                        model_id = r["id"]
                        break
                if model_id:
                    blocks.append(dict(kind="result", title="Model", record=model_id))
                else:
                    blocks.append(
                        dict(
                            kind="note",
                            title="Model",
                            text="Bağlı model kaydı yok; katsayı uydurulmaz.",
                        )
                    )
            if 8 in indexes:
                blocks.append(
                    dict(
                        kind="assumption",
                        title="Sınırlamalar",
                        text=" · ".join(LIMITATIONS[:4]),
                    )
                )
                blocks.append(
                    dict(kind="bibliography", title="Kaynakça", references=[])
                )
            if not blocks:
                blocks = raw["blocks"]
            raw["blocks"] = blocks[:32]
            return dump(recipe(raw))
        except (ValueError, TypeError, KeyError, ProjectError, StopIteration) as e:
            self.fail(e)
            return self.template("scientific")

    @Slot(str, int, str, str, result=str)
    def editText(self, text, index, title, body):
        """Edit presentation fields; preserve dataset, run and redaction bindings."""
        try:
            raw = recipe(parse(text))
            if index == -1:
                raw["title"] = title
            elif 0 <= index < len(raw["blocks"]):
                block = raw["blocks"][index]
                block["title"] = title
                if block["kind"] in ("section", "note", "assumption"):
                    block["text"] = body
                elif block["kind"] in ("chart", "table"):
                    block["caption"] = body
            else:
                raise ProjectError("Düzenlenecek rapor bölümü bulunamadı.")
            return dump(recipe(raw))
        except (ValueError, TypeError, KeyError) as error:
            self.fail(error)
            return text

    @Slot(str, result=str)
    def reuse(self, ident):
        try:
            r = next(r for r in self.projects.draft["results"] if r["id"] == ident)
            return dump(r["scientific_report"]["spec"])
        except (KeyError, StopIteration):
            return self.template("scientific")

    @Slot(str, result=str)
    def redactRecipe(self, text):
        try:
            raw = recipe(parse(text))
            clean, changes = redact(raw)
            recipe(clean)
            self._review = dump(
                dict(
                    redactions=changes,
                    scope="Tarif metni; hücre ve grafikler oluşturma sonrası ayrıca incelenmeli.",
                )
            )
            self.changed.emit()
            return dump(clean)
        except (ValueError, TypeError, KeyError) as e:
            self.fail(e)
            return text

    @Slot(str, str, result=str)
    def appendUxContext(self, text, context_json):
        """UX10: not/grafik/karar/model özetini note bloğu olarak tarife bağla."""
        try:
            from veri_ufku.exports.ux_report_context import (
                build_context,
                context_note_text,
            )

            raw = recipe(parse(text))
            payload = parse(context_json) if context_json else {}
            if not isinstance(payload, dict):
                payload = {}
            context = build_context(
                dataset_version=str(payload.get("dataset_version") or ""),
                row_count=payload.get("row_count"),
                column_count=payload.get("column_count"),
                chart_notes=payload.get("chart_notes") or {},
                outlier_candidates={
                    "applied": payload.get("outlier_candidates_applied"),
                    "union_row_ids": [
                        f"r{i}" for i in range(int(payload.get("outlier_union_n") or 0))
                    ],
                },
                model_candidates={
                    "status": payload.get("model_status"),
                    "auto_fit": payload.get("model_auto_fit"),
                    "starter_model": payload.get("model_starter"),
                    "structure": payload.get("model_structure"),
                },
                scope_note=str(payload.get("scope_note") or ""),
            )
            body = context_note_text(context)
            if len(body) > 2000:
                body = body[:1997] + "..."
            raw["blocks"].append(
                dict(
                    kind="note",
                    title="UX bağlam · sürüm ve sınırlamalar",
                    text=body,
                )
            )
            return dump(recipe(raw))
        except (ValueError, TypeError, KeyError, ProjectError) as e:
            self.fail(e)
            return text

    @Slot(str, str, str, str, result=str)
    def appendBlock(self, text, kind, dataset_id, record_id):
        try:
            raw = recipe(parse(text))
            b = dict(kind=kind, title=kind)
            if kind in ("section", "note", "assumption"):
                b["text"] = "Kullanıcı metni: amacı/varsayımı/sınırlamayı açıklayın."
            elif kind == "bibliography":
                b["references"] = []
            elif kind in ("dictionary", "table"):
                d = next(
                    d
                    for d in self.projects.draft["datasets"]
                    if d["version_id"] == dataset_id
                )
                b.update(
                    version=dataset_id,
                    columns=[c["id"] for c in d["import_metadata"]["columns"][:16]],
                )
                if kind == "table":
                    b.update(
                        rows=10,
                        caption="İlk10satır; kolon ve maskeleri paylaşmadan önce seçin.",
                    )
            else:
                b["record"] = record_id
                if kind == "chart":
                    b["caption"] = (
                        "Grafiğin örnekleme/filtre/agregasyon bağlamını açıklayın."
                    )
            raw["blocks"].append(b)
            return dump(recipe(raw))
        except (ValueError, TypeError, KeyError, StopIteration) as e:
            self.fail(e)
            return text

    @Slot(str, str, str, bool)
    def exportReport(self, ident, fmt, destination, reviewed):
        try:
            self.ready()
            if not reviewed:
                raise ProjectError(
                    "Önce redaction/artifact/protokol önizlemesini inceleyip onaylayın."
                )
            record = next(
                r
                for r in self.projects.draft["results"]
                if r["id"] == ident and "scientific_report" in r
            )
            if (
                self.result.get("review_hash")
                != record["scientific_report"]["review_hash"]
            ):
                raise ProjectError(
                    "Seçili raporu hash kontrolüyle açıp önizlemesini inceleyin."
                )
            name = {
                "md": "report.md",
                "html": "report.html",
                "pdf": "report.pdf",
                "zip": "report-package.zip",
            }[fmt]
            import threading

            self.cancel_event = threading.Event()
            self._error = ""
            self.exporting = True
            self.future = self.projects.executor.submit(
                storage.export_file,
                self.projects.store,
                copy.deepcopy(self.projects.draft),
                ident,
                name,
                destination,
                self.result["review_hash"],
                Control(cancel=self.cancel_event, budget=self.budget),
            )
            self.projects.dataset_active = True
            self.projects.changed.emit()
            self.changed.emit()
        except (ValueError, TypeError, KeyError, OSError, StopIteration) as e:
            self.fail(e)

    @Slot()
    def cancel(self):
        if self.exporting:
            self.cancel_event.set()
        else:
            super().cancel()

    def poll(self):
        if not self.exporting:
            return super().poll()
        if self.future is None or not self.future.done():
            return
        future, self.future = self.future, None
        self.exporting = False
        try:
            receipt = future.result()
            self._review = "Dışa aktarıldı: " + receipt["sha256"]
        except Exception as e:
            self.fail(e)
        self.projects.dataset_active = False
        self.projects.changed.emit()
        self.changed.emit()
