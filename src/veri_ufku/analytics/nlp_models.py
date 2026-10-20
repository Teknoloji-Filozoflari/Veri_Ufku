"""Safe static-vector/literal-entity/linear model bundles and explicit HTTPS acquisition."""

import hashlib
import json
import math
import os
import ssl
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from veri_ufku.importers.delimited import Control
from veri_ufku.storage.project_model import ProjectError, digest, encode

LIMIT = 16 * 1024**2


def parse(raw):
    if len(raw) > LIMIT:
        raise ProjectError("Yerel model16MiB sınırı.")

    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError
            out[k] = v
        return out

    try:
        m = json.loads(
            raw,
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        required = {
            "schema",
            "name",
            "languages",
            "license",
            "training_dataset",
            "dataset_license",
            "assumptions",
            "vectors",
            "entities",
            "classifier",
        }
        if (
            not isinstance(m, dict)
            or set(m) != required
            or m["schema"] != "LocalNLPBundle/v1"
        ):
            raise ValueError
        for key in [
            "name",
            "license",
            "training_dataset",
            "dataset_license",
            "assumptions",
        ]:
            if not isinstance(m[key], str) or not 1 <= len(m[key]) <= 1000:
                raise ValueError
        if (
            not isinstance(m["languages"], list)
            or not m["languages"]
            or any(x not in ("tr", "en", "other") for x in m["languages"])
        ):
            raise ValueError
        vec = m["vectors"]
        if not isinstance(vec, dict) or len(vec) > 10000:
            raise ValueError
        dims = {len(v) for v in vec.values() if isinstance(v, list)}
        if vec and (len(dims) != 1 or not 2 <= next(iter(dims)) <= 128):
            raise ValueError
        dimension = next(iter(dims), 0)
        for term, v in vec.items():
            if (
                not isinstance(term, str)
                or not 1 <= len(term) <= 100
                or not isinstance(v, list)
                or len(v) != dimension
                or any(
                    isinstance(x, bool)
                    or not isinstance(x, (int, float))
                    or not math.isfinite(x)
                    or abs(x) > 1e6
                    for x in v
                )
            ):
                raise ValueError
        if not isinstance(m["entities"], list) or len(m["entities"]) > 2000:
            raise ValueError
        for e in m["entities"]:
            if (
                not isinstance(e, dict)
                or set(e) != {"phrase", "label"}
                or not isinstance(e["phrase"], str)
                or not 1 <= len(e["phrase"]) <= 100
                or not isinstance(e["label"], str)
                or not 1 <= len(e["label"]) <= 40
            ):
                raise ValueError
        c = m["classifier"]
        if c is not None:
            if (
                not isinstance(c, dict)
                or set(c) != {"labels", "coefficient", "intercept"}
                or not vec
            ):
                raise ValueError
            if (
                not isinstance(c["labels"], list)
                or not 2 <= len(c["labels"]) <= 32
                or len(set(c["labels"])) != len(c["labels"])
                or any(
                    not isinstance(x, str) or not 1 <= len(x) <= 40 for x in c["labels"]
                )
            ):
                raise ValueError
            if len(c["coefficient"]) != len(c["labels"]) or len(c["intercept"]) != len(
                c["labels"]
            ):
                raise ValueError
            for v in c["coefficient"]:
                if len(v) != dimension or any(
                    isinstance(x, bool)
                    or not isinstance(x, (int, float))
                    or not math.isfinite(x)
                    or abs(x) > 1e6
                    for x in v
                ):
                    raise ValueError
            if any(
                isinstance(x, bool)
                or not isinstance(x, (int, float))
                or not math.isfinite(x)
                or abs(x) > 1e6
                for x in c["intercept"]
            ):
                raise ValueError
        return m
    except (ValueError, TypeError, KeyError, RecursionError, UnicodeError) as error:
        raise ProjectError(
            "Model bundle şeması/ağırlıkları geçersiz; script/pickle/remote-code desteklenmez."
        ) from error


def inspect(folder):
    path = Path(folder).expanduser() / "model.json"
    if not folder or not path.is_file():
        raise ProjectError(
            "Model yok: yerel klasörden LocalNLPBundle/v1 model.json seçin. Transformer/spaCy/ONNX backend bu ortamda desteklenmiyor."
        )
    if path.is_symlink() or path.stat().st_size > LIMIT:
        raise ProjectError("Model dosyası symlink/16MiB sınırında reddedildi.")
    raw = path.read_bytes()
    model = parse(raw)
    return model, dict(
        sha256=hashlib.sha256(raw).hexdigest(),
        bytes=len(raw),
        name=model["name"],
        languages=model["languages"],
        license=model["license"],
        training_dataset=model["training_dataset"],
        dataset_license=model["dataset_license"],
        assumptions=model["assumptions"],
        backend="static mean word vectors + exact literal gazetteer + linear scores; no transformer/negation/context guarantee",
        quality="not guaranteed by name/language; training claims supplied by model author",
        canonical_hash=digest(encode(model)),
    )


class Redirects(HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        if (
            self.count > 3
            or urlsplit(newurl).scheme != "https"
            or urlsplit(newurl).netloc != urlsplit(req.full_url).netloc
        ):
            raise ProjectError("Model redirect sınırı3/aynı HTTPS origin.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(
    url,
    expected_sha256,
    expected_bytes,
    cache,
    control=None,
    *,
    validator=parse,
    namespace="nlp-models",
):
    if namespace not in ("nlp-models", "vision-models"):
        raise ProjectError("Model cache namespace desteklenmiyor.")
    """Explicit public HTTPS file only; verified before cache publication, no auth or startup fetch."""
    control = control or Control()
    u = urlsplit(url)
    if (
        u.scheme != "https"
        or not u.hostname
        or u.username
        or u.password
        or u.query
        or u.fragment
        or len(url) > 2048
    ):
        raise ProjectError(
            "Public HTTPS URL gerekli; auth/query/fragment desteklenmiyor."
        )
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or any(c not in "0123456789abcdef" for c in expected_sha256)
        or type(expected_bytes) is not int
        or not 1 <= expected_bytes <= LIMIT
    ):
        raise ProjectError(
            "İndirme öncesi exact SHA256 ve1..16MiB byte boyutu gerekli."
        )
    target = Path(cache) / namespace / expected_sha256
    final = target / "model.json"
    if final.is_file():
        raw = final.read_bytes()
        if (
            len(raw) != expected_bytes
            or hashlib.sha256(raw).hexdigest() != expected_sha256
        ):
            raise ProjectError(
                "Offline cache hash/boyut değişmiş; otomatik üzerine yazılmaz."
            )
        validator(raw)
        return str(target)
    target.mkdir(parents=True, exist_ok=True)
    opener = build_opener(
        Redirects(), HTTPSHandler(context=ssl.create_default_context())
    )
    path = None
    try:
        with opener.open(
            Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Veri_Ufku-model-bundle/1",
                },
            ),
            timeout=min(10, control.budget.max_wall_seconds),
        ) as response:
            if (
                response.status != 200
                or response.headers.get("Content-Encoding", "identity") != "identity"
            ):
                raise ProjectError("Model HTTP status/content encoding desteklenmiyor.")
            length = response.headers.get("Content-Length")
            if length is not None and int(length) != expected_bytes:
                raise ProjectError("İndirilecek byte boyutu beyanla uyuşmuyor.")
            with tempfile.NamedTemporaryFile(
                dir=target, delete=False, prefix="pending-"
            ) as f:
                path = Path(f.name)
                h = hashlib.sha256()
                total = 0
                while True:
                    control.check()
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > expected_bytes:
                        raise ProjectError("Model download boyut sınırı.")
                    f.write(chunk)
                    h.update(chunk)
                    control.progress("Model indirme", total, expected_bytes)
                f.flush()
                os.fsync(f.fileno())
            if total != expected_bytes or h.hexdigest() != expected_sha256:
                raise ProjectError("Model download SHA256/boyut doğrulaması başarısız.")
            validator(path.read_bytes())
            control.check()
            os.replace(path, final)
            path = None
        return str(target)
    except (OSError, ValueError) as error:
        raise ProjectError(
            "Model HTTPS/timeout/download başarısız; URL/auth/log içeriği gösterilmez."
        ) from error
    finally:
        if path is not None:
            path.unlink(missing_ok=True)
