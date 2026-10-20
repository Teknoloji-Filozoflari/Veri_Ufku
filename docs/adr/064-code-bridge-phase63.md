# ADR064 — sınırlı GUI profile kod köprüsü ve explicit code process

2026-10-15; DEC63-01; yalnız açık Faz63 yetkisi.

Destekli numeric dataset profile için aynı Python motorunu ve açık SQLite subset'i
üret; bilinmeyen analizleri çevrilmiş gibi sunma. Pakete ham veri/output/secret değil
UUID/hash dataset reference ve exact runtime/engine lock koy. Notebook boş çıktılı.
Serbest code ayrı opt-in fresh process; doğrulanmış OS sandbox iddiası yok. User cell
stdin ile, hash-only provenance durable olduktan sonra çalışır. Stdout/stderr volatile,
mask best-effort; source/output otomatik saklanmaz. Tek registry/ComputeBudget/
Provenance/ProjectStore/neural journal ve Faz16 geçmişi korunur. Managed Jupyter
unavailable, dış notebook istemcisi optional; masaüstü core bağımsızdır.

[Kapsam, gerçek kontroller ve açıklar](../evidence/PHASE63.md). Faz64 yetkisi yok.
