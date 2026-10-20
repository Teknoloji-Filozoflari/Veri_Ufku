"""Versioned lesson paths and advisory prerequisite graph, data only."""

import json
from pathlib import Path

from veri_ufku.learning.catalog import Catalog, fold, identifier, text

CONTENT = Path(__file__).parent / "content/lessons.tr.json"
KERNELS = (
    "mean-median",
    "cleaning",
    "histogram",
    "sampling",
    "ci",
    "overfitting",
    "leakage",
    "calibration",
    "time-series",
    "confounding",
)


class Curriculum:
    def __init__(self, catalog=None, data=None):
        self.catalog = catalog or Catalog()
        if data is None:
            raw = CONTENT.read_bytes()
            if len(raw) > 1000000:
                raise ValueError("Lesson catalog too large")
            data = json.loads(raw)
        self.data = data
        self.validate()
        self.lessons = {v["id"]: v for v in data["lessons"]}
        self.paths = {v["id"]: v for v in data["paths"]}

    def validate(self):
        d = self.data
        if (
            set(d)
            != {"schema", "content_version", "paths", "lessons", "capability_paths"}
            or d["schema"] != "LessonCatalog/v1"
            or type(d["content_version"]) is not int
            or d["content_version"] < 1
        ):
            raise ValueError("Unsupported lesson schema")
        paths = d["paths"]
        lessons = d["lessons"]
        if (
            not isinstance(paths, list)
            or len(paths) != 8
            or not isinstance(lessons, list)
            or not 1 <= len(lessons) <= 100
        ):
            raise ValueError("Eight bounded learning paths required")
        path_ids = []
        ids = []
        for p in paths:
            if set(p) != {"id", "title", "summary"}:
                raise ValueError("Invalid lesson path")
            identifier(p["id"])
            text(p["title"])
            text(p["summary"])
            path_ids.append(p["id"])
        if len(set(path_ids)) != 8:
            raise ValueError("Duplicate path")
        fields = {
            "id",
            "version",
            "path",
            "article_id",
            "title",
            "purpose",
            "data",
            "problem",
            "assumptions",
            "steps",
            "expected",
            "misinterpretation",
            "own_data",
            "daily_example",
            "equation",
            "prerequisites",
            "control",
            "review",
            "check",
        }
        for lesson in lessons:
            if (
                set(lesson) != fields
                or type(lesson["version"]) is not int
                or lesson["version"] < 1
            ):
                raise ValueError("Missing lesson field/version")
            ident = lesson["id"]
            identifier(ident)
            ids.append(ident)
            if (
                ident not in KERNELS
                or lesson["path"] not in path_ids
                or lesson["article_id"] not in self.catalog.articles
            ):
                raise ValueError("Missing lesson kernel/path/article")
            for k in (
                "title",
                "purpose",
                "data",
                "problem",
                "assumptions",
                "expected",
                "misinterpretation",
                "own_data",
                "daily_example",
                "equation",
            ):
                text(lesson[k])
            if (
                not isinstance(lesson["steps"], list)
                or not 1 <= len(lesson["steps"]) <= 12
            ):
                raise ValueError("Missing steps")
            for v in lesson["steps"]:
                text(v)
            c = lesson["control"]
            if (
                set(c) != {"label", "minimum", "maximum", "default", "step"}
                or any(
                    type(c[k]) is not int
                    for k in ("minimum", "maximum", "default", "step")
                )
                or not c["minimum"] <= c["default"] <= c["maximum"]
                or c["step"] <= 0
            ):
                raise ValueError("Invalid lesson slider")
            text(c["label"])
            r = lesson["review"]
            if (
                set(r) != {"date", "status", "scope", "article_version"}
                or r["status"] != "technical-reference"
                or r["article_version"]
                != self.catalog.articles[lesson["article_id"]]["content_version"]
            ):
                raise ValueError("Review missing or article version stale")
            from datetime import date

            date.fromisoformat(r["date"])
            text(r["scope"])
            check = lesson["check"]
            if (
                set(check) != {"question", "options", "correct", "feedback"}
                or not isinstance(check["options"], list)
                or not 2 <= len(check["options"]) <= 4
                or type(check["correct"]) is not int
                or not 0 <= check["correct"] < len(check["options"])
                or len(check["feedback"]) != len(check["options"])
            ):
                raise ValueError("Invalid optional self check")
            text(check["question"])
            for v in check["options"] + check["feedback"]:
                text(v)
        if set(ids) != set(KERNELS) or len(ids) != len(set(ids)):
            raise ValueError("Every implemented lab needs one lesson")
        by_id = {v["id"]: v for v in lessons}
        visited = set()
        pending = set()

        def visit(k):
            if k in pending:
                raise ValueError("Prerequisite cycle")
            if k in visited:
                return
            pending.add(k)
            prerequisites = by_id[k]["prerequisites"]
            if not isinstance(prerequisites, list) or len(prerequisites) != len(
                set(prerequisites)
            ):
                raise ValueError("Invalid prerequisites")
            for p in prerequisites:
                if p not in by_id:
                    raise ValueError("Missing prerequisite")
                visit(p)
            pending.remove(k)
            visited.add(k)

        for k in ids:
            visit(k)
        mapping = d["capability_paths"]
        if not isinstance(mapping, dict) or any(
            v not in path_ids for v in mapping.values()
        ):
            raise ValueError("Invalid module coverage map")

    def coverage(self):
        from veri_ufku.domain.capabilities import CAPABILITIES

        mapping = self.data["capability_paths"]
        if set(mapping) != set(CAPABILITIES):
            raise ValueError("Missing/stale capability learning coverage")
        out = []
        for ident, cap in CAPABILITIES.items():
            article = self.catalog.article_for(ident)
            if not cap.help_links or any(
                a not in self.catalog.articles for a in cap.help_links
            ):
                raise ValueError("Broken module learning article")
            out.append(
                dict(
                    capability_id=ident,
                    path=mapping[ident],
                    articles=list(dict.fromkeys([article, *cap.help_links])),
                    level="interactive lesson"
                    if ident.startswith("learn.lab.")
                    else "linked article; module-specific lab not claimed",
                )
            )
        return out

    def search(self, query="", path="", favorites=()):
        words = fold(query[:200]).split()
        return [
            v
            for v in self.data["lessons"]
            if (not path or v["path"] == path)
            and all(w in fold(json.dumps(v, ensure_ascii=False)) for w in words)
            and (not favorites or v["article_id"] in favorites)
        ]


def spec(parameters):
    if (
        not isinstance(parameters, dict)
        or set(parameters) != {"lesson", "value", "seed"}
        or parameters["lesson"] not in KERNELS
        or type(parameters["seed"]) is not int
        or not 0 <= parameters["seed"] <= 2**31 - 1
    ):
        raise ValueError("Invalid lab recipe")
    curriculum = Curriculum()
    lesson = curriculum.lessons[parameters["lesson"]]
    c = lesson["control"]
    v = parameters["value"]
    if (
        type(v) is not int
        or not c["minimum"] <= v <= c["maximum"]
        or (v - c["minimum"]) % c["step"]
    ):
        raise ValueError("Lab slider outside budget")
    return dict(parameters), lesson, curriculum
