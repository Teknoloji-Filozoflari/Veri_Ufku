"""Small graph references, strict XML, multi-edge identity and view-scope tests."""

import copy
import json
import threading
from contextlib import closing
from dataclasses import replace

import networkx as nx
import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.importers.delimited import Control, capture, hash_artifact
from veri_ufku.importers.graphs import read
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import detect, get_adapter
from veri_ufku.modeling.graph_contracts import GraphSpec
from veri_ufku.modeling.graphs import analyze, calculate, view
from veri_ufku.modeling.recommendation_contracts import identity
from veri_ufku.storage.graph_store import export_graph
from veri_ufku.storage.neural_store import load, publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore


def xml(kind="graphml"):
    if kind == "graphml":
        return b"""<graphml xmlns="http://graphml.graphdrawing.org/xmlns"><key id="w" for="edge" attr.name="weight" attr.type="double"/><graph id="G" edgedefault="undirected"><node id="a"/><node id="b"/><node id="c"/><node id="isolated"/><edge id="e1" source="a" target="b"><data key="w">2</data></edge><edge id="e2" source="b" target="c"><data key="w">3</data></edge><edge id="e3" source="a" target="c"><data key="w">9</data></edge></graph></graphml>"""
    return b"""<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2"><graph mode="static" defaultedgetype="undirected"><nodes><node id="a" label="A"/><node id="b"/><node id="c"/><node id="isolated"/></nodes><edges><edge id="e1" source="a" target="b" weight="2"/><edge id="e2" source="b" target="c" weight="3"/><edge id="e3" source="a" target="c" weight="9"/></edges></graph></gexf>"""


def fixture(tmp_path, task="degree", kind="graphml"):
    source = tmp_path / ("source." + kind)
    source.write_bytes(xml(kind))
    work = tmp_path / "work"
    work.mkdir()
    snapshot = capture(source, work, any_format=True)
    assert detect(snapshot) == kind
    adapter = get_adapter(kind)
    result = adapter.import_data(
        snapshot, StructuredSettings(adapter_id=kind), work, Control()
    )
    store = ProjectStore.create(tmp_path / "project")
    store.publish_import(result)
    d = store.state["datasets"][-1]
    request = dict(
        path=str(store.path(d["snapshot_uri"])),
        fingerprint=hash_artifact(store.path(d["snapshot_uri"]), Control()),
        columns=d["import_metadata"]["columns"],
        row_count=d["import_metadata"]["row_count"],
        version_id=d["version_id"],
        origin_version=d["version_id"],
        source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
        run_id="run:graph61",
        prior_test_use_ids=[],
        graph_metadata=d["import_metadata"]["settings"]["format_metadata"],
    )
    spec = GraphSpec(
        task=task,
        source=column(request, "source"),
        target=column(request, "target"),
        node=column(request, "node_id"),
        record_type=column(request, "record_type"),
        edge_id=column(request, "edge_id"),
        weight=column(request, "weight"),
        attributes=column(request, "attributes"),
        path_source='"a"',
        path_target='"c"',
    )
    return store, request, work, spec


