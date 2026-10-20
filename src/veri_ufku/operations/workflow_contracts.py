"""Typed DAG recipes extend OperationSpec; port types live in Capability registry."""

import copy
import itertools
import json
import math
import re
from dataclasses import asdict, dataclass, field

from veri_ufku.storage.project_model import ProjectError, entity_id

KINDS = tuple(
    "workflow_" + k
    for k in ("source", "quality", "analysis", "train", "predict", "export")
)


def parameters(request, kind, columns, params):
    """Build hook for the existing OperationSpec contract, not a new operation schema."""
    ids = {c["id"] for c in columns}
    k = kind.removeprefix("workflow_")
    expected = {
        "source": {"version_id"},
        "quality": {"column", "fail_on_null"},
        "analysis": {"column", "ddof"},
        "train": {"feature", "target", "confirmed"},
        "predict": {"prediction_column"},
        "export": {"format"},
    }
    if k not in expected or set(params) != expected[k]:
        raise ProjectError("Workflow operation kapalı parametre şeması geçersiz.")
    for key in ("column", "feature", "target"):
        if key in params and params[key] not in ids:
            raise ProjectError("Workflow ColumnId giriş şemasında yok.")
    if k == "source":
        entity_id(params["version_id"], "dv")
    if k == "quality" and type(params["fail_on_null"]) is not bool:
        raise ProjectError("Quality explicit fail_on_null boolean gerekir.")
    if k == "analysis" and (
        type(params["ddof"]) is not int or params["ddof"] not in (0, 1)
    ):
        raise ProjectError("Analysis ddof0/1 gerekir.")
    if k == "train" and (
        params["confirmed"] is not True or params["feature"] == params["target"]
    ):
        raise ProjectError(
            "OLS feature/target farklı ve assumptions explicit confirmed olmalı."
        )
    if k == "predict":
        entity_id(params["prediction_column"], "col")
        if params["prediction_column"] in ids or any(
            c["name"] == "prediction" for c in columns
        ):
            raise ProjectError("Prediction kolonu var; sessiz overwrite yok.")
        return columns + [
            dict(
                id=params["prediction_column"],
                name="prediction",
                original_name="prediction",
                type="Float64",
            )
        ]
    if k == "export" and params["format"] != "parquet":
        raise ProjectError("Workflow export yalnız native Parquet.")
    return columns if k in ("source", "quality") else []


