# GitHub yükleme hazırlığı — 2026-10-21

Mevcut origin: `https://github.com/Teknoloji-Filozoflari/Veri_Ufku.git`, dal `main`.
GitHub CLI bu makinede kurulu. Kullanıcının normal masaüstü terminalinde:

```sh
gh auth login --hostname github.com --git-protocol https --web --scopes workflow
gh auth setup-git
gh auth status
```

Tarayıcıdaki kodu onaylayın. Giriş anahtarını komuta, projeye veya sohbete
kopyalamayın. GitHub CLI sistem credential store kullanır; bulunamazsa düz dosyaya
dönebilir. `gh auth status` saklama yerini gösterir; `--insecure-storage` kullanmayın.
[Resmî komut belgesi](https://cli.github.com/manual/gh_auth_login).
Bu hazırlık çalışmasında hesap oturumu/uzak yazma yetkisi doğrulanmadı.

## Yapılan temizlik

Eski üç Flatpak builddir çalışma kopyası, eski Windows runtime açılımı ve
src/tests/scripts/examples Python bytecode ile pytest/Ruff önbellekleri silindi.
Her hedef için git tracked kontrolü yapıldı; tracked kaynak silinmedi.
[Silinen üretilmiş alanların boyut/adet kaydı](evidence/github-preparation/cleanup.json).
Tekrar test çalıştırmak küçük önbellekleri yeniden oluşturabilir.

Çalışan `.venv`, eski paket binary/repo arşivi, indirilen offline build kaynakları,
logo tasarımları, tools/wheels içindeki kilitli Ruff wheel'i ve bütün tarihsel test
kanıtları korundu. `build/` ve `dist/` zaten Git dışında. Eski builddir üzerinden
çalıştırma artık mümkün değildir; gerekirse paket build betiğiyle tekrar oluşturulur.
Saklanan paketler güncel sürüm doğrulaması sayılmaz.

`.gitignore`: yerel credential/agent dizinleri, .env, editör/coverage/cache çıktıları
hariç tutuldu. `docs/evidence` ve `output/branding` bütünüyle ignore edilmedi:
belgeler bunlara bağlı, logo üretim betiği seçilmiş kaynak PNG'yi kullanıyor.

## Gönderim önkontrolü

```sh
bash scripts/publish_github.sh --check
```

Bu mod ağ/kimlik doğrulama, stage, commit veya push yapmaz. `check_publish.py`:
çalışma ağacındaki tracked+untracked gönderim adaylarını, gerekli dağıtım dosyalarını,
ignore edilmiş ama tracked dosyaları, symlink'leri ve dosya boyutlarını kontrol eder.
Metinde GitHub token, AWS erişim kimliği, özel anahtar başlığı ve credential URL
biçimlerini tarar; eşleşen gizli değeri çıktıya yazmaz. İncelenmiş sahte URL test
fixture'ları yalnız dosya yolu ve tam eşleşme hash'iyle istisnadır; testler veya
kanıt dizinleri topluca tarama dışı bırakılmaz.

Bu sınırlı desen taraması bütün sırları, PII'yi, binary/compressed artifact içeriğini
ve Git geçmişini doğrulamış sayılmaz. Yaklaşık968MiB aday içerik bulunuyor; büyük
kısmı belgelerin bağlı olduğu tarihsel kanıtlardır.100MiB üstü dosya bulunmadı.
GitHub100MiB üstünü reddeder; küçük depo önerir.
[Resmî boyut sınırları](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

Gönderim betiğinin açık path listesine önceden atlanan LICENSE, CHANGELOG,
CONTRIBUTING, packaging, examples ve output/branding eklendi. Gerçek gönderim
istenirse `bash scripts/publish_github.sh` **stage, commit ve main push yapar**;
`--check` ile karıştırılmamalı. Bu görevde o mod çalıştırılmadı. Force push yok.

## Gerçek kontroller

- [3 önkontrol testi](evidence/github-preparation/tests.xml): gizli değeri yazmadan
  token/büyük dosya/symlink reddi; ignore tracked credential'ı saklamaz; gerekli
  dosya ve generated cache ayrımı; index değişmezliği.
- [Gönderim dry check](evidence/github-preparation/publish-check.json): hata yok.
- [Belge](evidence/github-preparation/docs.log),
  [artifact](evidence/github-preparation/artifacts.log),
  [Ruff](evidence/github-preparation/ruff.log),
  [format](evidence/github-preparation/format.log): PASS; shell `bash -n` PASS.
- Uygulama runtime kodu değişmedi; bu temizlikte bilimsel/GUI suite yeniden koşulmadı.

Çalışma ağacındaki önceki bütün kaynak değişiklikleri ve untracked yeni modüller
korundu. Stage/commit/push yapılmadı; resmî faz kabul durumu değişmedi.
