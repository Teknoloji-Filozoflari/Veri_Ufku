"""Export UI binding and publication receipts; no table calculation on the GUI thread."""

import copy
import json
import multiprocessing as mp
import os
import shutil
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from veri_ufku.exports.data import ExportSpec, plan
from veri_ufku.exports.reports import ReportSpec
from veri_ufku.exports.worker import process_entry
from veri_ufku.jobs.admission import start_controller
from veri_ufku.storage.project_model import ProjectError, decode, encode, uid
from veri_ufku.ui.projects import project_error_text


class ExportController(QObject):
    changed = Signal()

    def __init__(self, data, projects, charts, cache, budget, parent=None):
        super().__init__(parent)
        self.data, self.projects, self.charts, self.cache, self.budget = (
            data,
            projects,
            charts,
            Path(cache),
            budget,
        )
        self.process = self.connection = self.cancel_event = None
        self.workspace = None
        self.cancel_time = None
        self._error = ""
        self._message = "Veri veya rapor için yeni çıktı dosyası seçin. Kaynak korunur."
        self.result = {}
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        data.changed.connect(self.changed)
        projects.changed.connect(self.changed)

    busy = Property(bool, lambda self: self.process is not None, notify=changed)
    errorText = Property(str, lambda self: self._error, notify=changed)
    message = Property(str, lambda self: self._message, notify=changed)
    receipt = Property("QVariantMap", lambda self: self.result, notify=changed)

    def fail(self, error):
        self._error = project_error_text(error)
        self.changed.emit()

    statisticsReport = Property(
        str, lambda self: self.statistics_report(), notify=changed
    )

    def statistics_report(self):
        from veri_ufku.exports.report_statistics import statistics_report_text

        if not self.data.dataset():
            return "Veri yok. İstatistik sonucu uydurulmaz."
        try:
            analyses = self.report_context().get("analyses") or []
        except (KeyError, TypeError, ProjectError):
            return "Kayıtlı istatistik okunamadı. Sonuç uydurulmaz."
        return statistics_report_text(analyses)

    operationPython = Property(
        str, lambda self: self.operation_python(), notify=changed
    )

    def operation_python(self):
        from veri_ufku.exports.operation_python import operation_history_python

        if not self.data.dataset():
            return "Veri yok. Python dökümü uydurulmaz."
        try:
            operations = self.report_context().get("operations") or []
        except (KeyError, TypeError, ProjectError):
            return "İşlem geçmişi okunamadı. Döküm uydurulmaz."
        return operation_history_python(operations)

    reportEnvironment = Property(
        str, lambda self: self.report_environment(), notify=changed
    )

    def report_environment(self):
        from veri_ufku.exports.environment_text import current_environment_text

        return current_environment_text()

    sourceNote = Property(str, lambda self: self.source_note(), notify=changed)

    def source_note(self):
        from veri_ufku.exports.source_note import source_note

        if not self.data.dataset():
            return "Veri yok. Kaynak uydurulmaz."
        try:
            sources = self.report_context().get("sources") or []
        except (KeyError, TypeError, ProjectError):
            return "Kaynak kaydı okunamadı. Kaynak uydurulmaz."
        return source_note(sources)

    reportSeed = Property(str, lambda self: self.report_seed(), notify=changed)

    def report_seed(self):
        from veri_ufku.exports.seed_text import seed_text

        if not self.data.dataset():
            return "Veri yok. Tohum uydurulmaz."
        try:
            context = self.report_context()
        except (KeyError, TypeError, ProjectError):
            return "Tohum kaydı okunamadı. Tohum uydurulmaz."
        return seed_text(
            context.get("project_seed"),
            context.get("operations") or [],
            context.get("result_seeds") or [],
        )

    @Slot(bool, int, result=str)
    def reportPrivacy(self, include, table_rows):
        from veri_ufku.exports.query import scoped
        from veri_ufku.exports.report_privacy import column_findings, privacy_note

        if not self.data.dataset():
            return "Veri yok. Kişisel sütun uydurulmaz."
        rows = table_rows if type(table_rows) is int and 1 <= table_rows <= 200 else 20
        try:
            request = self.request()
            spec = ReportSpec(
                "html",
                scope="view",
                view=self.data.view.data(),
                table_rows=rows,
                include_personal=bool(include),
            )
            query, _schema, _view = scoped(request, spec)
            names = [c["name"] for c in request["columns"]][:20]
            frame = (
                query.select(names).head(rows).collect(engine="streaming")
                if names
                else None
            )
            values = (
                {name: frame.get_column(name).to_list() for name in names}
                if frame is not None
                else {}
            )
        except (KeyError, TypeError, ProjectError, ValueError, OSError):
            return "Kişisel sütun önizlemesi okunamadı. Sütun uydurulmaz."
        return privacy_note(column_findings(names, values), bool(include))

    def request(self):
        d = self.data.dataset()
        if not d or not self.projects.store:
            raise ProjectError("Önce proje oluşturup dosya içe aktarın.")
        fp = self.projects.store.manifest["artifacts"][d["snapshot_uri"]]
        return dict(
            path=str(self.projects.store.path(d["snapshot_uri"])).replace(
                "/proc/self/", f"/proc/{os.getpid()}/", 1
            ),
            fingerprint={k: fp[k] for k in ("size", "sha256")},
            columns=copy.deepcopy(d["import_metadata"]["columns"]),
            row_count=d["import_metadata"]["row_count"],
            version_id=d["version_id"],
            snapshot_uri=d["snapshot_uri"],
            source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
        )

    @Slot(str, str, bool, str, result="QVariantMap")
    def describe(self, fmt, scope, safe, null_marker="\\N"):
        try:
            return plan(
                self.request(),
                ExportSpec(
                    fmt, scope, self.data.view.data(), safe, null_marker=null_marker
                ),
            )
        except (ValueError, KeyError, OSError) as error:
            return {"error": project_error_text(error)}

    def report_context(self):
        state = self.projects.draft
        d = self.data.dataset()
        versions = {v["version_id"]: v for v in state["datasets"]}
        ancestors = set()

        def visit(version):
            if version in ancestors or version not in versions:
                return
            ancestors.add(version)
            for parent in versions[version].get("parent_version_ids", []):
                visit(parent)
            for parent in versions[version].get("input_version_ids", []):
                visit(parent)

        visit(d["version_id"])
        records = state["results"]
        quality = [
            r["quality"]
            for r in records
            if "quality" in r and set(r["dataset_version_ids"]) & ancestors
        ]
        profiles = [
            r["profile"]
            for r in records
            if "profile" in r and set(r["dataset_version_ids"]) & ancestors
        ]
        if (
            self.data.quality_result
            and self.data.quality_result.get("dataset_version") in ancestors
            and self.data.quality_result not in quality
        ):
            quality.append(self.data.quality_result)
        if (
            self.data.profile_result
            and self.data.profile_result.get("dataset_version") in ancestors
            and self.data.profile_result not in profiles
        ):
            profiles.append(self.data.profile_result)
        charts = []
        for record in records:
            chart = record.get("chart")
            if not chart or chart["dataset_version"] != d["version_id"]:
                continue
            uri = chart["artifact_uris"]["png"]
            fp = self.projects.store.manifest["artifacts"][uri]
            charts.append(
                dict(
                    path=str(self.projects.store.path(uri)).replace(
                        "/proc/self/", f"/proc/{os.getpid()}/", 1
                    ),
                    fingerprint={k: fp[k] for k in ("size", "sha256")},
                    title=chart["spec"]["title"] or chart["spec"]["kind"],
                    context="Sürüm: " + chart["dataset_version"],
                    metadata={
                        k: chart[k]
                        for k in (
                            "spec",
                            "details",
                            "warnings",
                            "scope",
                            "filters",
                            "used_n",
                        )
                    },
                )
            )
        if self.charts.current:
            chart = self.charts.result
            if not any(
                c["fingerprint"] == chart["fingerprints"]["png"] for c in charts
            ):
                charts.append(
                    dict(
                        path=chart["paths"]["png"],
                        fingerprint=chart["fingerprints"]["png"],
                        title=chart["spec"]["title"] or chart["spec"]["kind"],
                        context="Sürüm: " + chart["dataset_version"],
                        metadata={
                            k: chart[k]
                            for k in (
                                "spec",
                                "details",
                                "warnings",
                                "scope",
                                "filters",
                                "used_n",
                            )
                        },
                    )
                )
            profiles.extend(chart["summary"])
        return dict(
            sources=[
                {k: v for k, v in s.items() if k not in ("portable_uri",)}
                for s in state["sources"]
                if s["id"] in {versions[v].get("source_id") for v in ancestors}
            ],
            dataset_provenance=dict(
                dataset_id=d["dataset_id"],
                version_id=d["version_id"],
                source_id=d.get("source_id"),
                ancestor_versions=[
                    {
                        k: versions[v][k]
                        for k in (
                            "version_id",
                            "parent_version_ids",
                            "input_version_ids",
                            "operation_id",
                        )
                        if k in versions[v]
                    }
                    for v in sorted(ancestors)
                ],
                import_settings=d["import_metadata"]["settings"],
                columns=d["import_metadata"]["columns"],
                semantic_metadata=d.get("semantic_metadata", {}),
                analysis_unit=d.get("analysis_unit", ""),
            ),
            quality=quality,
            profiles=profiles,
            operations=[
                {k: v for k, v in op.items() if k not in ("before", "after")}
                for op in state["operations"]
                if any(
                    v.get("operation_id") == op["id"]
                    for vid, v in versions.items()
                    if vid in ancestors
                )
            ],
            charts=charts,
            analyses=[
                copy.deepcopy(r["analysis"])
                for r in state["results"]
                if "analysis" in r and r["analysis"]["dataset_version"] in ancestors
            ],
            lineage_record_ids=[
                r["id"]
                for r in records
                if set(r["dataset_version_ids"]) & ancestors
                and any(k in r for k in ("quality", "profile", "analysis"))
            ]
            + [
                r["id"]
                for r in records
                if "chart" in r and r["chart"]["dataset_version"] == d["version_id"]
            ],
            lineage_context_version=1,
            project_seed=state.get("seed"),
            result_seeds=[
                {"id": r.get("id", ""), "seed": r.get("seed")}
                for r in records
                if set(r.get("dataset_version_ids") or []) & ancestors
            ],
            environment=dict(
                application="Veri_Ufku0.1.0 experimental",
                chart_backend="Matplotlib Agg",
                report_backend="Qt QTextDocument/QPdfWriter",
                content_version=15,
            ),
        )

    @Slot(str, str, str)
    def create(self, kind, parameters_json, destination):
        if kind not in ("data", "report", "package") or self.busy or self.projects.busy:
            return self.fail(
                ProjectError("Devam eden işi bekleyin; veri veya rapor seçin.")
            )
        try:
            request = self.request()
            parameters = json.loads(parameters_json)
            parameters["view"] = self.data.view.data()
            if kind == "package":
                fields = {
                    "format": "html",
                    "title": parameters.get("title")
                    or "Veri_Ufku veri inceleme raporu",
                    "purpose": parameters.get("purpose") or "Dosyamı anlamak istiyorum",
                    "scope": parameters.get("scope") or "view",
                    "view": parameters["view"],
                    "table_rows": parameters.get("table_rows") or 100,
                    "include_personal": parameters.get("include_personal") is True,
                    "license_note": parameters.get("license_note") or "",
                }
                mode = parameters.get("share_mode") or "ozet"
                if mode not in ("ozet", "orneklem"):
                    raise ProjectError(
                        "Paylaşım özet veya örneklem olmalı. Tam kopya bu pakette yok."
                    )
                spec = ReportSpec(**fields)
                parameters = {**fields, "format": "zip", "share_mode": mode}
            else:
                spec = (
                    ExportSpec(**parameters)
                    if kind == "data"
                    else ReportSpec(**parameters)
                )
            spec.validate(request["columns"])
            if kind in ("report", "package"):
                request["report_context"] = copy.deepcopy(self.report_context())
            url = QUrl(destination)
            target = url.toLocalFile() if url.isLocalFile() else destination
            self.cache.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.mkdtemp(prefix="export-", dir=self.cache)
            ctx = mp.get_context("spawn")
            self.cancel_event = ctx.Event()
            self.connection, sender = ctx.Pipe(duplex=False)
            self.process = ctx.Process(
                target=process_entry,
                args=(
                    kind,
                    request,
                    parameters,
                    self.workspace,
                    target,
                    str(self.projects.store.root),
                    self.cancel_event,
                    sender,
                    self.budget,
                ),
            )
            self.kind = kind
            self.started = time.monotonic()
            self.cancel_time = None
            if not start_controller(self, sender):
                return
            sender.close()
            self.projects.dataset_active = True
            self._error = ""
            self._message = "Çıktı hazırlanıyor; mevcut dosyalar korunur."
            self.projects.changed.emit()
            self.changed.emit()
        except (OSError, ValueError, TypeError, KeyError) as error:
            self.release()
            self.fail(error)

    @Slot()
    def cancel(self):
        if self.process and self.cancel_time is None:
            self.cancel_time = time.monotonic()
            self.cancel_event.set()
            self._message = "İptal isteniyor…"
            self.changed.emit()

    def release(self):
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
        if self.workspace:
            shutil.rmtree(self.workspace, ignore_errors=True)
        self.workspace = None
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
            self._message = "İptal edildi; son proje ve kaynak korundu."
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
            self.release()
            if kind == "result":
                self.result = {k: v for k, v in value.items() if k != "artifact"}
                self._message = (
                    "Çıktı doğrulandı ve kaydedildi: " + value["published"]["path"]
                )
                if not self.projects.readOnly:
                    self.projects.draft["results"].append(
                        dict(
                            id="result:" + uid(),
                            dataset_version_ids=[value["dataset_version"]],
                            seed=None,
                            capability_id="export." + value["format"],
                            export=decode(encode(self.result)),
                        )
                    )
                    self._message += (
                        " · Export/rapor kaydını korumak için Projeyi kaydet kullanın."
                    )
            elif kind == "error":
                self._error = value
            else:
                self._message = "İptal edildi; mevcut dosyalar korundu."
            self.projects.changed.emit()
            self.changed.emit()
            return
        if self.process and not self.process.is_alive() and not self.connection.poll():
            self.release()
            self._error = "Çıktı süreci durdu; proje/kaynak korundu."
            self.projects.changed.emit()
            self.changed.emit()

    def shutdown(self):
        self.timer.stop()
        self.release()
