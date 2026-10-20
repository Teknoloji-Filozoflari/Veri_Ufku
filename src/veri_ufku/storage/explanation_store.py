"""Append-only explanation artifacts through the existing ProjectStore transaction."""

import copy
import json

from veri_ufku.modeling.explanation import LIMITATIONS, ExplainSpec
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import file_hash
from veri_ufku.storage.validation_store import prior_uses, transaction

MAX_BYTES = 16 * 1024**2


def validate(value, versions, summary=False):
    p = value["provenance"]
    s = ExplainSpec.from_dict(value["spec"], require_backend=False)
    if (
        value["schema"] != "ExplanationRun/v1"
        or value["status"] != "completed"
        or value["limitations"] != LIMITATIONS
        or p["fit_calls"] != 0
        or p["dataset_version"] not in versions
        or p["background_dataset_version"] != p["dataset_version"]
        or p["source_snapshot_id"]
        != versions[p["dataset_version"]]["import_metadata"]["source_snapshot_id"]
        or not 0 < p["n"] <= 500
        or not 0 < p["background_n"] <= 100
        or not 0 < p["prediction_row_passes"] <= p["prediction_row_pass_budget"]
        or p["prediction_row_pass_budget"] != 300000
    ):
        raise ProjectError("Explanation source/status/budget/provenance geçersiz.")
    common = p["common"]
    if (
        common["dataset_versions"] != [p["dataset_version"]]
        or common["capability_id"] != "model.explain." + s.method
        or common["parameters_hash"] != digest(s.data())
        or common["source_snapshot_ids"] != [p["source_snapshot_id"]]
        or common["seed"] != s.seed
        or p["sensitive_columns"] != s.sensitive_columns
    ):
        raise ProjectError(
            "Explanation ortak Provenance/sensitive seçim bağı geçersiz."
        )
    if summary:
        if value["details_fingerprint"]["size"] > MAX_BYTES:
            raise ProjectError("Explanation artifact boyutu geçersiz.")
        return
    if value["identity"] != "explanation:" + digest(
        {k: v for k, v in value.items() if k != "identity"}
    ):
        raise ProjectError("Explanation safe result identity uyuşmuyor.")
    ids = p["evaluation_row_ids"]
    bg = p["background_row_ids"]
    card = value["card"]
    if (
        len(ids) != p["n"]
        or len(bg) != p["background_n"]
        or len(set(ids)) != len(ids)
        or len(set(bg)) != len(bg)
        or set(ids) & set(bg)
        or not set(ids) <= set(card["split"]["membership"]["validation"])
        or not set(bg) <= set(card["fit_row_ids"])
        or set(ids + bg) & set(card["split"]["membership"]["test"])
        or p["dataset_version"] != card["dataset_version"]
        or p["snapshot_fingerprint"] != card["snapshot_fingerprint"]
    ):
        raise ProjectError(
            "Explanation evaluation/background/model/test üyeliği geçersiz."
        )
    if [r["row_id"] for r in value["prediction_records"]] != ids:
        raise ProjectError("Explanation prediction records üyeliği uyuşmuyor.")
    for m in value["feature_mapping"]:
        if m["column_id"] not in {f["id"] for f in card["features"]} or not set(
            m["dependencies"]
        ) <= {f["id"] for f in card["features"]}:
            raise ProjectError("Explanation feature mapping ColumnId geçersiz.")
    if s and s.method == "permutation":
        for row in value["permutation"]["values"]:
            import numpy as np

            if (
                len(row["repeat_values"]) != s.repeats
                or row["mean"] != float(np.mean(row["repeat_values"]))
                or row["std"] != float(np.std(row["repeat_values"], ddof=1))
            ):
                raise ProjectError("Permutation reference özeti uyuşmuyor.")
    if "pdp" in value:
        import numpy as np

        if (
            len(value["pdp"]["grid"]) != len(value["pdp"]["mean"])
            or not np.isfinite(value["pdp"]["mean"]).all()
        ):
            raise ProjectError("PDP grid/mean geçersiz.")
        if value.get("ice") and not np.allclose(
            np.array([r["values"] for r in value["ice"]]).mean(axis=0),
            value["pdp"]["mean"],
        ):
            raise ProjectError("ICE/PDP reference uyuşmuyor.")
    if "local" in value:
        v = value["local"]
        if not math_isclose(
            v["baseline"] + sum(c["value"] for c in v["contributions"]), v["prediction"]
        ):
            raise ProjectError("Local additive açıklama uyuşmuyor.")


def math_isclose(a, b):
    import math

    return (
        math.isfinite(a)
        and math.isfinite(b)
        and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    )


