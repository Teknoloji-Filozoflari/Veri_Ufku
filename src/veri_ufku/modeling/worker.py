"""Disposable preparation scan; project writes remain in the parent."""

import os

from veri_ufku.domain.contracts import Progress
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError


def process_entry(request, parameters, workspace, cancel, connection, budget):
    try:
        from veri_ufku.modeling.preparation import calculate

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        result = calculate(request, parameters, workspace, control)
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
                    f"Model hazırlığı tamamlanamadı ({type(error).__name__}); veri korundu.",
                ),
            )
        )
    finally:
        connection.close()


def validation_entry(request, parameters, workspace, cancel, connection, budget):
    try:
        from veri_ufku.modeling.baseline import calculate

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        result = calculate(request, parameters, workspace, control)
        result["worker_pid"] = os.getpid()
        control.disk(workspace, force=True)
        control.check()
        connection.send(("result", result))
    except Canceled:
        connection.send(("canceled", None))
    except ProjectError as error:
        connection.send(
            (
                "error",
                dict(
                    message=str(error),
                    invalid_folds=getattr(
                        error,
                        "invalid_folds",
                        [dict(scope="protocol", status="invalid", reason=str(error))],
                    ),
                ),
            )
        )
    except Exception as error:
        connection.send(
            (
                "error",
                dict(
                    message=resource_error_text(
                        error,
                        f"Model değerlendirmesi tamamlanamadı ({type(error).__name__}); sonuç başarılı sayılmadı.",
                    ),
                    invalid_folds=[],
                ),
            )
        )
    finally:
        connection.close()


def unsupervised_entry(request, parameters, workspace, cancel, connection, budget):
    try:
        from veri_ufku.modeling.unsupervised import calculate

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        result = calculate(request, parameters, workspace, control)
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
                    f"Etiketsiz analiz tamamlanamadı ({type(error).__name__}); veri korundu.",
                ),
            )
        )
    finally:
        connection.close()


def time_series_entry(request, parameters, workspace, cancel, connection, budget):
    try:
        from veri_ufku.modeling.time_series import calculate

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        result = calculate(request, parameters, workspace, control)
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
                    f"Zaman serisi tamamlanamadı ({type(error).__name__}); sonuç başarılı sayılmadı.",
                ),
            )
        )
    finally:
        connection.close()


def text_entry(request, parameters, workspace, cancel, connection, budget):
    try:
        from veri_ufku.analytics.text import calculate

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )
        result = calculate(request, parameters, workspace, control)
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
                    f"Metin incelemesi tamamlanamadı ({type(error).__name__}); sonuç başarılı sayılmadı.",
                ),
            )
        )
    finally:
        connection.close()


def search_entry(
    request, protocol, spec, workspace, cancel, connection, budget, resume=None
):
    """JSON checkpoint messages only; parent owns all ProjectStore/ACTIVE writes."""
    try:
        from veri_ufku.modeling.search import calculate

        apply_process_limits(budget)
        control = Control(cancel, budget=budget)
        result = calculate(
            request,
            protocol,
            spec,
            workspace,
            control,
            resume,
            checkpoint=lambda data: connection.send(("checkpoint", data)),
        )
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
                    f"Arama süreci başarısız ({type(error).__name__}); önceki sonuç korundu.",
                ),
            )
        )
    finally:
        connection.close()


def neural_entry(
    request, protocol, parameters, workspace, cancel, connection, budget, resume, pause
):
    """Checkpoint ACK keeps parent atomic publication ahead of worker progress."""
    try:
        from veri_ufku.modeling.neural import calculate

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )

        def checkpoint(value):
            value["worker_pid"] = os.getpid()
            connection.send(("checkpoint", value))
            if (
                not connection.poll(budget.max_wall_seconds)
                or connection.recv() != "published"
            ):
                raise ProjectError("Checkpoint parent atomik yayını onaylamadı.")

        value = calculate(
            request, protocol, parameters, workspace, control, resume, checkpoint, pause
        )
        value["worker_pid"] = os.getpid()
        connection.send(("result", value))
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
                    f"Tensor eğitimi tamamlanmadı ({type(error).__name__}); önceki checkpoint korundu.",
                ),
            )
        )
    finally:
        connection.close()


def neural_predict_entry(request, model, workspace, cancel, connection, budget):
    try:
        import polars as pl

        from veri_ufku.analytics.dataset import checked
        from veri_ufku.modeling.neural import predict

        apply_process_limits(budget)
        control = Control(cancel, budget=budget)
        checked(request, control)
        value = predict(model, pl.read_parquet(request["path"]), control=control)
        value.update(
            dataset_version=request["version_id"],
            source_snapshot_id=request["source_snapshot_id"],
            snapshot_fingerprint=request["fingerprint"],
            training_id=request["model_training_id"],
            worker_pid=os.getpid(),
        )
        connection.send(("result", value))
    except Canceled:
        connection.send(("canceled", None))
    except ProjectError as error:
        connection.send(("error", str(error)))
    except Exception as error:
        connection.send(
            (
                "error",
                resource_error_text(
                    error, f"Tensor prediction tamamlanmadı ({type(error).__name__})."
                ),
            )
        )
    finally:
        connection.close()


