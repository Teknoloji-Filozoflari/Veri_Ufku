"""Bounded review/share worker takes only immutable envelopes, never writes ACTIVE."""

from veri_ufku.exports.share_bundle import build, compare, open_bundle, prepare
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError


def public_open(opened):
    out = {k: v for k, v in opened.items() if k != "payload"}
    if "sample-reference.json" in opened["payload"]:
        import io

        import pyarrow.parquet as pq

        from veri_ufku.storage.project_model import decode

        out["sample_reference"] = decode(opened["payload"]["sample-reference.json"])
        out["sample_preview"] = (
            pq.read_table(io.BytesIO(opened["payload"]["sample.parquet"]))
            .slice(0, 10)
            .to_pylist()
        )
    import math

    if "sample_preview" in out:
        out["sample_preview"] = [
            {
                k: (str(v) if isinstance(v, float) and not math.isfinite(v) else v)
                for k, v in row.items()
            }
            for row in out["sample_preview"]
        ]
    return dict(action="open", **out)


def calculate(request, workspace, control):
    action = request["action"]
    if action == "preview":
        value, _ = prepare(request, request["spec"], workspace, control)
        return dict(action="preview", **value)
    if action == "bundle":
        if request["reviewed"] is not True or type(request["allow_pii"]) is not bool:
            raise ProjectError("Inclusion/redaction önizlemesi explicit onay ister.")
        return build(
            request,
            request["spec"],
            workspace,
            request["destination"],
            request["preview_hash"],
            request["allow_pii"],
            control,
        )
    if action == "open":
        return public_open(open_bundle(request["archive"], control))
    if action == "diff":
        return compare(
            open_bundle(request["left"], control),
            open_bundle(request["right"], control),
        )
    raise ProjectError("Share action desteklenmiyor.")


def worker(request, spec, workspace, cancel, sender, budget):
    try:
        apply_process_limits(budget)
        sender.send(
            ("result", calculate(request, workspace, Control(cancel, budget=budget)))
        )
    except Canceled:
        sender.send(("canceled", None))
    except ProjectError as e:
        sender.send(("error", str(e)))
    except Exception as e:
        sender.send(
            (
                "error",
                resource_error_text(
                    e,
                    "Paylaşım tamamlanamadı ("
                    + type(e).__name__
                    + "); önceki proje korundu.",
                ),
            )
        )
    finally:
        sender.close()
