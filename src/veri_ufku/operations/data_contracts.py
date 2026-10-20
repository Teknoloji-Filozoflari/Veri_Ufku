"""Closed declarative dataset contracts and explicit human identity decisions."""

import copy
from datetime import datetime

import polars as pl

from veri_ufku.operations.types import dtype_of
from veri_ufku.storage.project_model import ProjectError, entity_id

KINDS = {
    "schema_contract",
    "contract_check",
    "entity_candidates",
    "category_candidates",
    "entity_merge",
    "category_map",
}
LEVELS = ("nominal", "ordinal", "interval", "ratio", "unknown")
RULES = {
    "range": "row",
    "nullable": "row",
    "ordinal": "row",
    "unique": "column",
    "type": "column",
    "unit": "column",
    "row_count": "table",
    "foreign_key": "cross_table",
}


def require(condition, message="Veri sözleşmesi alanları geçersiz."):
    if not condition:
        raise ProjectError(message)


def contract_validate(value, columns):
    require(isinstance(value, dict) and set(value) == {"schema_version", "rules"})
    require(type(value["schema_version"]) is int and value["schema_version"] == 1)
    require(isinstance(value["rules"], list) and len(value["rules"]) <= 100)
    ids = {c["id"] for c in columns}
    seen = set()
    for r in value["rules"]:
        require(
            isinstance(r, dict)
            and set(r) == {"id", "kind", "column_id", "severity", "parameters"}
        )
        require(
            isinstance(r["id"], str) and 0 < len(r["id"]) <= 100 and r["id"] not in seen
        )
        seen.add(r["id"])
        require(r["kind"] in RULES and r["severity"] in ("warning", "error"))
        require(
            r["column_id"] in ids if r["kind"] != "row_count" else r["column_id"] == ""
        )
        p = r["parameters"]
        require(isinstance(p, dict))
        kind = r["kind"]
        if kind == "range":
            require(
                set(p) == {"minimum", "maximum"}
                and all(
                    v is None or isinstance(v, str) and len(v) <= 200
                    for v in p.values()
                )
            )
            require(any(v is not None for v in p.values()))
            from veri_ufku.analytics.dataset import literal

            dtype = dtype_of(
                next(c for c in columns if c["id"] == r["column_id"])["type"]
            )
            for bound in p.values():
                if bound is not None:
                    literal(bound, dtype)
            if all(v is not None for v in p.values()):
                require(
                    pl.select(
                        literal(p["minimum"], dtype) <= literal(p["maximum"], dtype)
                    ).item(),
                    "Geçerli alt sınır üst sınırı aşamaz.",
                )
        elif kind == "nullable":
            require(set(p) == {"allowed"} and type(p["allowed"]) is bool)
        elif kind == "unique":
            require(set(p) == {"nulls_equal"} and type(p["nulls_equal"]) is bool)
        elif kind in ("unit", "type"):
            require(
                set(p) == {"expected"}
                and isinstance(p["expected"], str)
                and 0 < len(p["expected"]) <= 200
            )
        elif kind == "ordinal":
            require(
                set(p) == {"order"}
                and isinstance(p["order"], list)
                and 0 < len(p["order"]) <= 1000
                and all(isinstance(v, str) and len(v) <= 256 for v in p["order"])
                and len(set(p["order"])) == len(p["order"])
            )
        elif kind == "row_count":
            require(
                set(p) == {"minimum", "maximum"}
                and all(type(v) is int and 0 <= v <= 10**12 for v in p.values())
                and p["minimum"] <= p["maximum"]
            )
        else:
            require(set(p) == {"version_id", "column_id", "nullable"})
            entity_id(p["version_id"], "dv")
            entity_id(p["column_id"], "col")
            require(type(p["nullable"]) is bool)
    return copy.deepcopy(value)


def approval(p):
    a = p.get("approval")
    require(
        isinstance(a, dict) and set(a) == {"approved", "reviewer", "reason", "at"},
        "Birleşme için açık insan onayı, inceleyen ve gerekçe gerekli.",
    )
    require(
        a["approved"] is True
        and all(
            isinstance(a[k], str) and 0 < len(a[k].strip()) <= 1000
            for k in ("reviewer", "reason", "at")
        )
    )
    try:
        require(datetime.fromisoformat(a["at"]).utcoffset() is not None)
    except ValueError as e:
        raise ProjectError("Onay tarihi saat dilimi taşımalı.") from e


