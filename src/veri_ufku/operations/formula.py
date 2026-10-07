"""Bounded expression AST interpreted as data; never eval, exec or attribute access."""

import ast
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from veri_ufku.storage.project_model import ProjectError

FUNCTIONS = {"col", "abs", "coalesce", "ifelse", "lower", "upper", "length", "round"}
BINARY = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}
COMPARE = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
}


def parse(expression, columns):
    if (
        not isinstance(expression, str)
        or not expression.strip()
        or len(expression) > 4096
    ):
        raise ProjectError("Formül boş olamaz; en fazla4096 karakter.")
    try:
        root = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError, RecursionError) as error:
        raise ProjectError("Formül sözdizimi geçersiz.") from error
    if sum(1 for _ in ast.walk(root)) > 256:
        raise ProjectError("Formül256 AST düğüm sınırını aşıyor.")
    available = {c["id"] for c in columns}
    referenced = []

    def visit(node, depth=0):
        if depth > 16:
            raise ProjectError("Formül derinliği16 sınırını aşıyor.")

        def child(n):
            return visit(n, depth + 1)

        if isinstance(node, ast.Constant):
            value = node.value
            if type(value) in (int, float):
                raw = (
                    str(value)
                    if type(value) is int
                    else ast.get_source_segment(expression, node)
                )
                number = Decimal(raw)
                if (
                    not number.is_finite()
                    or len(number.as_tuple().digits) > 80
                    or abs(number.adjusted()) > 100
                ):
                    raise ProjectError("Formül sayısal sabiti sınır dışında.")
                return {"op": "number", "value": str(number)}
            if value is None or type(value) in (str, bool):
                return {"op": "literal", "value": value}
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in FUNCTIONS
            and not node.keywords
        ):
            name = node.func.id
            counts = {
                "col": (1,),
                "abs": (1,),
                "lower": (1,),
                "upper": (1,),
                "length": (1,),
                "round": (2,),
                "ifelse": (3,),
                "coalesce": tuple(range(2, 9)),
            }
            if len(node.args) not in counts[name]:
                raise ProjectError("Formül fonksiyonunun argüman sayısı geçersiz.")
            if name == "col":
                n = node.args[0]
                if not isinstance(n, ast.Constant) or n.value not in available:
                    raise ProjectError(
                        "col() bilinen kalıcı ColumnId metni gerektirir."
                    )
                if n.value not in referenced:
                    referenced.append(n.value)
                return {"op": "column", "id": n.value}
            return {"op": "call", "name": name, "args": [child(n) for n in node.args]}
        if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
            return {
                "op": BINARY[type(node.op)],
                "args": [child(node.left), child(node.right)],
            }
        if isinstance(node, ast.UnaryOp) and isinstance(
            node.op, (ast.USub, ast.UAdd, ast.Not)
        ):
            return {
                "op": "neg"
                if isinstance(node.op, ast.USub)
                else "pos"
                if isinstance(node.op, ast.UAdd)
                else "not",
                "args": [child(node.operand)],
            }
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and type(node.ops[0]) in COMPARE
        ):
            return {
                "op": COMPARE[type(node.ops[0])],
                "args": [child(node.left), child(node.comparators[0])],
            }
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            return {
                "op": "and" if isinstance(node.op, ast.And) else "or",
                "args": [child(n) for n in node.values],
            }
        raise ProjectError(
            "Bu AST düğümü/fonksiyon izinli değil: öznitelik, indeks, import, lambda, comprehension ve kullanıcı kodu çalışmaz."
        )

    return visit(root.body), referenced


def numeric(value):
    if type(value) is bool or not isinstance(value, (int, float, Decimal)):
        raise ProjectError(
            "Formül aritmetiği sayısal tür gerektirir; örtük metin/bool dönüşümü yok."
        )
    number = Decimal.from_float(value) if isinstance(value, float) else Decimal(value)
    if not number.is_finite():
        raise ProjectError(
            "Formülde NaN/inf açıkça dönüştürülmeli; sonlu sayı gerekiyor."
        )
    return number


def evaluate(tree, values, policy, diagnostics):
    op = tree["op"]
    if op == "column":
        return values[tree["id"]]
    if op == "number":
        return Decimal(tree["value"])
    if op == "literal":
        return tree["value"]
    args = tree.get("args", [])
    if op == "call" and tree["name"] in ("ifelse", "coalesce"):
        if tree["name"] == "ifelse":
            condition = evaluate(args[0], values, policy, diagnostics)
            if condition is None:
                return None
            if type(condition) is not bool:
                raise ProjectError("ifelse koşulu Boolean olmalı.")
            return evaluate(args[1 if condition else 2], values, policy, diagnostics)
        for arg in args:
            value = evaluate(arg, values, policy, diagnostics)
            if value is not None:
                return value
        return None
    v = [evaluate(a, values, policy, diagnostics) for a in args]
    if op in ("and", "or"):
        if any(x is not None and type(x) is not bool for x in v):
            raise ProjectError("and/or Boolean veya null gerektirir.")
        decisive = False if op == "and" else True
        return decisive if decisive in v else None if None in v else not decisive
    if any(x is None for x in v):
        return None
    with localcontext() as ctx:
        ctx.prec = 1200
        if op in ("+", "-", "*", "/"):
            a, b = map(numeric, v)
            if op == "/" and not b:
                diagnostics["zero_divisions"] += 1
                if policy == "reject":
                    raise ProjectError(
                        "Formülde sıfıra bölme; işlem uygulanmadı. Açık null politikasını seçebilirsiniz."
                    )
                return None
            return (
                a + b
                if op == "+"
                else a - b
                if op == "-"
                else a * b
                if op == "*"
                else a / b
            )
        if op in ("==", "!=", "<", "<=", ">", ">="):
            a, b = v
            if type(a) is not type(b) and not all(
                isinstance(x, (Decimal, int, float)) and type(x) is not bool for x in v
            ):
                raise ProjectError("Formül karşılaştırma türleri uyuşmuyor.")
            if all(
                isinstance(x, (Decimal, int, float)) and type(x) is not bool for x in v
            ):
                a, b = map(numeric, v)
            return (
                a == b
                if op == "=="
                else a != b
                if op == "!="
                else a < b
                if op == "<"
                else a <= b
                if op == "<="
                else a > b
                if op == ">"
                else a >= b
            )
        if op in ("neg", "pos"):
            return -numeric(v[0]) if op == "neg" else numeric(v[0])
        if op == "not":
            if type(v[0]) is not bool:
                raise ProjectError("not Boolean gerektirir.")
            return not v[0]
        if op == "call":
            name = tree["name"]
            if name == "abs":
                return abs(numeric(v[0]))
            if name in ("lower", "upper", "length"):
                if not isinstance(v[0], str):
                    raise ProjectError("Metin fonksiyonu String gerektirir.")
                return (
                    len(v[0])
                    if name == "length"
                    else v[0].lower()
                    if name == "lower"
                    else v[0].upper()
                )
            if name == "round":
                number, digits = map(numeric, v)
                if digits != digits.to_integral_value() or not 0 <= digits <= 38:
                    raise ProjectError("round basamak sayısı0–38 tam sayı olmalı.")
                result = number.quantize(
                    Decimal(1).scaleb(-int(digits)), rounding=ROUND_HALF_EVEN
                )
                diagnostics["rounded_values"] += result != number
                return result
    raise ProjectError("Formül düğümü desteklenmiyor.")
