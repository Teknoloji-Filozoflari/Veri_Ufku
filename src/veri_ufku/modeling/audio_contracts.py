"""Closed offline audio processing; channel and sample-time choices are explicit."""

from dataclasses import asdict, dataclass

from veri_ufku.storage.project_model import ProjectError


@dataclass(frozen=True)
class AudioSpec:
    task: str = "features"
    target_rate: int = 16000
    channel: int = 0
    n_fft: int = 256
    hop: int = 128
    n_mels: int = 24
    n_mfcc: int = 13
    f_min: float = 0
    f_max: float = 0
    silence_dbfs: float = -60
    clip_level: float = 0.999
    gain_db: float = 0
    seed: int = 58
    stt_folder: str = ""
    language: str = "tr"
    stt_consent: bool = False

    @classmethod
    def from_dict(cls, value):
        try:
            s = cls(**value)
        except (TypeError, ValueError):
            raise ProjectError("Audio tarifi geçersiz.") from None
        if (
            s.task not in ("features", "classification", "transcribe")
            or any(
                type(getattr(s, k)) is not int
                for k in (
                    "target_rate",
                    "channel",
                    "n_fft",
                    "hop",
                    "n_mels",
                    "n_mfcc",
                    "seed",
                )
            )
            or s.target_rate != 0
            and not 8000 <= s.target_rate <= 96000
            or not 0 <= s.channel <= 1
            or s.n_fft not in (128, 256, 512, 1024)
            or not 1 <= s.hop <= s.n_fft
            or not 8 <= s.n_mels <= 64
            or not 1 <= s.n_mfcc <= s.n_mels
            or not 0 <= s.seed < 2**32
        ):
            raise ProjectError("Audio task/rate/channel/FFT/hop/mel/MFCC/seed sınırı.")
        for k, lo, hi in (
            ("f_min", 0, 48000),
            ("f_max", 0, 48000),
            ("silence_dbfs", -120, -1),
            ("clip_level", 0.9, 1),
            ("gain_db", -12, 12),
        ):
            if type(getattr(s, k)) not in (int, float) or not lo <= getattr(s, k) <= hi:
                raise ProjectError("Audio frekans/seviye parametresi geçersiz.")
        if (
            not isinstance(s.stt_folder, str)
            or len(s.stt_folder) > 4096
            or not isinstance(s.language, str)
            or not 1 <= len(s.language) <= 40
            or type(s.stt_consent) is not bool
        ):
            raise ProjectError("STT yerel klasör/dil/onay şeması geçersiz.")
        if s.task == "transcribe" and (not s.stt_folder or not s.stt_consent):
            raise ProjectError(
                "Yerel küçük speech modeli yok/onay verilmedi: unavailable; model indirilmeyecek."
            )
        if s.task != "classification" and s.gain_db:
            raise ProjectError("Gain augmentation yalnız classification train'de.")
        return s

    def data(self):
        return asdict(self)
