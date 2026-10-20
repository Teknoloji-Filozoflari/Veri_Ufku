"""Explicit reproducible holdouts and development folds; no fallback protocol."""

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass

from veri_ufku.storage.project_model import ProjectError


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class ValidationSpec:
    structure: str = "independent"
    method: str = "auto"
    entity_use: str = "new"
    prediction_moment: str = ""
    horizon_seconds: int = 0
    availability: dict | None = None
    test_fraction: float = 0.2
    validation_fraction: float = 0.2
    folds: int = 3
    seed: int = 42
    baseline: str = "auto"

    @classmethod
    def from_dict(cls, value):
        try:
            return cls(**value)
        except (TypeError, ValueError):
            raise ProjectError("Değerlendirme protokolü alanları geçersiz.") from None

    def data(self):
        return asdict(self)

    def resolved(self, preparation):
        if any(
            not isinstance(v, str)
            for v in (self.structure, self.method, self.entity_use, self.baseline)
        ):
            raise ProjectError("Protokol seçimleri metin olmalı.")
        p = preparation["spec"]
        if p["purpose"] not in ("regression", "classification"):
            raise ProjectError(
                "Baseline yalnız regresyon/sınıflandırma içindir; bu amaç desteklenmiyor."
            )
        if self.structure not in ("independent", "group", "time", "group_time"):
            raise ProjectError("Kayıt yapısı desteklenmiyor.")
        expected = {
            "independent": "stratified"
            if p["purpose"] == "classification"
            else "random",
            "group": "group",
            "time": "time",
            "group_time": "group_time",
        }[self.structure]
        method = expected if self.method == "auto" else self.method
        if (
            method not in ("random", "stratified", "group", "time", "group_time")
            or (self.structure != "independent" and method != expected)
            or (
                self.structure == "independent"
                and method not in ("random", "stratified")
            )
        ):
            raise ProjectError(
                "Seçilen protokol kayıt yapısıyla uyumsuz; rastgele fallback yok."
            )
        if method == "stratified" and p["purpose"] != "classification":
            raise ProjectError("Stratified yalnız sınıflandırmada destekleniyor.")
        if self.entity_use not in ("new", "same_future") or (
            self.entity_use == "same_future" and self.structure != "time"
        ):
            raise ProjectError(
                "Aynı varlığın geleceği yalnız zaman protokolünde desteklenir; grup ayrılığıyla çakışan kullanım engellendi."
            )
        if self.entity_use == "same_future" and not p["group"]:
            raise ProjectError(
                "Aynı varlığın geleceğini doğrulamak için kişi/cihaz grup sütunu seçin."
            )
        if self.structure in ("group", "group_time") and not p["group"]:
            raise ProjectError("Kişi/cihaz grubu için grup sütunu seçin.")
        if self.structure in ("time", "group_time") and not p["time"]:
            raise ProjectError("Zaman sırası için Date/Datetime sütunu seçin.")
        if (
            self.structure == "independent"
            and (p["group"] or p["time"])
            or self.structure == "group"
            and p["time"]
            or self.structure == "time"
            and p["group"]
            and self.entity_use != "same_future"
        ):
            raise ProjectError(
                "Hazırlıkta seçilen grup/zaman kısıtlarını birlikte koruyan protokol seçin."
            )
        if (
            type(self.seed) is not int
            or not 0 <= self.seed < 2**32
            or type(self.folds) is not int
            or not 2 <= self.folds <= 10
        ):
            raise ProjectError("Seed 0..2³²−1; fold sayısı 2..10 olmalı.")
        if (
            type(self.horizon_seconds) is not int
            or not 0 <= self.horizon_seconds <= 10**10
        ):
            raise ProjectError("Hedef ufku negatif olmayan saniye olmalı.")
        if (
            any(
                type(v) not in (float, int) or not 0.05 <= v <= 0.4
                for v in (self.test_fraction, self.validation_fraction)
            )
            or self.test_fraction + self.validation_fraction >= 0.8
        ):
            raise ProjectError(
                "Validation/test oranı ayrı ayrı %5..40 olmalı; train en az %20 ayrılmalı."
            )
        if (
            not isinstance(self.prediction_moment, str)
            or not self.prediction_moment.strip()
            or len(self.prediction_moment) > 1000
        ):
            raise ProjectError("Tahmin anını açıkça belirtin.")
        if not isinstance(self.availability, dict) or set(self.availability) != set(
            p["features"]
        ):
            raise ProjectError(
                "Her özellik için bilginin kullanılabilirlik zamanı gerekir."
            )
        for value in self.availability.values():
            if (
                not isinstance(value, dict)
                or type(value.get("offset_seconds")) is not int
                or value["offset_seconds"] > 0
                or not isinstance(value.get("note"), str)
                or not value["note"].strip()
                or len(value["note"]) > 1000
            ):
                raise ProjectError(
                    "Özellik bilgisi tahmin anında/öncesinde mevcut olmalı; saniye farkı ve gerekçe belirtin."
                )
        strategy = (
            self.baseline
            if self.baseline != "auto"
            else ("mean" if p["purpose"] == "regression" else "prior")
        )
        if strategy not in (
            ("mean", "median")
            if p["purpose"] == "regression"
            else ("prior", "most_frequent", "stratified")
        ):
            raise ProjectError("Baseline yaklaşımı amaçla uyumsuz.")
        return (
            method,
            strategy,
            "Bağımsız kategorilerde sınıf oranını korur."
            if method == "stratified"
            else {
                "random": "Bağımsız kayıtlar seed ile karıştırılır.",
                "group": "Yeni kişiler/cihazlar bütün olarak ayrılır.",
                "time": "Geçmişten geleceğe; hedef ufku için eğitim sonu arındırılır.",
                "group_time": "Çakışan grup zaman aralıkları birlikte tutulur; yeni varlık ve gelecek birlikte korunur.",
            }[method],
        )


