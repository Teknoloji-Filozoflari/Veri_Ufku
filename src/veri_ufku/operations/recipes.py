"""Versioned data-only operation replay. Dry runs never publish project state."""

import ast
import copy

from veri_ufku.domain.json import parse, raw_json, sha
from veri_ufku.importers.delimited import Control
from veri_ufku.operations.contracts import OperationSpec, build
from veri_ufku.operations.engine import calculate, transformed_dataset
from veri_ufku.storage.project_model import ProjectError, entity_id, uid

MAX_BYTES = 2 * 1024**2


def validate(value):
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "seed",
        "sources",
        "steps",
        "origin_version",
    }:
        raise ProjectError(
            "Tarif alanları geçersiz; yalnız declarative JSON kabul edilir."
        )
    if (
        value["schema"] != "AnalysisRecipe/v1"
        or type(value["seed"]) is not int
        or not 0 <= value["seed"] < 2**32
    ):
        raise ProjectError("Tarif sürümü/seed desteklenmiyor.")
    if (
        not isinstance(value["sources"], dict)
        or not value["sources"]
        or len(value["sources"]) > 100
    ):
        raise ProjectError("Tarif kaynakları geçersiz.")
    if not isinstance(value["steps"], list) or not 1 <= len(value["steps"]) <= 100:
        raise ProjectError("Tarif 1–100 adım içermeli.")
    available = {}
    for version, source in value["sources"].items():
        entity_id(version, "dv")
        if set(source) != {
            "columns",
            "semantic_metadata",
            "fingerprint",
        } or not isinstance(source["columns"], list):
            raise ProjectError("Tarif kaynak şeması geçersiz.")
        ids, names = set(), set()
        if not 1 <= len(source["columns"]) <= 2000 or not isinstance(
            source["semantic_metadata"], dict
        ):
            raise ProjectError("Tarif kolon/rol sınırı geçersiz.")
        for column in source["columns"]:
            if not isinstance(column, dict) or set(column) != {
                "id",
                "name",
                "original_name",
                "type",
            }:
                raise ProjectError("Tarif kolon alanları geçersiz.")
            entity_id(column["id"], "col")
            if (
                column["id"] in ids
                or column["name"] in names
                or any(
                    not isinstance(column[k], str)
                    or not column[k]
                    or len(column[k]) > 1000
                    for k in ("name", "original_name", "type")
                )
            ):
                raise ProjectError("Tarif kolon kimlik/ad/tür geçersiz.")
            ids.add(column["id"])
            names.add(column["name"])
        if not set(source["semantic_metadata"]) <= ids:
            raise ProjectError("Tarif rol bağı bilinmeyen kolon içeriyor.")
        from veri_ufku.analytics.contracts import validate_semantics

        validate_semantics(
            dict(
                import_metadata={"columns": source["columns"]},
                semantic_metadata=source["semantic_metadata"],
            )
        )
        fingerprint = source["fingerprint"]
        if (
            not isinstance(fingerprint, dict)
            or set(fingerprint) != {"size", "sha256"}
            or type(fingerprint["size"]) is not int
            or fingerprint["size"] < 0
            or not isinstance(fingerprint["sha256"], str)
            or len(fingerprint["sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in fingerprint["sha256"])
        ):
            raise ProjectError("Tarif fingerprint geçersiz.")
        available[version] = source["columns"]
    for step in value["steps"]:
        if set(step) != {"spec", "output_version"}:
            raise ProjectError("Tarif adımı geçersiz.")
        spec = OperationSpec.from_dict(step["spec"])
        entity_id(step["output_version"], "dv")
        if (
            spec.input_version_id not in available
            or step["output_version"] in available
            or any(v not in available for v in spec.input_version_ids)
        ):
            raise ProjectError("Tarif giriş/çıktı zinciri geçersiz.")
        available[step["output_version"]] = spec.output_schema
    if value["origin_version"] != value["steps"][-1]["output_version"]:
        raise ProjectError("Tarif son sürüm bağı geçersiz.")
    if len(raw_json(value)) > MAX_BYTES:
        raise ProjectError("Tarif 2MiB sınırını aşıyor.")
    return copy.deepcopy(value)


def read(path):
    with open(path, "rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ProjectError("Tarif 2MiB sınırını aşıyor.")
    try:
        return validate(parse(raw))
    except (TypeError, KeyError, RecursionError) as error:
        raise ProjectError("Tarif şeması geçersiz.") from error


def export(state, version, artifacts, seed=42):
    datasets = {d["version_id"]: d for d in state["datasets"]}
    operations = {
        o.get("output_version_id"): o for o in state["operations"] if "spec" in o
    }
    steps = []
    cursor = version
    while cursor in operations:
        op = operations[cursor]
        steps.insert(0, dict(spec=copy.deepcopy(op["spec"]), output_version=cursor))
        cursor = op["spec"]["input_version_id"]
        if len(steps) > 100:
            raise ProjectError("Tarif 100 adım sınırını aşıyor.")
    sources = {}
    produced = {s["output_version"] for s in steps}
    for step in steps:
        spec = step["spec"]
        for source in spec.get("input_version_ids") or [spec["input_version_id"]]:
            if source in produced or source in sources:
                continue
            d = datasets[source]
            sources[source] = dict(
                columns=copy.deepcopy(d["import_metadata"]["columns"]),
                semantic_metadata=copy.deepcopy(d.get("semantic_metadata", {})),
                fingerprint={
                    k: artifacts[d["snapshot_uri"]][k] for k in ("size", "sha256")
                },
            )
    return validate(
        dict(
            schema="AnalysisRecipe/v1",
            seed=seed,
            sources=sources,
            steps=steps,
            origin_version=version,
        )
    )


REFERENCE_FIELDS = {
    "id",
    "column_id",
    "flag_column_id",
    "secondary_version_id",
    "header_column",
    "value_column",
    "left_column",
    "right_column",
}
REFERENCE_LISTS = {
    "column_ids",
    "order_columns",
    "group_columns",
    "resolved_drop_ids",
    "index_columns",
    "value_columns",
    "left_keys",
    "right_keys",
}


def parameters_for(original, ids, columns, secondary_ids=None):
    def visit(value, field=""):
        if isinstance(value, str):
            return (
                ids.get(value, value)
                if field in REFERENCE_FIELDS | REFERENCE_LISTS
                else value
            )
        if isinstance(value, list):
            return [visit(v, field) for v in value]
        if isinstance(value, dict):
            return {
                ids.get(k, k) if field == "semantic_metadata" else k: visit(v, k)
                for k, v in value.items()
            }
        return value

    parameters = visit(original["parameters"])
    if secondary_ids is not None:
        old = original["parameters"]
        if original["kind"] == "join":
            parameters["right_keys"] = [
                secondary_ids.get(c, c) for c in old["right_keys"]
            ]
            for item, source_item in zip(
                parameters["right_outputs"], old["right_outputs"], strict=True
            ):
                item["column_id"] = secondary_ids.get(
                    source_item["column_id"], source_item["column_id"]
                )
        elif original["kind"] == "append":
            for item, source_item in zip(
                parameters["mapping"], old["mapping"], strict=True
            ):
                item["right_column"] = secondary_ids.get(
                    source_item["right_column"], source_item["right_column"]
                )
    if original["kind"] == "computed":
        from veri_ufku.operations.formula import parse

        parse(original["parameters"]["expression"], columns)
        tree = ast.parse(original["parameters"]["expression"], mode="eval")
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "col"
            ):
                node.args[0].value = ids[node.args[0].value]
        parameters["expression"] = ast.unparse(tree)
        parameters.pop("tree", None)
    return parameters


def remap(value, ids):
    if isinstance(value, str):
        return ids.get(value, value)
    if isinstance(value, list):
        return [remap(v, ids) for v in value]
    if isinstance(value, dict):
        return {ids.get(k, k): remap(v, ids) for k, v in value.items()}
    return value


def dry_run(recipe, sources, mappings, workspace, control=None):
    recipe = validate(recipe)
    control = control or Control()
    requests = copy.deepcopy(sources)
    ids = {}
    version_maps = copy.deepcopy(mappings)
    reports, results = [], []
    errors = []
    for source, required in recipe["sources"].items():
        actual = requests.get(source)
        if not actual:
            errors.append(f"Kaynak eşlenmedi: {source}")
            continue
        ids[source] = actual["version_id"]
        used = set()
        for c in required["columns"]:
            selected = mappings.get(source, {}).get(c["id"])
            target = next((a for a in actual["columns"] if a["id"] == selected), None)
            if not target:
                errors.append(f"Eksik kolon/eşleme: {c['name']}")
                continue
            if target["id"] in used:
                errors.append(f"Tekrarlanan eşleme: {c['name']}")
            used.add(target["id"])
            compatible = target["type"] == c["type"]
            if not compatible:
                from veri_ufku.operations.types import dtype_of

                try:
                    compatible = dtype_of(target["type"]) == dtype_of(c["type"])
                except ProjectError:
                    compatible = False
            if not compatible:
                errors.append(
                    f"Tür uyumsuz: {c['name']} ({c['type']} → {target['type']})"
                )
            old_role = required["semantic_metadata"].get(c["id"], {})
            new_role = actual.get("semantic_metadata", {}).get(target["id"], {})
            for key in ("role", "unit", "ordinal_order"):
                if old_role.get(key) and old_role.get(key) != new_role.get(key):
                    errors.append(f"Rol/birim/sıra uyumsuz: {c['name']} · {key}")
            ids[c["id"]] = target["id"]
    if errors:
        return dict(
            valid=False,
            errors=errors,
            steps=[
                dict(
                    index=i + 1,
                    kind=s["spec"]["kind"],
                    status="blocked",
                    error="; ".join(errors),
                )
                for i, s in enumerate(recipe["steps"])
            ],
            results=[],
        )
    for i, step in enumerate(recipe["steps"]):
        control.check()
        original = step["spec"]
        try:
            request = copy.deepcopy(requests[original["input_version_id"]])
            secondary = original["parameters"].get("secondary_version_id")
            if secondary:
                request["secondary"] = requests[secondary]
            ids.update(version_maps.get(original["input_version_id"], {}))
            # New output ColumnIds are mapped once and then reused by later steps.
            for col in original["output_schema"]:
                ids.setdefault(col["id"], "col:" + uid())
            parameters = parameters_for(
                original,
                ids,
                [{"id": c} for c in original["column_ids"]],
                version_maps.get(secondary) if secondary else None,
            )
            if original["kind"] == "filter":
                by_id = {c["id"]: c for c in request["columns"]}
                for item in parameters["filters"]:
                    item["literal"]["dtype"] = by_id[item["column_id"]]["type"]
            spec = build(
                request,
                original["kind"],
                remap(list(original["column_ids"]), ids),
                parameters,
                "chain",
            )
            result = calculate(request, spec, workspace, control)
            spec = OperationSpec.from_dict(result["spec"])
            output_mapping = {}
            for old_column in original["output_schema"]:
                found = next(
                    (
                        c
                        for c in spec.output_schema
                        if c["id"] == ids.get(old_column["id"])
                        or c["name"] == old_column["name"]
                    ),
                    None,
                )
                if found:
                    ids[old_column["id"]] = found["id"]
                    output_mapping[old_column["id"]] = found["id"]
            version_maps[step["output_version"]] = output_mapping
            result["provenance"]["seed"] = recipe["seed"]
            result["provenance"]["seed_reason"] = (
                "Tarif seed'i; mevcut dönüşümler deterministik"
            )
            result["provenance"]["parameters_hash"] = sha(
                raw_json(dict(recipe=recipe, mappings=mappings))
            )
            results.append(result)
            reports.append(
                dict(
                    index=i + 1,
                    kind=spec.kind,
                    status="succeeded",
                    error="",
                    impact=result["impact"],
                    diagnostics=result["diagnostics"],
                )
            )
            parent = dict(
                import_metadata=dict(
                    columns=request["columns"], settings=request.get("settings", {})
                ),
                version_id=request["version_id"],
                semantic_metadata=request.get("semantic_metadata", {}),
            )
            after = transformed_dataset(
                parent,
                result,
                "temporary",
                dict(
                    import_metadata=dict(
                        columns=request["secondary"]["columns"],
                        settings=request["secondary"].get("settings", {}),
                    ),
                    version_id=request["secondary"]["version_id"],
                )
                if secondary
                else None,
            )
            requests[step["output_version"]] = dict(
                request,
                path=result["path"],
                fingerprint=result["fingerprint"],
                columns=list(spec.output_schema),
                row_count=result["impact"]["after_rows"],
                version_id=result["version_id"],
                semantic_metadata=after.get("semantic_metadata", {}),
            )
            requests[step["output_version"]].pop("secondary", None)
            ids[step["output_version"]] = result["version_id"]
        except (ProjectError, KeyError, TypeError, ValueError) as error:
            reports.append(
                dict(
                    index=i + 1,
                    kind=original["kind"],
                    status="failed",
                    error=str(error),
                )
            )
            reports.extend(
                dict(
                    index=j + 1,
                    kind=s["spec"]["kind"],
                    status="blocked",
                    error="Önceki adım başarısız",
                )
                for j, s in enumerate(recipe["steps"][i + 1 :], i + 1)
            )
            return dict(
                valid=False,
                errors=[f"Adım {i + 1}: {error}"],
                steps=reports,
                results=[],
            )
    return dict(
        valid=True,
        errors=[],
        steps=reports,
        results=results,
        recipe=recipe,
        mappings=mappings,
    )


def publish(store, state, preview, checkpoint=lambda point: None):
    if not preview.get("valid") or not preview.get("results"):
        raise ProjectError("Başarılı güncel dry-run gerekli.")
    previous, pending = copy.deepcopy(store.state), dict(store.pending)
    commit = store.commit_id
    try:
        store.state = copy.deepcopy(state)
        for index, result in enumerate(preview["results"]):
            store.publish_operation(
                copy.deepcopy(result), _defer=True, checkpoint=checkpoint
            )
            store.state["operations"][-1]["seed"] = preview["recipe"]["seed"]
            store.state["operations"][-1]["recipe_replay"] = dict(
                schema="RecipeReplay/v1",
                recipe_hash=sha(raw_json(preview["recipe"])),
                origin_version=preview["recipe"]["origin_version"],
                original_step_id=preview["recipe"]["steps"][index]["spec"]["id"],
                mappings=preview["mappings"],
                seed=preview["recipe"]["seed"],
            )
        store.save(checkpoint=checkpoint)
        return copy.deepcopy(store.state)
    except BaseException:
        from veri_ufku.storage.project_model import decode

        if decode(store._read("ACTIVE", 4096))["commit_id"] != commit:
            store._load("ACTIVE")
            store.pending.clear()
        else:
            store.state, store.pending = previous, pending
        raise
