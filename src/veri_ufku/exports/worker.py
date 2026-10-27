"""Disposable process for data/report export, including its own offscreen PDF runtime."""

import os

from veri_ufku.domain.contracts import Progress
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError


def process_entry(
    kind,
    request,
    parameters,
    workspace,
    destination,
    project_root,
    cancel,
    connection,
    budget,
):
    try:
        qt_app = None
        if parameters["format"] == "pdf":
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            from PySide6.QtGui import (
                QFont,
                QFontDatabase,
                QFontMetrics,
                QGuiApplication,
            )
            from PySide6.QtPdf import QPdfDocument

            from veri_ufku.exports.reports import ASSETS

            qt_app = QGuiApplication(["veri-ufku-report"])
            QFontDatabase.addApplicationFont(str(ASSETS / "fonts/DejaVuSans.ttf"))
            QFontMetrics(QFont("DejaVu Sans", 10)).horizontalAdvance("Türkçe")
            QPdfDocument(qt_app)
        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        if kind == "data":
            from veri_ufku.exports.data import export
        elif kind == "package":
            from veri_ufku.exports.local_package import export
        else:
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            from veri_ufku.exports.reports import export
        value = export(
            request, parameters, workspace, destination, project_root, control
        )
        value["worker_pid"] = os.getpid()
        # Once exclusive publication happened, report it even if cancellation arrived late.
        connection.send(("result", value))
    except Canceled:
        connection.send(("canceled", None))
    except ProjectError as error:
        connection.send(("error", str(error)))
    except Exception as error:
        connection.send(
            (
                "error",
                resource_error_text(
                    error,
                    f"Çıktı oluşturulamadı ({type(error).__name__}); kaynak ve mevcut dosyalar korundu.",
                ),
            )
        )
    finally:
        connection.close()