@dataclass(frozen=True)
class DAGSpec:
    nodes: list
    cases: list = field(default_factory=list)
    sweep: list = field(default_factory=list)
    retries: int = 0
    seed: int = 64
    schema: str = "TypedDAG/v1"

    @classmethod
    def from_dict(cls, raw):
        try:
            s = cls(**copy.deepcopy(raw))
        except (TypeError, ValueError):
            raise ProjectError("TypedDAG kapalı şema geçersiz.") from None
        if (
            s.schema != "TypedDAG/v1"
            or not isinstance(s.nodes, list)
            or not 1 <= len(s.nodes) <= 24
            or type(s.retries) is not int
            or not 0 <= s.retries <= 2
            or type(s.seed) is not int
            or not 0 <= s.seed < 2**32
        ):
            raise ProjectError("DAG24node/retry0–2/seed sınırı.")
        from veri_ufku.domain.capabilities import get_capability

        nodes = {}
        for n in s.nodes:
            if (
                not isinstance(n, dict)
                or set(n)
                != {"id", "kind", "inputs", "after", "params", "method_version"}
                or not isinstance(n["id"], str)
                or not re.fullmatch("[a-z][a-z0-9-]{0,31}", n["id"])
                or n["id"] in nodes
                or n["kind"]
                not in (
                    "source",
                    "transform",
                    "quality",
                    "analysis",
                    "train",
                    "predict",
                    "export",
                )
                or type(n["method_version"]) is not int
                or n["method_version"] != 1
                or not isinstance(n["inputs"], dict)
                or not isinstance(n["after"], list)
                or not all(isinstance(p, str) for p in n["after"])
                or len(set(n["after"])) != len(n["after"])
                or not isinstance(n["params"], dict)
            ):
                raise ProjectError("DAG node kimlik/kind/version şeması geçersiz.")
            cap = get_capability("workflow." + n["kind"])
            if set(n["inputs"]) != {r.name for r in cap.inputs.roles}:
                raise ProjectError("DAG required input port eksik/fazla.")
            for edge in n["inputs"].values():
                if (
                    not isinstance(edge, dict)
                    or set(edge) != {"node", "port"}
                    or not all(isinstance(v, str) for v in edge.values())
                ):
                    raise ProjectError("DAG edge node/port şeması geçersiz.")
            nodes[n["id"]] = n
        for n in s.nodes:
            cap = get_capability("workflow." + n["kind"])
            for role in cap.inputs.roles:
                edge = n["inputs"][role.name]
                parent = nodes.get(edge["node"])
                if not parent:
                    raise ProjectError("DAG dependency node bulunamadı.")
                output = get_capability("workflow." + parent["kind"]).output_type
                port = "data" if output == "dataset" else output
                if edge["port"] != port or output not in role.dtypes:
                    raise ProjectError("DAG port/type uyuşmuyor.")
            if any(p not in nodes for p in n["after"]):
                raise ProjectError("DAG after dependency bilinmiyor.")
            if any(nodes[p]["kind"] == "export" for p in n["after"]):
                raise ProjectError(
                    "Export terminal side effect; after dependency olarak kullanılamaz."
                )
        remaining = set(nodes)
        order = []
        while remaining:
            ready = sorted(k for k in remaining if dependencies(nodes[k]) <= set(order))
            if not ready:
                raise ProjectError("DAG cycle reddedildi.")
            order += ready
            remaining -= set(ready)
        s.expanded()
        if len(json.dumps(raw, allow_nan=False).encode()) > 65536:
            raise ProjectError("DAG64KiB sınırı.")
        return s

    def expanded(self):
        if (
            not isinstance(self.cases, list)
            or not isinstance(self.sweep, list)
            or len(self.cases) > 8
            or len(self.sweep) > 3
        ):
            raise ProjectError("Batch8case/sweep3 sınırı.")
        sources = {n["id"] for n in self.nodes if n["kind"] == "source"}
        ids = {n["id"] for n in self.nodes}
        seen = set()
        cases = self.cases or [dict(id="default", sources={}, columns={})]
        for c in cases:
            if (
                not isinstance(c, dict)
                or set(c) != {"id", "sources", "columns"}
                or not re.fullmatch("[a-z][a-z0-9-]{0,31}", c["id"])
                or c["id"] in seen
                or not isinstance(c["sources"], dict)
                or not set(c["sources"]) <= sources
                or not isinstance(c["columns"], dict)
                or not set(c["columns"]) <= sources
            ):
                raise ProjectError(
                    "Batch explicit source/ColumnId mapping şeması geçersiz."
                )
            seen.add(c["id"])
            for v in c["sources"].values():
                entity_id(v, "dv")
            for mapping in c["columns"].values():
                if not isinstance(mapping, dict) or len(set(mapping.values())) != len(
                    mapping
                ):
                    raise ProjectError("Batch bijective ColumnId mapping gerekir.")
                for a, b in mapping.items():
                    entity_id(a, "col")
                    entity_id(b, "col")
        sweep_keys = set()
        for sweep in self.sweep:
            if (
                not isinstance(sweep, dict)
                or set(sweep) != {"node", "parameter", "values"}
                or sweep["node"] not in ids
                or sweep["parameter"] != "ddof"
                or next(n for n in self.nodes if n["id"] == sweep["node"])["kind"]
                != "analysis"
                or not isinstance(sweep["values"], list)
                or not 1 <= len(sweep["values"]) <= 2
                or any(type(v) is not int or v not in (0, 1) for v in sweep["values"])
            ):
                raise ProjectError(
                    "Sweep yalnız analysis.ddof0/1; açık bounded değer listesi."
                )
            key = (sweep["node"], sweep["parameter"])
            if key in sweep_keys or len(set(sweep["values"])) != len(sweep["values"]):
                raise ProjectError("Sweep duplicate parameter/value reddi.")
            sweep_keys.add(key)
        count = len(cases) * math.prod(len(v["values"]) for v in self.sweep)
        if count > 8:
            raise ProjectError("Batch×sweep8run bütçesi.")
        result = []
        for case in cases:
            for i, values in enumerate(
                itertools.product(*(s["values"] for s in self.sweep))
            ):
                nodes = copy.deepcopy(self.nodes)
                for sweep, value in zip(self.sweep, values, strict=True):
                    next(n for n in nodes if n["id"] == sweep["node"])["params"][
                        sweep["parameter"]
                    ] = value
                result.append(
                    dict(
                        case=copy.deepcopy(case),
                        id=case["id"] + ("-s" + str(i) if self.sweep else ""),
                        nodes=nodes,
                    )
                )
        return result

    def data(self):
        return asdict(self)


def dependencies(node):
    return {e["node"] for e in node["inputs"].values()} | set(node["after"])


def order(nodes):
    result = []
    remaining = {n["id"]: n for n in nodes}
    while remaining:
        ready = sorted(
            k for k, n in remaining.items() if dependencies(n) <= set(result)
        )
        if not ready:
            raise ProjectError("DAG cycle.")
        for k in ready:
            result.append(k)
            del remaining[k]
    return result
