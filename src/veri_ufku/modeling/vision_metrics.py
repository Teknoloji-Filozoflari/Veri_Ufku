"""Explicit half-open box matching/AP and pixel confusion aggregation; no COCO claim."""

import numpy as np

from veri_ufku.storage.project_model import ProjectError


def iou(a, b):
    for box in (a, b):
        if (
            len(box) != 4
            or any(type(v) not in (int, float) or not np.isfinite(v) for v in box)
            or not box[0] < box[2]
            or not box[1] < box[3]
        ):
            raise ProjectError("IoU bbox geçersiz.")
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) - max(a[1], b[1])
    )
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union


def detection_metrics(ground, predicted, labels, thresholds):
    out = []
    for threshold in thresholds:
        if not 0 < threshold <= 1:
            raise ProjectError("IoU threshold0..1 olmalı.")
        for label in labels:
            gt = [g for g in ground if g["label"] == label]
            pred = sorted(
                [p for p in predicted if p["label"] == label],
                key=lambda p: (-p["score"], p["image_id"], p["id"]),
            )
            used = set()
            matches = []
            tp = []
            fp = []
            for p in pred:
                candidates = [
                    (iou(p["xyxy"], g["xyxy"]), j, g)
                    for j, g in enumerate(gt)
                    if g["image_id"] == p["image_id"] and j not in used
                ]
                best = (
                    max(candidates, key=lambda x: (x[0], -x[1])) if candidates else None
                )
                hit = best is not None and best[0] >= threshold
                if hit:
                    used.add(best[1])
                tp.append(int(hit))
                fp.append(int(not hit))
                matches.append(
                    dict(
                        prediction_id=p["id"],
                        image_id=p["image_id"],
                        ground_id=best[2]["id"] if hit else None,
                        iou=best[0] if best else 0,
                        matched=hit,
                    )
                )
            if gt:
                if pred:
                    t = np.cumsum(tp)
                    f = np.cumsum(fp)
                    recall = t / len(gt)
                    precision = t / (t + f)
                    r = np.concatenate(([0], recall, [1]))
                    q = np.concatenate(([0], precision, [0]))
                    q = np.maximum.accumulate(q[::-1])[::-1]
                    ap = float(np.sum(np.diff(r) * q[1:]))
                else:
                    ap = 0.0
            else:
                ap = None
            out.append(
                dict(
                    label=label,
                    threshold=threshold,
                    ap=ap,
                    gt_n=len(gt),
                    prediction_n=len(pred),
                    tp=sum(tp),
                    fp=sum(fp),
                    fn=len(gt) - len(used),
                    matches=matches,
                )
            )
    aps = [r["ap"] for r in out if r["ap"] is not None]
    return dict(
        map=float(np.mean(aps)) if aps else None,
        by_class_threshold=out,
        definition="all-point interpolated precision envelope; global score-ranked per-class, per-image one-to-one greedy best IoU; absent-GT class undefined/excluded; not COCO 101-point/area/crowd mAP",
    )


def segmentation_metrics(ground, predicted, labels):
    if len(ground) != len(predicted) or not ground:
        raise ProjectError("Mask eşleşmesi boş/uyumsuz.")
    matrix = np.zeros((len(labels), len(labels)), dtype=np.int64)
    for g, p in zip(ground, predicted, strict=True):
        g = np.asarray(g)
        p = np.asarray(p)
        if (
            g.shape != p.shape
            or g.ndim != 2
            or not np.issubdtype(g.dtype, np.integer)
            or not np.issubdtype(p.dtype, np.integer)
            or min(g.min(), p.min()) < 0
            or max(g.max(), p.max()) >= len(labels)
        ):
            raise ProjectError("Mask shape/class index geçersiz.")
        matrix += np.bincount(
            (g.ravel() * len(labels) + p.ravel()), minlength=len(labels) ** 2
        ).reshape(matrix.shape)
    values = []
    for i, label in enumerate(labels):
        tp = int(matrix[i, i])
        fn = int(matrix[i].sum() - tp)
        fp = int(matrix[:, i].sum() - tp)
        union = tp + fp + fn
        values.append(
            dict(
                label=label,
                tp=tp,
                fp=fp,
                fn=fn,
                iou=tp / union if union else None,
                dice=2 * tp / (2 * tp + fp + fn) if union else None,
            )
        )
    fg = [v for v in values[1:] if v["iou"] is not None]
    return dict(
        confusion=matrix.tolist(),
        by_class=values,
        macro_foreground_iou=float(np.mean([v["iou"] for v in fg])) if fg else None,
        macro_foreground_dice=float(np.mean([v["dice"] for v in fg])) if fg else None,
        pixels=int(matrix.sum()),
        images=len(ground),
        definition="pooled pixel confusion over images; macro over present foreground classes; class0 background reported separately; absent-both undefined, never perfect1",
    )