def parameters(request, kind, selected, p, columns):
    ids = {c["id"] for c in columns}
    if kind == "schema_contract":
        require(set(p) == {"contract", "semantic_metadata", "analysis_unit"})
        contract_validate(p["contract"], columns)
        from veri_ufku.analytics.contracts import validate_semantics

        validate_semantics(
            dict(
                import_metadata={"columns": columns},
                semantic_metadata=p["semantic_metadata"],
                analysis_unit=p["analysis_unit"],
            )
        )
        return columns
    if kind == "contract_check":
        require(
            set(p) == {"contract", "policy"}
            and p["policy"] in ("stop", "quarantine", "continue")
        )
        contract_validate(p["contract"], columns)
        fks = [r for r in p["contract"]["rules"] if r["kind"] == "foreign_key"]
        require(
            len({r["parameters"]["version_id"] for r in fks}) <= 1,
            "Bir kontrolde en fazla bir referans sürümü; ayrı kontroller uygulayın.",
        )
        if fks:
            secondary = request.get("secondary", {})
            require(
                secondary.get("version_id") == fks[0]["parameters"]["version_id"],
                "Referans tablo sürümü bağlanmalı.",
            )
            other = {c["id"] for c in secondary.get("columns", [])}
            require(all(r["parameters"]["column_id"] in other for r in fks))
        return columns
    if kind == "category_map":
        require(set(p) == {"mapping", "approval"} and len(selected) == 1)
        require(
            dtype_of(next(c for c in columns if c["id"] == selected[0])["type"])
            == pl.String,
            "Kategori eşleme yalnız String sütunda destekli.",
        )
        approval(p)
        m = p["mapping"]
        require(
            isinstance(m, dict)
            and 0 < len(m) <= 200
            and all(
                isinstance(k, str)
                and isinstance(v, str)
                and len(k) <= 256
                and len(v) <= 256
                for k, v in m.items()
            )
        )
        return columns
    if kind == "category_candidates":
        require(
            set(p) == {"threshold"}
            and len(selected) == 1
            and type(p["threshold"]) in (float, int)
            and 0 <= p["threshold"] <= 1
        )
        require(
            dtype_of(next(c for c in columns if c["id"] == selected[0])["type"])
            == pl.String
        )
        return columns
    require(
        set(p)
        == (
            {"name_column", "block_column", "threshold"}
            if kind == "entity_candidates"
            else {
                "name_column",
                "block_column",
                "threshold",
                "pairs",
                "canonical_column",
                "approval",
            }
        )
    )
    require(
        p["name_column"] in ids
        and p["block_column"] in ids
        and p["name_column"] != p["block_column"]
    )
    require(
        all(
            dtype_of(next(c for c in columns if c["id"] == p[k])["type"]) == pl.String
            for k in ("name_column", "block_column")
        ),
        "Ad ve blocking sütunları String olmalı.",
    )
    require(type(p["threshold"]) in (float, int) and 0 <= p["threshold"] <= 1)
    if kind == "entity_merge":
        approval(p)
        require(isinstance(p["pairs"], list) and 0 < len(p["pairs"]) <= 200)
        for pair in p["pairs"]:
            require(isinstance(pair, list) and len(pair) == 2 and pair[0] != pair[1])
            for row in pair:
                entity_id(row, "row")
        canonical = p["canonical_column"]
        entity_id(canonical, "col")
        if canonical not in ids:
            require(
                not any(c["name"] == "canonical_id" for c in columns),
                "canonical_id adı kullanımda; mevcut String ColumnId seçin.",
            )
            columns.append(
                dict(
                    id=canonical,
                    name="canonical_id",
                    original_name="canonical_id",
                    type="String",
                )
            )
        else:
            require(
                request.get("entity_resolution", {}).get("canonical_column")
                == canonical,
                "Canonical alan yalnız önceki insan kararının alanı olabilir; kullanıcı sütunu üzerine yazılmaz.",
            )
            require(
                dtype_of(next(c for c in columns if c["id"] == canonical)["type"])
                == pl.String
            )
    return columns


def input_versions(request, kind, p):
    if kind == "contract_check" and request.get("secondary"):
        return (request["version_id"], request["secondary"]["version_id"])
    return ()
