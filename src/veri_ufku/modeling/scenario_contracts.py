"""Closed, bounded declarative scenario recipes; never executable expressions."""

import copy
import math
import re
from dataclasses import dataclass

from veri_ufku.storage.project_model import ProjectError

METHODS = (
    "monte-carlo",
    "linear",
    "mixed-integer",
    "nonlinear",
    "what-if",
    "model-optimize",
)
LIMITATIONS = [
    "Senaryo varsayımdır; tahmin farkı veya optimum nedensel etki değildir.",
    "Parametre belirsizliği bilgi/parametre; ölçüm belirsizliği ölçüm değişkenliğidir. Tür kullanıcı beyanıdır; otomatik ayrıştırılmaz.",
    "Monte Carlo hatası sonlu draw hatasıdır; input varsayımı, model hatası veya gerçek dünya belirsizliğini ölçmez.",
    "Sensitivity keşifseldir: korelasyonlu girdilerde marjinal ilişki bağımsız katkı veya neden değildir.",
    "Feasible yalnız kayıtlı matematiksel kısıtlara göredir; gerçek dünyada uygulanabilirlik doğrulanmadı.",
    "SLSQP yerel aday üretir; global optimum veya global infeasibility kanıtı değildir.",
    "Model geçerliliği fit satırlarının marjinal aralıklarıyla sınırlı kontrol edilir; ortak destek ve gelecek geçerliliği garanti edilmez.",
    "Kaynak kayıtlar/dış kaynaklar değiştirilmez; otomatik model eğitimi veya dış eylem yok.",
]


def closed(v, required, optional=()):
    if (
        not isinstance(v, dict)
        or not set(required) <= set(v)
        or set(v) - set(required) - set(optional)
    ):
        raise ProjectError(
            "Senaryo alanları eksik/bilinmeyen; declarative şemayı kullanın."
        )


def number(v):
    if type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e12:
        raise ProjectError("Sonlu, mutlak değeri ≤1e12 sayı gerekli.")
    return float(v)


def integer(v, low, high):
    if type(v) is not int or not low <= v <= high:
        raise ProjectError(f"Tam sayı {low}..{high} aralığında olmalı.")


def unit_text(v):
    if (
        not isinstance(v, str)
        or not 1 <= len(v) <= 96
        or not re.fullmatch(r"[A-Za-z0-9_ */().^+-]+", v)
    ):
        raise ProjectError(
            "Birim açık Pint ifadesi olmalı; boyutsuz için dimensionless."
        )


def quantity(v):
    closed(v, ("value", "unit"))
    number(v["value"])
    unit_text(v["unit"])


