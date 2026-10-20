"""Data-only v1 author interfaces. Python trust is NOT an OS permission sandbox."""

import copy
import json
import math
import re
from typing import Protocol

from veri_ufku.exports.share_privacy import SECRET_KEY, reason
from veri_ufku.storage.project_model import ProjectError

KINDS = ("importer", "transform", "stat", "model", "chart", "lesson")
PERMISSIONS = ("dataset.read", "result.emit", "python.same-user", "network")
MAX_OUTPUT = 1024 * 1024


class PluginV1(Protocol):
    def run(self, request: dict, context: "ContextV1") -> dict: ...


# Distinct versioned purposes; host output contracts differ for each kind.
class ImporterV1(PluginV1, Protocol): ...


class TransformV1(PluginV1, Protocol): ...


class StatisticV1(PluginV1, Protocol): ...


class ModelV1(PluginV1, Protocol): ...


class ChartV1(PluginV1, Protocol): ...


class LessonV1(PluginV1, Protocol): ...


class ContextV1:
    api_version = 1

    def __init__(self, control):
        self._control = control

    def check(self):
        self._control.check()

    @property
    def budget(self):
        from dataclasses import asdict

        return asdict(self._control.budget)


def token(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", value):
        raise ProjectError("Plugin kimliği1..64ASCII harf/rakam/tire olmalı.")
    return value


def text(value, maximum=2000):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or "\x00" in value:
        raise ProjectError("Plugin metin alanı sınırı geçersiz.")
    return value


def json_data(value, maximum=MAX_OUTPUT):
    # Closed JSON: no pickle, object hooks, paths, code import or executable model objects.
    def check(x, depth=0):
        if depth > 16:
            raise ProjectError("Plugin JSON nesting16sınırı.")
        if x is None or type(x) in (str, bool, int):
            return
        if type(x) is float and math.isfinite(x):
            return
        if type(x) is list:
            for v in x:
                check(v, depth + 1)
            return
        if type(x) is dict and all(type(k) is str for k in x):
            for v in x.values():
                check(v, depth + 1)
            return
        raise ProjectError("Plugin yalnız finite safe JSON döndürebilir.")

    check(value)
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, allow_nan=False
    ).encode()
    if len(raw) > maximum:
        raise ProjectError("Plugin JSON boyut bütçesi aşıldı.")
    return raw


