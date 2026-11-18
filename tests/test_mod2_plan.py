"""Mod 2 planı: veri sürümü üretmez, eğitim katında öğrenir, iptal edilebilir."""

import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from test_cleaning import run as clean
from test_dataset import column, prepare
from test_preparation import request as project_request

from veri_ufku.domain.contracts import ComputeBudget
from veri_ufku.modeling.baseline import calculate as baseline
from veri_ufku.modeling.contracts import PreparationSpec
from veri_ufku.modeling.plans import create_plan, pending_plans, validate_record
from veri_ufku.modeling.preparation import calculate as preparation
from veri_ufku.modeling.validation import ValidationSpec
from veri_ufku.operations.contracts import active_datasets
from veri_ufku.storage import plan_store
from veri_ufku.ui.operations import OperationsController

FILL_PARAMETERS = {
    "method": "median",
    "missing": "null",
    "value": "",
    "tie_policy": "reject",
}


@pytest.fixture(scope="module")
def app():
    # QGuiApplication kullanılır: QCoreApplication oturumu zehirler ve sonraki
    # GUI testlerinde create_application() hata verir.
    if QGuiApplication.instance() is None:
        QQuickStyle.setStyle("Basic")
    application = QGuiApplication.instance() or QGuiApplication(["veri-ufku-test"])
    yield application


def spin(app, predicate, timeout=60000):
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Koşul süresi doldu.")


class _Data(QObject):
    """Aktif veri sürümünü gösteren minimal dataset denetleyicisi."""

    changed = Signal()

    def __init__(self, projects):
        super().__init__()
        self.projects = projects
        self.revision = 0

    def dataset(self):
        datasets = active_datasets(self.projects.draft)
        return datasets[-1] if datasets else None


class _Projects(QObject):
    """Proje durumunu ve yazma işçisini paylaşan minimal proje denetleyicisi."""

    changed = Signal()

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.draft = copy.deepcopy(store.state)
        self.saved = copy.deepcopy(store.state)
        self.busy = False
        self.readOnly = False
        self.dataset_active = False
        self.executor = ThreadPoolExecutor(max_workers=1)

    def sync(self):
        self.draft = copy.deepcopy(self.store.state)
        self.saved = copy.deepcopy(self.store.state)


def controller(store, tmp_path):
    projects = _Projects(store)
    cache = tmp_path / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    ops = OperationsController(_Data(projects), projects, cache, ComputeBudget())
    return ops, projects


def preview_fill(app, ops, column_id, method="median", value=""):
    """Öğrenilen doldurma önizlemesi üretir; sürüm oluşturmaz."""
    parameters = dict(FILL_PARAMETERS, method=method, value=value)
    ops.previewCleaning(
        "fill", json.dumps([column_id]), json.dumps(parameters), "chain"
    )
    spin(app, lambda: not ops.busy and (ops.preview is not None or ops.errorText))
    assert not ops.errorText, ops.errorText
    assert ops.preview["spec"]["kind"] == "fill"
    return ops.preview


def frame():
    return pl.DataFrame(
        dict(
            x=[1.0, None, 3.0, 4.0, 5.0, 6.0],
            y=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        )
    )


def test_mod2_plan_creates_no_dataset_version(app, tmp_path):
    store, request, work = prepare(tmp_path, frame())
    with closing(store):
        ops, projects = controller(store, tmp_path)
        column_id = column(request, "x")
        preview_fill(app, ops, column_id, "median")
        before = copy.deepcopy(projects.draft["datasets"])
        before_operations = copy.deepcopy(projects.draft["operations"])
        source = (tmp_path / "source.parquet").read_bytes()
        ops.setPrepareScopeMode("mod2")
        ops.planForModel()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        assert projects.draft["datasets"] == before
        # Mod 2 planı bir işlem kaydı üretmez; içe aktarma kaydı dağişmez.
        assert projects.draft["operations"] == before_operations
        records = [r for r in projects.draft["results"] if "mod2_plan" in r]
        assert len(records) == 1
        plan = records[0]["mod2_plan"]
        assert plan["schema"] == "Mod2Plan/v1"
        assert plan["learn_scope"] == "training_fold" and plan["status"] == "planned"
        assert plan["operations"][0]["method"] == "median"
        assert plan["operations"][0]["column_ids"] == [column_id]
        assert plan["columns"][0]["name"] == "x"
        assert set(plan["columns"][0]) == {"id", "name", "type"}
        validate_record(
            records[0], {d["version_id"]: d for d in projects.draft["datasets"]}
        )
        assert "yeni veri sürümü oluşmadı" in ops.message
        assert (tmp_path / "source.parquet").read_bytes() == source


