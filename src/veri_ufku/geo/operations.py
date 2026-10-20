"""Declarative spatial operations through the existing preview/publish worker."""

import json
import math
from pathlib import Path

import numpy as np
import polars as pl
import shapely

from veri_ufku.geo import OPERATION_KINDS
from veri_ufku.geo.core import (
    crs,
    geographic_check,
    geometries,
    inspect,
    metric,
    numeric_values,
    reproject,
)
from veri_ufku.storage.project_model import ProjectError, entity_id, uid

KINDS = OPERATION_KINDS


def metadata(request):
    parts = request.get("format_metadata", {}).get("parts", [])
    return parts[0].get("geospatial", {}) if len(parts) == 1 else {}


def parameters(request, kind, ids, p, columns):
    expected = {
        "geo_coordinates": {"crs", "output_id", "output_name"},
        "geo_assign": {"crs"},
        "geo_reproject": {"crs", "target_crs"},
        "geo_repair": {"crs"},
        "geo_buffer": {"crs", "distance"},
        "geo_area": {"crs", "output_id", "output_name"},
        "geo_distance": {"crs", "reference_wkt", "output_id", "output_name"},
        "geo_clip": {"crs", "mask_wkt"},
        "geo_join": {
            "crs",
            "secondary_version_id",
            "secondary_geometry",
            "predicate",
            "output_id",
            "output_name",
        },
        "geo_block": {"crs", "block_size", "folds", "seed", "output_id", "output_name"},
        "geo_moran": {
            "crs",
            "neighbors",
            "threshold",
            "standardization",
            "permutations",
            "seed",
        },
    }[kind]
    if set(p) != expected or len(ids) != (
        2 if kind in ("geo_coordinates", "geo_moran") else 1
    ):
        raise ProjectError("Mekânsal işlem input şeması/parametre alanları geçersiz.")
    system = crs(p["crs"])
    stored = metadata(request).get("crs")
    if (
        stored
        and kind not in ("geo_assign", "geo_coordinates")
        and not system.equals(crs(stored), ignore_axis_order=True)
    ):
        raise ProjectError(
            "Seçilen kaynak CRS sürüm metadata ile uyuşmuyor; açık CRS atama işlemi ayrı."
        )
    names = {c["id"]: c for c in columns}
    if kind != "geo_coordinates" and names[ids[0]]["type"] != "String":
        raise ProjectError("Geometri String WKT sütunu ister.")
    if kind == "geo_coordinates" and any(
        not names[i]["type"].startswith(("Float", "Int", "UInt")) for i in ids
    ):
        raise ProjectError("Koordinat kolonları sayısal olmalı.")
    if kind == "geo_moran" and not names[ids[1]]["type"].startswith(
        ("Float", "Int", "UInt", "Decimal")
    ):
        raise ProjectError(
            "Moran ölçüm kolonu sayısal olmalı; açık tür dönüşümü seçin."
        )
    if "output_id" in p:
        entity_id(p["output_id"], "col")
        if (
            p["output_id"] in names
            or not isinstance(p["output_name"], str)
            or not p["output_name"]
            or p["output_name"].startswith("__vu_")
            or any(c["name"] == p["output_name"] for c in columns)
        ):
            raise ProjectError("Yeni mekânsal sütun adı/ColumnId geçersiz.")
        columns.append(
            dict(
                id=p["output_id"],
                name=p["output_name"],
                type="Float64" if kind in ("geo_area", "geo_distance") else "String",
                original_name=p["output_name"],
            )
        )
    if kind == "geo_reproject":
        crs(p["target_crs"])
    if kind == "geo_join":
        secondary = request.get("secondary")
        if (
            not secondary
            or secondary["version_id"] != p["secondary_version_id"]
            or p["secondary_geometry"] not in {c["id"] for c in secondary["columns"]}
        ):
            raise ProjectError("Spatial join ikinci geometri/sürüm seçimi eksik.")
        if p["predicate"] not in ("intersects", "within", "contains"):
            raise ProjectError("Join intersects/within/contains açık seçilmeli.")
    if kind in ("geo_buffer", "geo_block"):
        key = "distance" if kind == "geo_buffer" else "block_size"
        if type(p[key]) not in (int, float) or not math.isfinite(p[key]) or p[key] <= 0:
            raise ProjectError("Pozitif sonlu metre büyüklüğü seçin.")
    if kind == "geo_block" and (
        type(p["folds"]) is not int or not 2 <= p["folds"] <= 10
    ):
        raise ProjectError("Spatial block2–10 fold ister.")
    if kind == "geo_moran" and (
        p["neighbors"] not in ("queen", "rook", "distance")
        or p["standardization"] not in ("binary", "row")
        or type(p["permutations"]) is not int
        or not 0 <= p["permutations"] <= 999
    ):
        raise ProjectError("Moran komşuluk/binary-row/permutation seçimi geçersiz.")
    if "seed" in p and (type(p["seed"]) is not int or not 0 <= p["seed"] <= 2**32 - 1):
        raise ProjectError("Seed tam sayı0–2³²−1 ister.")
    return columns


