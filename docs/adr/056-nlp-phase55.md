# ADR056 — topic, local model, original offsets ve insan review sınırı

TextSpec/v1 optional advanced NLPSpec/v1; old data() omits None. Existing TextRun/v1
advanced NLPRun/v1 safe JSON artifact via same ProjectStore atomic publication.
No second registry; author model program/pickle/remote code never imported.
500documents/500000chars/5000chars perdoc/8topics/16MiB model JSON. Native safe
LocalNLPBundle/v1: model language/name/model-license/dataset/dataset-license/assumptions,
static word vectors mean+L2, exact original case-sensitive literal gazetteer,
optional linear softmax classifier. This is not transformer/contextual NER; negation/
word order/OOV/domain transfer limits explicit. Author declarations no quality proof.
No neural backend installed/runtime validation. External model folder selected explicitly;
weights copied into immutable run artifact, source/cache hash+canonical model hash.
Opening stored run does not access model folder/network. Public HTTPS explicit button,
exact bytes+SHA256, secure TLS, same-origin redirect≤3, timeout10, no auth/query/token;
no generic HuggingFace download support. Publisher/license/use conditions visible.

NMF TF-IDF and LDA raw counts use existing Analyzer/vocabulary on train only;
topic names manual/versioned. Classification fixed train-only TF-IDF/LogisticRegression
on approved human labels, validation only; test texts/labels excluded from fit/predict/
active pool (source integrity hashes still cover full snapshot). Exact document duplicates
across splits rejected. Pretrained suggestions never auto ground truth. Label schemas,
reviewer decision and revision history bind source/version/RowId/hash. Review publishes
new run/revision, original retained, annotation changes invalidate metrics/active selection
until refit; undo is another explicit revision. Export defaults IDs/labels/offsets/hash/
split/schema/revision, reviewer hashed, raw text only explicit checkbox; no overwrite.

NER matches immutable original strings, Python codepoint [start,end), explicit UTF16
for QML. No normalized-offset guess; emoji/combining fixture verifies original slice.
Static cosine is not probability; linear softmax uncalibrated. OOV/zero vector visible;
query outside vocab rejected, no invented score. Active learning only train unlabeled
pool, test labels cannot alter candidates. Retrieval metrics only query-specific complete
human judgments over the full non-test corpus including zero-vector/OOV documents; unjudged≠negative, no judgment
means metrics=None. Final-test serving/new-file fitted classifier/advanced model search
closed; previous Faz16/22 classification path and test ledger preserved.

Reviewed 2026-10-14 official [NMF](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.NMF.html),
[LDA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.LatentDirichletAllocation.html),
[Unicode str](https://docs.python.org/3/library/stdtypes.html#text-sequence-type-str).
Native adapters validated by actual synthetic local bundles, not a production Turkish
quality/accuracy benchmark. Backend architecture and runtime evidence distinct.
