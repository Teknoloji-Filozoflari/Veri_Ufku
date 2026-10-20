"""Synthetic learning runs in the same ProjectStore, never the user's project."""

import copy
import json

from veri_ufku.domain.json import sha
from veri_ufku.importers.delimited import Control
from veri_ufku.learning.curriculum import CONTENT, spec
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import ProjectError, encode, uid
from veri_ufku.storage.project_model import digest as byte_digest
from veri_ufku.storage.project_store import file_hash
from veri_ufku.storage.validation_store import transaction

MAX_BYTES = 2 * 1024**2


def request_for(store, state, parameters):
    from veri_ufku.storage.experiment_store import capture

    p, lesson, curriculum = spec(parameters)
    if (
        state.get("name") != "Veri_Ufku · Geçici öğrenme laboratuvarı"
        or state["datasets"]
        or state["sources"]
    ):
        raise ProjectError(
            "Laboratuvar yalnız ayrı sentetik örnek workspace içinde çalışır."
        )
    return dict(
        workspace_id=store.manifest["project_id"],
        curriculum_hash=sha(CONTENT.read_bytes()),
        experiment_capture=capture(p),
    )


def validate_value(v, full=True):
    p, lesson, curriculum = spec(v["spec"])
    c = v["experiment_capture"]
    if (
        v["schema"] != "LearningLabRun/v1"
        or v["status"] != "completed"
        or v["lesson_version"] != lesson["version"]
        or v["content_version"] != curriculum.data["content_version"]
        or v["article_id"] != lesson["article_id"]
        or v["article_version"] != lesson["review"]["article_version"]
        or v["review"] != lesson["review"]
        or v["provenance"]["parameters_hash"] != digest(p)
        or v["provenance"]["capability_id"] != "learn.lab." + p["lesson"]
        or v["provenance"]["dataset_versions"] != []
    ):
        raise ProjectError("Lab content/config/provenance bağı bozuk.")
    if (
        c["schema"] != "RunCapture/v1"
        or c["code_hash"] != byte_digest(encode(c["code_files"]))
        or c["environment_hash"] != byte_digest(encode(c["environment"]))
        or c["config_hash"] != byte_digest(encode(p))
    ):
        raise ProjectError("Lab run capture bozuk.")
    if full:
        if v["identity"] != digest({k: x for k, x in v.items() if k != "identity"}):
            raise ProjectError("Lab identity hash bozuk.")
        rows = v["input_records"]
        ids = [r["fixture_row_id"] for r in rows]
        if (
            not 1 <= len(rows) <= 10000
            or len(set(ids)) != len(rows)
            or v["fixture_hash"]
            != digest(
                [{k: x for k, x in r.items() if k != "fixture_row_id"} for r in rows]
            )
        ):
            raise ProjectError("Lab synthetic input kimliği/hash bozuk.")
        for key, values in v["split_ids"].items():
            if values != [ids[i] for i in v["split"][key]]:
                raise ProjectError("Lab split kimliği bozuk.")
        partitions = list(v["split_ids"].values())
        if sum(map(len, partitions)) != len(
            set(i for part in partitions for i in part)
        ):
            raise ProjectError("Lab train/calibration/evaluation örtüşüyor.")
    if len(encode(v)) > MAX_BYTES:
        raise ProjectError("Lab2MiB artifact sınırı.")


def public_report(value):
    return {
        k: copy.deepcopy(v)
        for k, v in value.items()
        if k not in ("input_records", "split_ids")
    }


def publish(store, state, value, control=None):
    control = control or Control()
    v = copy.deepcopy(value)
    validate_value(v)
    request = request_for(store, state, v["spec"])
    if request["workspace_id"] != v["workspace_id"]:
        raise ProjectError("Lab sonucu başka workspace ait.")
    raw = encode(v)
    control.check()
    control.disk(store.root, force=True)

    def add(draft):
        control.check()
        stage = store.path("staging") / uid()
        stage.mkdir(mode=0o700)
        path = stage / "lab.bin"
        path.write_bytes(raw)
        control.disk(store.root, force=True)
        fp = file_hash(path)
        uri = "sources/" + uid() + ".bin"
        store.pending[uri] = (path, dict(**fp, kind="source", rows=None, schema=None))
        summary = public_report(v)
        summary.update(details_uri=uri, details_fingerprint=fp)
        draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[],
                seed=v["spec"]["seed"],
                capability_id=v["provenance"]["capability_id"],
                learning_lab=summary,
            )
        )
        control.check()

    return transaction(store, state, add)


def validate_records(state):
    for r in state["results"]:
        if "learning_lab" in r:
            validate_value(r["learning_lab"], False)
            if (
                r["dataset_version_ids"]
                or r["learning_lab"]["details_fingerprint"]["size"] > MAX_BYTES
            ):
                raise ProjectError("Lab summary workspace/size bozuk.")


def load(store, record):
    s = record["learning_lab"]
    p = store.path(s["details_uri"])
    if file_hash(p) != s["details_fingerprint"]:
        raise ProjectError("Lab artifact hash değişmiş.")
    v = json.loads(p.read_bytes())
    validate_value(v)
    if public_report(v) != {
        k: x for k, x in s.items() if k not in ("details_uri", "details_fingerprint")
    }:
        raise ProjectError("Lab summary/artifact farklı.")
    return v
