"""Hidden model stage sends the shell to the report without a fake metric."""

from PySide6.QtCore import QObject
from test_import_gui import setup, spin, teardown
from test_learning_gui import visual_item

from veri_ufku.domain.capabilities import availability as real_availability


def test_missing_model_module_opens_the_report(tmp_path, monkeypatch):
    def unavailable(capability):
        if capability.capability_id == "model.prepare":
            return False, "Model modülü kurulu değil."
        return real_availability(capability)

    monkeypatch.setattr("veri_ufku.domain.capabilities.availability", unavailable)
    app, window, *_ = setup(tmp_path, monkeypatch)

    def item(name):
        return window.findChild(QObject, name) or visual_item(
            window.contentItem(), name
        )

    try:
        assert not item("moduleModel").property("visible")
        assert item("moduleRapor").property("visible")
        window.setProperty("selectedSection", 5)
        spin(app, lambda: window.property("selectedSection") == 6)
        note = item("reportWithoutModel")
        assert note.property("visible")
        assert "uydurulmaz" in note.property("text")
        assert "istatistik" in note.property(
            "text"
        ).lower() or "İstatistik" in note.property("text")
    finally:
        teardown(app, window)