@dataclass(frozen=True)
class ScenarioSpec:
    recipe: dict

    @classmethod
    def from_dict(cls, raw):
        closed(
            raw,
            ("method", "variables", "objective", "assumptions"),
            (
                "seed",
                "draws",
                "dependence",
                "correlation",
                "constraints",
                "direction",
                "seconds",
                "tolerance",
                "gap",
                "maxiter",
                "model",
                "point",
            ),
        )
        v = copy.deepcopy(raw)
        if (
            v["method"] not in METHODS
            or not isinstance(v["assumptions"], str)
            or not 1 <= len(v["assumptions"]) <= 1000
        ):
            raise ProjectError("Yöntem ve açık input varsayımları gerekli.")
        variables = v["variables"]
        if not isinstance(variables, list) or not 1 <= len(variables) <= 16:
            raise ProjectError("1..16 input/decision variable seçin.")
        names = []
        for x in variables:
            closed(
                x,
                ("name", "unit"),
                ("distribution", "uncertainty", "lower", "upper", "initial", "integer"),
            )
            name = x["name"]
            if (
                not isinstance(name, str)
                or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_:-]{0,95}", name)
                or name in names
            ):
                raise ProjectError(
                    "Variable kimliği benzersiz ve sınırlı ASCII olmalı."
                )
            names.append(name)
            unit_text(x["unit"])
            for k in ("lower", "upper", "initial"):
                if x.get(k) is not None:
                    number(x[k])
            if (
                x.get("lower") is not None
                and x.get("upper") is not None
                and x["lower"] > x["upper"]
            ):
                raise ProjectError("Variable alt sınırı üst sınırı aşamaz.")
            if type(x.get("integer", False)) is not bool:
                raise ProjectError("integer açık boolean olmalı.")
            if x.get("integer", False) and v["method"] != "mixed-integer":
                raise ProjectError("Integer karar yalnız mixed-integer yolunda.")
            if v["method"] == "monte-carlo":
                if x.get("uncertainty") not in ("parameter", "measurement"):
                    raise ProjectError(
                        "Her dağılımın parameter/measurement belirsizliğini seçin."
                    )
                d = x.get("distribution")
                if not isinstance(d, dict):
                    raise ProjectError("Dağılım şablonu gerekli.")
                if d.get("kind") == "normal":
                    closed(d, ("kind", "mean", "sd"))
                    number(d["mean"])
                    if number(d["sd"]) <= 0:
                        raise ProjectError("Normal sd pozitif olmalı.")
                elif d.get("kind") == "uniform":
                    closed(d, ("kind", "low", "high"))
                    if number(d["low"]) >= number(d["high"]):
                        raise ProjectError("Uniform low < high gerekli.")
                elif d.get("kind") == "triangular":
                    closed(d, ("kind", "low", "mode", "high"))
                    if (
                        not number(d["low"]) <= number(d["mode"]) <= number(d["high"])
                        or d["low"] == d["high"]
                    ):
                        raise ProjectError(
                            "Triangular low≤mode≤high ve low<high gerekli."
                        )
                else:
                    raise ProjectError("Normal/uniform/triangular şablonu seçin.")
                if any(k in x for k in ("lower", "upper", "initial", "integer")):
                    raise ProjectError(
                        "Simulation truncate/decision bounds desteklenmiyor; dağılım parametrelerini kullanın."
                    )
            elif "distribution" in x or "uncertainty" in x:
                raise ProjectError("Dağılım yalnız Monte Carlo yolunda.")
        n = len(variables)
        obj = v["objective"]
        closed(obj, ("unit",), ("offset", "linear", "quadratic"))
        unit_text(obj["unit"])
        if "model" not in v:
            if "linear" not in obj or len(obj["linear"]) != n:
                raise ProjectError(
                    "Objective linear katsayı sayısı input sayısıyla aynı olmalı."
                )
            for q in obj["linear"]:
                quantity(q)
            number(obj.get("offset", 0))
            if "quadratic" in obj:
                if (
                    v["method"] not in ("monte-carlo", "nonlinear")
                    or len(obj["quadratic"]) != n
                    or any(len(row) != n for row in obj["quadratic"])
                ):
                    raise ProjectError(
                        "Quadratic yalnız simulation/nonlinear ve n×n olmalı."
                    )
                for row in obj["quadratic"]:
                    for q in row:
                        quantity(q)
        else:
            if v["method"] not in ("what-if", "model-optimize") or set(obj) != {"unit"}:
                raise ProjectError(
                    "Frozen model objective yalnız what-if/model-optimize ve unit alır."
                )
            closed(v["model"], ("record_id",))
            if not isinstance(v["model"]["record_id"], str) or not re.fullmatch(
                r"result:[a-f0-9-]+", v["model"]["record_id"]
            ):
                raise ProjectError("Projede kayıtlı model record_id seçin.")
        if v["method"] in ("what-if", "model-optimize") and "model" not in v:
            raise ProjectError("Model senaryosu frozen model referansı ister.")
        if v["method"] == "monte-carlo":
            integer(v.get("seed"), 0, 2**32 - 1)
            integer(v.get("draws"), 256, 100000)
            if v.get("dependence") not in ("independent", "normal-correlation"):
                raise ProjectError(
                    "Bağımsızlık veya normal-correlation açık seçilmeli."
                )
            if v["dependence"] == "normal-correlation":
                if any(x["distribution"]["kind"] != "normal" for x in variables):
                    raise ProjectError(
                        "Correlated şablon yalnız joint-normal; başka copula desteklenmiyor."
                    )
                c = v.get("correlation")
                if (
                    not isinstance(c, list)
                    or len(c) != n
                    or any(not isinstance(r, list) or len(r) != n for r in c)
                ):
                    raise ProjectError("Correlation n×n matrisi gerekli.")
                for row in c:
                    for val in row:
                        number(val)
            elif "correlation" in v:
                raise ProjectError("Independent yolunda gizli correlation yok.")
            if any(
                k in v
                for k in (
                    "constraints",
                    "direction",
                    "seconds",
                    "tolerance",
                    "gap",
                    "maxiter",
                    "model",
                    "point",
                )
            ):
                raise ProjectError(
                    "Simulation yalnız dağılım/seed/draw/objective alanları alır."
                )
        else:
            if any(k in v for k in ("seed", "draws", "dependence", "correlation")):
                raise ProjectError(
                    "Solver deterministik; simulation alanlarını kaldırın."
                )
            constraints = v.setdefault("constraints", [])
            if not isinstance(constraints, list) or len(constraints) > 64:
                raise ProjectError("En fazla64 linear constraint.")
            for con in constraints:
                closed(con, ("linear", "unit", "sense", "rhs"))
                unit_text(con["unit"])
                if con["sense"] not in ("le", "ge", "eq") or len(con["linear"]) != n:
                    raise ProjectError("Constraint le/ge/eq ve n katsayı ister.")
                for q in con["linear"]:
                    quantity(q)
                number(con["rhs"])
            if v.setdefault("direction", "min") not in ("min", "max"):
                raise ProjectError("Objective min/max olmalı.")
            if (
                not 1e-6 <= number(v.setdefault("seconds", 30)) <= 600
                or not 1e-9 <= number(v.setdefault("tolerance", 1e-6)) <= 1e-2
                or not 0 <= number(v.setdefault("gap", 1e-4)) <= 0.1
            ):
                raise ProjectError("Solver süre/tolerance/gap aralığı geçersiz.")
            integer(v.setdefault("maxiter", 1000), 1, 10000)
            if v["method"] in ("nonlinear", "model-optimize"):
                if any(
                    x.get("lower") is None
                    or x.get("upper") is None
                    or x.get("initial") is None
                    or not x["lower"] <= x["initial"] <= x["upper"]
                    for x in variables
                ):
                    raise ProjectError(
                        "Bounded nonlinear sonlu lower/upper ve içinde initial ister."
                    )
            if v["method"] == "mixed-integer" and not any(
                x.get("integer") for x in variables
            ):
                raise ProjectError("Mixed integer en az bir integer variable ister.")
            if v["method"] == "what-if":
                if not isinstance(v.get("point"), list) or len(v["point"]) != n:
                    raise ProjectError("What-if açık n değerli point ister.")
                for x in v["point"]:
                    number(x)
            elif "point" in v:
                raise ProjectError("Point yalnız what-if yolunda.")
        return cls(v)

    def data(self):
        return copy.deepcopy(self.recipe)


def example(method):
    sim = method == "monte-carlo"
    variables = [dict(name="x", unit="meter")]
    if sim:
        variables[0].update(
            distribution=dict(kind="normal", mean=10, sd=2), uncertainty="measurement"
        )
    else:
        variables[0].update(lower=0, upper=10, initial=1)
        if method == "mixed-integer":
            variables[0]["integer"] = True
    v = dict(
        method=method,
        variables=variables,
        objective=dict(unit="meter", linear=[dict(value=1, unit="dimensionless")]),
        assumptions="Kullanıcı beyanı: x ölçümü metre; örnek input varsayımları gerçek kaynaktan öğrenilmedi.",
    )
    if sim:
        v.update(seed=42, draws=10000, dependence="independent")
    elif method == "nonlinear":
        v["objective"] = dict(
            unit="meter**2",
            offset=9,
            linear=[dict(value=-6, unit="meter")],
            quadratic=[[dict(value=2, unit="dimensionless")]],
        )
    return v


def public_report(value):
    import copy

    out = copy.deepcopy(value)
    domain = out.get("output", {}).get("model_domain")
    if domain:
        domain.pop("fit_row_ids", None)
        domain.pop("fit_source_record_ids", None)
    return out