def test_mod1_and_mod2_exclude_each_other(app, tmp_path):
    store, request, work = prepare(tmp_path, frame())
    with closing(store):
        ops, projects = controller(store, tmp_path)
        column_id = column(request, "x")
        preview_fill(app, ops, column_id, "median")
        ops.setPrepareScopeMode("mod2")
        ops.planForModel()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        # Aynı dönüşümün Mod 1 uygulaması reddedilir.
        preview_fill(app, ops, column_id, "median")
        before_operations = copy.deepcopy(projects.draft["operations"])
        ops.setPrepareScopeMode("mod1")
        ops.apply()
        assert "Mod 1 ve Mod 2 birbirini dışlar" in ops.errorText
        # Reddedilen uygulama hiçbir işlem kaydı yazmaz.
        assert projects.draft["operations"] == before_operations
        # Aynı dönüşümün ikinci Mod 2 planı reddedilir.
        ops.setPrepareScopeMode("mod2")
        ops.planForModel()
        spin(app, lambda: not ops.busy)
        assert "zaten Mod 2 için planlandı" in ops.errorText
        # Tüm veriye uygulanmış dönüşüm yeniden planlanamaz.
        # "median" öğrenilen bir yöntemdir ve y kolonunda (x'den farklı anahtar)
        # uygulanır; böylece çakışma bekleyen plandan değil uygulanmış işlemden gelir.
        clean(store, work, "y", "fill", {"method": "median"})
        projects.sync()
        preview_fill(app, ops, column(request, "y"), "median")
        ops.setPrepareScopeMode("mod2")
        ops.planForModel()
        spin(app, lambda: not ops.busy)
        assert "Mod 1 ve Mod 2 birbirini dışlar" in ops.errorText
        assert len([r for r in projects.draft["results"] if "mod2_plan" in r]) == 1


def test_mod2_plan_learns_only_in_training_fold(tmp_path):
    n = 80
    store, request, work = prepare(
        tmp_path,
        pl.DataFrame(
            dict(
                x=[float(i + 1) for i in range(40)] + [1_000_000.0] * 40,
                y=[float(i % 5) for i in range(n)],
                when=[date(2024, 1, 1) + timedelta(days=i) for i in range(n)],
            )
        ),
    )
    with closing(store):
        r = project_request(store)
        x = column(r, "x")
        version = r["version_id"]
        plan = create_plan(
            dataset_version=version,
            origin_version=version,
            operations=[
                dict(
                    kind="fill",
                    method="median",
                    column_ids=[x],
                    parameters=dict(missing="null", tie_policy="reject"),
                )
            ],
            columns=[dict(id=x, name="x", type="Float64")],
            reason=(
                "Model aşamasında yalnız eğitim katında öğrenilecek; "
                "test/doğrulama verisine bilgi sıkmaz."
            ),
        )
        plan_store.publish(store, store.state, plan)
        r = project_request(store)
        spec = PreparationSpec(
            "regression",
            (x,),
            target=column(r, "y"),
            family="linear",
            source_version=r["version_id"],
            time=column(r, "when"),
            numeric_imputation="none",
            scaling="standard",
        )
        report = preparation(r, spec, work)
        assert not report["blockers"], report["risks"]
        step = next(s for s in report["plan"]["steps"] if s["kind"] == "impute_numeric")
        assert step["learned_scope"] == "training_fold"
        assert step["parameters"]["strategy"] == "median"
        assert step["parameters"]["mod2_plan_id"]
        # Mod 2 adımı taşınmış bir Mod 1 işi değildir; taşıma izni taşımaz.
        assert "relocated_from_operation_id" not in step["parameters"]
        protocol = ValidationSpec(
            structure="time",
            test_fraction=0.4,
            prediction_moment="Ölçüm başlamadan önce",
            availability={x: dict(offset_seconds=0, note="Ölçüm öncesi kayıt")},
        )
        result = baseline(dict(r, preparation=report), protocol.data(), work)
        evaluation = result["evaluations"][0]
        index = report["plan"]["steps"].index(step)
        statistic = evaluation["fitted_parameters"][str(index)]["statistics"][0]
        fitted_rows = set(evaluation["fit_row_ids"])
        rows = pl.read_parquet(r["path"])
        lookup = {row["__vu_row_id"]: row["x"] for row in rows.iter_rows(named=True)}
        train_values = np.array(
            [lookup[row] for row in evaluation["fit_row_ids"]], dtype=float
        )
        global_median = float(np.median(rows["x"].to_numpy()))
        assert fitted_rows.isdisjoint(set(result["plan"]["membership"]["test"]))
        assert statistic == pytest.approx(float(np.median(train_values)))
        assert statistic != pytest.approx(global_median)
        assert global_median > 1000
        assert "1000000.0" not in json.dumps(evaluation["fitted_parameters"])


def test_plan_removal_clears_pending_plans(app, tmp_path):
    store, request, work = prepare(tmp_path, frame())
    with closing(store):
        ops, projects = controller(store, tmp_path)
        column_id = column(request, "x")
        preview_fill(app, ops, column_id, "median")
        ops.setPrepareScopeMode("mod2")
        ops.planForModel()
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        record = next(r for r in projects.draft["results"] if "mod2_plan" in r)
        version = (ops.data.dataset() or {})["version_id"]
        assert len(pending_plans(projects.draft, version)) == 1
        assert ops.mod2Plans[0]["id"] == record["id"]
        assert ops.mod2Plans[0]["canPlan"] is True
        ops.removePlan(record["id"])
        spin(app, lambda: not ops.busy)
        assert not ops.errorText, ops.errorText
        assert not [r for r in projects.draft["results"] if "mod2_plan" in r]
        assert pending_plans(projects.draft, version) == []
        assert len(projects.draft["datasets"]) == 1
