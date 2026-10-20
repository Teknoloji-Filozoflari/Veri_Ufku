"""Bounded NetworkX analyses, complete graph lineage and explicit view-only sampling."""

import copy
import json
import math
import time
from dataclasses import asdict
from datetime import UTC, datetime

import numpy as np
import polars as pl

from veri_ufku.analytics.dataset import checked
from veri_ufku.domain.contracts import Provenance
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.modeling.graph_contracts import GraphSpec, weight_value
from veri_ufku.modeling.recommendation_contracts import identity
from veri_ufku.modeling.validation import digest
from veri_ufku.packaging.optional import LazyModule
from veri_ufku.storage.project_model import ProjectError

nx = LazyModule("networkx", "graphs")


def read_graph(request, spec, control):
    checked(request, control)
    if not 1 <= request["row_count"] <= 2256:
        raise ProjectError("Graph önkontrolü256node/2000edge/2256row.")
    names = {c["id"]: c["name"] for c in request["columns"]}
    if any(
        c and c not in names
        for c in (
            spec.source,
            spec.target,
            spec.node,
            spec.record_type,
            spec.edge_id,
            spec.weight,
            spec.attributes,
        )
    ):
        raise ProjectError("Graph ColumnId kaynak sürümünde yok.")
    frame = pl.read_parquet(request["path"], n_rows=2257)
    if len(frame) != request["row_count"]:
        raise ProjectError("Graph snapshot row count uyuşmuyor.")
    nodes, edges = {}, []

    def add_node(value, lineage, attributes=None, declared=False):
        key = identity(value)
        if key in nodes and declared and nodes[key]["declared"]:
            raise ProjectError("Duplicate declared node ID.")
        n = nodes.setdefault(
            key,
            dict(
                id=key,
                original_id=value,
                source_records=[],
                attributes={},
                declared=False,
            ),
        )
        if lineage not in n["source_records"]:
            n["source_records"].append(lineage)
        if declared:
            n.update(declared=True, attributes=attributes or {})
        return key

    for raw in frame.iter_rows(named=True):
        control.check()
        lineage = dict(
            row_id=raw["__vu_row_id"],
            source_record_id=raw["__vu_source_record_id"],
            dataset_version=request["version_id"],
        )
        kind = raw[names[spec.record_type]] if spec.record_type else "edge"
        attributes = {}
        if spec.attributes:
            try:
                attributes = json.loads(raw[names[spec.attributes]] or "{}")
            except (ValueError, TypeError):
                raise ProjectError("Graph attributes JSON object olmalı.") from None
            if not isinstance(attributes, dict):
                raise ProjectError("Graph attributes object olmalı.")
        if kind == "node":
            add_node(raw[names[spec.node]], lineage, attributes, True)
        elif kind == "edge":
            a = add_node(raw[names[spec.source]], lineage)
            b = add_node(raw[names[spec.target]], lineage)
            eid = (
                identity(raw[names[spec.edge_id]])
                if spec.edge_id
                else identity(raw["__vu_source_record_id"])
            )
            w = raw[names[spec.weight]] if spec.weight else None
            if w is not None and (type(w) not in (int, float) or not math.isfinite(w)):
                raise ProjectError("Graph raw weight finite numeric veya null olmalı.")
            if spec.weight_meaning != "unweighted":
                weight_value(w)
            edges.append(
                dict(
                    id=eid,
                    original_id=raw[names[spec.edge_id]]
                    if spec.edge_id
                    else raw["__vu_source_record_id"],
                    source=a,
                    target=b,
                    weight=w,
                    attributes=attributes,
                    source_records=[lineage],
                )
            )
        else:
            raise ProjectError("Graph record_type node veya edge olmalı.")
    extra = request.get("node_request")
    if extra:
        checked(extra, control)
        nn = {c["id"]: c["name"] for c in extra["columns"]}
        if spec.node_column not in nn or not 1 <= extra["row_count"] <= 256:
            raise ProjectError("Node tablosu ColumnId/256row sınırı.")
        nf = pl.read_parquet(extra["path"], n_rows=257)
        if len(nf) != extra["row_count"]:
            raise ProjectError("Node snapshot row count uyuşmuyor.")
        for r in nf.iter_rows(named=True):
            control.check()
            add_node(
                r[nn[spec.node_column]],
                dict(
                    row_id=r["__vu_row_id"],
                    source_record_id=r["__vu_source_record_id"],
                    dataset_version=extra["version_id"],
                ),
                declared=True,
            )
    if spec.record_type or extra:
        if any(not n["declared"] for n in nodes.values()):
            raise ProjectError("Edge endpoint node tablosunda tanımlı değil.")
    if (
        not nodes
        or len(nodes) > 256
        or len(edges) > 2000
        or len({e["id"] for e in edges}) != len(edges)
    ):
        raise ProjectError("Graph256node/2000edge,unique edge ID önkontrolü.")
    source_meta = request.get("graph_metadata")
    if source_meta and source_meta["directed"] != spec.directed:
        raise ProjectError(
            "Graph dosya yönü farklı; yön dönüşümü ayrı açık işlem gerektirir."
        )
    graph = (nx.MultiDiGraph if spec.directed else nx.MultiGraph)()
    graph.add_nodes_from(nodes)
    pairs = set()
    for e in edges:
        pair = (
            (e["source"], e["target"])
            if spec.directed
            else tuple(sorted((e["source"], e["target"])))
        )
        if pair[0] == pair[1] and spec.self_loops == "reject":
            raise ProjectError("Self-loop var; preserve açık seçilmeli.")
        if pair in pairs and spec.multi_edges == "reject":
            raise ProjectError("Parallel edge var; preserve açık seçilmeli.")
        pairs.add(pair)
        graph.add_edge(
            e["source"],
            e["target"],
            key=e["id"],
            weight=1 if spec.weight_meaning == "unweighted" else e["weight"],
        )
    return graph, list(nodes.values()), edges