@pytest.mark.parametrize("kind", ["graphml", "gexf"])
@pytest.mark.parametrize(
    "task", ["degree", "centrality", "components", "shortest", "community", "layout"]
)
def test_real_algorithms_safe_reopen_export(tmp_path, kind, task):
    store, r, w, s = fixture(tmp_path, task, kind)
    if task == "shortest":
        s = replace(s, weight_meaning="distance")
    with closing(store):
        source = (tmp_path / ("source." + kind)).read_bytes()
        out = calculate(r, s.data(), w)
        assert out["status"] == "completed", out["warnings"]
        state = publish(store, store.state, out)
        record = state["results"][-1]
        assert load(store, record) == json.loads(json.dumps(out))
        assert not record["neural"].get("model_package_uri")
        assert "nodes" not in record["neural"]
        path = tmp_path / ("export." + kind)
        export_graph(out, path, kind)
        frame, _ = read(path.read_bytes(), kind)
        assert set(frame.filter(pl.col("record_type") == "node")["node_id"]) == {
            "a",
            "b",
            "c",
            "isolated",
        }
        ee = frame.filter(pl.col("record_type") == "edge")
        assert set(ee["edge_id"]) == {"e1", "e2", "e3"} and sorted(ee["weight"]) == [
            2,
            3,
            9,
        ]
        for payload in frame["attributes"]:
            decoded = json.loads(payload)
            assert json.loads(decoded["vu_payload"])["source_records"]
        with pytest.raises(ProjectError):
            export_graph(out, path, kind)
        assert source == (tmp_path / ("source." + kind)).read_bytes()
    with closing(ProjectStore.open(tmp_path / "project")) as reopened:
        assert load(reopened, record)["status"] == "completed"
        reopened.path(record["neural"]["details_uri"]).write_bytes(b"corrupt")
        with pytest.raises(ProjectError, match="hash"):
            load(reopened, record)


def test_shortest_reference_weight_and_unreachable(tmp_path):
    store, r, w, s = fixture(tmp_path, "shortest")
    with closing(store):
        out = calculate(r, replace(s, weight_meaning="distance").data(), w)
        a = out["analysis"]
        assert (
            a["path"] == [identity("a"), identity("b"), identity("c")]
            and a["distance"] == 5
        )
        assert a["edge_ids"] == [identity("e1"), identity("e2")]
        unreachable = calculate(r, replace(s, path_target='"isolated"').data(), w)[
            "analysis"
        ]
        assert unreachable == dict(
            reachable=False,
            distance=None,
            path=[],
            edge_ids=[],
            definition=unreachable["definition"],
        )
        with pytest.raises(ProjectError, match="Strength"):
            GraphSpec.from_dict(replace(s, weight_meaning="strength").data())
        inverse = calculate(
            r,
            replace(
                s, weight_meaning="strength", strength_to_distance="reciprocal"
            ).data(),
            w,
        )
        assert inverse["analysis"]["distance"] == pytest.approx(1 / 9)


def test_hand_centrality_components_degree():
    g = nx.MultiDiGraph()
    g.add_edges_from([("a", "b"), ("b", "a")])
    g.add_node("i")
    spec = GraphSpec(source="s", target="t", directed=True, task="centrality")
    out = analyze(g, [], [], spec, Control())
    values = {v["node"]: v["pagerank"] for v in out["values"]}
    # Symmetric two-cycle + isolated: i=(.15/3)/(1-.85/3)=3/43; a=b=20/43.
    assert values["i"] == pytest.approx(3 / 43, abs=1e-9)
    assert values["a"] == pytest.approx(20 / 43, abs=1e-9)
    expected = nx.pagerank(g, tol=1e-12)
    assert values == pytest.approx(expected, abs=1e-9)
    components = analyze(g, [], [], replace(spec, task="components"), Control())
    assert sorted(map(len, components["strong"])) == [1, 2]
    ug = nx.MultiGraph()
    ug.add_edge("a", "a")
    ug.add_edge("a", "b")
    ug.add_edge("a", "b")
    degrees = analyze(
        ug, [], [], replace(spec, task="degree", directed=False), Control()
    )["values"]
    assert {v["node"]: v["degree"] for v in degrees} == {"a": 4, "b": 2}


