"""Scenario presentation reuses the existing supervised immutable job lifecycle."""

import json

from PySide6.QtCore import Property, Slot

from veri_ufku.modeling.scenario_contracts import METHODS, example
from veri_ufku.modeling.scenario_service import worker
from veri_ufku.storage import scenario_store
from veri_ufku.ui.monitoring import MonitoringController


class ScenarioController(MonitoringController):
    storage = scenario_store
    worker = staticmethod(worker)
    result_kind = "scenario"

    @staticmethod
    def public_report(value):
        from veri_ufku.modeling.scenario_contracts import public_report

        return public_report(value)

    saved = Property(
        "QVariantList",
        lambda s: [
            dict(
                id=r["id"],
                label=r["scenario"]["spec"]["method"] + " · " + r["scenario"]["run_id"],
            )
            for r in s.projects.draft["results"]
            if "scenario" in r
        ],
        notify=MonitoringController.changed,
    )
    currentRoute = Property(
        "QVariantMap", lambda s: {}, notify=MonitoringController.changed
    )
    methods = Property("QVariantList", lambda s: list(METHODS), constant=True)

    errorText = Property(
        str,
        lambda s: s._error.replace("Monitoring", "Senaryo"),
        notify=MonitoringController.changed,
    )

    @Slot(str, str, result=str)
    def modelTemplate(self, method, record_id):
        if method not in (
            "what-if",
            "model-optimize",
        ) or record_id not in self.storage.models(self.projects.draft):
            return self.template(method)
        card = self.storage.models(self.projects.draft)[record_id]["card"]
        spec = dict(
            method=method,
            variables=[
                dict(
                    name=f["id"],
                    unit=f["unit"] or "dimensionless",
                    lower=-1,
                    upper=1,
                    initial=0,
                )
                for f in card["features"]
            ],
            objective=dict(unit=card["target"].get("unit") or "dimensionless"),
            model=dict(record_id=record_id),
            assumptions="Gerekli: model geçerlilik/kısıt varsayımlarını ve varsayılan -1..1 sınırlarını gözden geçirin; causal değildir.",
        )
        if method == "what-if":
            spec["point"] = [0.0] * len(card["features"])
        return json.dumps(spec, ensure_ascii=False, indent=2)

    @Slot(str, result=str)
    def template(self, method):
        if method in ("what-if", "model-optimize"):
            return json.dumps(
                dict(
                    method=method,
                    variables=[],
                    objective=dict(unit="dimensionless"),
                    model=dict(record_id=""),
                    assumptions="Modelin eğitim ColumnId/birimlerini ve geçerlilik alanını açık seçin.",
                ),
                ensure_ascii=False,
                indent=2,
            )
        return json.dumps(example(method), ensure_ascii=False, indent=2)

    @Slot(str, bool)
    def selectChampion(self, record_id, rollback):
        self._error = "Senaryo model referansını değiştirmez; açık model yönetimi yolunu kullanın."
        self.changed.emit()
