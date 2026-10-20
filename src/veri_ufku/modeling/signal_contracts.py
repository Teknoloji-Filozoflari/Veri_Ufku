"""Declarative regular-signal schema; no scientific imports on the Qt thread."""

import math
from dataclasses import asdict, dataclass, field

from veri_ufku.storage.project_model import ProjectError

METHODS = (
    "schema",
    "resample",
    "detrend",
    "window",
    "fft",
    "welch",
    "stft",
    "spectrogram",
    "peak",
    "filter",
    "zero-phase",
    "events",
    "classification",
)


@dataclass(frozen=True)
class SignalSpec:
    family: str = "signal"
    operation: str = "spectrogram"
    task: str = "analysis"
    sample_rate: float = 128.0
    time_unit: str = "s"
    channels: list[str] = field(default_factory=list)
    channel_units: dict[str, str] = field(default_factory=dict)
    bandlimit_hz: float = 0.0
    acquisition_note: str = "Unknown analog anti-alias acquisition"
    target_rate: float = 0.0
    allow_band_loss: bool = False
    mode: str = "offline"
    detrend: str = "none"
    window: str = "hann"
    segment_length: int = 128
    overlap: int = 64
    scaling: str = "density"
    filter_type: str = "none"
    cutoff: list[float] = field(default_factory=lambda: [20.0])
    order: int = 4
    zero_phase: bool = False
    prominence: float = 0.1
    peak_distance: int = 1
    event: str = ""
    block_columns: list[str] = field(default_factory=list)
    train_recordings: list[str] = field(default_factory=list)
    validation_recordings: list[str] = field(default_factory=list)
    label: str = ""
    seed: int = 54

    def data(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value, base, columns=None):
        try:
            if not isinstance(value, dict) or set(value) - set(
                cls.__dataclass_fields__
            ):
                raise ValueError
            s = cls(**value)
            s.validate(base, columns)
            return s
        except (TypeError, ValueError) as error:
            raise ProjectError("Sinyal tarifi geçersiz.") from error

    def validate(self, base, columns=None):
        if (
            self.family != "signal"
            or self.operation not in METHODS
            or self.task not in ("analysis", "classification")
        ):
            raise ProjectError("Desteklenmeyen sinyal görevi.")
        if base.resample or base.aggregation != "none":
            raise ProjectError(
                "Sinyal için takvim agregasyonu kapalı; target_rate seçin."
            )
        if self.time_unit not in ("s", "ms", "us", "ns") or self.mode not in (
            "offline",
            "online",
        ):
            raise ProjectError("Zaman birimi s/ms/us/ns ve offline/online seçin.")
        for name, lo, hi in (
            ("sample_rate", 1e-6, 1e6),
            ("target_rate", 0, 1e6),
            ("bandlimit_hz", 0, 1e6),
            ("prominence", 0, 1e12),
        ):
            v = getattr(self, name)
            if (
                isinstance(v, bool)
                or not isinstance(v, (int, float))
                or not math.isfinite(v)
                or not lo <= v <= hi
            ):
                raise ProjectError(f"{name}: sonlu değer gerekli.")
        for name, lo, hi in (
            ("segment_length", 32, 2048),
            ("overlap", 0, 2047),
            ("order", 1, 8),
            ("peak_distance", 1, 8192),
            ("seed", 0, 2**32 - 1),
        ):
            if (
                type(getattr(self, name)) is not int
                or not lo <= getattr(self, name) <= hi
            ):
                raise ProjectError(f"{name}: geçerli tam sayı gerekli.")
        if (
            self.overlap >= self.segment_length
            or self.segment_length - self.overlap < 8
        ):
            raise ProjectError("Overlap pencere boyundan küçük; stride en az8 örnek.")
        if (
            self.detrend not in ("none", "constant", "linear")
            or self.window not in ("boxcar", "hann", "hamming", "blackman")
            or self.scaling not in ("density", "spectrum")
        ):
            raise ProjectError("Detrend/window/normalizasyon seçimi desteklenmiyor.")
        if type(self.zero_phase) is not bool or type(self.allow_band_loss) is not bool:
            raise ProjectError("Offline/bant kaybı onayı boolean olmalı.")
        if self.mode == "online" and (
            self.zero_phase or self.target_rate or self.detrend != "none"
        ):
            raise ProjectError(
                "Zero-phase, merkezli resample ve tam-kayıt detrend geleceği kullanır: offline-only."
            )
        if self.bandlimit_hz >= self.sample_rate / 2:
            raise ProjectError(
                "Nyquist/aliasing: beyan edilen bant sample_rate/2 altında olmalı."
            )
        if (
            not isinstance(self.acquisition_note, str)
            or not 3 <= len(self.acquisition_note) <= 500
        ):
            raise ProjectError(
                "Analog bant/anti-alias kaynağı gerekçesi gerekli; beyan kanıt değildir."
            )
        fs = self.target_rate or self.sample_rate
        if (
            self.target_rate
            and self.bandlimit_hz >= fs / 2
            and not self.allow_band_loss
        ):
            raise ProjectError(
                "Yeni Nyquist bandı keser; anti-alias FIR ile bant kaybını açıkça onaylayın."
            )
        if self.filter_type not in (
            "none",
            "lowpass",
            "highpass",
            "bandpass",
            "bandstop",
        ):
            raise ProjectError("Butterworth SOS filtre türü geçersiz.")
        if self.zero_phase and self.filter_type == "none":
            raise ProjectError("Zero-phase için filtre seçin.")
        if (
            not isinstance(self.cutoff, list)
            or len(self.cutoff) not in (1, 2)
            or any(
                isinstance(x, bool)
                or not isinstance(x, (int, float))
                or not math.isfinite(x)
                for x in self.cutoff
            )
        ):
            raise ProjectError("Cutoff sonlu Hz listesi olmalı.")
        if self.filter_type != "none" and (
            len(self.cutoff) != (2 if self.filter_type.startswith("band") else 1)
            or not all(0 < x < fs / 2 for x in self.cutoff)
            or self.cutoff != sorted(set(self.cutoff))
        ):
            raise ProjectError("Cutoff: 0 < Hz < Nyquist; band için iki artan cutoff.")
        for name in (
            "channels",
            "block_columns",
            "train_recordings",
            "validation_recordings",
        ):
            v = getattr(self, name)
            if (
                not isinstance(v, list)
                or len(v) > (8 if name == "channels" else 16)
                or any(not isinstance(x, str) or not x for x in v)
                or len(set(v)) != len(v)
            ):
                raise ProjectError(f"{name}: benzersiz kimlik listesi gerekli.")
        if not 1 <= len(self.channels) <= 8 or base.measurement not in self.channels:
            raise ProjectError("1–8 kanal seçin; ana ölçüm kanallarda bulunmalı.")
        if (
            not isinstance(self.channel_units, dict)
            or set(self.channel_units) != set(self.channels)
            or any(
                not isinstance(x, str) or not 1 <= len(x) <= 40
                for x in self.channel_units.values()
            )
        ):
            raise ProjectError(
                "Her kanalın ölçüm birimini açıkça kaydedin (ör. V veya dimensionless)."
            )
        if not all(
            isinstance(x, str) for x in (self.event, self.label, base.date, base.group)
        ):
            raise ProjectError("Sinyal kolon seçimi geçersiz.")
        if self.task == "classification" and (
            not base.group
            or not self.label
            or not self.block_columns
            or not self.train_recordings
            or not self.validation_recordings
        ):
            raise ProjectError(
                "Classification kayıt/grup, label, kişi/cihaz/oturum blok kolonları ve açık train/validation kayıtları ister."
            )
        if set(self.train_recordings) & set(self.validation_recordings):
            raise ProjectError("Aynı kayıt train/validation olamaz.")
        selected = [
            base.date,
            *self.channels,
            *([base.group] if base.group else []),
            *([self.event] if self.event else []),
            *([self.label] if self.label else []),
        ]
        if len(selected) != len(set(selected)):
            raise ProjectError(
                "Zaman, kanal, kayıt, event ve label farklı kolonlar olmalı."
            )
        if set(self.block_columns) & (
            {base.date, *self.channels, self.event, self.label} - {""}
        ):
            raise ProjectError("Blok kimliği zaman/kanal/event/label olamaz.")
        if columns is not None and not set(selected + self.block_columns) <= {
            c["id"] for c in columns
        }:
            raise ProjectError("Bilinmeyen ColumnId.")
