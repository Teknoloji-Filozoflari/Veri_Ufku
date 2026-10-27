"""Installed runtime names and versions for a report. No paths or secrets."""

from importlib.metadata import PackageNotFoundError

from veri_ufku.storage.project_model import ProjectError


def environment_text(env):
    if not isinstance(env, dict):
        return "Paket sürümü okunamadı. Sürüm uydurulmaz."
    packages = env.get("packages")
    if not isinstance(packages, dict) or not packages:
        return "Paket sürümü okunamadı. Sürüm uydurulmaz."
    lines = [
        "Python: " + _show(env.get("python")),
        "Yorumlayıcı: " + _show(env.get("implementation")),
        "Makine: " + _show(env.get("machine")),
    ]
    names = sorted(packages)[:80]
    lines.extend(f"{name}=={_show(packages[name])}" for name in names)
    if len(packages) > 80:
        lines.append(f"İlk 80 paket. Kalan {len(packages) - 80} yazılmadı.")
    digest = _show(env.get("engine_hash"))
    if digest != "yok":
        lines.append("motor: " + digest[:64])
    return "\n".join(lines)


def current_environment_text():
    from veri_ufku.exports.code_bridge import environment

    try:
        return environment_text(environment())
    except (ProjectError, PackageNotFoundError, OSError, ValueError, TypeError):
        return "Paket sürümü okunamadı. Sürüm uydurulmaz."


def _show(value):
    raw = str(value or "").replace("\n", " ").strip()
    return raw[:80] or "yok"