def test_multiedge_community_projection_and_identity(tmp_path):
    store, r, w, s = fixture(tmp_path, "community")
    with closing(store):
        f = pl.read_parquet(r["path"])
        extra = f.filter(pl.col("edge_id") == "e1").with_columns(
            pl.lit("parallel").alias("edge_id"),
            pl.lit("row:parallel").alias("__vu_row_id"),
            pl.lit("sr:parallel").alias("__vu_source_record_id"),
        )
        f = pl.concat([f, extra])
        f.write_parquet(r["path"])
        r.update(row_count=len(f), fingerprint=hash_artifact(r["path"], Control()))
        with pytest.raises(ProjectError, match="Parallel"):
            calculate(r, s.data(), w)
        out = calculate(r, replace(s, multi_edges="preserve").data(), w)
        assert out["status"] == "failed" and "projection" in out["warnings"][-1]
        out = calculate(
            r, replace(s, multi_edges="preserve", projection="topology").data(), w
        )
        assert (
            out["status"] == "completed"
            and len(out["edges"]) == 4
            and out["analysis"]["projection_edge_count"] == 3
        )
        assert sorted(map(len, out["analysis"]["communities"])) == [1, 3]
        dest = tmp_path / "full.json"
        export_graph(out, dest, "json")
        assert len(json.loads(dest.read_text())["edges"]) == 4
        # Dijkstra retains the chosen source edge ID, rather than losing all parallel identities.
        out = calculate(
            r,
            replace(
                s, task="shortest", multi_edges="preserve", weight_meaning="distance"
            ).data(),
            w,
        )
        assert out["analysis"]["edge_ids"][0] == identity("e1")


def test_view_budget_filter_and_explicit_sample(tmp_path):
    store, r, w, s = fixture(tmp_path, "degree")
    with closing(store):
        failed = calculate(r, replace(s, view_nodes=2).data(), w)
        assert failed["status"] == "failed" and "bütçe" in failed["warnings"][-1]
        sampled = calculate(r, replace(s, view_nodes=2, sample_view=True).data(), w)
        assert sampled["view"]["sampled"] and len(sampled["view"]["nodes"]) == 2
        assert len(sampled["analysis"]["values"]) == 4
        again = calculate(r, replace(s, view_nodes=2, sample_view=True).data(), w)
        assert [n["id"] for n in sampled["view"]["nodes"]] == [
            n["id"] for n in again["view"]["nodes"]
        ]
        filtered = calculate(r, replace(s, filter_nodes=("isolated",)).data(), w)
        assert len(filtered["view"]["nodes"]) == 1 and not filtered["view"]["edges"]
        assert len(filtered["analysis"]["values"]) == 4
        export_graph(sampled, tmp_path / "complete.json", "json")
        assert len(json.loads((tmp_path / "complete.json").read_text())["nodes"]) == 4


@pytest.mark.parametrize(
    "bad",
    [
        dict(task="link_prediction"),
        dict(task="embedding"),
        dict(view_nodes=0),
        dict(seed=True),
        dict(weight_meaning="unknown"),
        dict(directed=True, task="community"),
        dict(weight_meaning="distance", task="community"),
        dict(task="shortest", path_source="not-json"),
    ],
)
def test_invalid_and_unsupported_specs(bad):
    with pytest.raises(ProjectError):
        GraphSpec.from_dict(GraphSpec(source="s", target="t", weight="w").data() | bad)


