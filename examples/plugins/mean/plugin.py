"""Independent API1 example: selected numeric column arithmetic mean, no downloads."""

import math


def run(request, context):
    column = request["columns"][0]["id"]
    values = []
    used = []
    for record in request["records"]:
        context.check()
        value = record["values"][column]
        if value is None:
            continue
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Only finite numbers")
        if isinstance(value, int) and abs(value) > 2**53:
            raise ValueError("Integer cannot be safely represented by this example")
        values.append(value)
        used.append(record["row_id"])
    if not values:
        raise ValueError("No numeric observations")
    return dict(
        schema="PluginOutput/v1",
        kind="stat",
        summary="Seçili sayısal kolonun aritmetik ortalaması",
        data=dict(metrics=dict(mean=math.fsum(values) / len(values), n=len(values))),
        used_row_ids=used,
        warnings=[
            "Null satırlar dışlandı; ağırlıksız aritmetik ortalama, nedensel veya inferential sonuç değildir."
        ],
    )
