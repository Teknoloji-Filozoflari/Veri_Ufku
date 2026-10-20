"""Phase75 explicit numeric witnesses; synthetic data, no general release certification."""

import hashlib
import json
import math
from contextlib import closing

import numpy as np
import polars as pl
from test_dataset import column, prepare


def witness(record_property, method, data, actual, reference, atol, assumption):
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    np.testing.assert_allclose(actual, reference, rtol=0, atol=atol)
    record_property(
        "scientific_witness",
        json.dumps(
            dict(
                method=method,
                input_sha256=hashlib.sha256(raw).hexdigest(),
                input_serialization="UTF8 JSON sorted keys; mathematical fixture, not storage bytes",
                actual=np.asarray(actual).tolist(),
                reference=np.asarray(reference).tolist(),
                absolute_tolerance=atol,
                relative_tolerance=0,
                assumptions=assumption,
                scope="small synthetic fixture; not all models/backends or human validation",
            ),
            ensure_ascii=False,
        ),
    )


def test_table_histogram_reference(tmp_path, record_property):
    from test_charts import run

    data = [1.0, 2.0, 3.0, 4.0]
    store, r, work = prepare(tmp_path, pl.DataFrame(dict(x=data)))
    with closing(store):
        out = run(r, work, "histogram", x=column(r, "x"), bins=2)
        witness(
            record_property,
            "histogram exact bins",
            data,
            [p["n"] for p in out["points"]],
            [2, 2],
            0,
            "finite observations; edges1/2.5/4; last bin closed",
        )


def test_weight_and_rubin_reference(tmp_path, record_property):
    from test_missing_sampling import calculate, rubin_pool, spec

    data = dict(x=[10.0, 20.0], weight=[1.0, 3.0])
    store, r, work = prepare(tmp_path, pl.DataFrame(data))
    with closing(store):
        s = spec(
            r, "weighted_mean", weight_type="frequency", weight=column(r, "weight")
        )
        a = calculate(r, s, work)["advanced"]
        pooled = rubin_pool([[1.0], [2.0], [3.0]], [[[4.0]]] * 3, 20)
        witness(
            record_property,
            "frequency mean + Rubin covariance",
            data,
            [a["estimate"], a["variance"], pooled["total_covariance"][0][0]],
            [17.5, 6.25, 16 / 3],
            1e-12,
            "frequency replication; independent observations; MI within4 between1 m3 complete df20",
        )


def test_bayes_conjugate_reference(record_property):
    from test_bayes import AnalysisSpec, conjugate, plan

    data = [1] * 8 + [0] * 2
    a = conjugate(
        np.array(data),
        AnalysisSpec(path="bayes", method="bayes_beta_binomial", x=""),
        plan(),
    )
    witness(
        record_property,
        "beta binomial analytic posterior",
        data,
        [a["alpha"], a["beta"], a["mean"]],
        [9, 3, 0.75],
        1e-14,
        "iid Bernoulli likelihood and Beta(1,1) prior; analytic, not MCMC convergence",
    )


def test_probability_order_reference(record_property):
    from veri_ufku.modeling.uncertainty import probability_report

    labels = ["z", "a", "z", "a"]
    p = [[0.8, 0.2], [0.3, 0.7], [0.6, 0.4], [0.1, 0.9]]
    out = probability_report(np.array(labels), np.array(p), ["z", "a"], 4)
    witness(
        record_property,
        "label-aware Brier/log loss",
        dict(labels=labels, probabilities=p),
        [out["brier"], out["log_loss"]],
        [
            (0.2**2 + 0.3**2 + 0.4**2 + 0.1**2) / 4,
            -sum(map(math.log, [0.8, 0.7, 0.6, 0.9])) / 4,
        ],
        1e-12,
        "binary label order z,a; Brier not calibration alone; no fitted calibrator here",
    )


def test_causal_reference(tmp_path, record_property):
    from test_causal import Control, calculate, fixture, recipe

    data = fixture("causal_randomized")
    store, r, work = prepare(tmp_path, data)
    with closing(store):
        out = calculate(r, recipe(r, "causal_randomized"), work, Control())[
            "causal_analysis"
        ]
        witness(
            record_property,
            "randomized ATE",
            data.to_dict(as_series=False),
            out["effect"]["estimate"],
            2.0,
            0.2,
            "synthetic randomized treatment; consistency/no interference; finite sample tolerance .2",
        )


def test_survival_reference(tmp_path, record_property):
    from test_survival import Control, calculate, fixture, recipe

    data = fixture()
    store, r, work = prepare(tmp_path, data)
    with closing(store):
        curve = calculate(r, recipe(r), work, Control())["survival_analysis"]["curves"][
            0
        ]["curve"]
        witness(
            record_property,
            "Kaplan Meier risk sets",
            data.to_dict(as_series=False),
            [v["survival"] for v in curve],
            [0.8, 0.6, 0.3],
            1e-12,
            "right censoring; independent censoring; observed risk counts10/8/4; not competing incidence",
        )


def test_vision_reference(record_property):
    from veri_ufku.modeling.vision_metrics import iou, segmentation_metrics

    g = np.array([[1, 0], [1, 0]], dtype=np.uint8)
    p = np.array([[1, 1], [0, 0]], dtype=np.uint8)
    m = segmentation_metrics([g], [p], ["background", "object"])["by_class"][1]
    witness(
        record_property,
        "bbox and segmentation IoU",
        dict(truth=g.tolist(), prediction=p.tolist()),
        [iou([0, 0, 2, 2], [1, 0, 3, 2]), m["iou"], m["dice"]],
        [1 / 3, 1 / 3, 0.5],
        1e-12,
        "binary mask foreground; intersection1 union3; axis-aligned xyxy boxes",
    )


