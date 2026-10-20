"""Bounded classifiers and explicit, label-stable classification metrics."""

import math

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    auc,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_curve,
)

from veri_ufku.modeling.family_contracts import FAMILY_METHODS, FamilyOptions
from veri_ufku.storage.project_model import ProjectError

CATALOG = ("baseline", "logistic", "forest") + FAMILY_METHODS


def settings(value):
    out = dict(
        candidates=list(CATALOG[:3]),
        C=1.0,
        trees=50,
        depth=8,
        averaging="macro",
        positive_class="",
        threshold_mode="default",
        threshold=0.5,
        cost_note="",
    )
    if not isinstance(value, dict) or set(value) - (
        set(out) | {"family_options", "explicit_model", "uncertainty"}
    ):
        raise ProjectError("Sınıflandırma ayarları geçersiz.")
    out.update(value)
    if (
        not isinstance(out["candidates"], list)
        or not out["candidates"]
        or len(set(out["candidates"])) != len(out["candidates"])
        or any(c not in CATALOG for c in out["candidates"])
        or "baseline" not in out["candidates"]
    ):
        raise ProjectError("Baseline ve desteklenen en fazla üç aday seçin.")
    if type(out["C"]) not in (int, float) or out["C"] not in (0.1, 1.0, 10.0):
        raise ProjectError("LogisticRegression C yalnız 0.1, 1 veya 10 olabilir.")
    if type(out["trees"]) is not int or out["trees"] not in (25, 50, 100):
        raise ProjectError("Forest ağaç sayısı 25/50/100 olmalı.")
    if type(out["depth"]) is not int or out["depth"] not in (4, 8, 12):
        raise ProjectError("Forest derinliği 4/8/12 olmalı.")
    if out["averaging"] not in ("macro", "weighted", "micro", "binary"):
        raise ProjectError("Averaging macro/weighted/micro/binary olmalı.")
    if out["threshold_mode"] not in ("default", "validation_manual", "validation_f1"):
        raise ProjectError("Eşik yalnız validation üzerinde seçilebilir.")
    if (
        type(out["threshold"]) not in (int, float)
        or not math.isfinite(out["threshold"])
        or not 0.05 <= out["threshold"] <= 0.95
    ):
        raise ProjectError("Eşik 0.05..0.95 arasında olmalı.")
    if out["threshold_mode"] == "default" and out["threshold"] != 0.5:
        raise ProjectError("Varsayılan eşik 0.5 olmalı.")
    if not isinstance(out["positive_class"], str) or len(out["positive_class"]) > 256:
        raise ProjectError("Pozitif sınıf metni geçersiz.")
    if not isinstance(out["cost_note"], str) or len(out["cost_note"]) > 2000:
        raise ProjectError("Hata maliyeti açıklaması en fazla2000 karakter olmalı.")
    if "family_options" in out:
        out["family_options"] = FamilyOptions.from_dict(out["family_options"]).data()
        if (
            out.get("explicit_model") not in out["candidates"]
            or out.get("explicit_model") not in FAMILY_METHODS
        ):
            raise ProjectError(
                "Faz48 explicit model seçilmeli; tek en iyi aday önerilmez."
            )
    elif any(m in FAMILY_METHODS for m in out["candidates"]):
        raise ProjectError("Faz48 family_options ve explicit_model gerekli.")
    if "uncertainty" in out:
        from veri_ufku.modeling.uncertainty import UncertaintySpec

        out["uncertainty"] = UncertaintySpec.from_dict(
            out["uncertainty"], "classification"
        ).data()
    return out


def validate_classes(config, labels):
    if (
        not isinstance(labels, list)
        or any(not isinstance(c, str) or len(c) > 256 for c in labels)
        or len(set(labels)) != len(labels)
    ):
        raise ProjectError("Sınıf etiketleri benzersiz ve en fazla256 karakter olmalı.")
    if not 2 <= len(labels) <= 20:
        raise ProjectError("Kategori hedefi 2..20 sınıf içermeli.")
    if config["positive_class"] and config["positive_class"] not in labels:
        raise ProjectError("Pozitif sınıf hedef sınıfları arasında bulunmuyor.")
    if len(labels) == 2 and config["positive_class"] not in labels:
        raise ProjectError("İkili hedef için pozitif sınıfı açıkça seçin.")
    if len(labels) != 2 and (
        config["averaging"] == "binary" or config["threshold_mode"] != "default"
    ):
        raise ProjectError(
            "Binary averaging ve eşik seçimi yalnız ikili hedef içindir."
        )