def split_plan(
    row_ids,
    y,
    groups,
    times,
    spec,
    method,
    classification,
    dataset_version,
    fingerprint,
    allow_missing_test_class=False,
):
    import numpy as np
    from sklearn.model_selection import (
        GroupKFold,
        GroupShuffleSplit,
        KFold,
        StratifiedKFold,
        train_test_split,
    )

    n = len(row_ids)
    indices = np.arange(n)
    classes = set(y) if classification else None
    if n < 8:
        raise ProjectError(
            "En az 8 kullanılabilir kayıt gerekiyor; bu teknik minimum yeterlilik garantisi değildir."
        )
    if classification and len(classes) < 2:
        raise ProjectError("En az iki sınıf gerekiyor.")
    if (method in ("group", "group_time") or spec.entity_use == "same_future") and (
        groups is None or any(g is None for g in groups)
    ):
        raise ProjectError("Grup anahtarı eksik/geçersiz; ayrım reddedildi.")
    if method in ("time", "group_time") and (
        times is None or not np.isfinite(times).all()
    ):
        raise ProjectError("Zaman anahtarı eksik/geçersiz; ayrım reddedildi.")
    invalid = []

    def check(train, evaluation, label):
        reason = None
        if len(train) < 2 or len(evaluation) < 2:
            reason = "Train/değerlendirme katı en az 2 kayıt olmalı."
        elif classification and (
            set(y[train]) != classes
            or (
                set(y[evaluation]) != classes
                and not (allow_missing_test_class and label == "final_test")
            )
        ):
            reason = "Küçük/sınıfı eksik fold veya bölüm; her sınıf iki tarafta da bulunmalı."
        elif method in ("group", "group_time") and set(groups[train]) & set(
            groups[evaluation]
        ):
            reason = "Gruplar bölümler arasında karışıyor."
        elif spec.entity_use == "same_future" and not set(groups[evaluation]) <= set(
            groups[train]
        ):
            reason = "Aynı varlığın geleceği protokolünde değerlendirmede yeni varlık var; bu ayrım reddedildi."
        elif method in ("time", "group_time") and max(
            times[train] + spec.horizon_seconds
        ) >= min(times[evaluation]):
            reason = "Gelecek/hedef ufku eğitimde; sıkı zaman ayrımı imkânsız."
        if reason:
            invalid.append(
                dict(
                    scope=label,
                    status="invalid",
                    reason=reason,
                    train_n=len(train),
                    evaluation_n=len(evaluation),
                )
            )
        return reason

    def purge(train, evaluation):
        return (
            train[times[train] + spec.horizon_seconds < min(times[evaluation])]
            if len(evaluation) and method in ("time", "group_time")
            else train
        )

    try:
        if method in ("random", "stratified"):
            development, test = train_test_split(
                indices,
                test_size=spec.test_fraction,
                random_state=spec.seed,
                stratify=y if method == "stratified" else None,
            )
            train, val = train_test_split(
                development,
                test_size=spec.validation_fraction / (1 - spec.test_fraction),
                random_state=spec.seed,
                stratify=y[development] if method == "stratified" else None,
            )
            cv = (
                StratifiedKFold(spec.folds, shuffle=True, random_state=spec.seed)
                if method == "stratified"
                else KFold(spec.folds, shuffle=True, random_state=spec.seed)
            )
            if (
                method == "stratified"
                and min(np.count_nonzero(y[development] == c) for c in classes)
                < spec.folds
            ):
                raise ProjectError(
                    "Geliştirme sınıf sayısı fold sayısından az; CV reddedildi."
                )
            folds = [
                (development[a], development[b])
                for a, b in cv.split(development, y[development])
            ]
        elif method == "group":
            a, b = next(
                GroupShuffleSplit(
                    1, test_size=spec.test_fraction, random_state=spec.seed
                ).split(indices, y, groups)
            )
            development, test = indices[a], indices[b]
            a, b = next(
                GroupShuffleSplit(
                    1,
                    test_size=spec.validation_fraction / (1 - spec.test_fraction),
                    random_state=spec.seed,
                ).split(development, y[development], groups[development])
            )
            train, val = development[a], development[b]
            folds = [
                (development[a], development[b])
                for a, b in GroupKFold(spec.folds).split(
                    development, y[development], groups[development]
                )
            ]
        else:
            if method == "time":
                buckets = defaultdict(list)
                for i, t in enumerate(times):
                    buckets[t].append(i)
                units = [np.array(buckets[t], dtype=int) for t in sorted(buckets)]
            else:
                # Connected overlapping group intervals cannot be separated without violating chronology.
                buckets = defaultdict(list)
                for i, g in enumerate(groups):
                    buckets[g].append(i)
                intervals = sorted(
                    (
                        min(times[rows]),
                        max(times[rows]) + spec.horizon_seconds,
                        str(g),
                        g,
                    )
                    for g, rows in buckets.items()
                )
                units, end, members = [], None, []
                for start, stop, _, group in intervals:
                    if end is not None and start > end:
                        units.append(
                            np.array(
                                [i for g in members for i in buckets[g]], dtype=int
                            )
                        )
                        members, end = [], None
                    members.append(group)
                    end = stop if end is None else max(end, stop)
                if members:
                    units.append(
                        np.array([i for g in members for i in buckets[g]], dtype=int)
                    )
            k = len(units)
            test_k = max(1, int(np.ceil(k * spec.test_fraction)))
            val_k = max(1, int(np.ceil(k * spec.validation_fraction)))
            if k - test_k - val_k < 1 or k - test_k < spec.folds + 1:
                raise ProjectError(
                    "Grup/zaman blokları çok az veya çakışıyor; geçerli birleşik ayrım/CV yok. Rastgele fallback yapılmadı."
                )
            test = np.concatenate(units[-test_k:])
            val = np.concatenate(units[-test_k - val_k : -test_k])
            train = purge(np.concatenate(units[: -test_k - val_k]), val)
            development = purge(np.concatenate(units[:-test_k]), test)
            val = val[np.isin(val, development)]
            chunks = np.array_split(np.arange(k - test_k), spec.folds + 1)
            folds = []
            for j in range(1, len(chunks)):
                b = np.concatenate([units[i] for i in chunks[j]])
                a = np.concatenate([units[i] for chunk in chunks[:j] for i in chunk])
                a = purge(a, b)
                a, b = a[np.isin(a, development)], b[np.isin(b, development)]
                folds.append((a, b))
        check(train, val, "validation")
        check(development, test, "final_test")
        for i, (a, b) in enumerate(folds):
            check(a, b, f"cv:{i + 1}")
    except ProjectError:
        raise
    except ValueError as error:
        raise ProjectError(
            "Ayrım/sınıf/grup sayısı bu protokol için yetersiz; oranları/fold sayısını inceleyin."
        ) from error
    if invalid:
        error = ProjectError(
            "Ayrım reddedildi: "
            + "; ".join(x["scope"] + ": " + x["reason"] for x in invalid)
        )
        error.invalid_folds = invalid
        raise error

    def ids(v):
        return sorted(str(row_ids[i]) for i in v)

    membership = dict(
        train=ids(train),
        validation=ids(val),
        development=ids(development),
        test=ids(test),
        folds=[dict(train=ids(a), validation=ids(b), status="valid") for a, b in folds],
        purged=ids(indices[~np.isin(indices, np.concatenate([train, val, test]))]),
    )
    protocol_id = "protocol:" + digest(dict(spec=spec.data(), method=method))
    split_id = "split:" + digest(
        dict(
            dataset_version=dataset_version,
            fingerprint=fingerprint,
            protocol_id=protocol_id,
            membership=membership,
        )
    )
    return dict(
        schema="ValidationPlan/v1",
        split_id=split_id,
        protocol_id=protocol_id,
        method=method,
        membership=membership,
        invalid_folds=[],
    ), (train, val, development, test, folds)


