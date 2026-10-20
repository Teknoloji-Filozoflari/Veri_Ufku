# Faz55 — bounded NLP ve versioned insan annotation

<a id="e55"></a>
DEC55-01 açık kullanıcı talimatı. Yalnız Faz55; Faz56 yetkisi yok.
ENV-55 lockedCPython3.13.15 CPU/offscreen/software.
[Ortam](phase55/environment.json),[sözleşme ve backend](../adr/056-nlp-phase55.md).
12 bounded native teknik kayıt doğrulandı; resmî sürüyor/deneysel/zorunlu. Mevcut TextSpec/TextRun/worker/atomic
ProjectStore/Capability/ComputeBudget/Provenance/Faz52 registry genişletilir.
Native static vector/literal gazetteer/linear bundle, pretrained neural backend değil.
Transformer/spaCy/ONNX bulunmuyor; desteklenmeyen klasör açıklamalı reddedilir.
Önceki fiziksel/insan/AT/minHW/offlineinstaller/remoteCI/fullrepo aggregate açık.

[437source core](phase55/source-core.xml),[437noneditablewheel core](phase55/wheel-core.xml),
[23actual GUI/regression](phase55/source-ui.xml),[1actual localhost TLS/cache](phase55/source-https.xml).
20new offline core+1sourceTLS,12newGUI. Network test excluded from broad suites;
not counted as passed/skipped there. Socket approval scope limited localhost test.
[12source actualGUI](phase55/source-gui-delivery/walkthrough.json),
[12installed actualGUI](phase55/wheel-gui-delivery/walkthrough.json):48PNG/48safeJSON run+masked registry.
[12C/V/G/H/P](phase55/acceptance.json),[commands/limits](phase55/verification.json),
[307byte-equal package](phase55/wheel.json),[frozen-head](phase55/frozen-head.json),
[fresh4XDG smoke](phase55/smoke.json),[gates](phase55/gates.json).

References: Turkish original spans with emoji/combining marks roundtrip via codepoint
and UTF16; model SHA/size/author-license/dataset-license/language visible. Missing model
unavailable explanation, wrong language visible error, no invented labels. Real local
safe weights→embedding/NER/sentiment pipeline; delete external model folder then stored
artifact reopen succeeds offline. Native topic train-only vocab/NMF/LDA; manual naming.
Human approved label classifier/validation and versioned annotation review/export, old
revision retained/undo; annotations invalidate metrics until refit. Test label poison
leaves fit/active candidates unchanged; training vocabulary excludes held test tokens.
Same-version saved test rows cannot be reclassified as training on schedule/publish.
Static cosine hand reference, no calibrated probability claim. Full non-test corpus
relevance mandatory for evaluation; relevant zero-vector documents remain denominator;
no judgment means no success metric. Original source bytes unchanged; raw export
opt-in, default reviewer hashed/IDs/offset/schema/revision only. Actual spawn cancel
preserves previous run. Text-analysis run IDs linked existing registry; corrupted
artifact hash verified, generic comparison metrics/protocol unknown rather than invented.

LocalNLPBundle/v1 native static word vectors mean+L2, exact literal case-sensitive
NER gazetteer and linear softmax; no transformer/context/negation/general Turkish
accuracy guarantee. Model/dataset license/training declarations belong to author.
500rows/500000chars/5000chars perdoc/8topics/16MiB bundle. Closed publicHTTPS exact
SHA/size download; authenticated/model-hub/neural model weights unsupported. No model
script/pickle import, no external model/network access on reopen. Fixed TF-IDF classifier
train/validation only; final-test/tuning/new-file fitted serving closed. Generic native
model comparison unavailable/unknown. Partial source-gui/source-gui-release and older
source-gui-final/wheel-gui-final are preliminary; delivery manifests authoritative.
Physical/human/AT/minHW/clean offline installer/remoteCI/full repository aggregate,
wheel network and production neural NLP benchmark not run; previous gaps preserved.
No stage/commit/push;Faz56 not started.

Stricter held-test vocabulary assertions additionally verified in [13source affected cases](phase55/source-token-guard.xml) and [13installed wheel affected cases](phase55/wheel-token-guard.xml); computational code unchanged after437+437.
