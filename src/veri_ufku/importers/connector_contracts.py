"""Data-only, secret-free connection requests; network starts only on capture."""

import ipaddress
import json
import re
from dataclasses import asdict, dataclass, field
from urllib.parse import parse_qsl, urlsplit

from veri_ufku.storage.project_model import ProjectError

CONNECTORS = (
    "postgresql",
    "mysql",
    "mariadb",
    "duckdb",
    "http",
    "s3",
    "tile",
    "geocoding",
)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[\w .-]{1,128}", value):
        raise ProjectError("Tablo/şema/sütun adı geçersiz.")
    return value


def safe_url(value, allow_loopback=False):
    parsed = urlsplit(value)
    if parsed.username or parsed.password or parsed.fragment or not parsed.hostname:
        raise ProjectError("URL içinde credential veya fragment kullanmayın.")
    loopback = parsed.hostname == "localhost"
    try:
        loopback = loopback or ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        pass
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and allow_loopback and loopback
    ):
        raise ProjectError(
            "Doğrulanmış HTTPS gerekli; HTTP yalnız açık yerel test seçimiyle."
        )
    if any(
        re.search(
            r"secret|password|token|api.?key|signature|credential|authorization",
            k,
            re.I,
        )
        for k, _ in parse_qsl(parsed.query)
    ):
        raise ProjectError(
            "URL credential taşıyamaz; sistem keyring referansını kullanın."
        )
    return value


@dataclass(frozen=True)
class ConnectorSpec:
    kind: str = "http"
    endpoint: str = ""
    database: str = ""
    user: str = ""
    port: int = 0
    credential_ref: str = ""
    ca_file: str = ""
    schema: str = "public"
    table: str = ""
    key_column: str = "id"
    columns: tuple[str, ...] = ()
    filters: tuple[dict, ...] = ()
    timeout: int = 10
    max_rows: int = 100000
    max_bytes: int = 67108864
    max_pages: int = 100
    retries: int = 2
    requests_per_second: int = 5
    allow_loopback_http: bool = False
    terms_acknowledged: bool = False
    records_field: str = "items"
    next_field: str = "next"
    total_field: str = "total"
    snapshot_header: str = ""
    field_mapping: dict = field(default_factory=dict)
    bucket: str = ""
    object_key: str = ""
    version_id: str = ""
    object_format: str = "parquet"
    region: str = "us-east-1"
    attribution: str = ""
    cache_policy: str = ""
    tile_z: int = 0
    tile_x: int = 0
    tile_y: int = 0

    def __post_init__(self):
        if self.kind not in CONNECTORS:
            raise ProjectError("Bağlantı adaptörü bulunamadı.")
        for value in asdict(self).values():
            if isinstance(value, str) and (len(value) > 4096 or "\x00" in value):
                raise ProjectError("Bağlantı metni sınır dışında.")
        for name, maximum in (
            ("timeout", 60),
            ("max_rows", 1000000),
            ("max_bytes", 536870912),
            ("max_pages", 1000),
            ("requests_per_second", 20),
        ):
            if (
                type(getattr(self, name)) is not int
                or not 1 <= getattr(self, name) <= maximum
            ):
                raise ProjectError("Bağlantı süre/boyut/sayfa sınırı geçersiz.")
        if type(self.retries) is not int or not 0 <= self.retries <= 5:
            raise ProjectError("En fazla5 tekrar denemesi.")
        if type(self.port) is not int or not 0 <= self.port <= 65535:
            raise ProjectError("Port geçersiz.")
        if not re.fullmatch(r"[a-zA-Z0-9_.-]{0,100}", self.credential_ref):
            raise ProjectError("Credential yalnız keyring referansı olabilir.")
        if (
            type(self.terms_acknowledged) is not bool
            or type(self.allow_loopback_http) is not bool
        ):
            raise ProjectError("Bağlantı onayları boolean olmalı.")
        if self.kind in ("tile", "geocoding") and (
            not self.attribution or self.cache_policy != "project-permitted"
        ):
            raise ProjectError(
                "Attribution ve project-permitted cache koşulu gerekli; sağlayıcı terms kullanıcı onayı ayrı."
            )
        if self.kind == "tile" and (
            any(type(v) is not int for v in (self.tile_z, self.tile_x, self.tile_y))
            or not 0 <= self.tile_z <= 18
            or not 0 <= self.tile_x < 2**self.tile_z
            or not 0 <= self.tile_y < 2**self.tile_z
        ):
            raise ProjectError("Tile XYZ sınırı geçersiz.")
        if self.kind in ("http", "s3", "tile", "geocoding"):
            if self.endpoint:
                safe_url(self.endpoint, self.allow_loopback_http)
            elif self.kind in ("http", "tile", "geocoding"):
                raise ProjectError("HTTPS kaynak URL'si gerekli.")
        elif self.kind != "duckdb":
            if not self.database or not self.user:
                raise ProjectError(
                    "Veritabanı adı ve açık salt okunur kullanıcı gerekli."
                )
            if not re.fullmatch(r"[a-zA-Z0-9_.:-]+", self.endpoint):
                raise ProjectError("Sunucu adı geçersiz; DSN/parola kabul edilmez.")
        if len(self.columns) > 256 or len(self.filters) > 8:
            raise ProjectError("Sorgu sütun/filtre sınırı aşıldı.")
        for name in self.columns:
            identifier(name)
        for condition in self.filters:
            if set(condition) != {"column", "op", "value"} or condition["op"] not in (
                "=",
                "!=",
                "<",
                "<=",
                ">",
                ">=",
            ):
                raise ProjectError(
                    "Yalnız sütun/işleç/bağlı değer sorgusu desteklenir."
                )
            identifier(condition["column"])
            if (
                type(condition["value"]) not in (str, int, float, bool)
                or len(str(condition["value"])) > 4096
            ):
                raise ProjectError("Sorgu parametresi scalar olmalı.")
        if not isinstance(self.field_mapping, dict) or len(self.field_mapping) > 256:
            raise ProjectError("Alan eşleme geçersiz.")
        for original, renamed in self.field_mapping.items():
            identifier(original)
            identifier(renamed)
        if len(set(self.field_mapping.values())) != len(self.field_mapping):
            raise ProjectError("Alan eşlemesinde hedef adı tekrarlandı.")
        if self.object_format not in ("parquet", "jsonl", "csv", "ipc"):
            raise ProjectError("Nesne formatı Parquet/JSONL/CSV/IPC olabilir.")
        for value in (
            self.records_field,
            self.next_field,
            self.total_field,
            self.snapshot_header,
        ):
            if value and not re.fullmatch(r"[\w-]{1,100}", value):
                raise ProjectError("API alanı/header geçersiz.")

    def data(self):
        return json.loads(json.dumps(asdict(self), ensure_ascii=False, allow_nan=False))

    @classmethod
    def from_dict(cls, value):
        value = dict(value)
        value["columns"] = tuple(value.get("columns", ()))
        value["filters"] = tuple(value.get("filters", ()))
        try:
            return cls(**value)
        except (TypeError, ValueError) as error:
            raise ProjectError(
                "Bağlantı ayarları geçersiz; secret alanları saklanmaz."
            ) from error