def vision_entry(
    request,
    parameters,
    workspace,
    cancel,
    connection,
    budget,
    action="train",
    model=None,
):
    try:
        from veri_ufku.modeling.vision import calculate, predict

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )

        def checkpoint(value):
            value["worker_pid"] = os.getpid()
            connection.send(("checkpoint", value))
            if (
                not connection.poll(budget.max_wall_seconds)
                or connection.recv() != "published"
            ):
                raise ProjectError("Vision checkpoint parent ACK eksik.")

        value = (
            predict(model, request, control)
            if action == "predict"
            else calculate(request, parameters, workspace, control, checkpoint)
        )
        value["worker_pid"] = os.getpid()
        connection.send(("result", value))
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
                    f"Vision işlem tamamlanmadı ({type(error).__name__}); kaynak korundu.",
                ),
            )
        )
    finally:
        connection.close()


def audio_entry(
    request,
    parameters,
    workspace,
    cancel,
    connection,
    budget,
    action="train",
    model=None,
):
    try:
        from veri_ufku.modeling.audio import calculate, predict

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )

        def checkpoint(value):
            value["worker_pid"] = os.getpid()
            connection.send(("checkpoint", value))
            if (
                not connection.poll(budget.max_wall_seconds)
                or connection.recv() != "published"
            ):
                raise ProjectError("Audio checkpoint parent ACK eksik.")

        value = (
            predict(model, request, control)
            if action == "predict"
            else calculate(request, parameters, workspace, control, checkpoint)
        )
        value["worker_pid"] = os.getpid()
        connection.send(("result", value))
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
                    f"Audio işlem tamamlanmadı ({type(error).__name__}); kaynak korundu.",
                ),
            )
        )
    finally:
        connection.close()


def recommendation_entry(
    request,
    parameters,
    workspace,
    cancel,
    connection,
    budget,
    action="train",
    model=None,
):
    try:
        from veri_ufku.modeling.recommendation import calculate, predict

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )

        def checkpoint(value):
            value["worker_pid"] = os.getpid()
            connection.send(("checkpoint", value))
            if (
                not connection.poll(budget.max_wall_seconds)
                or connection.recv() != "published"
            ):
                raise ProjectError("Recommendation checkpoint parent ACK eksik.")

        value = (
            predict(model, request, control)
            if action == "predict"
            else calculate(request, parameters, workspace, control, checkpoint)
        )
        value["worker_pid"] = os.getpid()
        connection.send(("result", value))
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
                    f"Recommendation işlem tamamlanmadı ({type(error).__name__}); kaynak korundu.",
                ),
            )
        )
    finally:
        connection.close()


def pattern_entry(
    request,
    parameters,
    workspace,
    cancel,
    connection,
    budget,
    action="train",
    model=None,
):
    try:
        from veri_ufku.modeling.patterns import calculate

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )

        def checkpoint(value):
            value["worker_pid"] = os.getpid()
            connection.send(("checkpoint", value))
            if (
                not connection.poll(budget.max_wall_seconds)
                or connection.recv() != "published"
            ):
                raise ProjectError("Pattern checkpoint parent ACK eksik.")

        value = calculate(request, parameters, workspace, control, checkpoint)
        value["worker_pid"] = os.getpid()
        connection.send(("result", value))
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
                    f"Pattern işlem tamamlanmadı ({type(error).__name__}); kaynak korundu.",
                ),
            )
        )
    finally:
        connection.close()


def graph_entry(
    request,
    parameters,
    workspace,
    cancel,
    connection,
    budget,
    action="train",
    model=None,
):
    try:
        from veri_ufku.modeling.graphs import calculate

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )

        def checkpoint(value):
            value["worker_pid"] = os.getpid()
            connection.send(("checkpoint", value))
            if (
                not connection.poll(budget.max_wall_seconds)
                or connection.recv() != "published"
            ):
                raise ProjectError("Graph checkpoint parent ACK eksik.")

        value = calculate(request, parameters, workspace, control, checkpoint)
        value["worker_pid"] = os.getpid()
        connection.send(("result", value))
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
                    f"Graph işlem tamamlanmadı ({type(error).__name__}); kaynak korundu.",
                ),
            )
        )
    finally:
        connection.close()


def stream_entry(
    request,
    parameters,
    workspace,
    cancel,
    connection,
    budget,
    action="train",
    model=None,
):
    try:
        if "task" in parameters:
            from veri_ufku.modeling.special_runs import calculate
        else:
            from veri_ufku.modeling.streams import calculate

        apply_process_limits(budget)
        control = Control(
            cancel,
            lambda phase, done, total: connection.send(
                ("progress", Progress(phase, done, total))
            ),
            budget,
        )

        def checkpoint(value):
            value["worker_pid"] = os.getpid()
            connection.send(("checkpoint", value))
            if (
                not connection.poll(budget.max_wall_seconds)
                or connection.recv() != "published"
            ):
                raise ProjectError("Stream checkpoint parent ACK eksik.")

        value = calculate(request, parameters, workspace, control, checkpoint)
        value["worker_pid"] = os.getpid()
        connection.send(("result", value))
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
                    f"Stream işlem tamamlanmadı ({type(error).__name__}); kaynak korundu.",
                ),
            )
        )
    finally:
        connection.close()
