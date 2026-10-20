"""Export/report scope matches the filtered and stably sorted table; all columns explicit."""

import polars as pl

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import filtered
from veri_ufku.storage.project_model import ProjectError


def scoped(request, spec):
    view = ViewSpec.from_dict(spec.view) if spec.scope == "view" else ViewSpec()
    query, schema, names = filtered(request, view)
    if view.sort_column:
        name = names[view.sort_column]
        if schema[name].is_nested() or schema[name] == pl.Binary:
            raise ProjectError(
                "Nested/binary görünüm sıralaması exportta desteklenmiyor."
            )
        token = "__vu_export_order"
        while token in schema:
            token += "_"
        query = query.with_row_index(token).sort(
            [name, token], descending=[view.descending, False], nulls_last=True
        )
    return query, schema, view
