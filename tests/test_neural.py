"""Real CPU tensors, epoch-boundary optimizer resume and isolated holdout tests."""

import copy
import json
import threading
from contextlib import closing
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from test_dataset import column, prepare

from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.contracts import PreparationSpec
from veri_ufku.modeling.neural import calculate, predict, unpack
from veri_ufku.modeling.neural_contracts import NeuralSpec
from veri_ufku.modeling.preparation import calculate as preparation
from veri_ufku.modeling.validation import ValidationSpec
from veri_ufku.storage.project_model import ProjectError


def fixture(tmp_path, template="mlp", purpose="regression", structure="independent"):
    rng = np.random.default_rng(56)
    n = 80
    values = rng.normal(size=(n, 16 if template == "cnn" else 2))
    frame = pl.DataFrame({f"x{i}": values[:, i] for i in range(values.shape[1])})
    frame = frame.with_columns(
        pl.Series(
            "y",
            np.where(values[:, 0] > 0, "evet", "hayır")
            if purpose == "classification"
            else values[:, 0] * 2 + values[:, 1],
        ),
        pl.Series("group", [f"g{i // 4}" for i in range(n)]),
        pl.date_range(pl.date(2024, 1, 1), pl.date(2024, 3, 20), eager=True).alias(
            "when"
        ),
    )
    store, r, work = prepare(tmp_path, frame)
    p = PreparationSpec(
        purpose,
        tuple(column(r, f"x{i}") for i in range(values.shape[1])),
        target=column(r, "y"),
        source_version=r["version_id"],
        prediction_context="Before measurement",
        numeric_imputation="mean",
        group=column(r, "group") if structure in ("group", "group_time") else "",
        time=column(r, "when") if structure in ("time", "group_time") else "",
    )
    r.update(origin_version=r["version_id"], history_state=store.state)
    r["preparation"] = preparation(r, p, work)
    r.update(run_id="run:cpu56", training_id="run:cpu56", prior_test_use_ids=[])
    protocol = ValidationSpec(
        structure=structure,
        folds=2,
        prediction_moment="Before measurement",
        availability={c: dict(offset_seconds=0, note="known") for c in p.features},
    )
    spec = NeuralSpec(
        template=template,
        epochs=6,
        patience=10,
        image_shape=(1, 4, 4) if template == "cnn" else (),
        image_ack="Pixels row-major" if template == "cnn" else "",
    )
    return store, r, work, protocol, spec


@pytest.mark.parametrize(
    "template,purpose",
    [("mlp", "regression"), ("mlp", "classification"), ("cnn", "classification")],
)
def test_actual_cpu_training_prediction_and_baseline(tmp_path, template, purpose):
    store, r, work, p, s = fixture(tmp_path, template, purpose)
    with closing(store):
        before = pl.read_parquet(r["path"])
        out = calculate(r, p.data(), s.data(), work)
        assert out["status"] == "completed" and out["epoch"] == 6
        assert len(out["curves"]) == 6
        assert out["comparison"]["neural"] >= 0
        new = before.drop("y").head(4)
        prediction = predict(out, new)
        assert prediction["row_ids"] == new["__vu_row_id"].to_list()
        assert len(prediction["values"]) == 4 and prediction["fit"] is False
        assert before.equals(pl.read_parquet(r["path"]))
        runtime = unpack(out["runtime"])
        assert runtime["optimizer"]["state"] and runtime["scheduler"]
        assert set(out["tensor_schema"]["fit_row_ids"]) == set(
            out["plan"]["membership"]["train"]
        )
        assert not set(out["tensor_schema"]["fit_row_ids"]) & set(
            out["plan"]["membership"]["test"]
        )


@pytest.mark.parametrize("optimizer", ["adam", "sgd"])
@pytest.mark.parametrize("template", ["mlp", "cnn"])
def test_full_pause_resume_bitwise_cpu(tmp_path, optimizer, template):
    store, r, work, p, s = fixture(
        tmp_path, template, "classification" if template == "cnn" else "regression"
    )
    with closing(store):
        s = replace(
            s,
            optimizer=optimizer,
            augmentation="horizontal_flip" if template == "cnn" else "none",
            class_weights="balanced" if template == "cnn" else "none",
        )
        original = calculate(r, p.data(), s.data(), work)
        pause = threading.Event()

        def stop(v):
            if v["epoch"] == 2:
                pause.set()

        paused = calculate(r, p.data(), s.data(), work, pause=pause, checkpoint=stop)
        assert paused["status"] == "paused" and paused["epoch"] == 2
        saved = copy.deepcopy(paused)
        resumed = calculate(r, p.data(), s.data(), work, resume=paused)
        assert resumed["curves"] == original["curves"]
        assert resumed["model_weights"] == original["model_weights"]
        assert paused == saved
        with pytest.raises(ProjectError, match="Resume uyumsuz"):
            calculate(r, p.data(), replace(s, lr=0.1).data(), work, resume=paused)
        broken = copy.deepcopy(paused)
        broken["runtime"]["pairs"] = [
            pair for pair in broken["runtime"]["pairs"] if pair[0] != "optimizer"
        ]
        with pytest.raises(ProjectError, match="Tam resume"):
            calculate(r, p.data(), s.data(), work, resume=broken)