def publish(store, state, value):
    value = copy.deepcopy(value)
    versions = {d["version_id"]: d for d in state["datasets"]}
    validate(value, versions)
    p = value["provenance"]
    source = versions[p["dataset_version"]]
    if (
        p["prior_test_use_ids"] != prior_uses(state)
        or file_hash(store.path(source["snapshot_uri"])) != p["snapshot_fingerprint"]
    ):
        raise ProjectError("Explanation source/test kullanım geçmişi değişti.")
    models = [
        r.get("baseline")
        for r in state["results"]
        if r.get("baseline", {}).get("run_id") == p["model_run_id"]
    ]
    if (
        len(models) != 1
        or models[0]["model_card"] != value["card"]
        or models[0]["model_package_fingerprint"] != p["model_package_fingerprint"]
    ):
        raise ProjectError(
            "Explanation model bu projede frozen kayıtla uyuşmuyor; external package explanation burada kapalı."
        )
    # Recompute memberships/missing/correlation and row counts in parent without model deserialization.
    import polars as pl

    frame = pl.read_parquet(store.path(source["snapshot_uri"]))
    ids = set(frame["__vu_row_id"].to_list())
    if not set(p["evaluation_row_ids"] + p["background_row_ids"]) <= ids:
        raise ProjectError("Explanation kaynak RowId kayıp.")
    from veri_ufku.modeling.explanation import diagnostic_columns

    sample = frame.filter(pl.col("__vu_row_id").is_in(p["evaluation_row_ids"]))
    bg = frame.filter(pl.col("__vu_row_id").is_in(p["background_row_ids"]))
    # Restore the exact sample order: seeded permutation, ICE and bootstrap use it.
    positions = {rid: i for i, rid in enumerate(frame["__vu_row_id"])}
    sample = frame[[positions[rid] for rid in p["evaluation_row_ids"]]]
    bg = frame[[positions[rid] for rid in p["background_row_ids"]]]
    if diagnostic_columns(sample, bg, value["card"]) != value["diagnostics"]:
        raise ProjectError("Explanation kaynak diagnostic verisi uyuşmuyor.")
    import numpy as np

    from veri_ufku.modeling.explanation import fairness_report, slices_report

    records = value["prediction_records"]
    target = value["card"]["target"]["name"]
    actual = (
        np.array([str(v) for v in sample[target]])
        if value["card"]["purpose"] == "classification"
        else sample[target].to_numpy().astype(float)
    )
    if [r["row_id"] for r in records] != p["evaluation_row_ids"] or any(
        r["actual"] != actual[i] for i, r in enumerate(records)
    ):
        raise ProjectError("Explanation source-bound actual/RowId uyuşmuyor.")
    predicted = np.array([r["prediction"] for r in records])
    spec = ExplainSpec.from_dict(value["spec"], require_backend=False)
    if spec.method == "slices":
        fresh = slices_report(sample, actual, predicted, value["card"], spec)
        if any(value[k] != fresh[k] for k in fresh):
            raise ProjectError("Source-bound slice metric/uncertainty uyuşmuyor.")
    if (
        spec.method == "fairness"
        and fairness_report(sample, actual, predicted, value["card"], spec)
        != value["fairness"]
    ):
        raise ProjectError("Source-bound fairness counts/rates uyuşmuyor.")
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, allow_nan=False
    ).encode()
    if len(raw) > MAX_BYTES:
        raise ProjectError("Explanation JSON16MiB üstünde; sample azaltın.")

    def add(draft):
        stage = store.path("staging") / uid()
        stage.mkdir(mode=0o700)
        path = stage / "explanation.bin"
        path.write_bytes(raw)
        fp = file_hash(path)
        uri = "sources/" + uid() + ".bin"
        store.pending[uri] = (path, dict(**fp, kind="source", rows=None, schema=None))
        summary = {
            k: value[k]
            for k in (
                "schema",
                "run_id",
                "status",
                "created_at",
                "spec",
                "provenance",
                "limitations",
                "identity",
            )
        }
        summary.update(details_uri=uri, details_fingerprint=fp)
        draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[p["dataset_version"]],
                seed=value["spec"]["seed"],
                capability_id="model.explain." + value["spec"]["method"],
                explanation=summary,
            )
        )

    return transaction(store, state, add)


def validate_records(state, versions):
    for record in state["results"]:
        if "explanation" not in record:
            continue
        r = record["explanation"]
        validate(r, versions, True)
        if (
            record["dataset_version_ids"] != [r["provenance"]["dataset_version"]]
            or record["seed"] != r["spec"]["seed"]
            or record["capability_id"] != "model.explain." + r["spec"]["method"]
        ):
            raise ProjectError("Explanation record/scope uyuşmuyor.")
        from veri_ufku.storage.project_model import fingerprint, relative

        relative(r["details_uri"])
        fingerprint(r["details_fingerprint"])


def load(store, record):
    r = record["explanation"]
    path = store.path(r["details_uri"])
    if path.stat().st_size > MAX_BYTES or file_hash(path) != r["details_fingerprint"]:
        raise ProjectError("Explanation safe artifact hash/boyut uyuşmuyor.")
    value = json.loads(path.read_bytes())
    validate(value, {d["version_id"]: d for d in store.state["datasets"]})
    if any(
        value[k] != r[k] for k in r if k not in ("details_uri", "details_fingerprint")
    ):
        raise ProjectError("Explanation summary/artifact uyuşmuyor.")
    return value
