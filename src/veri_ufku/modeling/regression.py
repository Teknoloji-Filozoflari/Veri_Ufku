"""Bounded initial regression candidates, with explicit resource limits."""

from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge

from veri_ufku.modeling.family_contracts import REGRESSION_FAMILIES, FamilyOptions
from veri_ufku.storage.project_model import ProjectError

CATALOG = {
    "baseline": "Eğitim hedefinin merkezini tahmin eder; özellik ilişkisi öğrenmez.",
    "linear": "Özelliklerin doğrusal katkılarını öğrenir; doğrusal ilişki varsayar.",
    "ridge": "Doğrusal katsayıları küçülterek aşırı öğrenmeyi sınırlar; scaling önerilir.",
    "forest": "Sınırlı derinlikte ağaçlarla doğrusal olmayan ilişkileri öğrenir; daha maliyetlidir.",
}

CATALOG.update(
    {
        m: "Faz48 bounded family adapter; explicit selection, same validation plan"
        for m in REGRESSION_FAMILIES
    }
)


def settings(value):
    if not isinstance(value, dict) or set(value) - {
        "candidates",
        "alpha",
        "trees",
        "depth",
        "unit",
        "family_options",
        "explicit_model",
        "uncertainty",
    }:
        raise ProjectError("Regresyon aday ayarları geçersiz.")
    out = dict(
        candidates=["baseline", "linear", "ridge", "forest"],
        alpha=1.0,
        trees=50,
        depth=8,
        unit="hedef birimi",
    )
    out.update(value)
    if (
        not isinstance(out["candidates"], list)
        or not out["candidates"]
        or len(set(out["candidates"])) != len(out["candidates"])
        or any(c not in CATALOG for c in out["candidates"])
        or "baseline" not in out["candidates"]
    ):
        raise ProjectError("Baseline ve en fazla dört desteklenen aday seçin.")
    if type(out["alpha"]) not in (int, float) or out["alpha"] not in (0.1, 1.0, 10.0):
        raise ProjectError("Ridge alpha yalnız 0.1, 1 veya 10 olabilir.")
    if type(out["trees"]) is not int or out["trees"] not in (25, 50, 100):
        raise ProjectError("Forest ağaç sayısı yalnız 25, 50 veya 100 olabilir.")
    if type(out["depth"]) is not int or out["depth"] not in (4, 8, 12):
        raise ProjectError("Forest derinliği yalnız 4, 8 veya 12 olabilir.")
    if not isinstance(out["unit"], str) or not 1 <= len(out["unit"].strip()) <= 80:
        raise ProjectError("Hedef ölçüm birimini 1..80 karakterle belirtin.")
    if "family_options" in out:
        out["family_options"] = FamilyOptions.from_dict(out["family_options"]).data()
        if (
            out.get("explicit_model") not in out["candidates"]
            or out.get("explicit_model") not in REGRESSION_FAMILIES
        ):
            raise ProjectError(
                "Faz48 explicit model seçilmeli; tek en iyi aday önerilmez."
            )
    elif any(m in REGRESSION_FAMILIES for m in out["candidates"]):
        raise ProjectError("Faz48 family_options ve explicit_model gerekli.")
    if "uncertainty" in out:
        from veri_ufku.modeling.uncertainty import UncertaintySpec

        out["uncertainty"] = UncertaintySpec.from_dict(
            out["uncertainty"], "regression"
        ).data()
    return out


def estimator(candidate, config, strategy, seed):
    return {
        "baseline": lambda: DummyRegressor(strategy=strategy),
        "linear": lambda: LinearRegression(n_jobs=1),
        "ridge": lambda: Ridge(alpha=config["alpha"]),
        "forest": lambda: RandomForestRegressor(
            n_estimators=config["trees"],
            max_depth=config["depth"],
            min_samples_leaf=2,
            random_state=seed,
            n_jobs=1,
        ),
    }[candidate]()
