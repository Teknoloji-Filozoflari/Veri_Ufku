# Veri_Ufku — contribution and plugin API guide

Use the locked CPython3.13.15 `.venv`; preserve Linux/PySide6/QML and the existing
Capability registry, ComputeBudget, Provenance and atomic ProjectStore protocol.
Never modify user source data silently. Add meaningful contract tests, offline
learning help and explicit limits; record only checks actually run.

API1: `ImporterV1`, `TransformV1`, `StatisticV1`, `ModelV1`, `ChartV1`, `LessonV1` in
`veri_ufku.plugins.sdk`. Manifest-only discovery does not import plugin code.
`plugin.py:run(request, context)` runs only after explicit trust and compatibility
checks. Data-only output artifacts survive a missing plugin. The first SDK host
archives importer/transform table previews, model JSON state, chart descriptors
and lesson text; native dataset apply/model prediction/chart editor/catalogue
installation remain unavailable. The actual GUI example is a mean analysis.

Python plugins retain same-user filesystem, network and keyring rights. Process
isolation and manifest permissions are not an OS sandbox. Only execute trusted
code. A contract test checks API/shape/identities, not scientific correctness or
publisher authenticity. See the [example](../examples/plugins/mean/README.md) and
[API contract](adr/074-plugin-sdk-phase73.md).

Distribution contributions must keep core and optional profiles separate, avoid
unreviewed native library substitution, update license/model-data notices and run
the selected real package smoke. A missing environment/backend is unavailable,
not a successful test. Release CI builds reviewable local candidates; publishing
requires a separate explicit request.
