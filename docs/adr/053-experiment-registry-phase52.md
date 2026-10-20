# ADR053 — yerel experiment/model registry

DEC52-01 yalnız açık Faz52. Existing ProjectStore results, single Capability registry,
Provenance/ComputeBudget extended; registry is a projection of current immutable runs,
not a second database. Existing IDs/final-test journal preserved. ExperimentEvent/v1
append-only hash chain with typed revisions is protected by existing transaction guard.
RunCapture/v1 captures reviewed local model/storage code-file hashes, typed config and
allowlisted runtime versions before scheduling. Worker read start and full wall elapsed
recorded on new supervised runs; neither is source snapshot collection time. Old absent
metadata unknown, no retrospective code/CPU claims. CPU/GPU determinism not guaranteed.

Model versions use training run identity and existing safe .vumodel/ModelCard references.
Selection verifies artifacts; statuses local, no deploy. New metric view is an explicit
revision; threshold/calibration/preprocessing changes require a new training run via
existing immutable workflow. Comparison uses actual BaselineRun folds or explicit
validation/final scope, dataset/snapshot/split/protocol/target/decision/uncertainty key;
unknown or mismatched protocols warn and suppress common Pareto. Historical reported
selected evaluation duration and newer full job elapsed have different cost scopes.
Other legacy result schemas listed but native statistical ranking not fabricated.

Streaming source/model/details integrity checks in Qt-free thread with Control wall/RAM/
cancel. Archive no delete; physical deletion closed with explicit loss explanation.
Default4GiB quota counts historical sources/snapshots, rejects promotion before cap;
metadata/free-space staging remains existing separate guard. No automatic GC.
Allowlisted aggregate JSON export excludes raw config/cards/free tags/labels/paths/env;
not anonymity. Tracking backend unconfigured/unvalidated; core no network dependence.
