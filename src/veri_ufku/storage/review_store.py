"""Human review is an append-only existing ProjectStore journal, never shared editing."""

import copy
import os
import shutil
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from veri_ufku.domain.contracts import Provenance
from veri_ufku.exports.share_privacy import scan
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.validation import digest
from veri_ufku.storage.project_model import (
    ProjectError,
    decode,
    encode,
    identifier,
    uid,
    validate_state,
)
from veri_ufku.storage.project_store import (
    ProjectStore,
    file_hash,
    publish_directory,
    validate_destination,
)
from veri_ufku.storage.validation_store import transaction

CHECKS = (
    "inclusion-reviewed",
    "secret-pii-reviewed",
    "schema-reviewed",
    "methods-assumptions-reviewed",
    "metrics-protocol-reviewed",
    "identity-conflicts-reviewed",
)
DECISIONS = (
    "comment",
    "keep-local",
    "incoming-as-separate-fork",
    "defer",
    "learning-note",
)


def request_for(store, state, parameters):
    if not isinstance(parameters, dict) or parameters.get("action") not in (
        "preview",
        "bundle",
        "open",
        "diff",
    ):
        raise ProjectError("Share eylemi kapalı şema ile seçilmeli.")
    action = parameters["action"]
    allowed = (
        {"action", "spec"}
        if action == "preview"
        else (
            {"action", "spec", "preview_hash", "destination", "allow_pii", "reviewed"}
            if action == "bundle"
            else (
                {"action", "archive"}
                if action == "open"
                else {"action", "left", "right"}
            )
        )
    )
    if set(parameters) != allowed:
        raise ProjectError("Share eylem alanları geçersiz.")
    req = copy.deepcopy(parameters)
    if action in ("preview", "bundle"):
        from veri_ufku.exports.share_bundle import spec

        req["spec"] = spec(req["spec"])
        req.update(
            state=copy.deepcopy(state),
            origin=dict(
                project_id=store.manifest["project_id"],
                commit_id=store.commit_id,
                schema_version=store.manifest["format_version"],
            ),
            artifacts={
                u: dict(
                    path=str(store.path(u)).replace(
                        "/proc/self/", f"/proc/{os.getpid()}/", 1
                    ),
                    metadata=copy.deepcopy(m),
                )
                for u, m in store.manifest["artifacts"].items()
            },
            project_root=str(store.root),
        )
    return req


def publish(store, state, value, control=None):
    (control or Control()).check()
    # Preview, open, diff and file export do not alter the current project.
    store._guard()
    if state != store.state:
        raise ProjectError("Proje değişmiş; incelemeyi yenileyin.")
    return copy.deepcopy(state)


def subject(projection, entity_key, bundle_fingerprint=None):
    if entity_key not in projection["entities"]:
        raise ProjectError("İnceleme hedef kimliği yok.")
    e = projection["entities"][entity_key]
    # Keep the exact old metadata context; no automatic rebind to a new artifact/run.
    category = {
        "dataset": "schema",
        "operation": "operations",
        "run": "runs_metrics",
    }.get(e["kind"])
    snapshot = (
        projection["categories"][category].get(e["id"], {})
        if category
        else projection["origin"]
    )
    return dict(
        origin=projection["origin"],
        entity=copy.deepcopy(e),
        context=copy.deepcopy(snapshot),
        bundle_fingerprint=bundle_fingerprint,
    )


def append_review(
    store, state, bound, author, note, checks, decision="comment", reply_to=None
):
    if (
        decision not in DECISIONS
        or not isinstance(checks, dict)
        or set(checks) != set(CHECKS)
        or any(type(v) is not bool for v in checks.values())
    ):
        raise ProjectError("Review decision/checklist kapalı değerleri gerekli.")
    if (
        not isinstance(author, str)
        or not 1 <= len(author) <= 100
        or not isinstance(note, str)
        or not 1 <= len(note) <= 2000
    ):
        raise ProjectError(
            "Review author1..100 ve not1..2000karakter gerekli; yerel kullanıcı beyanıdır."
        )
    if scan(dict(author=author, note=note, bound=bound)):
        raise ProjectError(
            "Yorum veya hedefte secret/PII deseni var; önce açıkça maskeleyin."
        )
    if reply_to and not any(
        r["id"] == reply_to and "review_event" in r for r in state["results"]
    ):
        raise ProjectError("Yanıt verilen review kaydı yok.")
    now = datetime.now(UTC).isoformat()
    event = dict(
        schema="ReviewEvent/v1",
        kind="human-review",
        subject=copy.deepcopy(bound),
        author=author,
        note=note,
        checklist=checks,
        decision=decision,
        reply_to=reply_to,
        created_at=now,
        provenance=asdict(
            Provenance(
                provenance_id="provenance:" + uid(),
                dataset_versions=(),
                config_revision=0,
                capability_id="share.review",
                parameters_hash=digest(
                    dict(subject=bound, checks=checks, decision=decision, note=note)
                ),
                environment=(("backend", "local human declaration"),),
                created_at=now,
                scope="immutable subject; no authentication/merge claim",
                seed_reason="no random operation",
            )
        ),
    )
    event["event_hash"] = digest(event)
    event = decode(encode(event))

    def add(draft):
        draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=[],
                seed=None,
                capability_id="share.review",
                review_event=event,
            )
        )

    return transaction(store, state, add)