def analyze(g, nodes, edges, spec, control):
    control.check()
    result = {}
    if spec.task == "degree":
        result["values"] = [
            dict(
                node=n,
                degree=int(g.degree(n)),
                in_degree=int(g.in_degree(n)) if g.is_directed() else None,
                out_degree=int(g.out_degree(n)) if g.is_directed() else None,
                weighted_degree=float(g.degree(n, weight="weight"))
                if spec.weight_meaning != "unweighted"
                else None,
            )
            for n in g
        ]
        result["definition"] = (
            "edge-incidence counts; parallel edges count separately; undirected self-loop counts2; weighted degree is sum of chosen weights, not importance"
        )
    elif spec.task == "components":
        if g.is_directed():
            result.update(
                weak=[sorted(c) for c in nx.weakly_connected_components(g)],
                strong=[sorted(c) for c in nx.strongly_connected_components(g)],
            )
        else:
            result["connected"] = [sorted(c) for c in nx.connected_components(g)]
    elif spec.task == "shortest":
        a, b = (
            identity(json.loads(spec.path_source)),
            identity(json.loads(spec.path_target)),
        )
        if a not in g or b not in g:
            raise ProjectError(
                "Path endpoint graph'ta yok; unseen node için yol uydurulmaz."
            )
        h = (nx.DiGraph if g.is_directed() else nx.Graph)()
        h.add_nodes_from(g)
        chosen = {}
        for e in edges:
            control.check()
            d = (
                1
                if spec.weight_meaning == "unweighted"
                else 1 / e["weight"]
                if spec.weight_meaning == "strength"
                else e["weight"]
            )
            if (
                not h.has_edge(e["source"], e["target"])
                or d < h[e["source"]][e["target"]]["distance"]
            ):
                h.add_edge(e["source"], e["target"], distance=d, edge_id=e["id"])
        try:
            length, path = nx.single_source_dijkstra(h, a, target=b, weight="distance")
            chosen = [h[u][v]["edge_id"] for u, v in zip(path, path[1:])]
            result.update(
                reachable=True, distance=float(length), path=path, edge_ids=chosen
            )
        except nx.NetworkXNoPath:
            result.update(reachable=False, distance=None, path=[], edge_ids=[])
        result["definition"] = (
            "Dijkstra positive distances; parallel edge minimum distance (first source-order tie); path retains chosen source edge IDs; original graph preserved"
        )
    elif spec.task == "centrality":
        # Explicit bounded power iteration, so cancellation and convergence are visible.
        if spec.weight_meaning == "distance":
            raise ProjectError(
                "PageRank distance kullanmaz; strength/unweighted seçin."
            )
        ids = list(g)
        index = {n: i for i, n in enumerate(ids)}
        a = nx.to_numpy_array(g, nodelist=ids, weight="weight")
        totals = a.sum(axis=1)
        matrix = np.divide(
            a, totals[:, None], out=np.zeros_like(a), where=totals[:, None] != 0
        )
        p = np.full(len(ids), 1 / len(ids))
        converged = False
        for iteration in range(200):
            control.check()
            new = 0.85 * (p @ matrix + p[totals == 0].sum() / len(ids)) + 0.15 / len(
                ids
            )
            residual = float(np.abs(new - p).sum())
            p = new
            if residual < 1e-10:
                converged = True
                break
        result.update(
            values=[dict(node=n, pagerank=float(p[index[n]])) for n in ids],
            converged=converged,
            iterations=iteration + 1,
            residual=residual,
            definition="PageRank alpha0.85,uniform teleport/dangling; strength summed across parallel edges; no importance/causality proof",
        )
        if not converged:
            raise ProjectError(
                "PageRank convergence bütçesi aşıldı; güvenilir badge yok."
            )
    elif spec.task == "community":
        has_parallel = len(edges) > len(
            {tuple(sorted((e["source"], e["target"]))) for e in edges}
        )
        if has_parallel and spec.projection == "reject":
            raise ProjectError(
                "Community simple projection ister; parallel multiplicity kaybını kabul ederek topology/sum_strength açık seçin."
            )
        h = nx.Graph()
        h.add_nodes_from(g)
        for e in edges:
            w = (
                e["weight"]
                if spec.weight_meaning == "strength" and spec.projection != "topology"
                else 1
            )
            if h.has_edge(e["source"], e["target"]):
                if spec.projection == "sum_strength":
                    h[e["source"]][e["target"]]["weight"] += w
            else:
                h.add_edge(e["source"], e["target"], weight=w)
        # Hierarchical generator yields merge boundaries for cooperative cancellation.
        if h.number_of_edges():
            from networkx.algorithms.community.modularity_max import (
                _greedy_modularity_communities_generator,
            )

            gen = _greedy_modularity_communities_generator(
                h, weight="weight", resolution=1
            )
            communities = list(next(gen))
            while True:
                control.check()
                try:
                    gain = next(gen)
                except StopIteration:
                    break
                if gain < 0:
                    break
                communities = list(next(gen))
        else:
            communities = [{n} for n in h]
        result.update(
            communities=[sorted(c) for c in communities],
            modularity=float(nx.community.modularity(h, communities, weight="weight"))
            if h.number_of_edges()
            else None,
            projection=spec.projection,
            projection_edge_count=h.number_of_edges(),
            definition="greedy modularity resolution1 undirected; communities structural not ground truth; original multigraph export unchanged",
        )
    return result


