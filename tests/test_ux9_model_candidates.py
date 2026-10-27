"""UX9: gerekçeli adaylar; sızıntı politikası; kullanıcı seçmeden fit yok."""

from veri_ufku.modeling.candidates import suggest_candidates
from veri_ufku.modeling.contracts import PreparationSpec
from veri_ufku.modeling.plan import blueprint


def test_candidates_marked_aday_no_autofit():
    bundle = suggest_candidates("classification", has_group=True, has_time=False)
    assert bundle["status"] == "aday"
    assert bundle["applied"] is False
    assert bundle["auto_fit"] is False
    assert bundle["selected_method"] is None
    assert bundle["structure"] == "group"
    assert bundle["structure_preserved"] is True
    assert (
        "eğitim fold" in bundle["leakage_policy"].lower()
        or "eğitim" in bundle["leakage_policy"].lower()
    )
    assert "bir kez" in bundle["test_policy"].lower()
    assert bundle["starter_model"] == "baseline"
    assert {c["id"] for c in bundle["candidates"]} >= {"baseline", "logistic", "forest"}
    for candidate in bundle["candidates"]:
        assert candidate["status"] == "aday"
        assert candidate["selected"] is False
        assert candidate["fitted"] is False
        assert candidate["why_suitable"]
        assert candidate["when_not_suitable"]
        assert candidate["metrics"]


def test_regression_candidates_preserve_time_structure():
    bundle = suggest_candidates("regression", has_group=False, has_time=True)
    assert bundle["structure"] == "time"
    assert bundle["auto_fit"] is False
    assert {c["id"] for c in bundle["candidates"]} >= {
        "baseline",
        "linear",
        "ridge",
        "forest",
    }


def test_preprocessing_steps_learn_on_training_fold_only():
    """Sızıntı kapısı: ölçekleme/imputasyon/encoding learned_scope=training_fold."""
    columns = [
        {
            "id": "col:x",
            "name": "x",
            "type": "Float64",
            "physical_type": "Float64",
        },
        {
            "id": "col:cat",
            "name": "cat",
            "type": "String",
            "physical_type": "String",
        },
        {
            "id": "col:y",
            "name": "y",
            "type": "Float64",
            "physical_type": "Float64",
        },
    ]
    # Minimal semantics + history for blueprint
    semantics = {}
    history = {"findings": []}
    spec = PreparationSpec.from_dict(
        dict(
            purpose="regression",
            features=["col:x", "col:cat"],
            target="col:y",
            family="linear",
            history_action="review",
            missing_indicator=False,
            imputation_neighbors=5,
            imputation_iterations=10,
            imputation_seed=42,
            numeric_imputation="median",
            categorical_imputation="most_frequent",
            encoding="onehot",
            scaling="standard",
            date_features=False,
            selection="none",
            group="",
            time="",
            allow_identifiers=False,
            prediction_context="",
            history_note="",
            invalid_numeric="reject",
            precision="reject",
            source_version="ds:test",
        )
    )
    plan = blueprint(spec, columns, semantics, history)
    learned = [
        s
        for s in plan["steps"]
        if s["kind"]
        in (
            "standard_scale",
            "impute_numeric",
            "impute_category",
            "encode_onehot",
            "encode_ordinal",
            "tfidf",
            "select_variance",
        )
    ]
    assert learned, "beklenen öğrenilen ön işleme adımı yok"
    assert all(s["learned_scope"] == "training_fold" for s in learned)
    assert all(s["state"] == "planned" for s in learned)