def development_folds(row_ids, y, groups, times, spec, method, classification):
    """Inner CV on an already isolated training pool; same joint constraints as outer CV."""
    import numpy as np
    from sklearn.model_selection import GroupKFold, KFold, StratifiedKFold

    indices = np.arange(len(row_ids))
    if method in ("random", "stratified"):
        splitter = (
            StratifiedKFold(spec.folds, shuffle=True, random_state=spec.seed)
            if method == "stratified"
            else KFold(spec.folds, shuffle=True, random_state=spec.seed)
        )
        try:
            folds = list(splitter.split(indices, y))
        except ValueError as error:
            raise ProjectError("Inner CV kayıt/sınıf sayısı yetersiz.") from error
    elif method == "group":
        if groups is None or any(g is None for g in groups):
            raise ProjectError("Inner CV grup anahtarı gerekli.")
        try:
            folds = list(GroupKFold(spec.folds).split(indices, y, groups))
        except ValueError as error:
            raise ProjectError("Inner CV grup sayısı yetersiz.") from error
    else:
        if times is None or not np.isfinite(times).all():
            raise ProjectError("Inner CV geçerli zaman anahtarı gerektirir.")
        buckets = defaultdict(list)
        for i, key in enumerate(times if method == "time" else groups):
            if key is None:
                raise ProjectError("Inner CV grup/zaman eksik.")
            buckets[key].append(i)
        if method == "time":
            units = [np.asarray(buckets[t], dtype=int) for t in sorted(buckets)]
        else:
            intervals = sorted(
                (min(times[rows]), max(times[rows]) + spec.horizon_seconds, str(g), g)
                for g, rows in buckets.items()
            )
            units = []
            end = None
            members = []
            for start, stop, _, group in intervals:
                if end is not None and start > end:
                    units.append(
                        np.asarray([i for g in members for i in buckets[g]], dtype=int)
                    )
                    members = []
                    end = None
                members.append(group)
                end = stop if end is None else max(end, stop)
            if members:
                units.append(
                    np.asarray([i for g in members for i in buckets[g]], dtype=int)
                )
        if len(units) < spec.folds + 1:
            raise ProjectError(
                "Inner CV birleşik grup/zaman blokları yetersiz; random fallback yok."
            )
        chunks = np.array_split(np.arange(len(units)), spec.folds + 1)
        folds = []
        for j in range(1, len(chunks)):
            a = np.concatenate([units[i] for chunk in chunks[:j] for i in chunk])
            b = np.concatenate([units[i] for i in chunks[j]])
            a = a[times[a] + spec.horizon_seconds < min(times[b])]
            folds.append((a, b))
    classes = set(y) if classification else None
    for a, b in folds:
        if len(a) < 2 or len(b) < 2 or set(a) & set(b):
            raise ProjectError("Inner CV boş/küçük/örtüşen fold.")
        if classification and (set(y[a]) != classes or set(y[b]) != classes):
            raise ProjectError("Inner CV fold sınıfları eksik; fallback yok.")
        if method in ("group", "group_time") and set(groups[a]) & set(groups[b]):
            raise ProjectError("Inner CV grupları karışıyor.")
        if spec.entity_use == "same_future" and not set(groups[b]) <= set(groups[a]):
            raise ProjectError(
                "Inner CV aynı varlığın geleceği planında yeni grup var."
            )
        if method in ("time", "group_time") and max(
            times[a] + spec.horizon_seconds
        ) >= min(times[b]):
            raise ProjectError("Inner CV geleceği/hedef ufkunu eğitimde kullanıyor.")
    membership = [
        dict(
            train=[str(row_ids[i]) for i in a], validation=[str(row_ids[i]) for i in b]
        )
        for a, b in folds
    ]
    return dict(
        schema="DevelopmentFolds/v1",
        method=method,
        folds=membership,
        plan_id="inner:" + digest(dict(spec=spec.data(), folds=membership)),
    ), folds
