# ADR-042: Faz41 açık bağımsız birim resampling

2026-10-11; DEC41-01 kullanıcı talimatı teknik uygulama yetkisidir. Önceki
resmî DEP-28-GATE/insan/AT/donanım kapıları kapanmaz. Python/PySide6/QML,
Capability registry, StatisticsController/spawn/ComputeBudget ve atomik
analysis_store/ProjectStore mevcut yolu genişletilir. Worker ACTIVE yazmaz.

## Yöntem ve birim

Percentile bootstrap: observation iid; cluster bütün satırlarla replacement;
time moving overlapping block sıralı tam veri,son blok n'ye kesilir.
Cluster bootstrap pooled row estimand; cluster-label permutation eşit ağırlıklı
cluster mean farkıdır. BCa yalnız iid/cluster mean,delete-one independent-unit
jackknife; bias midrank tie politikası. Median/trim/time BCa reddedilir.
Missing/nonfinite/sabit bootstrap veya degenerate jackknife/bias/tail5ten az
replicate: CI unavailable, sahte sınır yok. Linear quantile; MC endpoint
binomial order-statistic bands simülasyon belirsizliğidir, veri CI değil.

Permutation iki açık label,after−before,fark0/exchangeable distribution null;
sabit label counts. Heteroskedastic dağılımlarda yalnız mean eşitliği yeterli
exchangeability sayılmaz. Paired wide x/y ve benzersiz kişi key,
after−before−null için whole independent-unit sign; simetri/random-sign
ve exchangeability kullanıcı onayı şart. Time permutation/sign-flip yok.
Null uzayı≤10000 exhaustive inclusive ties; büyük uzay seedli bağımsız
replacement MC (k+1)/(B+1),Clopper–Pearson95% exceedance probability bandı.
Seed/tekrar/H0/tail/birim/mapping/draw-distribution kalıcı kayıt/exportta.

2000 satır,10000 tekrar ve2000000 satır×tekrar sınırı; kaynak/ColumnId/RowId/hash
korunur. Cluster/time missing satırı sessiz düşürülmez; grubu parçalama veya
sahte zaman bitişikliği ret. Time unique numeric/temporal order,n≥2L;
durağanlık/blok uzunluğu açık varsayım. Weight/decimal/nested desteklenmez.
PCG64 seed; cancellation/CPU/RAM/disk admission ve progress korunur.

## Robust, aile ve duyarlılık

Mean/median/trimmed mean/raw MAD; keep,3×1.4826MAD exclude (MAD0 ret),
linear quantile bounds winsorize. Kaynak değişmez; betimsel n/politika görünür.
Multiple testing ayrı p-değeri dataset sütunu +benzersiz testID +aile adı ve
açık seçili kimlik listesi. Geçerli original p-değerlerini kullanıcı getirir;
original null/tail/test varsayımları halen gereklidir, adapter bunları üretmez.
Holm/Bonferroni arbitrary dependence FWER; BH independence/PRDS FDR.
Seçili eksik/duplicate p/testID ret; aile sessiz küçülmez. Dışarıda bırakılan
kimlikler,raw/adjusted p/alpha/error-control ve üyeler exportta kayıtlı.

Duyarlılık baseline +en fazla8 önceden belirlenmiş filtre/outlier/missing/
alternatif ölçü senaryosu. Delta missing observed mean+delta,MI/çıkarım değil.
Sonuç/baseline değişimi,n,missing/imputed/outlier ve RowId görünür; ret senaryosu
unavailable kalır. Senaryolar bağımsız descriptive kapsamdır; farklı filtre
RowId union atomik üyelikte saklanır. En küçük pyi seçme/p-hacking öğretilir.

Safe JSON result/recipe +RowId üyelik +unit-draw/null/scenario parquet.
Aile ve audit kimlikleri atomic save/reopen/new-directory exportta korunur;
current dataset/view/source/config bağı olmadan save/export engellenir.
Desteklenen yöntemler gerçek desktop GUI +çevrimdışı help ile doğrulanır.
Gerçek referans ve test sonuçları docs/evidence/PHASE41.md içinde tutulur.
