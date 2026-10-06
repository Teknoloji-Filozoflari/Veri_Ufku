"""Versioned offline content. No Qt, analytics, network or executable markup."""

import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

CONTENT = Path(__file__).parent / "content/tr.json"
SCREEN_CONTEXTS = (
    "home",
    "data",
    "prepare",
    "explore",
    "compare",
    "model",
    "report",
    "learn",
)
ARTICLE_FIELDS = {
    "id",
    "content_version",
    "locale",
    "title",
    "category",
    "summary",
    "purpose",
    "when",
    "when_not",
    "example",
    "interpretation",
    "common_mistake",
    "guide",
    "related",
    "contexts",
    "sources",
    "critical",
    "try_action",
}


def fold(text):
    # Turkish dotted/dotless i plus accent-insensitive discovery, not data collation.
    text = text.replace("İ", "i").replace("ı", "i").casefold()
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
        raise ValueError("Invalid learning text")


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9.-]{0,79}", value):
        raise ValueError("Invalid learning identifier")


def validate(data):
    if not isinstance(data, dict) or set(data) != {
        "schema_version",
        "content_version",
        "locale",
        "articles",
        "contexts",
        "actions",
    }:
        raise ValueError("Unsupported learning schema")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("Unsupported learning schema version")
    if type(data["content_version"]) is not int or data["content_version"] < 1:
        raise ValueError("Invalid learning content version")
    if (
        data["locale"] != "tr"
        or not isinstance(data["articles"], list)
        or not 1 <= len(data["articles"]) <= 500
    ):
        raise ValueError("Unsupported learning locale or article count")
    articles = {}
    for article in data["articles"]:
        if not isinstance(article, dict) or set(article) != ARTICLE_FIELDS:
            raise ValueError("Invalid learning article fields")
        identifier(article["id"])
        if article["id"] in articles:
            raise ValueError("Duplicate learning article")
        if (
            type(article["content_version"]) is not int
            or article["content_version"] < 1
            or article["locale"] != data["locale"]
        ):
            raise ValueError("Invalid article version")
        for field in (
            "title",
            "category",
            "summary",
            "purpose",
            "when",
            "when_not",
            "interpretation",
            "common_mistake",
            "critical",
        ):
            text(article[field])
        if not isinstance(article["example"], dict) or set(article["example"]) != {
            "before",
            "after",
        }:
            raise ValueError("Invalid before/after example")
        for value in article["example"].values():
            text(value)
        if (
            not isinstance(article["guide"], list)
            or not 1 <= len(article["guide"]) <= 30
        ):
            raise ValueError("Invalid learning blocks")
        for block in article["guide"]:
            if (
                not isinstance(block, dict)
                or set(block) != {"kind", "text"}
                or block["kind"] not in {"paragraph", "note"}
            ):
                raise ValueError("Unsupported learning block")
            text(block["text"])
        for field in ("related", "contexts"):
            if not isinstance(article[field], list) or not article[field]:
                raise ValueError("Invalid learning links")
            for value in article[field]:
                text(value)
            if len(article[field]) != len(set(article[field])):
                raise ValueError("Duplicate learning links")
        if not isinstance(article["sources"], list) or not article["sources"]:
            raise ValueError("Missing learning sources")
        for source in article["sources"]:
            if not isinstance(source, dict) or set(source) != {
                "title",
                "reference",
                "reviewed",
            }:
                raise ValueError("Invalid learning source")
            for value in source.values():
                text(value)
            ref = source["reference"]
            parsed = urlparse(ref)
            if not (parsed.scheme == "https" and parsed.netloc) and not re.fullmatch(
                r"docs/[a-zA-Z0-9_/.-]+\.md", ref
            ):
                raise ValueError("Unsafe source reference")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["reviewed"]):
                raise ValueError("Invalid source review date")
        if article["try_action"] is not None:
            identifier(article["try_action"])
        articles[article["id"]] = article
    if not isinstance(data["contexts"], dict) or not isinstance(data["actions"], dict):
        raise ValueError("Invalid help registry")
    for context, article_id in data["contexts"].items():
        identifier(context)
        identifier(article_id)
        if article_id not in articles:
            raise ValueError(f"Missing help article for {context}")
    if not set(SCREEN_CONTEXTS).issubset(data["contexts"]):
        raise ValueError("Missing screen help")
    # This allowlist is an implemented UI action, never a function name from content.
    if set(data["actions"]) != {"learn.example"}:
        raise ValueError("Unsupported learning action")
    for action, entry in data["actions"].items():
        if not isinstance(entry, dict) or set(entry) != {
            "article_id",
            "feature",
            "label",
        }:
            raise ValueError("Invalid learning action")
        if (
            entry["article_id"] not in articles
            or entry["feature"] != "learn.search"
            or entry["feature"] not in data["contexts"]
        ):
            raise ValueError("Missing implemented feature for learning action")
        text(entry["label"])
    for article in articles.values():
        if any(context not in data["contexts"] for context in article["contexts"]):
            raise ValueError("Missing article screen or operation binding")
        if any(value not in articles for value in article["related"]):
            raise ValueError("Broken related article")
        action = article["try_action"]
        if action and (
            action not in data["actions"]
            or data["actions"][action]["article_id"] != article["id"]
        ):
            raise ValueError("Unbound learning action")
    return articles


class Catalog:
    def __init__(self, path=CONTENT):
        raw = Path(path).read_bytes()
        if len(raw) > 2_000_000:
            raise ValueError("Learning catalog too large")
        self.data = json.loads(raw)
        self.articles = validate(self.data)
        self.index = {
            key: fold(json.dumps(value, ensure_ascii=False))
            for key, value in self.articles.items()
        }

    def search(self, query="", category="Tümü", glossary=False):
        words = fold(query[:200]).split()
        return [
            article
            for key, article in self.articles.items()
            if (category == "Tümü" or article["category"] == category)
            and (not glossary or article["category"] != "Uygulama")
            and all(word in self.index[key] for word in words)
        ]

    def article_for(self, context):
        if context not in self.data["contexts"]:
            raise ValueError(f"Missing help context: {context}")
        return self.data["contexts"][context]


def validate_bindings(root, catalog=None):
    """CI gate: every declared QML context and capability must resolve."""
    from veri_ufku.domain.capabilities import CAPABILITIES

    catalog = catalog or Catalog()
    for capability in CAPABILITIES.values():
        if not capability.help_links:
            raise ValueError(f"Missing capability help: {capability.capability_id}")
        for article_id in capability.help_links:
            if article_id not in catalog.articles:
                raise ValueError(f"Missing capability article: {article_id}")
        catalog.article_for(capability.capability_id)
    count = 0
    for path in (Path(root) / "src/veri_ufku/ui/qml").glob("*.qml"):
        source = path.read_text()
        for _, context in re.findall(
            r"""(?:helpContext\s*:|openContext\()\s*(['"])([^'"\n]+)\1""", source
        ):
            catalog.article_for(context)
            count += 1
    if count < 1:
        raise ValueError("No declared UI help bindings")
    return count