def manifest(value):
    fields = {
        "schema",
        "api_version",
        "id",
        "version",
        "python",
        "entry",
        "code_sha256",
        "permissions",
        "dependencies",
        "capability",
        "learning",
    }
    if (
        not isinstance(value, dict)
        or set(value) != fields
        or value["schema"] != "Veri_UfkuPlugin/v1"
        or type(value["api_version"]) is not int
        or value["api_version"] != 1
    ):
        raise ProjectError(
            "Uyumsuz plugin API; yalnız Veri_UfkuPlugin/v1 API1 destekli."
        )
    token(value["id"])
    if not isinstance(value["version"], str) or not re.fullmatch(
        r"\d+\.\d+\.\d+", value["version"]
    ):
        raise ProjectError("Plugin semver x.y.z gerekli.")
    if (
        value["python"] != "3.13"
        or value["entry"] != "plugin.py:run"
        or not isinstance(value["code_sha256"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", value["code_sha256"])
    ):
        raise ProjectError(
            "Plugin Python3.13/self-contained plugin.py:run/hash gerekli."
        )
    perm = value["permissions"]
    if (
        not isinstance(perm, list)
        or any(not isinstance(p, str) or p not in PERMISSIONS for p in perm)
        or len(perm) != len(set(perm))
        or not {"result.emit", "python.same-user"} <= set(perm)
    ):
        raise ProjectError("Plugin permission manifest geçersiz.")
    deps = value["dependencies"]
    if (
        not isinstance(deps, dict)
        or len(deps) > 16
        or any(
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", k)
            or not isinstance(v, str)
            or not re.fullmatch(r"[A-Za-z0-9.+-]{1,40}", v)
            for k, v in deps.items()
        )
    ):
        raise ProjectError("Plugin dependency exact version şeması gerekli.")
    cap = value["capability"]
    if not isinstance(cap, dict) or set(cap) != {
        "id",
        "kind",
        "title",
        "method_version",
        "input_schema",
        "parameters",
        "output_schema",
    }:
        raise ProjectError("Plugin capability kapalı şema gerekli.")
    token(cap["id"])
    text(cap["title"], 100)
    if (
        cap["kind"] not in KINDS
        or type(cap["method_version"]) is not int
        or cap["method_version"] < 1
        or cap["input_schema"] != "PluginInput/v1"
        or cap["output_schema"] != "PluginOutput/v1"
    ):
        raise ProjectError("Plugin capability method/input/output uyumsuz.")
    if not isinstance(cap["parameters"], dict) or len(cap["parameters"]) > 16:
        raise ProjectError("Plugin en fazla16parametre.")
    for k, p in cap["parameters"].items():
        token(k)
        if (
            not isinstance(p, dict)
            or set(p) != {"type", "default"}
            or p["type"] not in ("number", "integer", "string", "boolean")
        ):
            raise ProjectError("Plugin parametre tipi geçersiz.")
        parameter(p["default"], p["type"])
    learn = value["learning"]
    if not isinstance(learn, dict) or set(learn) != {
        "id",
        "version",
        "title",
        "summary",
        "limitations",
    }:
        raise ProjectError("Plugin learning id/başlık/sınırlar zorunlu.")
    token(learn["id"])
    if type(learn["version"]) is not int or learn["version"] < 1:
        raise ProjectError("Plugin learning sürümü gerekli.")
    for k in ("title", "summary", "limitations"):
        text(learn[k])
    no_secrets(value)
    json_data(value, 65536)
    return copy.deepcopy(value)


def parameter(value, kind):
    valid = (
        type(value) in (int, float) and math.isfinite(value)
        if kind == "number"
        else type(value) is int
        if kind == "integer"
        else type(value) is bool
        if kind == "boolean"
        else isinstance(value, str) and len(value) <= 1000
    )
    if not valid:
        raise ProjectError("Plugin parametre değeri bildirilen tipe uymuyor.")
    return value


def no_secrets(value):
    if isinstance(value, str) and reason(value) == "secret-pattern":
        raise ProjectError(
            "Plugin metadata/output bilinen secret deseni içeriyor; keyring referansı kullanın."
        )
    if isinstance(value, dict):
        for k, v in value.items():
            if SECRET_KEY.search(k) and v not in (None, "", False):
                raise ProjectError(
                    "Plugin secret alanı metadata/output içinde saklanamaz."
                )
            no_secrets(v)
    if isinstance(value, list):
        for v in value:
            no_secrets(v)


def parameters(m, raw):
    declared = m["capability"]["parameters"]
    if not isinstance(raw, dict) or set(raw) != set(declared):
        raise ProjectError("Plugin parametre alanları manifestle aynı olmalı.")
    for k, v in raw.items():
        parameter(v, declared[k]["type"])
    no_secrets(raw)
    json_data(raw, 16384)
    return copy.deepcopy(raw)


def output(value, kind, row_ids):
    if (
        not isinstance(value, dict)
        or set(value)
        != {"schema", "kind", "summary", "data", "used_row_ids", "warnings"}
        or value["schema"] != "PluginOutput/v1"
        or value["kind"] != kind
    ):
        raise ProjectError("Plugin çıktı kapalı şeması uyuşmuyor.")
    text(value["summary"])
    if not isinstance(value["warnings"], list) or len(value["warnings"]) > 32:
        raise ProjectError("Plugin uyarı sınırı.")
    for v in value["warnings"]:
        text(v)
    ids = value["used_row_ids"]
    if (
        not isinstance(ids, list)
        or any(not isinstance(x, str) for x in ids)
        or len(ids) != len(set(ids))
        or not set(ids) <= set(row_ids)
    ):
        raise ProjectError(
            "Plugin RowId kaynağı geçersiz; yeni/global kimlik uydurulamaz."
        )
    data = value["data"]
    if not isinstance(data, dict):
        raise ProjectError("Plugin data nesnesi gerekli.")
    expected = {
        "stat": {"metrics"},
        "chart": {"x", "y", "x_label", "y_label"},
        "model": {"metrics", "state", "prediction_supported"},
        "importer": {"columns", "rows", "source_record_ids"},
        "transform": {"columns", "rows", "parent_row_ids"},
        "lesson": {"title", "paragraphs"},
    }[kind]
    if set(data) != expected:
        raise ProjectError("Plugin kind-specific output alanları uyuşmuyor.")
    if kind in ("stat", "model"):
        if not isinstance(data["metrics"], dict) or not 1 <= len(data["metrics"]) <= 32:
            raise ProjectError("Plugin1..32metric gerekli.")
        for k, v in data["metrics"].items():
            token(k)
            parameter(v, "number")
        if kind == "model" and (
            not isinstance(data["state"], dict)
            or data["prediction_supported"] is not False
        ):
            raise ProjectError(
                "SDK model JSON state arşivlenir; host prediction/reload henüz desteklenmiyor."
            )
    elif kind == "chart":
        if (
            not isinstance(data["x"], list)
            or not isinstance(data["y"], list)
            or not 1 <= len(data["x"]) == len(data["y"]) <= 10000
        ):
            raise ProjectError("Plugin chart x/y boyutu geçersiz.")
        for v in data["x"] + data["y"]:
            parameter(v, "number")
        text(data["x_label"], 100)
        text(data["y_label"], 100)
    elif kind in ("importer", "transform"):
        cols = data["columns"]
        rows = data["rows"]
        if (
            not isinstance(cols, list)
            or not 1 <= len(cols) <= 16
            or any(not isinstance(c, str) for c in cols)
            or len(set(cols)) != len(cols)
        ):
            raise ProjectError("Plugin tablo kolon şeması geçersiz.")
        for c in cols:
            text(c, 100)
        if (
            not isinstance(rows, list)
            or len(rows) > 10000
            or any(not isinstance(r, list) or len(r) != len(cols) for r in rows)
        ):
            raise ProjectError("Plugin table rows şekli geçersiz.")
        lineage = data["parent_row_ids" if kind == "transform" else "source_record_ids"]
        if (
            not isinstance(lineage, list)
            or len(lineage) != len(rows)
            or any(not isinstance(x, str) for x in lineage)
        ):
            raise ProjectError("Plugin tablo kaynak kimlikleri gerekli.")
        if kind == "transform" and not set(lineage) <= set(row_ids):
            raise ProjectError("Transform parent RowId kaynakta yok.")
        if kind == "importer" and len(set(lineage)) != len(lineage):
            raise ProjectError("Importer source record kimliği unique olmalı.")
    else:
        text(data["title"], 100)
        if (
            not isinstance(data["paragraphs"], list)
            or not 1 <= len(data["paragraphs"]) <= 16
        ):
            raise ProjectError("Plugin lesson1..16paragraph gerekli.")
        for v in data["paragraphs"]:
            text(v)
    no_secrets(value)
    json_data(value)
    return copy.deepcopy(value)


def input_contract(value, kind):
    fields = {
        "schema",
        "api_version",
        "kind",
        "dataset_version",
        "source_snapshot_id",
        "columns",
        "records",
        "params",
        "seed",
    }
    if (
        not isinstance(value, dict)
        or set(value) != fields
        or value["schema"] != "PluginInput/v1"
        or type(value["api_version"]) is not int
        or value["api_version"] != 1
        or value["kind"] != kind
    ):
        raise ProjectError("Plugin input API/kind/schema geçersiz.")
    text(value["dataset_version"], 100)
    text(value["source_snapshot_id"], 100)
    if type(value["seed"]) is not int or not 0 <= value["seed"] <= 2**32 - 1:
        raise ProjectError("Plugin input seed uint32 gerekli.")
    cols = value["columns"]
    rows = value["records"]
    if (
        not isinstance(cols, list)
        or not 1 <= len(cols) <= 16
        or any(
            not isinstance(c, dict) or not {"id", "name", "type"} <= c.keys()
            for c in cols
        )
    ):
        raise ProjectError("Plugin input kolon şeması gerekli.")
    for c in cols:
        for k in ("id", "name", "type"):
            text(c[k], 200)
    keys = [c["id"] for c in cols]
    if len(set(keys)) != len(keys) or not isinstance(rows, list) or len(rows) > 10000:
        raise ProjectError("Plugin input kolon/row sınırı.")
    ids = []
    for r in rows:
        if (
            not isinstance(r, dict)
            or set(r) != {"row_id", "source_record_id", "values"}
            or not isinstance(r["values"], dict)
            or set(r["values"]) != set(keys)
        ):
            raise ProjectError(
                "Plugin input RowId/SourceRecordId/value shape geçersiz."
            )
        text(r["row_id"], 200)
        text(r["source_record_id"], 200)
        ids.append(r["row_id"])
        if any(
            v is not None and type(v) not in (str, bool, int, float)
            for v in r["values"].values()
        ):
            raise ProjectError("Plugin yalnız scalar JSON input destekler.")
    if len(set(ids)) != len(ids):
        raise ProjectError("Plugin input RowId unique olmalı.")
    json_data(value, 8 * 1024**2)
    return value
