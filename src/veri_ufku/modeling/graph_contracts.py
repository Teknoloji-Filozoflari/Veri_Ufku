"""Graph semantics: strength never silently becomes distance."""

import json
import math
from dataclasses import asdict, dataclass

from veri_ufku.modeling.recommendation_contracts import identity
from veri_ufku.storage.project_model import ProjectError


@dataclass(frozen=True)
class GraphSpec:
    task: str = "degree"
    source: str = ""
    target: str = ""
    node: str = ""
    record_type: str = ""
    edge_id: str = ""
    weight: str = ""
    attributes: str = ""
    node_column: str = ""
    directed: bool = False
    multi_edges: str = "reject"
    self_loops: str = "reject"
    weight_meaning: str = "unweighted"
    strength_to_distance: str = "reject"
    projection: str = "reject"
    path_source: str = '"a"'
    path_target: str = '"b"'
    layout: str = "circular"
    filter_nodes: tuple = ()
    view_nodes: int = 64
    view_edges: int = 256
    sample_view: bool = False
    seed: int = 61

    @classmethod
    def from_dict(cls, raw):
        try:
            s = cls(**{**raw, "filter_nodes": tuple(raw.get("filter_nodes", ()))})
        except (ValueError, TypeError):
            raise ProjectError("Graph kapalı tarif şeması geçersiz.") from None
        if (
            s.task
            not in (
                "degree",
                "centrality",
                "components",
                "shortest",
                "community",
                "layout",
            )
            or s.multi_edges not in ("reject", "preserve")
            or s.self_loops not in ("reject", "preserve")
            or s.weight_meaning not in ("unweighted", "distance", "strength")
            or s.strength_to_distance not in ("reject", "reciprocal")
            or s.projection not in ("reject", "sum_strength", "topology")
            or s.layout not in ("circular", "spring")
        ):
            raise ProjectError(
                "Graph task/yön/weight/projection/layout seçimi geçersiz."
            )
        for k in (
            "source",
            "target",
            "node",
            "record_type",
            "edge_id",
            "weight",
            "attributes",
            "node_column",
            "path_source",
            "path_target",
        ):
            if not isinstance(getattr(s, k), str) or len(getattr(s, k)) > 512:
                raise ProjectError("Graph kolon/kimlik tarifi geçersiz.")
        if (
            not s.source
            or not s.target
            or s.source == s.target
            or s.record_type
            and not s.node
            or s.weight_meaning != "unweighted"
            and not s.weight
        ):
            raise ProjectError(
                "Ayrı source/target; birleşik node/edge şemasında node/type; ağırlık anlamı için weight seçin."
            )
        roles = [
            v
            for v in (
                s.source,
                s.target,
                s.node,
                s.record_type,
                s.edge_id,
                s.weight,
                s.attributes,
            )
            if v
        ]
        if len(set(roles)) != len(roles):
            raise ProjectError("Graph kolon rolleri ayrı olmalı.")
        if any(type(getattr(s, k)) is not bool for k in ("directed", "sample_view")):
            raise ProjectError("Graph direction/sample açık boolean olmalı.")
        for k, lo, hi in (
            ("view_nodes", 1, 128),
            ("view_edges", 1, 512),
            ("seed", 0, 2**32 - 1),
        ):
            v = getattr(s, k)
            if type(v) is not int or not lo <= v <= hi:
                raise ProjectError("Graph view/seed bütçesi geçersiz.")
        if len(s.filter_nodes) > 256:
            raise ProjectError("Graph filter256node sınırı.")
        for v in s.filter_nodes:
            identity(v)
        if s.task == "shortest":
            try:
                identity(json.loads(s.path_source))
                identity(json.loads(s.path_target))
            except (ValueError, TypeError):
                raise ProjectError(
                    "Path endpoint JSON scalar typed ID olmalı."
                ) from None
            if (
                s.weight_meaning == "strength"
                and s.strength_to_distance != "reciprocal"
            ):
                raise ProjectError(
                    "Strength distance değildir; shortest için açık reciprocal1/strength seçin veya reddedin."
                )
        if s.task == "community" and (s.directed or s.weight_meaning == "distance"):
            raise ProjectError(
                "Community bounded greedy modularity yalnız undirected strength/unweighted; directed/distance için dönüşüm otomatik yapılmaz."
            )
        if s.projection == "sum_strength" and s.weight_meaning != "strength":
            raise ProjectError("sum_strength yalnız strength anlamında.")
        return s

    def data(self):
        return asdict(self)


def weight_value(v):
    if type(v) not in (int, float) or not math.isfinite(v) or not 0 < v <= 1e12:
        raise ProjectError(
            "Seçili graph weight finite ve strictly positive olmalı; negatif/zero sessiz düzeltilmez."
        )
    return float(v)
