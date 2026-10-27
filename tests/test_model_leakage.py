"""Model leakage notice follows dataset-learned operations on the active version."""

from veri_ufku.ui.model_leakage import model_leakage_notice


def _state(current):
    return {
        "datasets": [
            {"version_id": "dv-1"},
            {
                "version_id": "dv-2",
                "parent_version_ids": ["dv-1"],
                "operation_id": "op-1",
            },
            {"version_id": "dv-other", "operation_id": "op-other"},
        ],
        "operations": [
            {
                "id": "op-1",
                "output_version_id": "dv-2",
                "spec": {
                    "kind": "fill",
                    "learned_scope": "dataset",
                    "parameters": {"method": "mean", "token": "s3cr3t-token"},
                    "column_ids": ["c-1"],
                    "input_version_id": "dv-1",
                },
            },
            {
                "id": "op-other",
                "output_version_id": "dv-other",
                "spec": {
                    "kind": "fill",
                    "learned_scope": "dataset",
                    "parameters": {"method": "mean"},
                    "column_ids": [],
                    "input_version_id": "dv-other",
                },
            },
        ],
    }


def test_full_data_fill_warns_on_the_child_version():
    text = model_leakage_notice(_state(None), "dv-2")
    assert text["warning"] is True
    assert text["count"] == 1
    assert "1" in text["text"]
    assert "fill" in text["text"]
    assert "s3cr3t-token" not in text["text"]
    assert "neden olur" not in text["text"]


def test_parent_stays_quiet_and_its_own_fill_warns():
    parent = model_leakage_notice(_state(None), "dv-1")
    other = model_leakage_notice(_state(None), "dv-other")
    assert parent["warning"] is False and parent["text"] == ""
    assert other["warning"] is True and other["count"] == 1


def test_constant_transform_does_not_invent_a_warning():
    state = _state(None)
    state["operations"][0]["spec"]["learned_scope"] = "none"
    state["operations"][0]["spec"]["kind"] = "rename"
    text = model_leakage_notice(state, "dv-2")
    assert text["warning"] is False
    assert text["text"] == ""


def test_missing_version_does_not_invent_a_warning():
    text = model_leakage_notice(_state(None), "")
    assert text == {"warning": False, "count": 0, "text": ""}
