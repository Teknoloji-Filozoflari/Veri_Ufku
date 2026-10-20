# ADR073 — bounded privacy, user decisions and encryption threat model

2026-10-16 DEC72-01; yalnız açık Faz72 talimatı. Linux/PySide6/QML ve tek
ProjectStore, Capability registry, ComputeBudget ve Provenance korunur.

PII taraması email/telefon/secret desenleri ve Türkçe/İngilizce kolon adı
ipuçlarıyla **aday** üretir. 32MiB snapshot,10000satır,64kolon; bulguda ham değer
örneği yerine ilk5RowId ve sayımlar. Yanlış pozitif/negatif vardır; özel nitelikli
veri, yüz/ses/metin bağlamı veya tüm kimlik biçimleri için detector değildir.
Kullanıcı1..16ColumnId için pii/not-pii/uncertain ve mask/drop/pseudonym/keep
kararı, yerel reviewer beyanı ve gerekçe kaydeder. Keep yalnız not-pii kararıyla;
secret deseni veya secret adlı kolon keep edilemez. Seçilmeyen kolonlar exporta
girmez. Kaynak, mevcut dataset ve geçmiş sürümler değiştirilmez.

PrivacyEvent/v1 mevcut results journal'ında, ortak Provenance ile atomik kaydedilir.
Review kaynak fingerprint ve DatasetVersion'a bağlıdır. Output önizleme hash'i,
policy hash'i ve source hash'i exportta yeniden doğrulanır. Günlükten eski event
silme önceki transaction korumasına eklenmiştir; ikinci DB/registry yoktur.
Yerel append-only yazılım kuralı yöneticiye/aynı kullanıcıya karşı değiştirilemez
kayıt veya güçlü nonrepudiation değildir. Reviewer kimlik doğrulaması değildir.

Export gerçek CSV/Parquet ve manifest ZIP'idir; kolonlar alias, internal RowId ve
SourceRecordId yoktur. Yerel kaynak kimlikleri korunur. Null maskede null kalır;
CSV formula-prefix escape; Parquet tip/null için asıl çıktıdır. Önizleme keep ve
pseudonym değerlerini de gizler. Manifestte ColumnId/hash/ref bulunması linkage
bilgisidir. Kullanıcı gerekçeli keep kararı yine PII kaçırabilir: tarama hukuki
uygunluk veya eksiksiz secret/PII garantisi değildir.

## Tehdit modeli / encryption kararı

| Tehdit | Kapsam / karar |
|---|---|
| Harici diskte kaybolan explicit export | Optional pyca cryptography50.0.2 Fernet ile authenticated encryption; en fazla32MiB expanded paket,48MiB sealed input |
| Anahtar üretimi/saklama | Kütüphane random32byte key; yalnız Linux Secret Service, purpose namespace hmac/fernet; referans exportta, değer asla manifest/logda değil |
| Kolon pseudonymization | Stdlib HMAC-SHA256; proje/ColumnId domain separation, aynı key ile eşit değer eşit pseudonym. Frekans/linkage/sözlük riski sürer; anonimlik değil |
| Kilitli/eksik servis, bozuk/kayıp key | Açık hata; dosya/env/plaintext fallback veya key overwrite yok. Key loss aynı pseudonymi ve decryption'ı engeller |
| Kurtarma | Aynı Secret Service anahtarıyla doğrulamalı decryption; otomatik escrow/backdoor/reset yok. Sistem keyring recovery/backup bu ürünün doğrulanmış yeteneği değil |
| Açık oturum, RAM/swap, kullanıcıya ait kötü niyetli kod/plugin | Korunmaz. Process isolation OS sandbox değildir; Python key byte'larının güvenli sıfırlandığı iddia edilmez |
| Canlı proje DB, snapshot/artifact/cache/source/backup | **Şifreli değil.** Export encryption bu kopyaları korumaz. Tam disk encryption işletim sistemi katmanıdır; bu faz uygulamaz/doğrulamaz |
| Bütün proje encryption ihtiyacı | At-rest tehdit için gereklidir; SQLite WAL/recovery/ACTIVE/snapshot/crash atomicity ve key lifecycle birlikte tasarlanmalıdır. SQLCipher backend bu ortamda yok; özel kripto veya sahte encrypted-project rozeti eklenmedi |
| Aynı kullanıcı/admin tarafından journal değiştirilmesi | Yerel history güçlü audit/nonrepudiation sağlamaz; hash gönderen kimliğini doğrulamaz |

