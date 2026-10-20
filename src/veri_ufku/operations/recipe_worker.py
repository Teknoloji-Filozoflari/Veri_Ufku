"""Disposable CPU recipe and monitoring tasks."""

import os

from veri_ufku.domain.contracts import Progress
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.operations.monitoring import compare, evaluate
from veri_ufku.operations.recipes import dry_run
from veri_ufku.storage.project_model import ProjectError


def process_entry(request, action, workspace, cancel, connection, budget):
    try:
        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        if action == "dry":
            result = dry_run(
                request["recipe"],
                request["sources"],
                request["mappings"],
                workspace,
                control,
            )
        elif action == "evaluate":
            from pathlib import Path

            import polars as pl

            from veri_ufku.analytics.dataset import checked
            from veri_ufku.storage.project_store import file_hash

            prediction = request["prediction"]
            target = request["target"]
            path = Path(prediction["output"])
            if (
                path.is_symlink()
                or path.stat().st_size > 128 * 1024**2
                or file_hash(path) != prediction["output_fingerprint"]
            ):
                raise ProjectError("Tahmin dosyası değişmiş/boyut sınırını aşmış.")
            checked(target, control)
            a, b = pl.read_parquet(path), pl.read_parquet(target["path"])
            if max(a.height, b.height) > 100000:
                raise ProjectError("Performans ölçümü 100000 kayıtla sınırlı.")
            result = evaluate(
                a,
                b,
                request["prediction_key"],
                request["target_key"],
                request["prediction_column"],
                request["target_column"],
                prediction["card"]["purpose"],
            )
            result.update(
                training_version=prediction["card"]["dataset_version"],
                model_run=prediction["card"]["run_id"],
                prediction_version=prediction["dataset_version"],
                prediction_fingerprint=prediction["output_fingerprint"],
                target_version=target["version_id"],
                target_fingerprint=target["fingerprint"],
                mapping={
                    k: request[k]
                    for k in (
                        "prediction_key",
                        "target_key",
                        "prediction_column",
                        "target_column",
                    )
                },
            )
            checked(target, control)
            if file_hash(path) != prediction["output_fingerprint"]:
                raise ProjectError("Ölçüm sırasında tahmin dosyası değişmiş.")
        else:
            result = compare(
                request["old"], request["new"], request["mapping"], control
            )
        result["worker_pid"] = os.getpid()
        control.disk(workspace, force=True)
        control.check()
        connection.send(("result", result))
    except Canceled:
        connection.send(("canceled", None))
    except ProjectError as error:
        connection.send(("error", str(error)))
    except Exception as error:
        connection.send(
            (
                "error",
                resource_error_text(
                    error,
                    f"Tarif/izleme başarısız ({type(error).__name__}); proje korundu.",
                ),
            )
        )
    finally:
        connection.close()