def estimator(candidate, config, strategy, seed):
    if candidate == "baseline":
        return DummyClassifier(strategy=strategy, random_state=seed)
    if candidate == "logistic":
        return LogisticRegression(C=config["C"], max_iter=500, random_state=seed)
    return RandomForestClassifier(
        n_estimators=config["trees"],
        max_depth=config["depth"],
        min_samples_leaf=2,
        n_jobs=1,
        random_state=seed,
    )


def probabilities(model, X, labels):
    if not hasattr(model, "predict_proba"):
        return None
    values = np.asarray(model.predict_proba(X), dtype=float)
    known = list(model.classes_)
    if set(known) != set(labels) or values.shape != (len(X), len(known)):
        raise ProjectError("Olasılık sınıf eşlemesi veya boyutu geçersiz.")
    values = values[:, [known.index(c) for c in labels]]
    if (
        not np.isfinite(values).all()
        or np.any(values < 0)
        or np.any(values > 1)
        or not np.allclose(values.sum(axis=1), 1, atol=1e-8)
    ):
        raise ProjectError("Model geçerli sınıf olasılıkları üretmedi.")
    return values


def predictions(pred, probability, labels, positive, threshold):
    if len(labels) != 2 or probability is None:
        return pred
    negative = next(c for c in labels if c != positive)
    return np.where(
        probability[:, labels.index(positive)] >= threshold, positive, negative
    )


def distribution(y, labels):
    return [
        dict(label=c, n=int(np.count_nonzero(y == c)), fraction=float(np.mean(y == c)))
        for c in labels
    ]


