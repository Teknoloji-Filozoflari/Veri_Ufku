"""GET-only bounded REST pages and pinned S3 objects; no ambient credentials."""

import hashlib
import json
import ssl
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

from veri_ufku.importers.connector_contracts import safe_url
from veri_ufku.importers.native import canonical
from veri_ufku.storage.project_model import ProjectError


def pause(seconds, control):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        control.check()
        time.sleep(min(0.05, max(0, end - time.monotonic())))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def retry_after(value, attempt):
    delay = min(2**attempt, 8)
    if value:
        try:
            delay = float(value)
        except ValueError:
            try:
                delay = (
                    parsedate_to_datetime(value) - datetime.now(UTC)
                ).total_seconds()
            except (ValueError, TypeError, OverflowError):
                pass
    if not 0 <= delay <= 30:
        raise ProjectError(
            "Rate-limit bekleme sınırı30 saniye; yeniden açıkça deneyin."
        )
    return delay


def page(spec, url, secret, control, remaining_bytes):
    safe_url(url, spec.allow_loopback_http)
    context = ssl.create_default_context(cafile=spec.ca_file or None)
    opener = urllib.request.build_opener(
        NoRedirect(),
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=context),
    )
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "Veri_Ufku/0.1",
    }
    if secret:
        if "\r" in secret or "\n" in secret:
            raise ProjectError("Keyring bearer değeri header için geçersiz.")
        headers["Authorization"] = "Bearer " + secret
    for attempt in range(spec.retries + 1):
        control.check()
        try:
            request = urllib.request.Request(url, headers=headers, method="GET")
            with opener.open(request, timeout=spec.timeout) as response:
                if (
                    spec.kind == "geocoding"
                    and "no-store" in response.headers.get("Cache-Control", "").lower()
                ):
                    raise ProjectError(
                        "Geocoding cache no-store: proje snapshot kaydı yapılamaz."
                    )
                if response.headers.get("Content-Encoding", "identity") != "identity":
                    raise ProjectError(
                        "Sıkıştırılmış API gövdesi desteklenmez; identity isteği gerekli."
                    )
                if response.headers.get_content_type() not in (
                    "application/json",
                    "application/problem+json",
                ):
                    raise ProjectError("API JSON içeriği gerekli.")
                if int(response.headers.get("Content-Length", "0")) > remaining_bytes:
                    raise ProjectError("API içerik boyutu sınırı aşıldı.")
                chunks, size = [], 0
                while chunk := response.read(65536):
                    control.check()
                    size += len(chunk)
                    if size > remaining_bytes:
                        raise ProjectError("API toplam içerik boyutu sınırı aşıldı.")
                    chunks.append(chunk)
                raw = b"".join(chunks)
                if secret and secret.encode() in raw:
                    raise ProjectError(
                        "API credential'ı veri gövdesinde geri döndürdü; secret içeren çıktı kaydedilmedi."
                    )
                document = json.loads(
                    raw,
                    parse_float=Decimal,
                    parse_constant=lambda _: (_ for _ in ()).throw(
                        ValueError("nonfinite")
                    ),
                )
                validators = {
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": size,
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                }
                token = (
                    response.headers.get(spec.snapshot_header)
                    if spec.snapshot_header
                    else None
                )
                return document, validators, token, attempt
        except urllib.error.HTTPError as error:
            status, delay = error.code, error.headers.get("Retry-After")
            error.close()
            if status in (429, 502, 503, 504) and attempt < spec.retries:
                pause(retry_after(delay, attempt), control)
                continue
            raise ProjectError(
                f"HTTP {status}: auth/yetki, rate-limit veya servis hatası. Yanıt gövdesi loglanmaz; redirect izlenmez."
            ) from None
        except ProjectError:
            raise
        except (OSError, ValueError, urllib.error.URLError) as error:
            control.check()
            # TLS validation is never retried with a weaker context.
            if attempt < spec.retries and not isinstance(
                getattr(error, "reason", error), ssl.SSLError
            ):
                pause(retry_after(None, attempt), control)
                continue
            raise ProjectError(
                "HTTP TLS/timeout/JSON okuma hatası; secret ve ham yanıt gösterilmez."
            ) from None
    raise ProjectError("API tekrar denemesi sınırı aşıldı.")


