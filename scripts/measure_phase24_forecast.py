"""Render the real unfitted model resource forecast at desktop and narrow widths."""

import json
import os
import tempfile
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["POLARS_MAX_THREADS"] = "2"
import polars as pl
from PySide6.QtCore import QObject, QPointF
from PySide6.QtTest import QTest

from veri_ufku.app import create_application

out = Path(__file__).resolve().parents[1] / "docs/evidence/phase24"


def main():
    with tempfile.TemporaryDirectory(prefix="vu-forecast24-") as directory:
        base = Path(directory)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key)
        source = base / "source.parquet"
        pl.LazyFrame().select(pl.int_range(0, 100000).alias("x")).with_columns(
            (pl.col("x") * 3 + 7).alias("y"),
            pl.lit("Seçilmeyen uzun alan").alias("note"),
        ).sink_parquet(source, engine="streaming")
        app, window, _ = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, data, prep = (
            engine._projects_resources,
            engine._imports_resources,
            engine._dataset_resources,
            engine._preparation_resources,
        )

        def wait(obj):
            start = time.monotonic()
            while obj.busy:
                app.processEvents()
                QTest.qWait(10)
                assert time.monotonic() - start < 90, obj.message
            assert not obj.errorText, obj.errorText

        try:
            assert projects.create(str(base / "project"))
            imports.choose(str(source))
            wait(imports)
            imports.importData()
            wait(imports)
            data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
            wait(data)
            cols = {c["name"]: c["id"] for c in prep.columns}
            prep.create(
                json.dumps(
                    dict(
                        purpose="regression",
                        target=cols["y"],
                        features=[cols["x"]],
                        family="linear",
                        prediction_context="Ölçüm öncesi",
                    )
                )
            )
            wait(prep)
            assert not prep.result["blockers"]
            window.setProperty("selectedSection", 5)
            window.setProperty("showDemo", False)
            app.processEvents()
            QTest.qWait(100)
            target = window.findChild(QObject, "modelResourceForecast")
            assert target is not None
            record = dict(
                environment="ENV-24",
                forecast=prep.result["resource_forecast"],
                text=target.property("text"),
                screenshots=[],
            )
            for width, height in ((1366, 768), (720, 560)):
                window.resize(width, height)
                app.processEvents()
                QTest.qWait(100)
                workspace = window.findChild(QObject, "workspace")
                flick = workspace.property("contentItem")
                pos = target.mapToItem(flick, QPointF(0, 0)).y() + flick.property(
                    "contentY"
                )
                flick.setProperty(
                    "contentY",
                    max(
                        0,
                        min(
                            pos - 20,
                            flick.property("contentHeight") - flick.property("height"),
                        ),
                    ),
                )
                app.processEvents()
                QTest.qWait(100)
                scene = target.mapToScene(QPointF(0, 0))
                assert target.property("visible") and scene.y() >= 0
                assert scene.x() + target.width() <= window.width() + 1
                path = out / f"forecast-{width}.png"
                assert window.grabWindow().save(str(path))
                record["screenshots"].append(
                    dict(
                        path=path.name,
                        width=width,
                        height=height,
                        label_scene_y=scene.y(),
                        label_height=target.height(),
                    )
                )
            (out / "forecast.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2)
            )
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    main()
