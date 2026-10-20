"""Standard-library HMAC / pyca Fernet keys, Linux Secret Service only."""

import base64
import hashlib
import hmac
import json

from veri_ufku.exports.privacy_contracts import reference
from veri_ufku.storage.project_model import ProjectError

PURPOSES = ("hmac", "fernet")


def generate(purpose, ref):
    reference(ref)
    if purpose not in PURPOSES:
        raise ProjectError("Key purpose hmac/fernet gerekli.")
    from veri_ufku.importers.credentials import backend

    try:
        from cryptography.fernet import Fernet

        vault = backend()
        service = "Veri_Ufku.privacy." + purpose
        if vault.get_password(service, ref) is not None:
            raise ProjectError(
                "Key referansı mevcut; üzerine yazılmaz. Yeni referans seçin."
            )
        key = Fernet.generate_key().decode("ascii")
        vault.set_password(service, ref, key)
        if vault.get_password(service, ref) != key:
            raise ProjectError("Keyring kayıt doğrulaması başarısız.")
        return dict(
            purpose=purpose,
            key_ref=ref,
            status="stored-in-Secret-Service; no recovery escrow",
        )
    except ImportError:
        raise ProjectError(
            "Optional privacy extra cryptography/keyring gerekli; plaintext fallback yok."
        ) from None
    except ProjectError:
        raise
    except Exception:
        raise ProjectError(
            "Secret Service key oluşturulamadı; dosya/env fallback yapılmadı."
        ) from None


def load(purpose, ref):
    reference(ref)
    if purpose not in PURPOSES:
        raise ProjectError("Key purpose geçersiz.")
    from veri_ufku.importers.credentials import backend

    try:
        key = backend().get_password("Veri_Ufku.privacy." + purpose, ref)
        if not isinstance(key, str) or len(base64.urlsafe_b64decode(key)) != 32:
            raise ValueError()
        return key.encode("ascii")
    except Exception:
        raise ProjectError(
            "Secret Service key bulunamadı/kilitli/uyumsuz; işlem yapılmadı. Key kaybı için otomatik recovery yok."
        ) from None


def pseudonym(key, project_id, column, value):
    # Domain separation uses the application contract, HMAC itself is the stdlib primitive.
    message = json.dumps(
        ["Veri_Ufku.pseudonym/v1", project_id, column, value],
        ensure_ascii=False,
        sort_keys=True,
        default=str,
        allow_nan=False,
    ).encode()
    return (
        "psn_"
        + hmac.new(base64.urlsafe_b64decode(key), message, hashlib.sha256).hexdigest()
    )


MAGIC = b"Veri_Ufku.FernetExport/v1\n"


def encrypt(payload, key):
    from cryptography.fernet import Fernet

    return MAGIC + Fernet(key).encrypt(payload)


def decrypt(payload, key):
    from cryptography.fernet import Fernet, InvalidToken

    try:
        if not payload.startswith(MAGIC):
            raise ValueError()
        return Fernet(key).decrypt(payload[len(MAGIC) :])
    except (InvalidToken, ValueError, TypeError):
        raise ProjectError(
            "Şifreli export doğrulanamadı; yanlış/kayıp key veya bozuk dosya. Plaintext çıkışı yapılmadı."
        ) from None
