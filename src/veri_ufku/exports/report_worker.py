"""Disposable PDF-capable worker, no application Qt objects or project writer."""

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError


def worker(request, spec, workspace, cancel, sender, budget):
    try:
        # Qt/font plugins need loading before the bounded address-space ceiling.
        import os

        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics, QGuiApplication
        from PySide6.QtPdf import QPdfDocument

        from veri_ufku.exports.reports import ASSETS

        app = QGuiApplication.instance() or QGuiApplication(["veri-ufku-report"])
        QFontDatabase.addApplicationFont(str(ASSETS / "fonts/DejaVuSans.ttf"))
        QFontMetrics(QFont("DejaVu Sans", 10)).horizontalAdvance("Türkçe")
        QPdfDocument(app)
        app.processEvents()
        apply_process_limits(budget)
        from veri_ufku.exports.report_builder import calculate

        sender.send(
            (
                "result",
                calculate(request, spec, workspace, Control(cancel, budget=budget)),
            )
        )
    except Canceled:
        sender.send(("canceled", None))
    except ProjectError as e:
        sender.send(("error", str(e)))
    except Exception as e:
        sender.send(
            (
                "error",
                resource_error_text(
                    e,
                    "Rapor tamamlanamadı ("
                    + type(e).__name__
                    + "); önceki rapor korundu.",
                ),
            )
        )
    finally:
        sender.close()
