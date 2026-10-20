"""Strict static GraphML/GEXF subset, hardened XML, immutable node/edge rows."""

import json
import math
from dataclasses import replace
from pathlib import Path

import polars as pl
from defusedxml import ElementTree as ET

from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.importers.native import describe
from veri_ufku.importers.sources import verify_sources
from veri_ufku.storage.project_model import ProjectError, uid


def read(raw, kind, control=None):
    control = control or Control()
    if not 1 <= len(raw) <= 2 * 1024**2:
        raise ProjectError("Graph XML2MiB önkontrol sınırı.")
    try:
        root = ET.fromstring(
            raw, forbid_dtd=True, forbid_entities=True, forbid_external=True
        )
    except Exception:
        raise ProjectError(
            "Güvenli Graph XML parse başarısız; DTD/entity/external desteklenmez."
        ) from None
    namespace = (
        "http://graphml.graphdrawing.org/xmlns"
        if kind == "graphml"
        else "http://www.gexf.net/1.2draft"
    )

    def tag(e):
        if not e.tag.startswith("{" + namespace + "}"):
            raise ProjectError(
                "Graph namespace/sürüm desteklenmiyor; GraphML veya GEXF1.2draft gerekir."
            )
        return e.tag.split("}", 1)[1]

    allowed = (
        {"graphml", "key", "default", "graph", "node", "edge", "data", "desc"}
        if kind == "graphml"
        else {
            "gexf",
            "meta",
            "creator",
            "description",
            "graph",
            "nodes",
            "node",
            "edges",
            "edge",
            "attributes",
            "attribute",
            "default",
            "attvalues",
            "attvalue",
        }
    )
    for e in root.iter():
        control.check()
        if tag(e) not in allowed:
            raise ProjectError(
                "Graph XML alt yeteneği desteklenmiyor: nested graph/ports/hyperedge/dynamic/viz sessiz kaybolmaz."
            )
        if any(k in e.attrib for k in ("start", "end", "startopen", "endopen", "pid")):
            raise ProjectError("Dynamic/hierarchical graph burada kapalı.")
    graphs = [e for e in root.iter() if tag(e) == "graph"]
    if len(graphs) != 1:
        raise ProjectError("Tek flat graph gerekli.")
    g = graphs[0]
    if tag(root) != ("graphml" if kind == "graphml" else "gexf"):
        raise ProjectError("Graph root formatı uyuşmuyor.")
    parents = {child: parent for parent in root.iter() for child in parent}
    if parents.get(g) is not root:
        raise ProjectError("Graph yalnız root altında flat olmalı.")
    for e in root.iter():
        t = tag(e)
        if t in ("node", "edge"):
            parent = parents.get(e)
            if (
                kind == "graphml"
                and parent is not g
                or kind == "gexf"
                and (
                    parent is None
                    or tag(parent) != ("nodes" if t == "node" else "edges")
                    or parents.get(parent) is not g
                )
            ):
                raise ProjectError("Nested node/edge graph desteklenmiyor.")
        if t in ("data", "default") and len(e):
            raise ProjectError("Nested attribute XML sessiz metne dönüştürülmez.")
    if kind == "graphml":
        direction = g.get("edgedefault")
    else:
        if g.get("mode", "static") != "static" or root.get("version") != "1.2":
            raise ProjectError("Yalnız static GEXF1.2.")
        direction = g.get("defaultedgetype", "undirected")
    if direction not in ("directed", "undirected"):
        raise ProjectError("Mixed/mutual direction desteklenmiyor.")
    directed = direction == "directed"
    defs = {}
    for e in root.iter():
        if tag(e) in ("key", "attribute"):
            key = e.get("id")
            name = e.get("attr.name", e.get("title", key))
            if not key or key in defs or not name:
                raise ProjectError("Graph attribute key unique olmalı.")
            defaults = [c.text or "" for c in e if tag(c) == "default"]
            if len({d["name"] for d in defs.values()}) != len(defs):
                raise ProjectError("Graph attribute adları unique olmalı.")
            defs[key] = dict(
                name=name,
                default=defaults[0] if defaults else None,
                scope=e.get("for", "all")
                if kind == "graphml"
                else parents[e].get("class", "all"),
                declared_type=e.get("attr.type", e.get("type", "string")),
            )

    def attrs(e):
        out = {
            d["name"]: d["default"]
            for d in defs.values()
            if d["default"] is not None and d["scope"] in ("all", tag(e))
        }
        children = list(e)
        if kind == "gexf":
            children = [v for c in e if tag(c) == "attvalues" for v in c]
        seen_keys = set()
        for child in children:
            t = tag(child)
            if t in ("data", "attvalue"):
                key = child.get("key", child.get("for"))
                if key not in defs:
                    raise ProjectError("Tanımsız graph attribute key.")
                if key in seen_keys or defs[key]["scope"] not in ("all", tag(e)):
                    raise ProjectError("Tekrarlı veya yanlış scope graph attribute.")
                seen_keys.add(key)
                name = defs[key]["name"]
                if name in out and out[name] != defs[key]["default"]:
                    raise ProjectError("Graph attribute tekrar ediyor.")
                out[name] = child.text or "" if t == "data" else child.get("value", "")
        if e.get("label") is not None:
            out["label"] = e.get("label")
        return out

    nodes = [e for e in root.iter() if tag(e) == "node"]
    edges = [e for e in root.iter() if tag(e) == "edge"]
    if not 1 <= len(nodes) <= 256 or len(edges) > 2000:
        raise ProjectError("Graph256node/2000edge önkontrolü.")
    ids = [e.get("id") for e in nodes]
    if any(not isinstance(v, str) or not 1 <= len(v) <= 128 for v in ids) or len(
        set(ids)
    ) != len(ids):
        raise ProjectError("Graph node ID boş/duplicate/aşırı uzun.")
    rows = []
    for e in nodes:
        rows.append(
            dict(
                record_type="node",
                record_id="node:" + e.get("id"),
                node_id=e.get("id"),
                source=None,
                target=None,
                edge_id=None,
                weight=None,
                directed=directed,
                attributes=json.dumps(attrs(e), ensure_ascii=False),
            )
        )
    seen = set()
    for i, e in enumerate(edges):
        control.check()
        if (
            e.get("directed") is not None
            and e.get("directed") not in (("true", "1") if directed else ("false", "0"))
            or e.get("type", direction) != direction
        ):
            raise ProjectError("Mixed edge direction kayıpsız desteklenmiyor.")
        eid = e.get("id")
        synthetic = eid is None
        eid = eid if eid is not None else "vu-generated-edge:" + str(i)
        if not 1 <= len(eid) <= 128 or eid in seen:
            raise ProjectError("Edge ID unique/nonnull olmalı.")
        seen.add(eid)
        if e.get("source") not in ids or e.get("target") not in ids:
            raise ProjectError("Graph edge endpoint node tablosunda yok.")
        a = attrs(e)
        w = e.get("weight", a.get("weight"))
        try:
            weight = float(w) if w is not None else None
        except (ValueError, TypeError):
            raise ProjectError("Graph weight sayısal değil.") from None
        if weight is not None and not math.isfinite(weight):
            raise ProjectError("Nonfinite graph weight.")
        if "vu_edge_id_generated" in a:
            raise ProjectError("Reserved graph metadata attribute çakışıyor.")
        a["vu_edge_id_generated"] = synthetic
        rows.append(
            dict(
                record_type="edge",
                record_id="edge:" + eid,
                node_id=None,
                source=e.get("source"),
                target=e.get("target"),
                edge_id=eid,
                weight=weight,
                directed=directed,
                attributes=json.dumps(a, ensure_ascii=False),
            )
        )
    return pl.DataFrame(
        rows,
        schema_overrides={
            k: pl.String
            for k in (
                "record_type",
                "record_id",
                "node_id",
                "source",
                "target",
                "edge_id",
                "attributes",
            )
        }
        | {"weight": pl.Float64, "directed": pl.Boolean},
    ), dict(
        schema="GraphTable/v1",
        directed=directed,
        format=kind,
        nodes=len(nodes),
        edges=len(edges),
        graph_attributes=attrs(g),
        attribute_definitions=defs,
        policy="static flat graph; attributes preserved as declared text; edge IDs/global direction/multi-edge/isolated nodes retained; missing edge IDs explicitly generated",
    )


