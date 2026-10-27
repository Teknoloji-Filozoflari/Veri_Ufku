"""Whether the core model stage is installed. Optional families stay separate."""


def model_module_status():
    """Return the registry availability of model.prepare. No metric is invented."""
    from veri_ufku.domain.capabilities import CAPABILITIES, availability

    installed, reason = availability(CAPABILITIES["model.prepare"])
    if installed:
        return {"installed": True, "reason": ""}
    return {
        "installed": False,
        "reason": reason or "Model modülü kurulu değil.",
    }
