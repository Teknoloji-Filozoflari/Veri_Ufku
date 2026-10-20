"""Secrets live only in a Linux Secret Service keyring and worker memory."""

from veri_ufku.storage.project_model import ProjectError

SERVICE = "Veri_Ufku.connectors"


def backend():
    try:
        import keyring
        from keyring.backends.SecretService import Keyring

        selected = keyring.get_keyring()
        # Refuse plaintext, fail, null and arbitrary plugin backends. Never
        # silently fall back to a file or environment credential chain.
        if not isinstance(selected, Keyring):
            raise ProjectError(
                "Linux Secret Service keyring açılmadı; dosyaya parola yazılmadı."
            )
        return selected
    except ImportError as error:
        raise ProjectError(
            "Connectors paketi/Secret Service eksik; temel uygulama çevrimdışı kullanılabilir."
        ) from error


def store(reference, secret):
    from veri_ufku.importers.connector_contracts import ConnectorSpec

    ConnectorSpec(kind="duckdb", credential_ref=reference)
    if not reference or not secret or len(secret) > 16384:
        raise ProjectError("Keyring referansı ve sınırlı secret gerekli.")
    try:
        backend().set_password(SERVICE, reference, secret)
    except Exception as error:
        raise ProjectError(
            "Secret Service kaydı başarısız; secret log/projeye yazılmadı."
        ) from error


def load(reference):
    if not reference:
        return None
    try:
        secret = backend().get_password(SERVICE, reference)
        if secret is None:
            raise ProjectError("Keyring referansı bulunamadı.")
        return secret
    except Exception as error:
        raise ProjectError(
            "Secret Service credential okunamadı; bağlantı başlatılmadı."
        ) from error