class GraphAdapter:
    def __init__(self, kind):
        self.adapter_id = kind

    def validate_source(self, request, control=None):
        if request.adapter_id != self.adapter_id or not request.path.is_file():
            raise ProjectError("Graph captured source bulunamadı.")

    def frame(self, snapshot, control):
        p = Path(snapshot["path"])
        if p.stat().st_size > 2 * 1024**2:
            raise ProjectError("Graph XML2MiB sınırı.")
        return read(p.read_bytes(), self.adapter_id, control)

    def inspect(self, snapshot, settings, control):
        _, meta = self.frame(snapshot, control)
        return dict(formula_behavior=json.dumps(meta, ensure_ascii=False))

    def preview(self, snapshot, settings, control=None):
        f, meta = self.frame(snapshot, control or Control())
        return dict(
            schema=dict(
                names=f.columns,
                original_headers=f.columns,
                types=[str(v) for v in f.dtypes],
                warnings=[meta["policy"]],
            ),
            rows=[
                [str(v) if v is not None else "∅" for v in r]
                for r in f.head(20).iter_rows()
            ],
            bad=[],
            examined=len(f),
            limited=False,
            suggestions=[str(v) for v in f.dtypes],
            settings=settings.data(),
            capture=snapshot,
            diagnostics=dict(scope="full", format_metadata=meta),
            importable=True,
        )

    def import_data(self, snapshot, settings, workspace, control):
        f, meta = self.frame(snapshot, control)
        names = f.columns
        types = [str(v) for v in f.dtypes]
        f = (
            f.with_row_index("__vu_start_line", offset=1)
            .with_columns(pl.col("__vu_start_line").cast(pl.Int64))
            .with_columns(
                pl.Series("__vu_row_id", ["row:" + uid() for _ in range(len(f))]),
                pl.Series(
                    "__vu_source_record_id", ["sr:" + uid() for _ in range(len(f))]
                ),
                pl.col("__vu_start_line").alias("__vu_end_line"),
                pl.concat_str(pl.lit("graph:"), pl.col("record_id")).alias(
                    "__vu_source_locator"
                ),
                pl.lit([], dtype=pl.List(pl.String)).alias("__vu_missing_fields"),
                pl.lit("{}").alias("__vu_expansion_index"),
            )
        )
        path = Path(workspace) / (uid() + ".dataset.parquet")
        f.write_parquet(path)
        saved = replace(
            settings,
            native_schema={n: describe(t) for n, t in f.schema.items()},
            format_metadata=meta,
        )
        verify_sources(snapshot, control)
        control.disk(workspace, force=True)
        return dict(
            path=str(path),
            quarantine=None,
            artifact_fingerprint=hash_artifact(path, control),
            quarantine_fingerprint=None,
            schema=dict(
                names=names,
                original_headers=names,
                types=types,
                warnings=[meta["policy"]],
            ),
            accepted=len(f),
            bad_count=0,
            examined=len(f),
            source_snapshot_id="snapshot:" + uid(),
            settings=saved.data(),
            capture=snapshot,
            adapter_id=self.adapter_id,
            diagnostics=dict(scope="full", format_metadata=meta),
            backend="defusedxml0.7.1/static GraphTable/v1",
        )
