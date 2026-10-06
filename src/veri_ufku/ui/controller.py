"""Only the GUI thread updates Qt properties; job supervisor stays Qt-free."""

from PySide6.QtCore import Property, QCoreApplication, QObject, QTimer, Signal, Slot

from veri_ufku.domain.contracts import AppError


def tr(text):
    return QCoreApplication.translate("Shell", text)


STATES = {
    "idle": "Ready",
    "queued": "Queued",
    "running": "Running",
    "cancel_requested": "Canceling",
    "succeeded": "Completed",
    "canceled": "Canceled",
    "failed": "Failed",
    "closing": "Closing safely",
}
ERRORS = {
    "worker": "The test task failed. You can try again.",
    "budget": "The task exceeded its resource budget. Reduce the task or check available space.",
    "cleanup": "Temporary files could not be removed. Check cache folder permissions.",
    "configuration": "Configuration is invalid. Check local settings.",
}


class ShellController(QObject):
    changed = Signal()
    shutdownReady = Signal()

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.job_id = ""
        self._state = "idle"
        self._result = ""
        self._error = ""
        self._progress = -1.0
        self._active = False
        self._closing = False
        self.beats = 0
        self._timer = QTimer(self)
        self._timer.setInterval(25)
        self._timer.timeout.connect(self.poll)
        self._timer.start()

    @Property(str, notify=changed)
    def stateCode(self):
        return self._state

    @Property(str, notify=changed)
    def stateText(self):
        return tr(STATES[self._state])

    @Property(str, notify=changed)
    def resultText(self):
        return self._result

    @Property(str, notify=changed)
    def errorText(self):
        return self._error

    @Property(str, notify=changed)
    def jobId(self):
        return self.job_id

    @Property(float, notify=changed)
    def progress(self):
        return self._progress

    @Property(bool, notify=changed)
    def active(self):
        return self._active

    @Property(bool, notify=changed)
    def closing(self):
        return self._closing

    @Property(bool, notify=changed)
    def closed(self):
        return self.session.manager.closed

    @Property(int, notify=changed)
    def revision(self):
        return self.session.binding.config_revision

    @Property(str, notify=changed)
    def sessionVersion(self):
        return self.session.binding.dataset_version

    @Slot(str)
    def start(self, capability_id):
        if self._active or self._closing:
            return
        self._result, self._error, self._progress = "", "", -1
        try:
            self.job_id = self.session.start(capability_id)
            self._active, self._state = True, "queued"
        except (ValueError, RuntimeError) as exception:
            error = AppError.create("budget", type(exception).__name__)
            self._error = (
                tr(ERRORS[error.code])
                + " "
                + tr("Reference:")
                + " "
                + error.correlation_id
            )
            self.session.manager.record_event("submit_failed", "", error)
            self._state = "failed"
        self.changed.emit()

    @Slot()
    def cancel(self):
        if self._active:
            if self.session.manager.cancel(self.job_id):
                self._state = "cancel_requested"
                self.changed.emit()
            else:
                self.poll()  # completion won the race; never claim a successful cancellation

    @Slot()
    def changeConfiguration(self):
        self.session.change_configuration()
        self._result = ""
        self.changed.emit()

    @Slot()
    def shutdown(self):
        self._closing, self._state = True, "closing"
        self.session.manager.request_shutdown()
        self.changed.emit()

    @Slot()
    def poll(self):
        self.beats += 1
        for snapshot in self.session.manager.drain_updates():
            if snapshot.job_id != self.job_id:
                continue
            self._state = snapshot.state.value if not self._closing else "closing"
            self._active = not snapshot.state.terminal
            self._progress = (
                snapshot.progress.done / snapshot.progress.total
                if snapshot.progress.total
                else -1
            )
            if snapshot.error:
                self._error = (
                    tr(ERRORS.get(snapshot.error.code, ERRORS["worker"]))
                    + " "
                    + tr("Reference:")
                    + " "
                    + snapshot.error.correlation_id
                )
            if snapshot.result_for(self.session.binding):
                self._result = tr("Test result:") + " " + str(snapshot.result.value)
            elif snapshot.result:
                self._result = tr(
                    "The result belongs to an earlier configuration and was not applied."
                )
            if snapshot.state.value == "canceled":
                self._result = tr("Canceled; no result was applied.")
            self.changed.emit()
        if self._closing and self.closed:
            self._timer.stop()
            self.changed.emit()
            self.shutdownReady.emit()
