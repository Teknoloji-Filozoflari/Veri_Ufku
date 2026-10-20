"""GUI-side RSS admission enforcement; workers never publish project commits."""

import os
import shutil
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from veri_ufku.jobs.admission import reservations
from veri_ufku.jobs.resources import (
    process_identity,
    process_tree,
    rss_bytes,
    terminate_identity,
)


def scratch_bytes(roots):
    total = 0
    for root in roots:
        for path in root.rglob("*"):
            try:
                if path.is_file() and not path.is_symlink():
                    total += path.stat().st_size
            except FileNotFoundError:
                pass  # Worker renamed/removed an output between samples.
    return total


class ResourceSupervisor(QObject):
    changed = Signal()
    report = Property("QVariantMap", lambda self: self._report, notify=changed)

    def __init__(self, controllers, budget, parent=None):
        super().__init__(parent)
        self.controllers, self.budget = controllers, budget
        self.peak_rss_bytes = 0
        self.peak_cpu_jobs = 0
        self.peak_temp_bytes = 0
        self._disk_checked = 0.0
        self._ui_notified = 0.0
        self._report = {}
        self._observed = {}
        self._history = []
        self._kill = {}
        self._children = {}
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    @Slot(str, result="QVariantList")
    def methods(self, query):
        from veri_ufku.domain.capabilities import CAPABILITIES

        return [
            dict(
                id=c.capability_id,
                memory=c.execution_memory,
                sparse=dict(c.supports).get("sparse", False),
                devices=list(c.device_support),
                limits=dict(c.limits),
            )
            for c in CAPABILITIES.values()
            if query.lower() in c.capability_id.lower()
        ][:50]

    def shutdown(self):
        self.timer.stop()
        for children in self._children.values():
            for pid, identity in children.items():
                terminate_identity(pid, identity)
        for pid, identity in self._kill:
            terminate_identity(pid, identity)
        self._children.clear()
        self._kill.clear()

    def poll(self):
        active = [c for c in self.controllers if getattr(c, "process", None)]
        pids = set()
        for process, _ in reservations():
            if process.pid:
                pids.update(process_tree(process.pid))
        for c in active:
            if c.process.pid:
                pids.update(process_tree(c.process.pid))
        total = rss_bytes(os.getpid()) + sum(rss_bytes(pid) for pid in pids)
        now = time.monotonic()
        current = set()
        for c in active:
            pid = c.process.pid
            if not pid:
                continue
            key = (pid, process_identity(pid))
            current.add(key)
            descendants = process_tree(pid) - {pid}
            self._children.setdefault(key, {}).update(
                {p: process_identity(p) for p in descendants}
            )
            if any(getattr(c, name, None) for name in ("cancel_time", "cancel_at")):
                for child, identity in self._children[key].items():
                    self._kill.setdefault((child, identity), now)
            row = self._observed.setdefault(
                key,
                dict(
                    kind=type(c).__name__,
                    pid=pid,
                    started=getattr(c, "started", now),
                    peak_rss_bytes=0,
                ),
            )
            row.update(
                seconds=round(now - row["started"], 3),
                state="running",
                device=c.budget.device,
                native_threads=c.budget.worker_threads,
            )
            row["peak_rss_bytes"] = max(
                row["peak_rss_bytes"], sum(rss_bytes(p) for p in process_tree(pid))
            )
        for key in list(self._observed):
            if key not in current:
                for child, identity in self._children.pop(key, {}).items():
                    self._kill.setdefault((child, identity), now)
                row = self._observed.pop(key)
                row["seconds"] = round(now - row["started"], 3)
                row["state"] = "Bitti; başarı/iptal/hata için iş sonucuna bakın"
                self._history.append(row)
                self._history[:] = self._history[-64:]
        # A task spawning children cannot silently multiply its process allowance.
        if (
            len(pids)
            > min(self.budget.max_processes, self.budget.max_concurrent_cpu_jobs)
            or sum(c.budget.worker_threads for c in active) > self.budget.cpu_threads
        ):
            for c in active:
                for pid in process_tree(c.process.pid):
                    self._kill.setdefault((pid, process_identity(pid)), now)
                c.cancel()
                c._error = (
                    "Toplam süreç/native thread bütçesi aşıldı; iş iptal ediliyor."
                )
                c.changed.emit()
        for (pid, identity), requested in list(self._kill.items()):
            if process_identity(pid) != identity:
                del self._kill[(pid, identity)]
            elif now - requested >= self.budget.cancel_grace_ms / 1000:
                try:
                    terminate_identity(pid, identity)
                except ProcessLookupError:
                    pass
                del self._kill[(pid, identity)]
        self._report = dict(
            rss_bytes=total,
            processes=len(pids),
            cpu_threads=self.budget.cpu_threads,
            process_limit=self.budget.max_processes,
            temp_bytes=self.peak_temp_bytes,
            ram_limit=self.budget.ram_bytes,
            disk_limit=self.budget.temp_disk_bytes,
            rows=list(self._observed.values()) + list(reversed(self._history)),
            note="100 ms örnekleme; RSS paylaşılan sayfaları iki kez sayabilir. Kısa zirveler kaçabilir. GPU/remote ölçümü yok.",
        )
        if now - self._ui_notified >= 1:
            self._ui_notified = now
            self.changed.emit()
        self.peak_rss_bytes = max(self.peak_rss_bytes, total)
        self.peak_cpu_jobs = max(self.peak_cpu_jobs, len(active))
        if total > self.budget.ram_bytes:
            for controller in active:
                controller.cancel()
                controller._error = "Uygulama ve işlerin toplam bellek bütçesi aşıldı. Özellikleri azaltın veya açıkça daha küçük veri sürümü seçin; önceki proje korundu."
                controller.changed.emit()
        now = time.monotonic()
        if active and now - self._disk_checked >= 0.25:
            self._disk_checked = now
            # Retained previews/recipe results share the same application budget.
            roots = {Path(c.cache) for c in self.controllers if Path(c.cache).is_dir()}
            used = scratch_bytes(roots)
            self.peak_temp_bytes = max(self.peak_temp_bytes, used)
            if used > self.budget.temp_disk_bytes or any(
                shutil.disk_usage(root).free < self.budget.reserve_disk_bytes
                for root in roots
            ):
                for controller in active:
                    controller.cancel()
                    controller._error = "Paylaşılan geçici disk bütçesi aşıldı veya boş alan yetersiz. Alan açıp yeniden deneyin; önceki proje korundu."
                    controller.changed.emit()
