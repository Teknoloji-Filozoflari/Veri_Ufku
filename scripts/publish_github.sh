#!/usr/bin/env bash
# Run in a normal desktop terminal; authentication stays in GitHub CLI.
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "$project_root"
repository='Teknoloji-Filozoflari/Veri_Ufku'
remote_url="https://github.com/${repository}.git"
trap 'printf "\nİşlem tamamlanamadı. Yukarıdaki hata metnini paylaşabilirsiniz; erişim anahtarını paylaşmayın.\n" >&2' ERR

for required_tool in git gh; do
    if ! command -v "$required_tool" >/dev/null 2>&1; then
        printf 'Gerekli komut bulunamadı: %s\n' "$required_tool" >&2
        exit 1
    fi
done

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
    printf 'GitHub oturumu açılacak. Terminaldeki yönergeleri ve tarayıcı onayını tamamlayın.\n'
    gh auth login --hostname github.com --git-protocol https --web --scopes workflow
fi
# Confirm access before touching local Git metadata.
gh api "repos/${repository}" --jq .full_name
# Use gh credentials for this invocation, without modifying global Git configuration.
github_git() {
    git -c credential.helper= -c 'credential.helper=!gh auth git-credential' "$@"
}
github_git ls-remote "$remote_url" >/dev/null

if [[ -L .git ]]; then
    printf '.git bir sembolik bağlantı; otomatik değiştirilmedi.\n' >&2
    exit 1
fi
if [[ -d .git ]] && [[ ! -f .git/HEAD ]]; then
    if [[ -n "$(find .git -mindepth 1 -print -quit)" ]]; then
        printf '.git geçerli değil ve boş değil; içerik korunarak işlem durduruldu.\n' >&2
        exit 1
    fi
    backup_path="$(mktemp -d "$project_root/.git-before-github.XXXXXX")"
    mv -- .git "$backup_path/empty-git"
fi
if [[ ! -e .git ]]; then
    git init -b main
fi
if [[ "$(git rev-parse --show-toplevel)" != "$project_root" ]]; then
    printf 'Git deposunun kökü proje klasörüyle eşleşmiyor.\n' >&2
    exit 1
fi
if git remote get-url origin >/dev/null 2>&1; then
    if [[ "$(git remote get-url origin)" != "$remote_url" ]]; then
        printf 'Mevcut origin farklı; değiştirilmedi.\n' >&2
        exit 1
    fi
else
    git remote add origin "$remote_url"
fi
if [[ "$(git symbolic-ref --short HEAD)" != main ]]; then
    printf 'Mevcut dal main değil; dallar otomatik değiştirilmedi.\n' >&2
    exit 1
fi

# Keep existing configured author identity; otherwise use the authenticated account.
if [[ -z "$(git config user.name || true)" ]]; then
    git config user.name "$(gh api user --jq .login)"
fi
if [[ -z "$(git config user.email || true)" ]]; then
    github_login="$(gh api user --jq .login)"
    github_user_id="$(gh api user --jq .id)"
    git config user.email "${github_user_id}+${github_login}@users.noreply.github.com"
fi

# Explicit project paths: never add virtual environments, credentials or local logs.
git add -- .gitignore .python-version .github AGENTS.md README.md \
    Veri_Ufku_Birlestirilmis_Gelistirme_Promptlari.md \
    pyproject.toml uv.lock src tests scripts docs tools/wheels
if ! git diff --cached --quiet; then
    git commit -m 'feat: bootstrap Veri_Ufku desktop and phase 01 infrastructure'
fi
commit_id="$(git rev-parse HEAD)"
printf '\nProje GitHub main dalına gönderiliyor.\n'
# No force push: an existing divergent remote history is preserved.
github_git push --set-upstream origin main
printf '\nGönderildi: https://github.com/%s/commit/%s\n' "$repository" "$commit_id"
printf 'CI koşusu bekleniyor…\n'
run_id=''
for ((attempt=0; attempt<30; attempt++)); do
    run_id="$(gh run list --repo "$repository" --commit "$commit_id" --workflow docs.yml \
        --limit 1 --json databaseId --jq '.[0].databaseId // empty')"
    if [[ -n "$run_id" ]]; then break; fi
    sleep 2
done
if [[ -z "$run_id" ]]; then
    printf 'Dosyalar gönderildi; CI koşusu henüz listelenmedi. Kontrol: https://github.com/%s/actions\n' "$repository"
    exit 2
fi
printf 'CI: https://github.com/%s/actions/runs/%s\n' "$repository" "$run_id"
gh run watch "$run_id" --repo "$repository" --exit-status
printf '\nCI başarılı. Yukarıdaki CI bağlantısını paylaşın; Faz 01 kabul kaydını tamamlayalım.\n'
