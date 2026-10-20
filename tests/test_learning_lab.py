"""Reference solvers, optional learning marks and closed coverage contracts."""

import copy
import json
import multiprocessing as mp
from contextlib import closing

import numpy as np
import pytest
from scipy import stats

from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.workers import Canceled
from veri_ufku.learning.curriculum import KERNELS, Curriculum
from veri_ufku.learning.lab_engine import calculate
from veri_ufku.storage import learning_lab_store as storage
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.ui.learning import LearningController


def run(tmp_path, lesson, value=None):
    c = Curriculum()
    entry = c.lessons[lesson]
    p = dict(
        lesson=lesson,
        value=entry["control"]["default"] if value is None else value,
        seed=42,
    )
    with closing(
        ProjectStore.create(
            tmp_path / "project", "Veri_Ufku · Geçici öğrenme laboratuvarı"
        )
    ) as store:
        v = calculate(storage.request_for(store, store.state, p), p, tmp_path)
        storage.publish(store, store.state, v)
        assert storage.load(store, store.state["results"][-1]) == v
        return v


@pytest.mark.parametrize("lesson", KERNELS)
def test_real_kernel_safe_publication(tmp_path, lesson):
    v = run(tmp_path, lesson)
    assert v["status"] == "completed" and len(v["input_records"]) <= 10000
    assert v["provenance"]["dataset_versions"] == []
    assert len({r["fixture_row_id"] for r in v["input_records"]}) == len(
        v["input_records"]
    )
    assert all(np.isfinite(p).all() for c in v["curves"] for p in c["points"])
    assert "input_records" not in storage.public_report(v)
    if lesson == "mean-median":
        assert v["metrics"] == dict(mean=40.0, median=20.0, n=3)
    if lesson == "histogram":
        assert sum(v["details"]["counts"]) == 200
    if lesson == "sampling":
        chosen = v["details"]["selected_indices"]
        assert len(set(chosen)) == 20 and v["metrics"]["sample_mean"] == np.mean(chosen)
    if lesson == "ci":
        a = np.array([r["x"] for r in v["input_records"][:20]])
        half = stats.t.ppf(0.975, 19) * a.std(ddof=1) / np.sqrt(20)
        assert v["metrics"]["first_low"] == pytest.approx(a.mean() - half)
    if lesson == "overfitting":
        assert (
            len(v["split_ids"]["train"]) == 40
            and len(v["split_ids"]["validation"]) == 160
        )
    if lesson == "leakage":
        assert v["metrics"]["contaminated_mse"] < 1e-20 and v["details"]["leaked"]
    if lesson == "calibration":
        assert v["details"]["label_order"] == [0, 1]
        assert sum(b["n"] for b in v["details"]["reliability_bins"]) == 400
        assert v["metrics"]["calibrated_brier"] < v["metrics"]["raw_brier"]
    if lesson == "confounding":
        assert v["metrics"]["adjusted_coefficient"] == pytest.approx(2, abs=0.2)
        assert abs(v["metrics"]["naive_coefficient"] - 2) > 0.5


def test_all_paths_prerequisites_coverage_and_negative_mutations():
    c = Curriculum()
    assert len(c.paths) == 8 and len(c.coverage()) == 416
    for change in (
        lambda d: d["lessons"][0].update(article_id="absent"),
        lambda d: d["lessons"][0].update(prerequisites=["leakage"]),
        lambda d: d["lessons"][0].pop("own_data"),
        lambda d: d["lessons"][0]["review"].update(article_version=999),
    ):
        data = copy.deepcopy(c.data)
        change(data)
        with pytest.raises(ValueError):
            Curriculum(data=data)
    data = copy.deepcopy(c.data)
    data["capability_paths"].pop("dataset.profile")
    with pytest.raises(ValueError, match="coverage"):
        Curriculum(data=data).coverage()


def test_optional_progress_migration_version_and_optout(tmp_path):
    old = dict(
        schema_version=1, enabled=True, read=["mean-median"], bookmarks=["leakage"]
    )
    path = tmp_path / "learning-marks.json"
    path.write_text(json.dumps(old))
    c = LearningController(tmp_path)
    assert c.marksEnabled
    c.openLesson("leakage")
    c.answerLesson(1)
    assert "sertifika" in c.lessonFeedback and not c.lessonCompleted
    c.completeLesson()
    assert c.lessonCompleted
    saved = json.loads(path.read_text())
    assert (
        saved["schema_version"] == 2
        and saved["read"] == old["read"]
        and saved["bookmarks"] == old["bookmarks"]
    )
    again = LearningController(tmp_path)
    again.openLesson("leakage")
    assert again.lessonCompleted
    again.curriculum.lessons["leakage"]["version"] += 1
    assert not again.lessonCompleted and "Önceki sürüm" in again.lessonProgressText
    again.setMarksEnabled(False)
    assert not again.lessonCompleted and json.loads(path.read_text())["lessons"] == {}
    assert again.openLesson("confounding")  # no prerequisite or quiz gating
    again.completeLesson()
    assert not again.lessonCompleted


def test_cancel_immutable_user_project_and_hash(tmp_path):
    with closing(ProjectStore.create(tmp_path / "user")) as user:
        before = user.commit_id
        p = dict(lesson="ci", value=20, seed=42)
        with pytest.raises(ProjectError):
            storage.request_for(user, user.state, p)
        assert user.commit_id == before and not user.state["results"]
    with closing(
        ProjectStore.create(tmp_path / "lab", "Veri_Ufku · Geçici öğrenme laboratuvarı")
    ) as store:
        cancel = mp.get_context("spawn").Event()
        cancel.set()
        req = storage.request_for(store, store.state, p)
        with pytest.raises(Canceled):
            calculate(req, p, tmp_path, Control(cancel))
        v = calculate(req, p, tmp_path)
        previous = store.commit_id
        with pytest.raises(Canceled):
            storage.publish(store, store.state, v, Control(cancel))
        assert store.commit_id == previous
        storage.publish(store, store.state, v)
        record = store.state["results"][-1]
        store.path(record["learning_lab"]["details_uri"]).write_bytes(b"broken")
        with pytest.raises(ProjectError, match="hash"):
            storage.load(store, record)


def test_slider_reproducibility_and_closed_recipe(tmp_path):
    with closing(
        ProjectStore.create(tmp_path / "lab", "Veri_Ufku · Geçici öğrenme laboratuvarı")
    ) as store:
        p = dict(lesson="sampling", value=20, seed=42)
        req = storage.request_for(store, store.state, p)
        a = calculate(req, p, tmp_path)
        b = calculate(req, p, tmp_path)
        assert a["input_records"] == b["input_records"] and a["curves"] == b["curves"]
        for invalid in (
            dict(p, code="x"),
            dict(p, value=101),
            dict(p, seed=True),
            dict(p, lesson="unknown"),
        ):
            with pytest.raises(ValueError):
                storage.request_for(store, store.state, invalid)


def test_qt_property_notify_metadata_is_valid():
    from veri_ufku.ui.learning_lab import LearningLabController

    meta = LearningLabController.staticMetaObject
    for name in ("workspaceId", "starting"):
        prop = meta.property(meta.indexOfProperty(name))
        assert (
            prop.isValid() and prop.hasNotifySignal() and prop.notifySignalIndex() >= 0
        )