def test_cancel_and_train_only_transform(tmp_path, monkeypatch):
    import veri_ufku.modeling.neural as module

    store, r, work, p, s = fixture(tmp_path)
    with closing(store):
        seen = []
        original = module.fitted_input

        def spy(x, indices, method):
            seen.append(indices.tolist())
            return original(x, indices, method)

        monkeypatch.setattr(module, "fitted_input", spy)
        event = threading.Event()
        out = calculate(
            r,
            p.data(),
            s.data(),
            work,
            Control(cancel=event),
            checkpoint=lambda v: event.set() if v["epoch"] == 1 else None,
        )
        assert out["status"] == "canceled" and out["epoch"] == 1
        f = pl.read_parquet(r["path"])
        assert [f[i]["__vu_row_id"].item() for i in seen[0]] == out["tensor_schema"][
            "fit_row_ids"
        ]
        assert not set(out["plan"]["membership"]["validation"]) & set(
            out["tensor_schema"]["fit_row_ids"]
        )


@pytest.mark.parametrize("structure", ["group", "time", "group_time"])
def test_joint_validation_membership(tmp_path, structure):
    store, r, work, p, s = fixture(tmp_path, structure=structure)
    with closing(store):
        out = calculate(r, p.data(), s.data(), work)
        assert out["plan"]["method"] == structure
        assert not set(out["tensor_schema"]["fit_row_ids"]) & set(
            out["tensor_schema"]["validation_row_ids"]
        )


def test_safe_closed_schema_rejects_objects_and_bad_tensor():
    with pytest.raises(ProjectError):
        unpack({"arbitrary": "os.system"})
    with pytest.raises(ProjectError):
        unpack({"tensor": "float32", "shape": [100000000], "data": []})
    with pytest.raises(ProjectError):
        NeuralSpec.from_dict(dict(device="cuda"))
    with pytest.raises(ProjectError):
        NeuralSpec.from_dict(dict(template="cnn", image_shape=[1, 4, 4]))


def test_sgd_autograd_matches_hand_gradient():
    from veri_ufku.modeling.neural import framework

    t = framework()
    layer = t.nn.Linear(1, 1)
    with t.no_grad():
        layer.weight.fill_(1)
        layer.bias.zero_()
    optimizer = t.optim.SGD(layer.parameters(), lr=0.1)
    x, y = t.tensor([[1.0], [2.0]]), t.tensor([[3.0], [5.0]])
    # residuals −2,−3: dL/dw=mean(2*r*x)=−8; dL/db=−5.
    loss = t.nn.MSELoss()(layer(x), y)
    loss.backward()
    assert float(loss.detach()) == 6.5
    assert float(layer.weight.grad.item()) == -8
    assert float(layer.bias.grad.item()) == -5
    optimizer.step()
    assert layer.weight.item() == pytest.approx(1.8)
    assert layer.bias.item() == pytest.approx(0.5)


def test_class_weights_train_counts_and_train_only_augmentation(tmp_path, monkeypatch):
    from veri_ufku.modeling.neural import framework

    t = framework()
    store, r, work, p, s = fixture(tmp_path, "cnn", "classification")
    with closing(store):
        flipped = []
        original = t.Tensor.flip

        def spy(value, *args, **kwargs):
            flipped.append(tuple(value.shape))
            assert t.is_grad_enabled()
            return original(value, *args, **kwargs)

        monkeypatch.setattr(t.Tensor, "flip", spy)
        out = calculate(
            r,
            p.data(),
            replace(s, augmentation="horizontal_flip", class_weights="balanced").data(),
            work,
        )
        assert flipped and all(shape[1:] == (1, 4, 4) for shape in flipped)
        f = pl.read_parquet(r["path"])
        rows = f.filter(
            pl.col("__vu_row_id").is_in(out["tensor_schema"]["fit_row_ids"])
        )
        counts = [
            rows.filter(pl.col("y") == label).height
            for label in out["tensor_schema"]["class_labels"]
        ]
        np.testing.assert_allclose(
            out["class_weights"], rows.height / (2 * np.array(counts))
        )
        flips_before = len(flipped)
        predict(out, f.head(5))
        assert len(flipped) == flips_before


