"""Read-only Python view of saved operations. Nothing here is executed."""

import json

from veri_ufku.exports.repro import SECRET_KEY
from veri_ufku.exports.share_privacy import reason


def operation_history_python(operations):
    if not operations:
        return "İşlem yok. Python dökümü uydurulmaz."
    lines = [
        "# Veri_Ufku işlem geçmişi. Bu metin çalıştırılmaz.",
        "# Parametre değerleri yazılmaz. Sürüm kimlikleri korunur.",
        "steps = [",
    ]
    shown = list(operations)[:100]
    for index, op in enumerate(shown, start=1):
        lines.append("    " + _step(index, op) + ",")
    lines.append("]")
    if len(operations) > 100:
        lines.append("# İlk 100 adım. Devamı yazılmadı.")
    return "\n".join(lines)


def _step(index, op):
    if not isinstance(op, dict):
        return '{"step": %s, "kind": "okunamadı"}' % index
    spec = op.get("spec") if isinstance(op.get("spec"), dict) else op
    kind = _public(spec.get("kind") or op.get("capability_id") or "bilinmiyor")
    fields = {"step": index, "kind": kind}
    source = _public(spec.get("input_version_id") or "")
    output = _public(op.get("output_version_id") or op.get("version_id") or "")
    if source:
        fields["input"] = source
    if output:
        fields["output"] = output
    columns = spec.get("column_ids")
    if isinstance(columns, list) and columns:
        fields["columns"] = [_public(item) for item in columns[:20]]
    parameters = spec.get("parameters")
    if isinstance(parameters, dict) and parameters:
        keys = [
            _public(key)
            for key in list(parameters)[:20]
            if not SECRET_KEY.search(str(key)) and _public(key) != "gizli"
        ]
        if keys:
            fields["parameter_keys"] = keys
    return json.dumps(fields, ensure_ascii=False)


def _public(value):
    raw = str(value or "").replace("\n", " ").strip()[:120]
    if not raw:
        return ""
    if SECRET_KEY.search(raw) or reason(raw):
        return "gizli"
    return raw
