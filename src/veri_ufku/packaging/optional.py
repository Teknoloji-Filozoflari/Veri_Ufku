"""Optional backend import deferred to an explicit operation, never a fake fallback."""

import importlib

from veri_ufku.storage.project_model import ProjectError


class LazyModule:
    def __init__(self, name, extra):
        self.name, self.extra = name, extra

    def __getattr__(self, name):
        try:
            module = importlib.import_module(self.name)
        except (ImportError, OSError):
            raise ProjectError(
                "Optional "
                + self.extra
                + " backend eksik/uyumsuz; otomatik indirme veya sessiz fallback yok."
            ) from None
        return getattr(module, name)
