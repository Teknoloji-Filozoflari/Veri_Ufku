"""Human privacy decisions use the existing append-only ProjectStore journal."""

import copy
from dataclasses import asdict
from datetime import UTC, datetime

from veri_ufku.domain.contracts import Provenance
from veri_ufku.exports.privacy_contracts import policy, reference
from veri_ufku.importers.delimited import Control
from veri_ufku.modeling.validation import digest
from veri_ufku.operations.workflow import references
from veri_ufku.storage.project_model import ProjectError, decode, encode, uid
from veri_ufku.storage.validation_store import transaction


def append(store, state, kind, payload, versions=()):
    now = datetime.now(UTC).isoformat()
    event = dict(
        schema="PrivacyEvent/v1",
        kind=kind,
        payload=payload,
        created_at=now,
        provenance=asdict(
            Provenance(
                provenance_id="provenance:" + uid(),
                dataset_versions=tuple(versions),
                config_revision=0,
                capability_id="privacy."
                + (
                    "review"
                    if kind == "review"
                    else "export"
                    if kind == "export"
                    else "retention"
                ),
                parameters_hash=digest(payload),
                environment=(("backend", "local privacy v1"),),
                created_at=now,
                scope="local declaration; no immutable audit claim",
                seed_reason="no random analysis",
            )
        ),
    )
    event = decode(encode(event))
    event["event_hash"] = digest(event)

    def add(draft):
        draft["results"].append(
            dict(
                id="result:" + uid(),
                dataset_version_ids=list(versions),
                seed=None,
                capability_id=event["provenance"]["capability_id"],
                privacy_event=event,
            )
        )

    return transaction(store, state, add)


def review(store, state, raw):
    p = policy(raw)
    ref = references(store, state).get(p["version"])
    if not ref or not {r["column"] for r in p["rules"]} <= {
        c["id"] for c in ref["columns"]
    }:
        raise ProjectError("Privacy dataset/ColumnId yok.")
    return append(
        store,
        state,
        "review",
        dict(policy=p, policy_hash=digest(p), fingerprint=ref["fingerprint"]),
        (p["version"],),
    )


def request_for(store, state, parameters):
    if not isinstance(parameters, dict):
        raise ProjectError("Privacy kapalı eylem şeması gerekli.")
    action = parameters.get("action")
    shapes = {
        "scan": {"action", "version"},
        "generate-key": {"action", "purpose", "key_ref"},
        "preview": {"action", "review_id"},
        "export": {
            "action",
            "review_id",
            "format",
            "destination",
            "preview_hash",
            "reviewed",
            "encryption_key_ref",
        },
        "inspect": {"action", "archive", "encryption_key_ref"},
    }
    if action not in shapes or set(parameters) != shapes[action]:
        raise ProjectError("Privacy eylem alanları geçersiz.")
    req = copy.deepcopy(parameters)
    req.update(project_id=store.manifest["project_id"], project_root=str(store.root))
    if action in ("inspect", "generate-key"):
        reference(req["encryption_key_ref"] if action == "inspect" else req["key_ref"])
        return req
    refs = references(store, state)
    if action == "scan":
        version = req["version"]
    else:
        event = next(
            (
                r["privacy_event"]
                for r in state["results"]
                if r["id"] == req["review_id"]
                and r.get("privacy_event", {}).get("kind") == "review"
            ),
            None,
        )
        if not event:
            raise ProjectError("Önce kolon kararlarını insan onayıyla kaydedin.")
        req["policy"] = event["payload"]["policy"]
        version = req["policy"]["version"]
        if (
            version not in refs
            or refs[version]["fingerprint"] != event["payload"]["fingerprint"]
        ):
            raise ProjectError("Privacy review kaynağı değişmiş.")
    if version not in refs:
        raise ProjectError("Privacy dataset sürümü yok.")
    req["source"] = refs[version]
    return req


def publish(store, state, value, control=None):
    (control or Control()).check()
    store._guard()
    if state != store.state:
        raise ProjectError("Privacy sırasında proje değişmiş.")
    if value.get("action") == "export":
        # No raw cells, key material or external destination paths in the journal.
        return append(
            store,
            state,
            "export",
            dict(
                preview=value["preview"],
                receipt={k: value["receipt"][k] for k in ("size", "sha256")},
            ),
            (value["preview"]["version"],),
        )
    return copy.deepcopy(state)


def retention(store, state, days):
    if type(days) is not int or not 1 <= days <= 3650:
        raise ProjectError("Retention1..3650gün; süre dolması otomatik silme değildir.")
    return append(
        store,
        state,
        "retention",
        dict(days=days, scope="owned idle privacy scratch only", automatic=False),
    )


def dependencies(state, manifest=None):
    from veri_ufku.storage.lineage import graph

    marked = {
        r["privacy_event"]["payload"]["policy"]["version"]
        for r in state["results"]
        if r.get("privacy_event", {}).get("kind") == "review"
        and any(
            x["classification"] != "not-pii"
            for x in r["privacy_event"]["payload"]["policy"]["rules"]
        )
    }
    if len(state["datasets"]) + len(state["results"]) + len(state["operations"]) > 1900:
        return dict(
            status="dependency preview budget exceeded; no purge allowed",
            marked_versions=sorted(marked),
        )
    g = graph(state, manifest or dict(artifacts={}, project_id="not_recorded"))
    reached = set(marked)
    while True:
        before = len(reached)
        reached.update(e["target"] for e in g["edges"] if e["source"] in reached)
        if before == len(reached):
            break
    linked = [
        dict(
            id=n["id"],
            kind=n["kind"],
            status="potential dataset-level PII dependency; not column/parameter proof",
        )
        for n in g["nodes"]
        if n["id"] in reached
        and n["id"] not in marked
        and n["metadata"].get("record_kind") != "privacy_event"
    ]
    return dict(
        marked_versions=sorted(marked),
        potential_results=linked,
        deletion="protected; no model/report/source purge",
        unknown="Only existing lineage graph edges; absent provenance and external copies/backups stay unknown",
    )


def validate_records(state):
    versions = {d["version_id"] for d in state["datasets"]}
    for r in state["results"]:
        e = r.get("privacy_event")
        if e is None:
            continue
        if (
            e.get("schema") != "PrivacyEvent/v1"
            or e.get("kind") not in ("review", "export", "retention", "cleanup")
            or e.get("event_hash")
            != digest({k: v for k, v in e.items() if k != "event_hash"})
        ):
            raise ProjectError("Privacy journal/hash geçersiz.")
        if not set(r["dataset_version_ids"]) <= versions:
            raise ProjectError("Privacy provenance dataset yok.")
        if e["kind"] == "review":
            p = policy(e["payload"]["policy"])
            if digest(p) != e["payload"]["policy_hash"] or r["dataset_version_ids"] != [
                p["version"]
            ]:
                raise ProjectError("Privacy review bağı geçersiz.")


def cleanup(store, state, cache, plan, confirmed, control):
    from veri_ufku.exports.privacy_cleanup import apply

    store._guard()
    if state != store.state:
        raise ProjectError("Cleanup sırasında proje değişmiş.")
    receipt = apply(cache, store.root, plan, confirmed, control)
    try:
        saved = append(store, state, "cleanup", receipt)
    except Exception:
        raise ProjectError(
            "Scratch temizlendi fakat yerel history kaydı yayımlanamadı; silinen scratch geri getirilmedi. Kaynaklar korundu."
        ) from None
    return saved, receipt