def metrics(y, pred, probability, labels, config, scope):
    y, pred = np.asarray(y), np.asarray(pred)
    if (
        not len(y)
        or len(pred) != len(y)
        or not set(y) <= set(labels)
        or not set(pred) <= set(labels)
    ):
        raise ProjectError("Metrik hedef/tahmin sınıf eşlemesi geçersiz.")
    matrix = confusion_matrix(y, pred, labels=labels)
    support, predicted = matrix.sum(axis=1), matrix.sum(axis=0)
    tp = np.diag(matrix).astype(float)
    precision = np.divide(
        tp, predicted, out=np.zeros(len(labels)), where=predicted != 0
    )
    recall = np.divide(tp, support, out=np.zeros(len(labels)), where=support != 0)
    f1 = np.divide(
        2 * tp,
        support + predicted,
        out=np.zeros(len(labels)),
        where=(support + predicted) != 0,
    )
    avg = config["averaging"]

    def aggregate(values):
        if avg == "binary":
            return float(values[labels.index(config["positive_class"])])
        if avg == "micro":
            return float(tp.sum() / len(y))
        return (
            float(np.average(values, weights=support))
            if avg == "weighted"
            else float(np.mean(values))
        )

    scores = [
        dict(
            metric=k,
            value=v,
            direction="maximize",
            scope=scope,
            n=len(y),
            status="valid",
            coverage="all eligible records in this evaluation partition",
            averaging=a,
        )
        for k, v, a in [
            ("accuracy", float(tp.sum() / len(y)), "per_record"),
            ("precision", aggregate(precision), avg),
            ("recall", aggregate(recall), avg),
            ("f1", aggregate(f1), avg),
        ]
    ]
    per_class = [
        dict(
            label=c,
            support=int(support[i]),
            predicted_n=int(predicted[i]),
            precision=float(precision[i]),
            recall=float(recall[i]),
            f1=float(f1[i]),
            precision_status="valid" if predicted[i] else "undefined_no_predictions",
            recall_status="valid" if support[i] else "undefined_absent_class",
            f1_status="valid"
            if support[i] + predicted[i]
            else "undefined_no_support_or_predictions",
        )
        for i, c in enumerate(labels)
    ]
    curves = []
    curve_labels = [config["positive_class"]] if len(labels) == 2 else labels
    for label in curve_labels:
        actual = (y == label).astype(int)
        reason = (
            "Model predict_proba desteklemiyor."
            if probability is None
            else "Bu bölümde pozitif veya negatif sınıf yok."
            if len(set(actual)) < 2
            else ""
        )
        entry = dict(
            label=label,
            status="unavailable" if reason else "valid",
            reason=reason,
            roc_auc=None,
            pr_auc=None,
            average_precision=None,
            roc=[],
            pr=[],
        )
        if not reason:
            score = probability[:, labels.index(label)]
            fpr, tpr, _ = roc_curve(actual, score)
            pr, rec, _ = precision_recall_curve(actual, score)
            entry.update(
                roc_auc=float(auc(fpr, tpr)),
                pr_auc=float(auc(rec, pr)),
                average_precision=float(average_precision_score(actual, score)),
            )
            for kind, x, z in (("roc", fpr, tpr), ("pr", rec, pr)):
                idx = np.linspace(0, len(x) - 1, min(1000, len(x)), dtype=int)
                entry[kind] = [dict(x=float(x[i]), y=float(z[i])) for i in idx]
            entry["curve_coverage"] = (
                "At most1000 evenly spaced curve points; AUC uses all thresholds. PR-AUC trapezoidal; AP non-interpolated."
            )
        curves.append(entry)
    for key in ("roc_auc", "pr_auc"):
        valid = [e for e in curves if e["status"] == "valid"]
        reason = ""
        value = None
        if len(valid) == len(curves):
            if len(labels) == 2:
                value = valid[0][key]
            elif avg == "micro":
                if probability is not None:
                    actual = (
                        np.column_stack([y == c for c in labels]).astype(int).ravel()
                    )
                    score = probability.ravel()
                    fpr, tpr, _ = roc_curve(actual, score)
                    pr, rec, _ = precision_recall_curve(actual, score)
                    value = float(auc(fpr, tpr) if key == "roc_auc" else auc(rec, pr))
            else:
                value = float(
                    np.average(
                        [e[key] for e in valid],
                        weights=support if avg == "weighted" else None,
                    )
                )
        else:
            reason = (
                "Bazı sınıflarda eğri hesaplanamıyor; ortalamadan sessiz çıkarılmadı."
            )
        scores.append(
            dict(
                metric=key,
                value=value,
                direction="maximize",
                scope=scope,
                n=len(y),
                status="valid" if value is not None else "undefined",
                reason=reason,
                coverage="all eligible records in this evaluation partition",
                averaging="binary" if len(labels) == 2 else avg + "_ovr",
            )
        )
    return dict(
        metrics=scores,
        classes=labels,
        confusion_matrix=matrix.tolist(),
        axes=dict(rows="actual", columns="predicted"),
        per_class=per_class,
        class_distribution=distribution(y, labels),
        curves=curves,
        zero_division_policy="0 with explicit per-class undefined status; macro includes all declared labels",
        warnings=[
            "Bu bölümde bulunmayan sınıf: " + c
            for i, c in enumerate(labels)
            if not support[i]
        ]
        + [
            "Hiç tahmin edilmeyen sınıf: " + c
            for i, c in enumerate(labels)
            if not predicted[i]
        ],
    )


def choose_threshold(y, pred, probability, labels, config):
    if len(labels) != 2:
        return 0.5, []
    if probability is None and config["threshold_mode"] != "default":
        raise ProjectError("Eşik seçimi için predict_proba desteği gerekli.")
    if config["threshold_mode"] != "validation_f1":
        return config["threshold"], []
    if set(y) != set(labels):
        raise ProjectError("Validation eşik seçimi iki sınıfı da içermeli.")
    rows = []
    positive = config["positive_class"]
    actual = np.asarray(y) == positive
    for step in range(1, 20):
        threshold = step / 20
        chosen = (
            predictions(pred, probability, labels, positive, float(threshold))
            == positive
        )
        tp = int(np.count_nonzero(actual & chosen))
        den = int(actual.sum() + chosen.sum())
        rows.append(
            dict(
                threshold=round(float(threshold), 2),
                positive_f1=2 * tp / den if den else 0.0,
            )
        )
    winner = max(
        rows,
        key=lambda e: (e["positive_f1"], -abs(e["threshold"] - 0.5), -e["threshold"]),
    )
    return winner["threshold"], rows


