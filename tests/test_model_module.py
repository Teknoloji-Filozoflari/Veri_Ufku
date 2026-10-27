"""Core model stage follows model.prepare availability."""

from veri_ufku.domain.capabilities import CAPABILITIES
from veri_ufku.ui.model_module import model_module_status


def test_installed_model_stage_stays_available():
    status = model_module_status()
    assert status["installed"] is True
    assert status["reason"] == ""
    assert "metrik" not in status["reason"]


def test_missing_model_prepare_hides_the_stage(monkeypatch):
    def unavailable(capability):
        if capability.capability_id == "model.prepare":
            return False, "Model modülü kurulu değil."
        return True, ""

    monkeypatch.setattr("veri_ufku.domain.capabilities.availability", unavailable)
    status = model_module_status()
    assert status["installed"] is False
    assert "kurulu değil" in status["reason"]
    assert CAPABILITIES["model.prepare"].capability_id == "model.prepare"
