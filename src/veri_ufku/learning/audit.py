"""Structural help and shared UI regression gate; semantic review stays human."""

import re
from pathlib import Path
from xml.etree import ElementTree

from veri_ufku.learning.catalog import Catalog, validate_bindings


def qml_blocks(source, types):
    for match in re.finditer(r"\b(" + "|".join(types) + r")\s*\{", source):
        level, quote, escaped, index = 1, None, False, match.end()
        top = []
        while index < len(source) and level:
            char = source[index]
            if quote:
                if level == 1:
                    top.append(char)
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
            elif char in "\"'":
                quote = char
                if level == 1:
                    top.append(char)
            elif char == "{":
                level += 1
            elif char == "}":
                level -= 1
            elif level == 1:
                top.append(char)
            index += 1
        yield match[1], "".join(top), source[match.start() : index]


def audit(root, catalog=None):
    root = Path(root)
    catalog = catalog or Catalog()
    bindings = validate_bindings(root, catalog)
    articles = []
    lexical_review = []
    for article in catalog.articles.values():
        articles.append(
            dict(
                id=article["id"],
                version=article["content_version"],
                summary=bool(article["summary"].strip()),
                example=all(article["example"].values()),
                suitability=bool(article["when"] and article["when_not"]),
                interpretation=bool(article["interpretation"]),
                contexts=article["contexts"],
            )
        )
        # Candidates, not a classifier of truth or reading difficulty.
        for field in ("summary", "critical", "interpretation"):
            if re.search(
                r"\b(fit|fold|scope|fingerprint|vocab|ddof|exact|asymptotic)\b|kesin|garanti|henüz",
                article[field],
                re.I,
            ):
                lexical_review.append(
                    dict(article=article["id"], field=field, text=article[field])
                )
    qml = root / "src/veri_ufku/ui/qml"
    controls = []
    for path in sorted(qml.glob("*.qml")):
        if path.stem in {
            "UiCombo",
            "UiTextField",
            "UiTextArea",
            "UiSpinBox",
            "ConnectorField",
        }:
            continue
        source = path.read_text()
        if re.search(r"\b(ComboBox|TextField|TextArea|SpinBox)\s*\{", source):
            raise ValueError(f"Use the accessible shared control: {path.name}")
        for kind, top, _ in qml_blocks(
            source,
            ("UiCombo", "UiTextField", "UiTextArea", "UiSpinBox", "ConnectorField"),
        ):
            if not re.search(r"\b(accessibleLabel|Accessible\.name)\s*:", top):
                raise ValueError(f"Missing accessible purpose: {path.name}: {kind}")
            if re.search(r'(?:accessibleLabel|Accessible\.name)\s*:\s*""', top):
                raise ValueError(f"Empty accessible purpose: {path.name}")
            controls.append(dict(file=path.name, kind=kind, properties=top.strip()))
    tree = ElementTree.parse(root / "src/veri_ufku/learning/i18n/en.ts")
    messages = tree.findall(".//message")
    for message in messages:
        translation = message.find("translation")
        if (
            translation is None
            or not translation.text
            or translation.get("type") == "unfinished"
        ):
            raise ValueError("Incomplete core English translation")
    return dict(
        content_version=catalog.data["content_version"],
        articles=articles,
        ui_bindings=bindings,
        accessible_controls=controls,
        core_english_messages=len(messages),
        lexical_candidates=lexical_review,
        semantic_review="Lexical candidates require manual review; this is not a readability or scientific validation test.",
        assistive_technology_test=False,
        real_user_test=False,
    )
