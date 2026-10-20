"""Explicit single-tile GET; no redirects, ambient credentials or automatic refresh."""

import hashlib
import ssl
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds

from veri_ufku.importers.connector_contracts import safe_url
from veri_ufku.importers.http_connectors import NoRedirect, pause, retry_after
from veri_ufku.storage.project_model import ProjectError


def tile_capture(spec, secret, workspace, control):
    safe_url(spec.endpoint, spec.allow_loopback_http)
    if not spec.attribution or spec.cache_policy != "project-permitted":
        raise ProjectError(
            "Tile attribution ve sağlayıcının project cache izni açık seçilmeli."
        )
    if secret:
        raise ProjectError(
            "Tile auth desteklenmez; public HTTPS endpoint seçin. Credential URL kabul edilmez."
        )
    z, x, y = spec.tile_z, spec.tile_x, spec.tile_y
    if not (0 <= z <= 18 and 0 <= x < 2**z and 0 <= y < 2**z):
        raise ProjectError("XYZ tile z/x/y sınırı dışında.")
    opener = urllib.request.build_opener(
        NoRedirect(),
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(
            context=ssl.create_default_context(cafile=spec.ca_file or None)
        ),
    )
    raw = None
    validator = {}
    for attempt in range(spec.retries + 1):
        control.check()
        try:
            with opener.open(
                urllib.request.Request(
                    spec.endpoint,
                    headers={
                        "User-Agent": "Veri_Ufku/0.1",
                        "Accept": "image/png,image/jpeg",
                        "Accept-Encoding": "identity",
                    },
                    method="GET",
                ),
                timeout=spec.timeout,
            ) as response:
                if (
                    response.headers.get_content_type()
                    not in ("image/png", "image/jpeg")
                    or response.headers.get("Content-Encoding", "identity")
                    != "identity"
                ):
                    raise ProjectError("Tile PNG/JPEG identity içerik ister.")
                maximum = min(
                    spec.max_bytes, 4 * 1024**2, control.budget.ram_bytes // 8
                )
                if int(response.headers.get("Content-Length", "0")) > maximum:
                    raise ProjectError("Tile içerik sınırı.")
                chunks = []
                size = 0
                while chunk := response.read(65536):
                    control.check()
                    size += len(chunk)
                    if size > maximum:
                        raise ProjectError("Tile içerik sınırı.")
                    chunks.append(chunk)
                raw = b"".join(chunks)
                validator = dict(
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                    cache_control=response.headers.get("Cache-Control"),
                )
                if "no-store" in (validator["cache_control"] or "").lower():
                    raise ProjectError(
                        "Provider no-store koşulu: proje cache üretilmedi."
                    )
                break
        except urllib.error.HTTPError as error:
            if error.code in (429, 502, 503, 504) and attempt < spec.retries:
                pause(retry_after(error.headers.get("Retry-After"), attempt), control)
                continue
            raise ProjectError(
                f"Tile HTTP {error.code}; redirect uygulanmadı."
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt < spec.retries:
                pause(min(2**attempt, 8), control)
                continue
            raise ProjectError(
                "Tile ağ/TLS/timeout hatası; URL/credential loglanmadı."
            ) from None
    if not raw:
        raise ProjectError("Tile boş içerik.")
    with rasterio.Env(GDAL_PAM_ENABLED="NO", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with MemoryFile(raw) as mem:
            with mem.open() as image:
                if (
                    image.driver not in ("PNG", "JPEG")
                    or image.width not in (256, 512)
                    or image.height != image.width
                    or image.count not in (1, 3, 4)
                ):
                    raise ProjectError("Tile256/512 kare PNG/JPEG ve1/3/4kanal ister.")
                if (
                    image.width * image.height * image.count
                    > control.budget.ram_bytes // 8
                ):
                    raise ProjectError("Tile decoded RAM sınırı.")
                data = image.read()
                width = image.width
                count = image.count
                dtype = image.dtypes[0]
    radius = 20037508.342789244
    span = 2 * radius / 2**z
    bounds = (
        -radius + x * span,
        radius - (y + 1) * span,
        -radius + (x + 1) * span,
        radius - y * span,
    )
    dest = Path(workspace) / "tile.tif"
    with rasterio.open(
        dest,
        "w",
        driver="GTiff",
        width=width,
        height=width,
        count=count,
        dtype=dtype,
        crs="EPSG:3857",
        transform=from_bounds(*bounds, width, width),
    ) as target:
        target.write(data)
    control.check()
    return (
        dest,
        "geotiff",
        dict(
            consistency="single captured tile response; acquisition interval, no cross-tile snapshot",
            source_sha256=hashlib.sha256(raw).hexdigest(),
            bytes=len(raw),
            validators=validator,
            xyz=[z, x, y],
            attribution=spec.attribution,
            cache_policy=spec.cache_policy,
            captured_at=datetime.now(UTC).isoformat(),
            notice="Explicit one tile, no mosaic/background auto-fetch. Raster preview selected color channel/window; RGB compositor unavailable. Web Mercator display only; no metre inference.",
        ),
    )