@pytest.mark.parametrize("kind", ["graphml", "gexf"])
def test_strict_xml_rejects_entities_dynamic_and_bad_ids(kind):
    raw = xml(kind)
    with pytest.raises(ProjectError):
        read(b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>' + raw, kind)
    with pytest.raises(ProjectError):
        read(raw.replace(b'id="b"', b'id="a"', 1), kind)
    with pytest.raises(ProjectError):
        read(raw.replace(b'source="a"', b'source="missing"', 1), kind)
    if kind == "graphml":
        with pytest.raises(ProjectError):
            read(
                raw.replace(b'<node id="a"/>', b'<node id="a"><port name="p"/></node>'),
                kind,
            )
    else:
        with pytest.raises(ProjectError):
            read(raw.replace(b'mode="static"', b'mode="dynamic"'), kind)


def test_cooperative_cancel_at_publication(tmp_path):
    store, r, w, s = fixture(tmp_path)
    with closing(store):
        event = threading.Event()

        def checkpoint(v):
            if v["status"] == "running":
                event.set()

        result = calculate(r, s.data(), w, Control(event), checkpoint)
        assert result["status"] == "canceled" and not result["analysis"]
        publish(store, store.state, result)


def test_separate_node_table_and_typed_ids(tmp_path):
    store, r, w = prepare(tmp_path, pl.DataFrame(dict(s=[1], t=[2], eid=[10])))
    r.update(
        run_id="run:separate61", origin_version=r["version_id"], prior_test_use_ids=[]
    )
    second = tmp_path / "nodes"
    second.mkdir()
    node_store, nr, _ = prepare(second, pl.DataFrame(dict(node=[1, 2, 3])))
    try:
        spec = GraphSpec(
            source=column(r, "s"),
            target=column(r, "t"),
            edge_id=column(r, "eid"),
            node_column=column(nr, "node"),
        )
        out = calculate(r | dict(node_request=nr), spec.data(), w)
        assert out["status"] == "completed" and len(out["nodes"]) == 3
        assert {n["original_id"] for n in out["nodes"]} == {1, 2, 3}
        export_graph(out, tmp_path / "integer.json", "json")
        assert all(
            type(n["original_id"]) is int
            for n in json.loads((tmp_path / "integer.json").read_text())["nodes"]
        )
        with pytest.raises(ProjectError, match="Integer|string|XML"):
            export_graph(out, tmp_path / "typed.graphml", "graphml")
    finally:
        store.close()
        node_store.close()


def test_directed_multigraph_xml_identity_and_loops(tmp_path):
    for kind in ("graphml", "gexf"):
        raw = xml(kind).replace(b"undirected", b"directed")
        if kind == "graphml":
            raw = raw.replace(
                b"</graph>",
                b'<edge id="parallel" source="a" target="b"/><edge id="loop" source="a" target="a"/></graph>',
            )
        else:
            raw = raw.replace(
                b"</edges>",
                b'<edge id="parallel" source="a" target="b"/><edge id="loop" source="a" target="a"/></edges>',
            )
        f, meta = read(raw, kind)
        assert meta["directed"] and meta["nodes"] == 4 and meta["edges"] == 5
        assert set(f.filter(pl.col("record_type") == "edge")["edge_id"]) == {
            "e1",
            "e2",
            "e3",
            "parallel",
            "loop",
        }


def test_directed_unreachable_and_strength_reject(tmp_path):
    store, r, w, s = fixture(tmp_path, "shortest")
    with closing(store):
        r["graph_metadata"]["directed"] = True
        out = calculate(
            r, replace(s, directed=True, path_source='"c"', path_target='"a"').data(), w
        )
        assert out["analysis"]["reachable"] is False
        out = calculate(
            r,
            replace(
                s, task="centrality", directed=True, weight_meaning="distance"
            ).data(),
            w,
        )
        assert out["status"] == "failed" and "distance" in out["warnings"][-1]
        with pytest.raises(ProjectError, match="yönü"):
            calculate(r, s.data(), w)


@pytest.mark.parametrize("bad", [0, -1, float("inf"), None])
def test_invalid_distance_weights(tmp_path, bad):
    store, r, w, s = fixture(tmp_path, "shortest")
    with closing(store):
        f = pl.read_parquet(r["path"]).with_columns(
            pl.when(pl.col("record_type") == "edge")
            .then(pl.lit(bad, dtype=pl.Float64))
            .otherwise(pl.col("weight"))
            .alias("weight")
        )
        f.write_parquet(r["path"])
        r["fingerprint"] = hash_artifact(r["path"], Control())
        with pytest.raises(ProjectError):
            calculate(r, replace(s, weight_meaning="distance").data(), w)


def test_cooperative_cancel_in_pagerank_and_spring():
    from veri_ufku.jobs.workers import Canceled

    class Limited(Control):
        count = 0

        def check(self):
            self.count += 1
            if self.count == 5:
                raise Canceled()

    g = nx.MultiDiGraph()
    g.add_edges_from([(str(i), str(i + 1)) for i in range(20)])
    with pytest.raises(Canceled):
        analyze(
            g,
            [],
            [],
            GraphSpec(task="centrality", source="s", target="t", directed=True),
            Limited(),
        )
    nodes = [dict(id=n, original_id=n) for n in g]
    with pytest.raises(Canceled):
        view(
            g,
            nodes,
            [],
            GraphSpec(
                task="layout", source="s", target="t", directed=True, layout="spring"
            ),
            Limited(),
        )


def test_xml_nested_invalid_scope_and_empty_ids_rejected():
    raw = xml()
    for altered in (
        raw.replace(b'<node id="a"/>', b'<node id="a"><node id="nested"/></node>'),
        raw.replace(b'key="w">2', b'key="w"><nested/>2'),
        raw.replace(b'for="edge"', b'for="node"'),
        raw.replace(b'id="e1"', b'id=""'),
    ):
        with pytest.raises(ProjectError):
            read(altered, "graphml")


def test_multiple_source_node_table_published_and_journal(tmp_path):

    store, r, w, s = fixture(tmp_path, "degree")
    with closing(store):
        source = tmp_path / "nodes.parquet"
        pl.DataFrame(dict(node=["a", "b", "c", "isolated"])).write_parquet(source)
        snapshot = capture(source, w, any_format=True)
        imported = get_adapter("parquet").import_data(
            snapshot, StructuredSettings(adapter_id="parquet"), w, Control()
        )
        store.publish_import(imported)
        d = store.state["datasets"][-1]
        nr = dict(
            path=str(store.path(d["snapshot_uri"])),
            fingerprint=hash_artifact(store.path(d["snapshot_uri"]), Control()),
            columns=d["import_metadata"]["columns"],
            version_id=d["version_id"],
            source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
            snapshot_uri=d["snapshot_uri"],
            row_count=4,
        )
        source = tmp_path / "edges.parquet"
        pl.read_parquet(r["path"]).filter(pl.col("record_type") == "edge").select(
            "source", "target", "edge_id", "weight", "attributes"
        ).write_parquet(source)
        snap = capture(source, w, any_format=True)
        imp = get_adapter("parquet").import_data(
            snap, StructuredSettings(adapter_id="parquet"), w, Control()
        )
        store.publish_import(imp)
        ed = store.state["datasets"][-1]
        r.update(
            path=str(store.path(ed["snapshot_uri"])),
            fingerprint=hash_artifact(store.path(ed["snapshot_uri"]), Control()),
            columns=ed["import_metadata"]["columns"],
            row_count=3,
            version_id=ed["version_id"],
            source_snapshot_id=ed["import_metadata"]["source_snapshot_id"],
            node_request=nr,
            origin_version=nr["version_id"],
            graph_metadata=None,
        )
        s = GraphSpec(
            source=column(r, "source"),
            target=column(r, "target"),
            edge_id=column(r, "edge_id"),
            node_column=column(nr, "node"),
        )
        out = calculate(r, s.data(), w)
        assert (
            len(out["provenance"]["dataset_versions"]) == 2
            and len(out["provenance"]["source_snapshot_ids"]) == 2
        )
        assert all(
            any(v["dataset_version"] == nr["version_id"] for v in n["source_records"])
            for n in out["nodes"]
        )
        state = publish(store, store.state, out)
        record = state["results"][-1]
        assert set(record["dataset_version_ids"]) == {r["version_id"], nr["version_id"]}
        assert load(store, record)["node_source"]["version_id"] == nr["version_id"]
        from veri_ufku.storage.experiment_store import rows
        from veri_ufku.storage.neural_store import validate_journal

        assert rows(store)[-1]["params"]["graph_spec"]
        fake = copy.deepcopy(state)
        fake["results"][-1]["neural"]["node_source"]["source_snapshot_id"] = (
            "snapshot:wrong"
        )
        with pytest.raises(ProjectError, match="journal"):
            validate_journal(fake, {v["version_id"]: v for v in state["datasets"]})
