"""Closed CPU tensor templates. Optional framework never downloads at application startup."""

import importlib.util
import math
from dataclasses import asdict, dataclass

from veri_ufku.storage.project_model import ProjectError


@dataclass(frozen=True)
class NeuralSpec:
    template: str = "mlp"
    device: str = "cpu"
    epochs: int = 12
    batch: int = 16
    hidden: int = 16
    lr: float = 0.01
    optimizer: str = "adam"
    scheduler: str = "step"
    patience: int = 5
    gradient_clip: float = 5.0
    seed: int = 56
    deterministic: bool = True
    class_weights: str = "none"
    image_shape: tuple = ()
    image_ack: str = ""
    augmentation: str = "none"
    mixed_precision: bool = False
    wall_seconds: float = 120

    @classmethod
    def from_dict(cls, value, require_backend=True):
        try:
            result = cls(**value)
            result = cls(**dict(asdict(result), image_shape=tuple(result.image_shape)))
        except (ValueError, TypeError):
            raise ProjectError("Tensor eğitim tarifi geçersiz.") from None
        result.validate(require_backend)
        return result

    def data(self):
        return dict(asdict(self), image_shape=list(self.image_shape))

    def validate(self, require_backend=True):
        for field, low, high in (
            ("epochs", 1, 100),
            ("batch", 1, 128),
            ("hidden", 2, 64),
            ("patience", 1, 100),
            ("seed", 0, 2**32 - 1),
        ):
            if (
                type(getattr(self, field)) is not int
                or not low <= getattr(self, field) <= high
            ):
                raise ProjectError("Epoch/batch/hidden/patience/seed bütçesi geçersiz.")
        for field, low, high in (
            ("lr", 1e-6, 1),
            ("gradient_clip", 0.01, 100),
            ("wall_seconds", 1, 600),
        ):
            v = getattr(self, field)
            if (
                type(v) not in (int, float)
                or not math.isfinite(v)
                or not low <= v <= high
            ):
                raise ProjectError("LR/gradient/süre bütçesi geçersiz.")
        if (
            self.template not in ("mlp", "cnn")
            or self.optimizer not in ("adam", "sgd")
            or self.scheduler not in ("step", "none")
        ):
            raise ProjectError(
                "Yalnız kapalı MLP/CNN ve Adam/SGD/StepLR şablonları desteklenir."
            )
        if self.device != "cpu" or self.mixed_precision is not False:
            raise ProjectError(
                "Bu doğrulanmış adapter CPU float32; GPU/VRAM/mixed precision bu ortamda doğrulanmadı ve kapalı."
            )
        if type(self.deterministic) is not bool or self.class_weights not in (
            "none",
            "balanced",
        ):
            raise ProjectError("Determinism/class weights seçimi geçersiz.")
        if (
            self.augmentation not in ("none", "horizontal_flip")
            or self.template == "mlp"
            and self.augmentation != "none"
        ):
            raise ProjectError(
                "Horizontal flip yalnız açık görüntü CNN eğitiminde desteklenir."
            )
        if self.template == "cnn":
            if (
                len(self.image_shape) != 3
                or any(type(v) is not int or not 1 <= v <= 16 for v in self.image_shape)
                or min(self.image_shape[1:]) < 2
                or not isinstance(self.image_ack, str)
                or not self.image_ack.strip()
            ):
                raise ProjectError(
                    "CNN: kanal/yükseklik/genişlik ve row-major piksel sırası gerekçesi gerekir."
                )
        elif self.image_shape:
            raise ProjectError("MLP görüntü boyutu almaz.")
        if require_backend and importlib.util.find_spec("torch") is None:
            raise ProjectError(
                "Optional PyTorch yok; yerel CPU extra kurulmadan eğitim yapılamaz. Otomatik ağ isteği yok."
            )