def validate_evaluation(e, labels, config):
    matrix = e.get("confusion_matrix")
    if (
        e.get("classes") != labels
        or not isinstance(matrix, list)
        or len(matrix) != len(labels)
        or any(
            not isinstance(row, list)
            or len(row) != len(labels)
            or any(type(v) is not int or v < 0 for v in row)
            for row in matrix
        )
        or sum(map(sum, matrix)) != e["evaluation_n"]
    ):
        raise ProjectError("Karışıklık matrisi sınıf/sayı bağı geçersiz.")
    # Reconstruct pairs only for the four count-based metrics (never invent scores/curves).
    actual = []
    predicted = []
    for i, row in enumerate(matrix):
        for j, n in enumerate(row):
            actual.extend([labels[i]] * n)
            predicted.extend([labels[j]] * n)
    expected = metrics(actual, predicted, None, labels, config, e["scope"])
    if (
        e["metrics"][:4] != expected["metrics"][:4]
        or e["per_class"] != expected["per_class"]
    ):
        raise ProjectError("Sınıf bazlı metrikler karışıklık matrisiyle uyuşmuyor.")
    if e["class_distribution"] != expected["class_distribution"]:
        raise ProjectError("Sınıf dağılımı metrik kapsamıyla uyuşmuyor.")
    curve_labels = [config["positive_class"]] if len(labels) == 2 else labels
    curves = e["curves"]
    if (
        len(e["metrics"]) != 6
        or [m["metric"] for m in e["metrics"][-2:]] != ["roc_auc", "pr_auc"]
        or [c["label"] for c in curves] != curve_labels
    ):
        raise ProjectError("Kategori eğri/metrik kaydı eksik.")
    for curve in curves:
        support = next(
            c["support"] for c in e["per_class"] if c["label"] == curve["label"]
        )
        available = e["probability_supported"] and 0 < support < e["evaluation_n"]
        if (curve["status"] == "valid") != available:
            raise ProjectError("Eğri durumu sınıf/olasılık kapsamıyla uyuşmuyor.")
        if available:
            if any(
                type(curve[k]) not in (float, int)
                or not math.isfinite(curve[k])
                or not 0 <= curve[k] <= 1
                for k in ("roc_auc", "pr_auc", "average_precision")
            ):
                raise ProjectError("Eğri/olasılık desteği geçersiz.")
            for kind in ("roc", "pr"):
                points = curve[kind]
                if not 2 <= len(points) <= 1000 or any(
                    set(p) != {"x", "y"}
                    or any(
                        type(v) not in (float, int)
                        or not math.isfinite(v)
                        or not 0 <= v <= 1
                        for v in p.values()
                    )
                    for p in points
                ):
                    raise ProjectError("Gerçek eğri noktaları geçersiz.")
        elif (
            any(
                curve[k] is not None for k in ("roc_auc", "pr_auc", "average_precision")
            )
            or curve["roc"]
            or curve["pr"]
            or not curve["reason"]
        ):
            raise ProjectError("Geçersiz eğri için sayı veya çizgi uydurulamaz.")
    for m in e["metrics"][-2:]:
        if m["averaging"] != (
            "binary" if len(labels) == 2 else config["averaging"] + "_ovr"
        ):
            raise ProjectError("AUC averaging stratejisi geçersiz.")
        if any(c["status"] != "valid" for c in curves):
            if m["value"] is not None or m["status"] != "undefined" or not m["reason"]:
                raise ProjectError("Eksik sınıf/olasılıkta AUC uydurulamaz.")
        elif len(labels) == 2 or config["averaging"] != "micro":
            value = float(
                np.average(
                    [c[m["metric"]] for c in curves],
                    weights=[c["support"] for c in e["per_class"]]
                    if config["averaging"] == "weighted" and len(labels) != 2
                    else None,
                )
            )
            if m["value"] != value or m["status"] != "valid":
                raise ProjectError("AUC sınıf eğrileriyle uyuşmuyor.")