def rest_capture(spec, secret, workspace, control, identity):
    source = workspace / "api.jsonl"
    url, visited, records, total_bytes = spec.endpoint, set(), 0, 0
    pages, expected_total, snapshot_token = [], None, None
    origin = urlsplit(spec.endpoint)
    with source.open("x", encoding="utf-8") as stream:
        while url:
            control.check()
            safe_url(url, spec.allow_loopback_http)
            current = urlsplit(url)
            if (current.scheme, current.hostname, current.port) != (
                origin.scheme,
                origin.hostname,
                origin.port,
            ):
                raise ProjectError(
                    "API next başka origin'e gidiyor; credential aktarılmadı."
                )
            if url in visited or len(visited) >= spec.max_pages:
                raise ProjectError(
                    "API sonsuz/tekrarlanan sayfa veya sayfa sınırı; kısmi yayın yok."
                )
            visited.add(url)
            pause(1 / spec.requests_per_second, control)
            document, validators, token, retries = page(
                spec, url, secret, control, spec.max_bytes - total_bytes
            )
            if not isinstance(document, dict) or not isinstance(
                document.get(spec.records_field), list
            ):
                raise ProjectError("API kayıt dizisi alanını seçin.")
            if spec.next_field and spec.next_field not in document:
                raise ProjectError(
                    "API next alanı bulunamadı; yanlış alan adıyla ilk sayfa tamamlanmış sayılmaz."
                )
            batch = document[spec.records_field]
            if len(batch) + records > spec.max_rows:
                raise ProjectError("API satır sınırı; kısmi dataset yayımlanmadı.")
            total = document.get(spec.total_field) if spec.total_field else None
            if total is not None:
                if (
                    type(total) is not int
                    or total < 0
                    or expected_total not in (None, total)
                ):
                    raise ProjectError(
                        "API toplam kayıt sayısı değişti/geçersiz; tutarlı snapshot yok."
                    )
                expected_total = total
            if spec.snapshot_header:
                if not token or snapshot_token not in (None, token):
                    raise ProjectError(
                        "API snapshot token kayıp/değişti; yeniden açıkça okuyun."
                    )
                snapshot_token = token
            for record in batch:
                if not isinstance(record, dict) or spec.key_column not in record:
                    raise ProjectError(
                        "Her API kaydı seçilen kaynak kimliğini taşımalı."
                    )
                if spec.field_mapping and any(
                    k not in record for k in spec.field_mapping
                ):
                    raise ProjectError(
                        "API alan eşleme kaynağı bulunamadı; alan atılmadı."
                    )
                identity(record[spec.key_column])
                mapped = {spec.field_mapping.get(k, k): v for k, v in record.items()}
                if len(mapped) != len(record):
                    raise ProjectError("API alan eşlemesi bir sütunu örttü.")
                stream.write(canonical(mapped) + "\n")
            records += len(batch)
            total_bytes += validators["bytes"]
            pages.append(
                dict(
                    number=len(pages) + 1,
                    records=len(batch),
                    retries=retries,
                    **validators,
                )
            )
            control.disk(workspace)
            control.progress("API sayfası okuma", records, expected_total)
            next_url = document.get(spec.next_field)
            if next_url is not None and not isinstance(next_url, str):
                raise ProjectError(
                    "API next URL/null olmalı; implicit offset sayfalama yok."
                )
            if not batch and next_url:
                raise ProjectError("Boş API sayfasında next: ilerleme yok.")
            url = urljoin(url, next_url) if next_url else None
    if expected_total is not None and records != expected_total:
        raise ProjectError(
            "API yinelenen/atlanan kayıt: beyan edilen toplam uyuşmuyor."
        )
    return (
        source,
        "jsonl",
        dict(
            pages=pages,
            rows=records,
            expected_total=expected_total,
            duplicate_check="unique source keys; all pages",
            skipped_check="declared total matched"
            if expected_total is not None
            else "unknown; server does not declare total",
            snapshot_token=snapshot_token,
            consistency="server_declared_token; contract requires server guarantee"
            if snapshot_token
            else "observed_pages; no single-time snapshot guarantee",
            scope="completed bounded pagination",
            freshness="captured interval; refresh requires explicit network action",
        ),
    )


