"""Parent-only process/thread reservations shared by GUI and the job manager.

A reservation counts configured native compute threads, not idle runtime threads.
No controller, Qt object or project writer is sent to workers.
"""

import shutil
import threading
from pathlib import Path

from veri_ufku.jobs.limits import configure_threads

_LOCK = threading.RLock()
_RUNNING = []


def _live():
    def alive(p):
        try:
            return p.is_alive() if hasattr(p, "is_alive") else p.poll() is None
        except ValueError:
            return False

    _RUNNING[:] = [(p, b) for p, b in _RUNNING if alive(p)]
    return _RUNNING


def reservations():
    """Current app-owned roots, including GUI, kernel and manager processes."""
    with _LOCK:
        return tuple(_live())


def capacity(budget):
    with _LOCK:
        live = _live()
        process_limit = min(
            [budget.max_processes, budget.max_concurrent_cpu_jobs]
            + [min(b.max_processes, b.max_concurrent_cpu_jobs) for _, b in live]
        )
        thread_limit = min([budget.cpu_threads] + [b.cpu_threads for _, b in live])
        return (
            len(live) < process_limit
            and sum(b.worker_threads for _, b in live) + budget.worker_threads
            <= thread_limit
        )


def spawn(factory, budget):
    """Factory is called under reservation lock; supports Popen and mp.Process."""
    with _LOCK:
        if not capacity(budget):
            raise ValueError(
                "Toplam süreç/native thread bütçesi dolu; çalışan işi bitirin veya iptal edin."
            )
        if budget.device != "cpu":
            raise ValueError(
                "Bu yerel süreç yolu CPU destekler; GPU için doğrulanmış yöntem gerekir. Otomatik fallback yok."
            )
        configure_threads(budget.worker_threads)
        process = factory()
        _RUNNING.append((process, budget))
        return process


def start(process, budget):
    def launch():
        process.start()
        return process

    return spawn(launch, budget)


def start_controller(controller, sender):
    """Reject before spawn; keep saved results and user datasets untouched."""
    try:
        start(controller.process, controller.budget)
        return True
    except (ValueError, OSError) as error:
        sender.close()
        controller.process.close()
        controller.process = None
        if controller.connection:
            controller.connection.close()
            controller.connection = None
        controller._error = (
            str(error)
            if isinstance(error, ValueError)
            else "Süreç başlatılamadı; önceki proje korundu."
        )
        workspace = getattr(controller, "workspace", None)
        if workspace and Path(workspace).is_relative_to(Path(controller.cache)):
            shutil.rmtree(workspace, ignore_errors=True)
            controller.workspace = None
        if not _live() and hasattr(controller, "projects"):
            controller.projects.dataset_active = False
            controller.projects.import_active = False
        controller.changed.emit()
        return False