def view(g, nodes, edges, spec, control):
    wanted = {identity(v) for v in spec.filter_nodes} if spec.filter_nodes else set(g)
    if wanted - set(g):
        raise ProjectError("View filter node ID graph'ta yok.")
    eligible = sorted(wanted)
    relevant = [e for e in edges if e["source"] in wanted and e["target"] in wanted]
    if (
        len(eligible) > spec.view_nodes or len(relevant) > spec.view_edges
    ) and not spec.sample_view:
        raise ProjectError(
            "Görsel node/edge bütçesi aşıldı; açık view sample veya filter seçin. Analiz tüm graph üzerinde kalır."
        )
    rng = np.random.default_rng(spec.seed)
    selected = (
        set(
            rng.choice(
                eligible, min(len(eligible), spec.view_nodes), replace=False
            ).tolist()
        )
        if spec.sample_view
        else wanted
    )
    ee = [e for e in relevant if e["source"] in selected and e["target"] in selected]
    if len(ee) > spec.view_edges:
        ee = [
            ee[i]
            for i in sorted(
                rng.choice(len(ee), spec.view_edges, replace=False).tolist()
            )
        ]
    h = g.subgraph(sorted(selected))
    control.check()
    # Fixed bounded32-step spring: check cancellation each step; view topology only.
    if spec.layout == "spring":
        pos = nx.circular_layout(h)
        for _ in range(32):
            control.check()
            pos = nx.spring_layout(
                h, pos=pos, iterations=1, weight=None, seed=spec.seed
            )
    else:
        pos = nx.circular_layout(h)
    nn = [
        dict(n, x=float(pos[n["id"]][0]), y=float(pos[n["id"]][1]))
        for n in nodes
        if n["id"] in selected
    ]
    return dict(
        nodes=nn,
        edges=ee,
        total_nodes=len(g),
        total_edges=len(edges),
        filtered_nodes=len(wanted),
        sampled=len(nn) < len(wanted) or len(ee) < len(relevant),
        sample_consent=spec.sample_view,
        seed=spec.seed,
        layout=spec.layout,
        scope="view only; statistics use complete source graph; exported graph is complete source graph",
        excluded_nodes=len(g) - len(nn),
        excluded_edges=len(edges) - len(ee),
    )


