"""Immutable privacy envelope; key bytes stay in process memory, never reports."""

import os
from pathlib import Path

from veri_ufku.exports.privacy import export, inspect_sealed, pii_scan, project_policy
from veri_ufku.importers.delimited import Control
from veri_ufku.jobs.limits import apply_process_limits, resource_error_text
from veri_ufku.jobs.workers import Canceled
from veri_ufku.storage.project_model import ProjectError, encode


def calculate(request, workspace, control):
    Path(workspace, "marker.json").write_bytes(
        encode(
            dict(schema="PrivacyScratch/v1", owner="Veri_Ufku.privacy", pid=os.getpid())
        )
    )
    action = request["action"]
    from veri_ufku.exports.privacy_keys import generate, load

    if action == "generate-key":
        return dict(action=action, **generate(request["purpose"], request["key_ref"]))
    if action in ("preview", "export") and any(
        r["strategy"] == "pseudonym" for r in request["policy"]["rules"]
    ):
        request["hmac_key"] = load("hmac", request["policy"]["key_ref"])
    if action == "inspect" or action == "export" and request["format"] == "sealed":
        request["seal_key"] = load("fernet", request["encryption_key_ref"])

    if action == "scan":
        return dict(action=action, **pii_scan(request, control))
    if action == "preview":
        _, p = project_policy(
            request, request["policy"], request.get("hmac_key"), control
        )
        return dict(action=action, **p)
    if action == "export":
        return export(
            request,
            request,
            workspace,
            control,
            request.get("hmac_key"),
            request.get("seal_key"),
        )
    if action == "inspect":
        return inspect_sealed(request["archive"], request["seal_key"], control)
    raise ProjectError("Privacy eylemi desteklenmiyor.")


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
                    "Privacy işlemi tamamlanamadı ("
                    + type(e).__name__
                    + "); önceki proje korundu.",
                ),
            )
        )
    finally:
        sender.close()
