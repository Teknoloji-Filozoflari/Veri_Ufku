"""Explicit complete-graph export; safe JSON or static XML, never view sampling."""

import json
import os
from pathlib import Path
from xml.etree import ElementTree as ET

from veri_ufku.modeling.graphs import validate
from veri_ufku.storage.project_model import ProjectError


def export_graph(data, destination, fmt):
    validate(data)
    if data["status"] != "completed" or fmt not in ("json", "graphml", "gexf"):
        raise ProjectError("Completed graph ve json/graphml/gexf formatı gerekir.")
    path = Path(destination)
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ProjectError("Yeni mutlak export dosyası seçin; üzerine yazılmaz.")
    payload = dict(
        schema="GraphExport/v1",
        dataset_version=data["dataset_version"],
        node_source=data.get("node_source"),
        source_snapshot_id=data["source_snapshot_id"],
        directed=data["graph_spec"]["directed"],
        weight_meaning=data["graph_spec"]["weight_meaning"],
        nodes=data["nodes"],
        edges=data["edges"],
        scope="complete source graph; original identities and source record links; no view filter/sample",
        warnings=data["warnings"],
        graph_metadata=data.get("graph_metadata"),
    )
    if fmt == "json":
        raw = json.dumps(
            payload, ensure_ascii=False, allow_nan=False, indent=2
        ).encode()
    else:
        if any(type(n["original_id"]) is not str for n in data["nodes"]) or any(
            type(e["original_id"]) is not str for e in data["edges"]
        ):
            raise ProjectError(
                "XML ID string olmalı; integer/string tipi kaybını önlemek için JSON export seçin."
            )
        direction = "directed" if payload["directed"] else "undirected"
        if fmt == "graphml":
            ns = "http://graphml.graphdrawing.org/xmlns"
            ET.register_namespace("", ns)
            root = ET.Element("{" + ns + "}graphml")
            for key in ("weight", "vu_payload"):
                ET.SubElement(
                    root,
                    "{" + ns + "}key",
                    {
                        "id": key,
                        "for": "all",
                        "attr.name": key,
                        "attr.type": "double" if key == "weight" else "string",
                    },
                )
            graph = ET.SubElement(
                root, "{" + ns + "}graph", {"id": "G", "edgedefault": direction}
            )

            def attrs(e, source):
                ET.SubElement(
                    e, "{" + ns + "}data", {"key": "vu_payload"}
                ).text = json.dumps(source, ensure_ascii=False, allow_nan=False)
                if source.get("weight") is not None:
                    ET.SubElement(e, "{" + ns + "}data", {"key": "weight"}).text = str(
                        source["weight"]
                    )

            node_parent = edge_parent = graph
        else:
            ns = "http://www.gexf.net/1.2draft"
            ET.register_namespace("", ns)
            root = ET.Element("{" + ns + "}gexf", {"version": "1.2"})
            graph = ET.SubElement(
                root,
                "{" + ns + "}graph",
                {"mode": "static", "defaultedgetype": direction},
            )
            # GEXF1.2 IDs are scoped by node/edge attribute class.
            definitions = ET.SubElement(
                graph, "{" + ns + "}attributes", {"class": "node"}
            )
            ET.SubElement(
                definitions,
                "{" + ns + "}attribute",
                {"id": "node_payload", "title": "vu_payload", "type": "string"},
            )
            definitions = ET.SubElement(
                graph, "{" + ns + "}attributes", {"class": "edge"}
            )
            ET.SubElement(
                definitions,
                "{" + ns + "}attribute",
                {"id": "edge_payload", "title": "vu_payload", "type": "string"},
            )
            node_parent = ET.SubElement(graph, "{" + ns + "}nodes")
            edge_parent = ET.SubElement(graph, "{" + ns + "}edges")

            def attrs(e, source):
                values = ET.SubElement(e, "{" + ns + "}attvalues")
                ET.SubElement(
                    values,
                    "{" + ns + "}attvalue",
                    {
                        "for": "node_payload"
                        if "original_id" in source and "source" not in source
                        else "edge_payload",
                        "value": json.dumps(
                            source, ensure_ascii=False, allow_nan=False
                        ),
                    },
                )

        mapping = {n["id"]: n["original_id"] for n in data["nodes"]}
        for node in data["nodes"]:
            el = ET.SubElement(
                node_parent, "{" + ns + "}node", {"id": node["original_id"]}
            )
            attrs(el, node)
        for edge in data["edges"]:
            aa = dict(
                id=edge["original_id"],
                source=mapping[edge["source"]],
                target=mapping[edge["target"]],
            )
            if fmt == "gexf" and edge["weight"] is not None:
                aa["weight"] = str(edge["weight"])
            el = ET.SubElement(edge_parent, "{" + ns + "}edge", aa)
            attrs(el, edge)
        raw = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if len(raw) > 2 * 1024**2:
        raise ProjectError("Graph export2MiB sınırı.")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