[Fernet resmi belge](https://cryptography.io/en/stable/fernet/) full-message memory
sınırı nedeniyle küçük explicit bundle tercih edildi. [Secret Service standardı](https://specifications.freedesktop.org/secret-service/latest-single/)
oturum servisini tanımlar. Optional extra `privacy`; temel açılış cryptography/keyring
import etmez ve internete ihtiyaç duymaz. Ağdan bağımlılık/model indirme açılışta yok.
Keys yalnız explicit action'da budget/cancel kontrollü worker belleğinde yüklenir;
Qt parent'a key dönmez. Key oluşturma servis tarafında iptalden önce tamamlanabilir; iptal key rollback garantisi değildir, tekrar aynı referansı overwrite etmez. Şifreli manifest inceleme extract/code import yapmaz.
Python `privacy_keys.decrypt` aynı key ile ZIP byte'larını geri verir; test bu
recovery primitive'ini doğrular, GUI yalnız authenticated manifest incelemesi yapar.

## Retention / deletion scope

Gün1..3650 retention insan politikasıdır, otomatik silme değildir. Cleanup sadece
bu controller'ın cache kökünde işaretli, flat, eski, owner process'i yaşamayan privacy
scratch dizinleri içindir. 128dizin/toplam32MiB; marker/payload.zip/sealed.vupseal
allowlist; hash/inode/root identity onayı ve yeniden doğrulama. Symlink, hardlink,
unknown member, yeni dosya, canlı/recycled PID korunur. Preview hash +explicit onay
olmadan unlink yok. Aynı kullanıcı tarafından düşmanca eşzamanlı filesystem yarışına
karşı OS güvenlik sınırı iddiası yoktur; uygulama idle +single writer gerektirir.

Current/historical project artifact, ACTIVE/SQLite/recovery, dataset/source, model,
rapor, kullanıcı exportu ve dış dosya **silinmez**. Genel artifact purge yoktur;
referanslı veri silinip geçmişi kırılmaz. Kaynak PII ilişkisi dataset düzeyinde
muhafazakâr operation closure/potential result listesidir; bilinmeyen provenance
uydurulmaz, learned parameter/ColumnId düzeyinde unutma kanıtı veya dış backup
keşfi değildir. Fiziksel SSD/snapshot/backup secure erase garantisi yoktur.
Silme geri alınamaz; cancel tamamlanan scratch silmelerini geri getirmez. History
publish silmeden sonra başarısızsa bu açık hata olarak belirtilir, rollback iddiası yok.

## Hedefli import/code/plugin/network yeniden denetimi

| Sınır | İncelenen yol / sonuç |
|---|---|
| Import | `importers/registry.py` sabit adaptörler; `ods.py` bounded ZIP/path/symlink/DTD/entity reddi. `tests/test_security_audit.py` hostile fixture ve kaynak koruma. Tüm parsers'ın formal security proof'u değil |
| Code | `modeling/code_kernel.py` explicit subprocess -I, kaynak16KiB/output64KiB, timeout/cancel/processgroup/resource limit; `code_workspace.py` hash-only persisted source/output. Aynı kullanıcı FS/network hakları var; güvenli sandbox değil |
| Plugin | Registry/app incelendi: entrypoint/dosya paketinden otomatik untrusted plugin yükleme yolu yok. Trusted installed Python/backend aynı kullanıcı haklarıyla çalışır; plugin permission sandbox yok |
| Network | `http_connectors.py`: GET-only, default TLS verification, no redirect, no ambient proxy, bounded retries/content, reflected credential ret. `tests/test_connectors.py` HTTP altkümesi gerçek local TLS server ile yeniden koşulur; PostgreSQL/MySQL/S3 bu fazda yeniden test edildi sayılmaz |
| Logs | `logging_setup.py` teknik event allowlist; exception text/cell/path/key yok. Privacy worker generic exception type-only, keyring failure secret exception metni bastırılır |
| DP | Mevcut değil: mekanizma/sensitivity/komşuluk ve toplam epsilon/delta accountant yok. Noise veya hash DP diye etiketlenmez |

Gerçek çalıştırma ve ortam [E72](../evidence/PHASE72.md). Servis bulunmayan
Secret Service entegrasyonu, canlı proje encryption, DP, insan/AT/fiziksel/minHW/
offlineinstaller/remoteCI doğrulanmış sayılmaz.