def s3_capture(spec, secret, workspace, control):
    client = None
    try:
        import boto3
        from botocore import UNSIGNED
        from botocore.config import Config

        auth = json.loads(secret) if secret else {}
        if set(auth) - {"access_key", "secret_key", "session_token"} or (
            auth and not {"access_key", "secret_key"} <= set(auth)
        ):
            raise ProjectError(
                "S3 keyring JSON: access_key/secret_key ve isteğe bağlı session_token."
            )
        client = boto3.client(
            "s3",
            endpoint_url=spec.endpoint or None,
            region_name=spec.region,
            aws_access_key_id=auth.get("access_key", "unsigned"),
            aws_secret_access_key=auth.get("secret_key", "unsigned"),
            aws_session_token=auth.get("session_token"),
            verify=spec.ca_file or True,
            config=Config(
                signature_version="s3v4" if auth else UNSIGNED,
                connect_timeout=spec.timeout,
                read_timeout=spec.timeout,
                retries={"total_max_attempts": spec.retries + 1, "mode": "standard"},
                s3={"addressing_style": "path"},
                proxies={},
            ),
        )

        def reject_redirect(response=None, **kwargs):
            if response and 300 <= response[0].status_code < 400:
                raise ProjectError("S3 redirect izlenmez; doğru endpoint/region seçin.")

        client.meta.events.register_first("needs-retry.s3", reject_redirect)
        args = dict(Bucket=spec.bucket, Key=spec.object_key)
        if spec.version_id:
            args["VersionId"] = spec.version_id
        control.check()
        head = client.head_object(**args)
        if head["ContentLength"] > spec.max_bytes:
            raise ProjectError("S3 nesne boyutu sınırı aşıldı.")
        version = spec.version_id or head.get("VersionId")
        if version:
            args["VersionId"] = version
        args["IfMatch"] = head["ETag"]
        response = client.get_object(**args)
        body = response["Body"]
        source = workspace / ("object." + spec.object_format)
        size = 0
        try:
            with source.open("xb") as stream:
                while chunk := body.read(65536):
                    control.check()
                    size += len(chunk)
                    if size > spec.max_bytes:
                        raise ProjectError("S3 içerik sınırı aşıldı.")
                    stream.write(chunk)
                    control.disk(workspace)
        finally:
            body.close()
            client.close()
        if size != head["ContentLength"] or response["ETag"] != head["ETag"]:
            raise ProjectError("S3 nesne snapshot'ı değişti/eksik; yayın yok.")
        return (
            source,
            spec.object_format,
            dict(
                consistency="single versioned object"
                if version
                else "single conditional object GET; ETag is a validator, not SHA256",
                version_id=version,
                etag=head["ETag"],
                last_modified=head["LastModified"].isoformat(),
                bytes=size,
                scope="single object",
                freshness="capture time; no automatic refresh",
            ),
        )
    except ImportError as error:
        raise ProjectError("S3 connectors paketi eksik.") from error
    except Exception as error:
        control.check()
        if isinstance(error, ProjectError):
            raise
        raise ProjectError(
            "S3 TLS/auth/timeout/nesne okuma hatası; credential ve sunucu hata gövdesi gösterilmez."
        ) from None
    finally:
        if client is not None:
            client.close()
