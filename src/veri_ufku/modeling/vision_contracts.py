"""Closed local vision tasks; original annotations and transforms are explicit."""

from dataclasses import asdict, dataclass

from veri_ufku.storage.project_model import ProjectError


@dataclass(frozen=True)
class VisionSpec:
    task: str = "classification"
    size: int = 8
    crop: tuple = (0.0, 0.0, 1.0, 1.0)
    flip: bool = False
    epochs: int = 6
    seed: int = 57
    learning_rate: float = 0.01
    model_folder: str = ""
    score_threshold: float = 0.5
    iou_thresholds: tuple = (0.5, 0.75, 0.95)

    @classmethod
    def from_dict(cls, value):
        try:
            spec = cls(**value)
            spec = cls(
                **dict(
                    asdict(spec),
                    crop=tuple(spec.crop),
                    iou_thresholds=tuple(spec.iou_thresholds),
                )
            )
        except (TypeError, ValueError):
            raise ProjectError("Vision tarifi geçersiz.") from None
        if (
            spec.task
            not in ("scan", "classification", "transfer", "detection", "segmentation")
            or type(spec.size) is not int
            or not 4 <= spec.size <= 16
            or type(spec.epochs) is not int
            or not 1 <= spec.epochs <= 50
            or type(spec.seed) is not int
            or not 0 <= spec.seed < 2**32
            or type(spec.flip) is not bool
        ):
            raise ProjectError("Vision task/size/epoch/seed sınırı geçersiz.")
        if (
            len(spec.crop) != 4
            or any(type(v) not in (int, float) or not 0 <= v <= 1 for v in spec.crop)
            or not (spec.crop[0] < spec.crop[2] and spec.crop[1] < spec.crop[3])
        ):
            raise ProjectError("Crop normalized XYXY pozitif alanlı olmalı.")
        if (
            type(spec.learning_rate) not in (int, float)
            or not 1e-6 <= spec.learning_rate <= 0.1
            or type(spec.score_threshold) not in (int, float)
            or not 0 <= spec.score_threshold <= 1
            or not 1 <= len(spec.iou_thresholds) <= 10
            or any(
                type(v) not in (int, float) or not 0 < v <= 1
                for v in spec.iou_thresholds
            )
            or len(set(spec.iou_thresholds)) != len(spec.iou_thresholds)
        ):
            raise ProjectError("LR/score/IoU threshold geçersiz.")
        if (
            not isinstance(spec.model_folder, str)
            or len(spec.model_folder) > 4096
            or spec.task == "transfer"
            and not spec.model_folder
        ):
            raise ProjectError(
                "Transfer için yerel safe VisionWeights/v1 modeli gerekli; otomatik indirme yok."
            )
        if spec.task in ("detection", "segmentation") and spec.flip:
            raise ProjectError(
                "Bu pixel adapterde augmentation kapalı; classification CNN flip train-only."
            )
        return spec

    def data(self):
        return dict(
            asdict(self), crop=list(self.crop), iou_thresholds=list(self.iou_thresholds)
        )