def test_audio_reference(record_property):
    from veri_ufku.modeling.audio_contracts import AudioSpec
    from veri_ufku.modeling.audio_features import features

    signal = 0.4 * np.sin(2 * np.pi * 1000 * np.arange(4096) / 16000)
    _, v = features(signal, 16000, AudioSpec(n_fft=256, hop=256))
    psd = 10 ** (np.array(v["spectrogram_db"])[0] / 10)
    witness(
        record_property,
        "windowed sine PSD",
        signal.tolist(),
        [v["frequency_hz"][int(np.argmax(psd))], psd.sum() * 16000 / 256],
        [1000, 0.08],
        1e-8,
        "regular16kHz; integer-bin sine1kHz amplitude.4; integrated one-sided PSD=A²/2",
    )


def test_ranking_reference(record_property):
    from veri_ufku.modeling.recommendation import metrics

    m = metrics(["bad", "a", "b"], {"a", "b", "c", "d"}, 3)
    witness(
        record_property,
        "topK full relevance denominator",
        dict(ranked=["bad", "a", "b"], relevant=["a", "b", "c", "d"], k=3),
        [m["precision"], m["recall"], m["ap"]],
        [2 / 3, 0.5, (1 / 2 + 2 / 3) / 3],
        1e-12,
        "fixed candidate universe; four relevant items; AP denominator min(K,n_relevant)=3",
    )


def test_graph_reference(record_property):
    import networkx as nx

    from veri_ufku.importers.delimited import Control
    from veri_ufku.modeling.graph_contracts import GraphSpec
    from veri_ufku.modeling.graphs import analyze

    g = nx.MultiDiGraph([("a", "b"), ("b", "a")])
    g.add_node("i")
    out = analyze(
        g,
        [],
        [],
        GraphSpec(source="s", target="t", directed=True, task="centrality"),
        Control(),
    )
    v = {r["node"]: r["pagerank"] for r in out["values"]}
    witness(
        record_property,
        "PageRank dangling node",
        dict(edges=[["a", "b"], ["b", "a"]], isolated="i", alpha=0.85),
        [v["a"], v["b"], v["i"]],
        [20 / 43, 20 / 43, 3 / 43],
        1e-9,
        "uniform teleport and dangling redistribution; centrality not causal importance",
    )


def test_experiment_reference(tmp_path, record_property):
    from test_experiments import calculate, frame, recipe

    data = frame()
    store, r, work = prepare(tmp_path, data)
    with closing(store):
        effect = calculate(r, recipe(r), work)["experiment_analysis"]["effect"]
        values = data["outcome"].to_numpy()
        # Independent Welch standard error from the fixed20/20 assignment fixture.
        control, treated = values[:20], values[20:]
        delta = float(treated.mean() - control.mean())
        witness(
            record_property,
            "experiment absolute mean difference",
            data.to_dict(as_series=False),
            effect["absolute_effect"],
            delta,
            1e-12,
            "fixed-horizon independent arms20/20; randomization is user assumption, not verified from data",
        )


def test_spatial_reference(record_property):
    import shapely

    from veri_ufku.geo.core import reproject

    data = dict(
        points=[[0, 0], [1, 0]], source="EPSG:4326", target="EPSG:3857", always_xy=True
    )
    values, details = reproject(
        [shapely.Point(0, 0), shapely.Point(1, 0)], "EPSG:4326", "EPSG:3857"
    )
    assert details["always_xy"] and not details["network"]
    witness(
        record_property,
        "CRS coordinate transformation",
        data,
        [values[1].x, values[1].y],
        [111319.49079327357, 0],
        1e-6,
        "always XY; ellipsoidal registry transform; WebMercator is not approved general metric-distance CRS",
    )


def test_nlp_reference(tmp_path, record_property):
    from test_nlp import TextSpec, bundle, embedding

    model = bundle(tmp_path / "model")
    left, counts = embedding("güzel iyi unknown", model, TextSpec("col:x"))
    right, _ = embedding("mükemmel", model, TextSpec("col:x"))
    witness(
        record_property,
        "local Turkish embedding cosine",
        dict(
            left="güzel iyi unknown",
            right="mükemmel",
            model="synthetic phase55 local fixture",
        ),
        [float(left @ right), counts["oov_token_count"]],
        [1, 1],
        1e-12,
        "fixed local toy vectors; cosine is not probability or real retrieval-quality evidence",
    )


def test_workflow_reference(tmp_path, record_property):
    from test_workflow import recipe, run

    data = dict(x=[1.0, 2.0, 3.0, 4.0], y=[2.0, 4.0, 6.0, 8.0])
    store, r, _ = prepare(tmp_path, pl.DataFrame(data))
    with closing(store):
        spec = recipe(r)
        first = run(store, spec, tmp_path)
        node = next(n for n in first["nodes"] if n["node"] == "summary")
        witness(
            record_property,
            "typed DAG native profile",
            data,
            float(node["value"]["report"]["numeric"]["mean"]),
            2.5,
            1e-14,
            "immutable source, ddof1, all4finite; cache validation separately tested",
        )