def test_poisoned_holdout_cannot_change_train_preprocessing(tmp_path, monkeypatch):
    import veri_ufku.modeling.neural as module

    store, r, work, p, s = fixture(tmp_path)
    with closing(store):
        original = module.fitted_input
        seen = []

        def poisoned(x, indices, method):
            # Simulate arbitrary validation/test features only after frozen split.
            outside = np.array([i for i in range(len(x)) if i not in indices])
            poison = x.copy()
            poison[outside] = 1000000
            ref = original(x, indices, method)
            actual = original(poison, indices, method)
            assert actual == ref
            seen.append(actual)
            return actual

        monkeypatch.setattr(module, "fitted_input", poisoned)
        out = calculate(r, p.data(), s.data(), work)
        assert out["preprocessing"] == seen[0]


def test_atomic_checkpoint_roundtrip_tamper_and_journal(tmp_path):
    from veri_ufku.storage.neural_store import load, publish
    from veri_ufku.storage.project_model import validate_state
    from veri_ufku.storage.validation_store import choice, complete

    store, r, work, p, s = fixture(tmp_path)
    with closing(store):
        state = choice(
            store,
            store.state,
            r["version_id"],
            p.data(),
            r["preparation"]["plan"]["version_id"],
            r["run_id"],
        )
        out = calculate(r, p.data(), s.data(), work)
        state = publish(store, state, out)
        state = complete(store, state, status="completed", run_id=r["run_id"])
        record = (
            state["results"][-1]
            if "neural" in state["results"][-1]
            else next(v for v in state["results"] if "neural" in v)
        )
        loaded = load(store, record)
        assert loaded == json.loads(json.dumps(out))
        assert (
            predict(loaded, pl.read_parquet(r["path"]).head(3))["values"]
            == predict(out, pl.read_parquet(r["path"]).head(3))["values"]
        )
        changed = copy.deepcopy(state)
        next(v for v in changed["results"] if "neural" in v)["neural"]["tensor_schema"][
            "fit_row_ids"
        ] = out["tensor_schema"]["validation_row_ids"]
        with pytest.raises(ProjectError, match="sızıntısı"):
            validate_state(changed)
        path = store.path(record["neural"]["details_uri"])
        path.write_bytes(b'{"schema":"pickle"}')
        with pytest.raises(ProjectError, match="hash"):
            load(store, record)


def test_bounded_budget_and_early_stopping(tmp_path, monkeypatch):
    import veri_ufku.modeling.neural as module

    store, r, work, p, s = fixture(tmp_path)
    with closing(store):
        t = module.framework()
        original_loss = t.nn.MSELoss

        class PlateauLoss(original_loss):
            def forward(self, prediction, target):
                if not t.is_grad_enabled() and len(prediction) == 16:
                    return t.tensor(1.0)
                return super().forward(prediction, target)

        monkeypatch.setattr(t.nn, "MSELoss", PlateauLoss)
        out = calculate(r, p.data(), replace(s, epochs=100, patience=1).data(), work)
        assert out["epoch"] == 2 and out["stop_reason"] == "early_stopping_validation"
        # Deliberately advance the timer after context; no fit may occur beyond budget.
        original = module.context

        def delayed(*args):
            value = original(*args)
            monkeypatch.setattr(module.time, "monotonic", lambda: 1e9)
            return value

        monkeypatch.setattr(module, "context", delayed)
        control = Control()
        monkeypatch.setattr(control, "check", lambda: None)
        out = calculate(r, p.data(), replace(s, wall_seconds=1).data(), work, control)
        assert out["status"] == "budget_exhausted" and out["epoch"] == 0


def test_missing_optional_backend_is_explicit(monkeypatch):
    import importlib.util

    original = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: None if name == "torch" else original(name),
    )
    with pytest.raises(ProjectError, match="Optional PyTorch yok"):
        NeuralSpec.from_dict({})
    assert NeuralSpec.from_dict({}, require_backend=False).device == "cpu"