def execute(request, spec, workspace, control):
    p = spec.parameters
    kind = spec.kind
    if (
        request["row_count"] > 10000
        or request["fingerprint"]["size"] > control.budget.ram_bytes // 4
    ):
        raise ProjectError("Mekânsal10000satır/RAM admission sınırı.")
    frame = pl.read_parquet(request["path"])
    names = {c["id"]: c["name"] for c in request["columns"]}
    c = crs(p["crs"])
    diagnostics = dict(
        warnings=[
            "CRS atama dönüşüm değildir. Geographic derecede metre hesabı yok; kaynak korunur."
        ],
        modified_rows=0,
        changed_columns=1,
    )
    relation = None
    if kind == "geo_coordinates":
        x, y = [numeric_values(frame[names[i]].to_list()) for i in spec.column_ids]
        gs = [shapely.Point(a, b) for a, b in zip(x, y)]
        geographic_check(gs, c)
        frame = frame.with_columns(
            pl.Series(
                p["output_name"], shapely.to_wkt(gs, rounding_precision=-1).tolist()
            )
        )
        geometry = p["output_name"]
    else:
        geometry = names[spec.column_ids[0]]
        gs = geometries(
            frame[geometry].to_list(), valid=kind not in ("geo_repair", "geo_assign")
        )
        geographic_check(gs, c)
    original = [g.wkt for g in gs]
    if kind == "geo_reproject":
        gs, operation = reproject(gs, p["crs"], p["target_crs"])
        c = crs(p["target_crs"])
        diagnostics["transformation"] = operation
    elif kind == "geo_repair":
        gs = [shapely.make_valid(g, method="linework") for g in gs]
        diagnostics["repair"] = dict(
            method="GEOS make_valid linework",
            before_types=[g.geom_type for g in geometries(original, False)],
            after_types=[g.geom_type for g in gs],
            changed=sum(a != b.wkt for a, b in zip(original, gs)),
            notice="May change geometry type/split/collapse. Preview only until explicit apply; original version/RowId retained.",
        )
        if any(g.is_empty for g in gs):
            raise ProjectError("Repair empty çıktı; kaynak değişmedi.")
    elif kind in ("geo_buffer", "geo_area", "geo_distance", "geo_block"):
        metric(gs, c)
        if kind == "geo_buffer":
            gs = [g.buffer(p["distance"], quad_segs=16) for g in gs]
            diagnostics["buffer"] = dict(
                distance_m=p["distance"],
                quad_segs=16,
                method="planar projected; approximate arcs",
            )
        elif kind == "geo_area":
            frame = frame.with_columns(
                pl.Series(p["output_name"], [g.area for g in gs])
            )
            diagnostics["unit"] = "m²; projected area distortion depends on CRS"
        elif kind == "geo_distance":
            ref = geometries([p["reference_wkt"]])[0]
            metric([ref], c)
            frame = frame.with_columns(
                pl.Series(p["output_name"], [g.distance(ref) for g in gs])
            )
            diagnostics["unit"] = "m; planar minimum geometry distance"
        else:
            if len(gs) > 2000:
                raise ProjectError("Spatial block plan en fazla2000satır.")
            blocks = [
                (
                    math.floor(g.centroid.x / p["block_size"]),
                    math.floor(g.centroid.y / p["block_size"]),
                )
                for g in gs
            ]
            unique = sorted(set(blocks))
            if len(unique) < p["folds"]:
                raise ProjectError("Fold sayısından az mekânsal block var.")
            rng = np.random.default_rng(p["seed"])
            rng.shuffle(unique)
            mapping = {b: i % p["folds"] for i, b in enumerate(unique)}
            labels = [f"{b[0]}:{b[1]}" for b in blocks]
            frame = frame.with_columns(pl.Series(p["output_name"], labels))
            ids = frame["__vu_row_id"].to_list()
            diagnostics["spatial_validation"] = dict(
                block_size_m=p["block_size"],
                origin=[0, 0],
                seed=p["seed"],
                method="grid centroid blocks; deterministic shuffled block allocation",
                folds=[
                    dict(
                        fold=k,
                        train_row_ids=[
                            r for r, b in zip(ids, blocks) if mapping[b] != k
                        ],
                        validation_row_ids=[
                            r for r, b in zip(ids, blocks) if mapping[b] == k
                        ],
                    )
                    for k in range(p["folds"])
                ],
                block_to_fold={str(b): v for b, v in mapping.items()},
                limitation="Adjacent blocks may remain dependent; no buffer zone. Choose size from process scale, not validation score. Random split does not resolve spatial dependence. Use generated block column as GROUP in model validation; this plan itself fits no model.",
            )
    elif kind == "geo_clip":
        mask = geometries([p["mask_wkt"]])[0]
        geographic_check([mask], c)
        gs = [g.intersection(mask) for g in gs]
        keep = [i for i, g in enumerate(gs) if not g.is_empty]
        frame = frame[keep]
        gs = [gs[i] for i in keep]
        if not gs:
            raise ProjectError("Clip tüm kayıtları boş yaptı; yayın yok.")
        diagnostics["clip"] = dict(
            removed=len(original) - len(gs),
            policy="empty intersections removed explicitly; surviving RowIds unchanged",
        )
    elif kind == "geo_join":
        other = request["secondary"]
        if (
            other["row_count"] > 10000
            or other["fingerprint"]["size"] > control.budget.ram_bytes // 4
        ):
            raise ProjectError("Join ikinci kaynak admission sınırı.")
        meta = metadata(other)
        if not meta.get("crs") or not c.equals(
            crs(meta["crs"]), ignore_axis_order=True
        ):
            raise ProjectError(
                "Spatial join aynı CRS ister; ikinci kaynak açık reproject gerektirir."
            )
        field = next(
            v["name"] for v in other["columns"] if v["id"] == p["secondary_geometry"]
        )
        right = pl.read_parquet(other["path"])
        rg = geometries(right[field].to_list())
        geographic_check(rg, c)
        tree = shapely.STRtree(rg)
        matches = []
        edges = []
        for i, g in enumerate(gs):
            control.check()
            hits = sorted(tree.query(g, predicate=p["predicate"]).tolist())
            matches.append(json.dumps([right["__vu_row_id"][j] for j in hits]))
            edges.extend(
                dict(
                    output_row_id=frame["__vu_row_id"][i],
                    input_row_id=right["__vu_row_id"][j],
                    input_version_id=other["version_id"],
                    input_source_record_id=right["__vu_source_record_id"][j],
                    side="secondary",
                    occurrence=j,
                )
                for j in hits
            )
            if len(edges) > 100000:
                raise ProjectError("Join100000membership sınırı; kısmi yayın yok.")
        frame = frame.with_columns(pl.Series(p["output_name"], matches))
        diagnostics["matching"] = dict(
            predicate=p["predicate"],
            matches=len(edges),
            unmatched=sum(x == "[]" for x in matches),
            multiple=sum(len(json.loads(x)) > 1 for x in matches),
            policy="all matching right RowIds in JSON list; no nearest/fuzzy name match; boundaries depend on predicate; source identities retained",
        )
        if edges:
            relation = Path(workspace) / (uid() + ".geo-membership.parquet")
            pl.DataFrame(edges).write_parquet(relation)
    elif kind == "geo_moran":
        if len(gs) > 500:
            raise ProjectError("Moran500satır/neighborhood önkontrol sınırı.")
        vals = frame[names[spec.column_ids[1]]].to_list()
        report = moran(gs, vals, c, p, control)
        diagnostics["moran"] = report
    if kind in ("geo_reproject", "geo_repair", "geo_buffer", "geo_clip"):
        frame = frame.with_columns(
            pl.Series(geometry, shapely.to_wkt(gs, rounding_precision=-1).tolist())
        )
        diagnostics["modified_rows"] = len(gs)
    diagnostics["geospatial"] = inspect([g.wkt for g in gs], c.to_wkt())
    diagnostics["geospatial"]["geometry_column"] = geometry
    path = Path(workspace) / (uid() + ".geo.parquet")
    frame.write_parquet(path)
    control.check()
    return spec, path, diagnostics, relation


