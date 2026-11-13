"""Dependency-free DOCX writer for the report export.

A DOCX file is a ZIP container of OOXML parts. The writer emits the minimal,
valid part set needed for a text report: no macros, no external references and
no network access. Only report text produced by the report builder is written.
"""

import io
import zipfile

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:pPr><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Preformatted"><w:name w:val="Preformatted"/><w:rPr><w:rFonts w:ascii="DejaVu Sans Mono" w:hAnsi="DejaVu Sans Mono"/><w:sz w:val="18"/></w:rPr></w:style>
</w:styles>"""


def escape(value):
    """XML text escape; control characters are dropped, not silently kept."""
    out = []
    for char in str(value):
        if char in ("&", "<", ">"):
            out.append({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[char])
        elif char == '"':
            out.append("&quot;")
        elif char == "\t" or ord(char) >= 32:
            out.append(char)
    return "".join(out)


def _paragraph(text, style=None, bold=False):
    properties = ""
    if style:
        properties += '<w:pPr><w:pStyle w:val="' + style + '"/></w:pPr>'
    run = "<w:r>"
    if bold:
        run += "<w:rPr><w:b/></w:rPr>"
    run += '<w:t xml:space="preserve">' + escape(text) + "</w:t></w:r>"
    return "<w:p>" + properties + run + "</w:p>"


def _text_blocks(value):
    """Flatten the report value into (style, text) paragraphs."""
    spec = value["spec"]
    out = [(None, spec["title"]), ("Heading2", "Protokol: " + spec["protocol"])]
    out.append((None, spec["protocol_note"]))
    stale = value["stale"]
    out.append(
        (
            None,
            "Güncellik: "
            + (
                "STALE"
                if stale
                else "Seçilen dataset/run için daha yeni kayıt bulunmadı."
            ),
        )
    )
    for block in value["blocks"]:
        out.append(("Heading1", block["title"]))
        if block["kind"] == "table" and block.get("data"):
            rows = block["data"]
            names = list(rows[0])
            out.append(("Preformatted", " | ".join(names)))
            for row in rows:
                out.append(
                    ("Preformatted", " | ".join(str(row[name]) for name in names))
                )
            continue
        for key, item in block.items():
            if key in ("title", "kind", "image", "attachments", "references"):
                continue
            if key == "findings":
                continue
            if isinstance(item, str):
                text = item
            else:
                import json

                text = json.dumps(item, ensure_ascii=False, indent=2, default=str)
            for line in text.splitlines() or [""]:
                out.append(("Preformatted" if key not in ("text",) else None, line))
        for name in block.get("attachments", []):
            out.append((None, "Ek: " + name))
        for ref in block.get("references", []):
            out.append((None, ref["title"] + " — " + ref["url"]))
    out.append(("Heading1", "Sınırlamalar"))
    for limitation in value.get("limitations") or []:
        out.append((None, limitation))
    return out


def document(value):
    """Return the DOCX bytes for a scientific report value."""
    body = []
    for index, (style, text) in enumerate(_text_blocks(value)):
        body.append(_paragraph(text, style=style, bold=(index == 0 and style is None)))
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="' + NS + '"><w:body>' + "".join(body) + "<w:sectPr/>"
        "</w:body></w:document>"
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", ROOT_RELS)
        archive.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS)
        archive.writestr("word/styles.xml", STYLES)
        archive.writestr("word/document.xml", document_xml)
    raw = out.getvalue()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip() is not None:
            raise ValueError("DOCX paket doğrulaması başarısız.")
        if "word/document.xml" not in archive.namelist():
            raise ValueError("DOCX belge parçası eksik.")
    return raw