def validate_run(r, record, versions):
    config = settings(r["classification"])
    labels = r["classes"]
    validate_classes(config, labels)
    if (
        r["preparation_spec"]["purpose"] != "classification"
        or r["selected_model"] not in config["candidates"]
    ):
        raise ProjectError("Kategori model/hedef seçimi geçersiz.")
    if (
        r["interpretation"]
        != (
            "exploratory"
            if r["prior_test_use_ids"]
            else "project_test_not_previously_used"
        )
        or r.get("external_test_use_known") is not False
    ):
        raise ProjectError("Test kullanımının bilinmezliği gizlenemez.")
    decision = r["decision"]
    if (
        decision["model"] != r["selected_model"]
        or decision["positive_class"] != config["positive_class"]
        or decision["mode"] != config["threshold_mode"]
        or decision["cost_note"] != config["cost_note"]
        or decision["selection_scope"] != "validation"
        or not 0.05 <= decision["threshold"] <= 0.95
    ):
        raise ProjectError("Dondurulmuş eşik/sınıf kararı geçersiz.")
    if r.get("details_uri"):
        return
    members = r["plan"]["membership"]
    if decision["validation_row_ids"] != members["validation"]:
        raise ProjectError("Eşik seçimi yalnız validation üyeliğine bağlı olmalı.")
    if r["mode"] == "development":
        if [c["model"] for c in r["comparison"]] != config["candidates"]:
            raise ProjectError("Kategori aday karşılaştırması eksik.")
        winner = (
            next(c for c in r["comparison"] if c["model"] == config["explicit_model"])
            if config.get("explicit_model")
            else max(r["comparison"], key=lambda c: c["cv_f1"])
        )
        if (
            winner["model"] != r["selected_model"]
            or winner["evaluations"] != r["evaluations"]
        ):
            raise ProjectError("Kategori seçimi yalnız geliştirme CV F1 ile yapılmalı.")
        from veri_ufku.modeling.baseline import validate_saved

        for c in r["comparison"]:
            child = dict(r, evaluations=c["evaluations"])
            child.pop("classification")
            validate_saved(
                dict(record, baseline=child, capability_id="model.baseline"), versions
            )
            if c["cv_f1"] != float(
                np.mean([e["metrics"][3]["value"] for e in c["evaluations"][1:]])
            ):
                raise ProjectError("CV F1 fold skorlarıyla uyuşmuyor.")
            for e in c["evaluations"]:
                validate_evaluation(e, labels, config)
        d = r["decision_validation"]
        if (
            d["scope"] != "validation_threshold"
            or sorted(d["fit_row_ids"]) != sorted(members["train"])
            or d["evaluation_n"] != len(members["validation"])
            or d["threshold"] != decision["threshold"]
        ):
            raise ProjectError("Validation eşik hesabı kapsamı geçersiz.")
        if decision["mode"] == "validation_f1":
            grid = d["threshold_candidates"]
            if (
                len(grid) != 19
                or [g["threshold"] for g in grid] != [i / 20 for i in range(1, 20)]
                or any(
                    type(g["positive_f1"]) not in (int, float)
                    or not math.isfinite(g["positive_f1"])
                    or not 0 <= g["positive_f1"] <= 1
                    for g in grid
                )
                or max(
                    grid,
                    key=lambda e: (
                        e["positive_f1"],
                        -abs(e["threshold"] - 0.5),
                        -e["threshold"],
                    ),
                )["threshold"]
                != decision["threshold"]
            ):
                raise ProjectError("Validation eşik seçimi kaydı geçersiz.")
        elif decision["threshold"] != config["threshold"]:
            raise ProjectError("Kullanıcı/varsayılan eşik uyuşmuyor.")
        validate_evaluation(d, labels, config)
    elif (
        r["comparison"]
        or r["decision_validation"] is not None
        or any(
            e["threshold_candidates"] or e["threshold"] != decision["threshold"]
            for e in r["evaluations"]
        )
    ):
        raise ProjectError("Final test model/eşik optimize edemez.")
    for e in r["evaluations"]:
        validate_evaluation(e, labels, config)