def validate_records(state):
    for r in state["results"]:
        if "review_event" not in r:
            continue
        v = r["review_event"]
        if (
            v["schema"] != "ReviewEvent/v1"
            or v["kind"] not in ("human-review", "share-import")
            or v["event_hash"]
            != digest({k: x for k, x in v.items() if k != "event_hash"})
        ):
            raise ProjectError("Review immutable context/hash bozuk.")
        if r["dataset_version_ids"]:
            raise ProjectError("Review dış kökeni yerel dataset diye iliştiremez.")
        if v["kind"] == "human-review":
            if set(v["checklist"]) != set(CHECKS) or v["decision"] not in DECISIONS:
                raise ProjectError("Review checklist/karar geçersiz.")
            e = v["subject"]["entity"]
            identifier(e["id"])
            if (
                e["kind"] not in ("project", "dataset", "operation", "run")
                or len(e["entity_hash"]) != 64
            ):
                raise ProjectError("Review hedef bağı geçersiz.")


def binding_status(event, state, manifest):
    if event["kind"] != "human-review":
        return "import-origin"
    e = event["subject"]["entity"]
    kind = e["kind"]
    current = next(
        (
            x
            for x in state.get(
                {
                    "dataset": "datasets",
                    "operation": "operations",
                    "run": "results",
                }.get(kind, ""),
                [],
            )
            if x.get("version_id", x.get("id")) == e["id"]
        ),
        None,
    )
    if event["subject"]["origin"]["project_id"] != manifest["project_id"]:
        return "external-origin; original context retained"
    if kind == "project":
        return "historical project context; commit-bound"
    from veri_ufku.exports.share_bundle import entity_binding

    return (
        "same recorded entity/artifact context"
        if current
        and entity_binding(current, manifest["artifacts"])["entity_hash"]
        == e["entity_hash"]
        else "historical/missing context; not rebound"
    )


def restore(archive, destination, expected_fingerprint, control=None):
    from veri_ufku.exports.share_bundle import open_bundle

    control = control or Control()
    opened = open_bundle(archive, control)
    if (
        opened["fingerprint"] != expected_fingerprint
        or opened["manifest"]["mode"] != "full-copy"
    ):
        raise ProjectError(
            "Restore yalnız incelenen tam kopya; fingerprint/mode uyuşmuyor."
        )
    target = Path(destination).absolute()
    validate_destination(target)
    if target.parent.resolve() != target.parent:
        raise ProjectError("Restore parent symlink olamaz.")
    temp = Path(tempfile.mkdtemp(prefix=".veri-ufku-share-", dir=target.parent))
    project_dir = temp / "fork"
    try:
        native = decode(opened["payload"]["project.json"])
        with __import__("contextlib").closing(
            ProjectStore.create(project_dir)
        ) as store:
            store.state = copy.deepcopy(native["state"])
            for uri, meta in native["artifacts"].items():
                control.check()
                p = store.path("staging") / uid()
                p.write_bytes(opened["payload"]["artifacts/" + uri])
                control.disk(project_dir, force=True)
                if file_hash(p) != {k: meta[k] for k in ("size", "sha256")}:
                    raise ProjectError("Restore artifact değişmiş.")
                store.pending[uri] = (p, copy.deepcopy(meta))
            event = dict(
                schema="ReviewEvent/v1",
                kind="share-import",
                origin=opened["manifest"]["origin"],
                bundle_fingerprint=opened["fingerprint"],
                created_at=datetime.now(UTC).isoformat(),
                policy="new fork; identities retained; no merge/relink/code execution",
            )
            event["event_hash"] = digest(event)
            store.state["results"].append(
                dict(
                    id="result:" + uid(),
                    dataset_version_ids=[],
                    seed=None,
                    capability_id="share.restore",
                    review_event=event,
                )
            )
            validate_state(store.state)
            store.save()
            fork_id = store.manifest["project_id"]
        control.check()
        publish_directory(
            target.parent, str(project_dir.relative_to(target.parent)), target.name
        )
        return dict(
            status="restored-new-fork",
            path=str(target),
            project_id=fork_id,
            origin=opened["manifest"]["origin"],
            limitations="single local writer only; old RowId/ColumnId preserved; no automatic merge",
        )
    finally:
        shutil.rmtree(temp, ignore_errors=True)
