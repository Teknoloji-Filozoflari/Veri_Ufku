"""Native dtype strings are parsed through a closed grammar, never evaluated."""

import ast
import re

import polars as pl

from veri_ufku.importers.native import PRIMITIVES
from veri_ufku.storage.project_model import ProjectError


def dtype_of(value, depth=0):
    if depth > 16 or not isinstance(value, str) or len(value) > 65536:
        raise ProjectError("Tür derinliği/boyutu sınırı aşıldı.")
    aliases = {
        "text": pl.String,
        "int64": pl.Int64,
        "float64": pl.Float64,
        "decimal": pl.Decimal(38, 6),
        "date": pl.Date,
        "datetime": pl.Datetime("us"),
        "boolean": pl.Boolean,
    }
    if value in aliases:
        return aliases[value]
    if value in PRIMITIVES:
        return PRIMITIVES[value]
    m = re.fullmatch(r"Decimal\(precision=(\d+), scale=(\d+)\)", value)
    if m and 1 <= int(m[1]) <= 38 and 0 <= int(m[2]) <= int(m[1]):
        return pl.Decimal(int(m[1]), int(m[2]))
    m = re.fullmatch(
        r"Datetime\(time_unit='(ns|us|ms)', time_zone=(None|'([^']+)')\)", value
    )
    if m:
        return pl.Datetime(m[1], m[3])
    if value.startswith("List(") and value.endswith(")"):
        return pl.List(dtype_of(value[5:-1], depth + 1))
    if value.startswith("Struct(") and value.endswith(")"):
        try:
            node = ast.parse(value[7:-1], mode="eval").body
            if not isinstance(node, ast.Dict) or not 1 <= len(node.keys) <= 256:
                raise ProjectError("Struct tür sözleşmesi geçersiz.")
            fields = {}
            for key, item in zip(node.keys, node.values, strict=True):
                if (
                    not isinstance(key, ast.Constant)
                    or not isinstance(key.value, str)
                    or key.value in fields
                ):
                    raise ProjectError("Struct tür alanı geçersiz.")
                fields[key.value] = dtype_of(ast.unparse(item), depth + 1)
            return pl.Struct(fields)
        except (SyntaxError, RecursionError) as error:
            raise ProjectError("Struct türü çözümlenemedi.") from error
    raise ProjectError(
        "Bu dönüşüm native skaler tür gerektirir; nested/binary/duration desteklenmiyor."
    )