def validate(data):
    GraphSpec.from_dict(data["graph_spec"])
    if (
        data.get("schema") != "GraphRun/v1"
        or data.get("status")
        not in ("running", "completed", "failed", "canceled", "budget_exhausted")
        or data["epoch"] != 0
        or data["curves"]
    ):
        raise ProjectError("GraphRun kapalı schema/status hatası.")
    if data.get("details_uri"):
        if not data.get("lineage_hash"):
            raise ProjectError("Graph artifact lineage hash eksik.")
        return
    if len({n["id"] for n in data["nodes"]}) != len(data["nodes"]) or len(
        {e["id"] for e in data["edges"]}
    ) != len(data["edges"]):
        raise ProjectError("Graph source identity tekrar ediyor.")
    if len(json.dumps(data, allow_nan=False).encode()) > 16 * 1024**2:
        raise ProjectError("Graph safe JSON16MiB sınırı.")


def calculate(request, parameters, work, control=None, checkpoint=lambda value: None):
    control = control or Control()
    start = time.monotonic()
    spec = GraphSpec.from_dict(parameters)
    g, nodes, edges = read_graph(request, spec, control)
    now = datetime.now(UTC).isoformat()
    compat = digest(
        dict(
            source=request["fingerprint"],
            spec=spec.data(),
            node_source=(request.get("node_request") or {}).get("fingerprint"),
        )
    )
    data = dict(
        schema="GraphRun/v1",
        run_id=request["run_id"],
        training_id=request["run_id"],
        dataset_version=request["version_id"],
        origin_version=request["origin_version"],
        source_snapshot_id=request["source_snapshot_id"],
        snapshot_fingerprint=request["fingerprint"],
        seed=spec.seed,
        spec={},
        graph_spec=spec.data(),
        epoch=0,
        curves=[],
        elapsed_seconds=0,
        created_at=now,
        data_access_at=now,
        prior_test_use_ids=request.get("prior_test_use_ids", []),
        nodes=nodes,
        edges=edges,
        analysis={},
        view={},
        plan=dict(
            split_id="graph-descriptive:" + compat,
            membership=dict(train=[], validation=[], test=[]),
            scope="descriptive whole snapshot; no training/predictive final test",
        ),
        tensor_schema={},
        model_weights=None,
        runtime=None,
        compat_id=compat,
        metrics={},
        graph_metadata=copy.deepcopy(request.get("graph_metadata")),
        mode="descriptive_graph",
        environment=dict(networkx=nx.__version__, device="cpu"),
        experiment_capture=request.get("experiment_capture", {}),
        node_source=copy.deepcopy(
            {
                k: v
                for k, v in request.get("node_request", {}).items()
                if k
                in ("version_id", "fingerprint", "source_snapshot_id", "snapshot_uri")
            }
        ),
        warnings=[
            "Centrality/PageRank is structural, not importance or causal influence proof.",
            "Community is a method-dependent partition, not a real class label.",
            "View filter/layout/sample never changes analytical graph; complete identities remain in safe export.",
            "Link prediction and network embedding unavailable here; future-edge features/negative edges require separate temporal training protocol.",
        ],
    )
    versions = tuple(dict.fromkeys([data["dataset_version"], data["origin_version"]]))
    data["provenance"] = asdict(
        Provenance(
            provenance_id="provenance:" + compat,
            dataset_versions=versions,
            config_revision=request.get("config_revision", 0),
            capability_id="model.graph." + spec.task,
            parameters_hash=digest(spec.data()),
            environment=(("networkx", nx.__version__),),
            created_at=now,
            scope=data["plan"]["scope"],
            seed=spec.seed,
            source_snapshot_ids=tuple(
                dict.fromkeys(
                    [
                        request["source_snapshot_id"],
                        *(
                            [request["node_request"]["source_snapshot_id"]]
                            if request.get("node_request")
                            else []
                        ),
                    ]
                )
            ),
            row_lineage_ref=data["plan"]["split_id"],
        )
    )

    def emit(status):
        data.update(status=status, elapsed_seconds=time.monotonic() - start)
        validate(data)
        checkpoint(copy.deepcopy(data))

    emit("running")
    try:
        data["view"] = view(g, nodes, edges, spec, control)
        data["analysis"] = analyze(g, nodes, edges, spec, control)
        control.check()
        emit("completed")
    except Canceled:
        data["analysis"] = {}
        data["view"] = {}
        emit("canceled")
    except ProjectError as e:
        data["analysis"] = {}
        data["view"] = {}
        data["warnings"].append(str(e))
        emit("failed")
    return data