def moran(gs, values, system, p, control):
    n = len(gs)
    values = np.asarray(numeric_values(np.asarray(values).tolist()))
    if values.ndim != 1 or len(values) != n:
        raise ProjectError("Moran geometri ve ölçüm sayısı uyuşmalı.")
    if n < 3 or not np.isfinite(values).all() or (values == values[0]).all():
        raise ProjectError("Moran en az3 sonlu/sabit olmayan ölçüm ister.")
    if p["neighbors"] == "distance":
        metric(gs, system)
        if (
            not isinstance(p["threshold"], (int, float))
            or not math.isfinite(p["threshold"])
            or p["threshold"] <= 0
        ):
            raise ProjectError("Distance komşuluk pozitif metre threshold ister.")
    elif any(g.geom_type not in ("Polygon", "MultiPolygon") for g in gs):
        raise ProjectError("Queen/rook polygon geometry ister.")
    w = np.zeros((n, n))
    for i, g in enumerate(gs):
        control.check()
        for j in range(i + 1, n):
            if p["neighbors"] == "distance":
                match = g.distance(gs[j]) <= p["threshold"]
            else:
                shared = g.boundary.intersection(gs[j].boundary)
                match = (
                    not shared.is_empty
                    if p["neighbors"] == "queen"
                    else shared.length > 0
                )
            if match:
                w[i, j] = w[j, i] = 1
    degrees = w.sum(axis=1)
    if (degrees == 0).any():
        raise ProjectError(
            "İzole komşuluk kaydı var; threshold/graph değiştirin, sessiz dışlama yok."
        )
    if p["standardization"] == "row":
        w = w / degrees[:, None]
    # Moran's I is invariant to scale. Power-of-two scaling preserves ordinary
    # inputs exactly and bounds both centering and quadratic products. Remove
    # a common offset before averaging so representable small differences survive.
    _, exponent = np.frexp(np.max(np.abs(values)))
    scaled = np.ldexp(values, -int(exponent))
    shifted = scaled - scaled[0]
    z = shifted - shifted.mean()
    s0 = float(w.sum())

    def statistic(v):
        return float(n / s0 * (v @ w @ v) / (v @ v))

    observed = statistic(z)
    expected = -1 / (n - 1)
    rng = np.random.default_rng(p["seed"])
    extreme = 0
    for _ in range(p["permutations"]):
        control.check()
        extreme += abs(statistic(rng.permutation(z)) - expected) >= abs(
            observed - expected
        )
    return dict(
        I=observed,
        expected=expected,
        n=n,
        S0=s0,
        neighbors=p["neighbors"],
        threshold=p["threshold"],
        standardization=p["standardization"],
        degrees=degrees.tolist(),
        weights=w.tolist(),
        permutations=p["permutations"],
        seed=p["seed"],
        p_two_sided=(extreme + 1) / (p["permutations"] + 1)
        if p["permutations"]
        else None,
        limitation="Permutation exchangeability assumption; not causal. MAUP/neighborhood selection changes result.",
    )
