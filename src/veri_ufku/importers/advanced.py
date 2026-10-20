"""Phase30 adapters: bounded batches, explicit schema plan, native publication."""

import json
from dataclasses import replace
from importlib.metadata import version
from itertools import islice
from pathlib import Path
from urllib.parse import unquote

import polars as pl
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.ipc as ipc
import pyarrow.orc as orc
import pyarrow.parquet as pq

from veri_ufku.geo import FORMATS as GEO_FORMATS
from veri_ufku.importers import advanced_readers as readers
from veri_ufku.importers import arrays
from veri_ufku.importers.delimited import Control, hash_artifact, verify_capture
from veri_ufku.importers.native import EXTRA, describe
from veri_ufku.importers.parquet import names_for
from veri_ufku.importers.sources import (
    directory_members,
    input_snapshot,
    verify_sources,
)
from veri_ufku.storage.project_model import ProjectError, uid

ADVANCED_FORMATS = (
    "parquet_dataset",
    "arrow_dataset",
    "avro",
    "orc",
    "hdf5",
    "xml",
    "fixed_width",
    "spss",
    "stata",
    "sas",
)


def storage_type(dtype, depth=0):
    if depth > 16:
        raise ProjectError("Nested derinliği16 sınırını aştı.")
    if pa.types.is_dictionary(dtype):
        if depth:
            raise ProjectError("Nested dictionary varyantı henüz desteklenmiyor.")
        return storage_type(dtype.value_type, depth + 1)
    if pa.types.is_decimal(dtype):
        if dtype.precision > 38 or not 0 <= dtype.scale <= dtype.precision:
            raise ProjectError(
                "Decimal precision/scale Polars128 kesin sınırını aşıyor; kayıplı dönüşüm yok."
            )
        return pa.decimal128(dtype.precision, dtype.scale)
    if pa.types.is_struct(dtype):
        return pa.struct(
            [
                pa.field(
                    f.name,
                    storage_type(f.type, depth + 1),
                    nullable=f.nullable,
                    metadata=f.metadata,
                )
                for f in dtype
            ]
        )
    if pa.types.is_list(dtype) or pa.types.is_large_list(dtype):
        return pa.large_list(storage_type(dtype.value_type, depth + 1))
    if pa.types.is_timestamp(dtype) and dtype.unit not in ("ms", "us", "ns"):
        raise ProjectError(
            "Timestamp saniye birimi bu native sözleşmede yok; açık yeniden export gerekir."
        )
    if (
        pa.types.is_integer(dtype)
        or pa.types.is_floating(dtype)
        or pa.types.is_boolean(dtype)
        or pa.types.is_string(dtype)
        or pa.types.is_large_string(dtype)
        or pa.types.is_binary(dtype)
        or pa.types.is_large_binary(dtype)
        or pa.types.is_null(dtype)
        or pa.types.is_timestamp(dtype)
        or pa.types.is_date32(dtype)
        or pa.types.is_time64(dtype)
        or pa.types.is_time32(dtype)
    ):
        return dtype
    raise ProjectError(
        f"Arrow tür varyantı korunamıyor: {dtype}; sessiz metin dönüşümü yok."
    )


def merge_type(left, right):
    if left == right:
        return left
    if pa.types.is_null(left):
        return right
    if pa.types.is_null(right):
        return left
    if pa.types.is_integer(left) and pa.types.is_integer(right):
        if pa.types.is_signed_integer(left) == pa.types.is_signed_integer(right):
            return left if left.bit_width >= right.bit_width else right
        signed = left if pa.types.is_signed_integer(left) else right
        unsigned = right if pa.types.is_unsigned_integer(right) else left
        bits = max(signed.bit_width, unsigned.bit_width + 1)
        for width in (8, 16, 32, 64):
            if bits <= width:
                return getattr(pa, "int" + str(width))()
        return pa.decimal128(20, 0)
    if all(pa.types.is_integer(t) or pa.types.is_decimal(t) for t in (left, right)):

        def dimensions(t):
            if pa.types.is_decimal(t):
                return t.precision - t.scale, t.scale
            return (20 if pa.types.is_uint64(t) else 19 if t.bit_width == 64 else 10), 0

        ldigits, lscale = dimensions(left)
        rdigits, rscale = dimensions(right)
        scale = max(lscale, rscale)
        precision = max(ldigits, rdigits) + scale
        if precision <= 38:
            return pa.decimal128(precision, scale)
    if pa.types.is_floating(left) and pa.types.is_floating(right):
        return pa.float64()
    if all(pa.types.is_string(t) or pa.types.is_large_string(t) for t in (left, right)):
        return pa.large_string()
    if all(pa.types.is_binary(t) or pa.types.is_large_binary(t) for t in (left, right)):
        return pa.large_binary()
    if (
        pa.types.is_timestamp(left)
        and pa.types.is_timestamp(right)
        and left.tz == right.tz
    ):
        units = ("ms", "us", "ns")
        return pa.timestamp(max((left.unit, right.unit), key=units.index), left.tz)
    if pa.types.is_large_list(left) and pa.types.is_large_list(right):
        return pa.large_list(merge_type(left.value_type, right.value_type))
    if pa.types.is_struct(left) and pa.types.is_struct(right):
        names = list(dict.fromkeys([f.name for f in left] + [f.name for f in right]))
        lfields, rfields = {f.name: f for f in left}, {f.name: f for f in right}
        return pa.struct(
            [
                pa.field(
                    n,
                    merge_type(lfields[n].type, rfields[n].type)
                    if n in lfields and n in rfields
                    else (lfields.get(n) or rfields[n]).type,
                )
                for n in names
            ]
        )
    raise ProjectError(
        f"Tür çatışması: {left} / {right}. Kayıpsız ortak tür yok; sessiz string/float dönüşümü yapılmadı."
    )


def partitions(member):
    result = {}
    for component in Path(member).parts[:-1]:
        if "=" in component:
            name, value = component.split("=", 1)
            name, value = unquote(name), unquote(value)
            if not name or name in result:
                raise ProjectError("Hive partition adı boş veya yineleniyor.")
            result[name] = None if value == "__HIVE_DEFAULT_PARTITION__" else value
    return result


def parts_for(snapshot, adapter):
    if adapter in GEO_FORMATS:
        from veri_ufku.geo import readers as geo

        return [
            dict(
                name=snapshot["original"],
                path=geo.source_path(snapshot),
                fingerprint=snapshot["fingerprint"],
            )
        ]
    if adapter == "zarr":
        from veri_ufku.importers.sources import zarr_root

        return [
            dict(
                name=snapshot["original"],
                path=str(zarr_root(snapshot)),
                fingerprint=snapshot["fingerprint"],
            )
        ]
    if adapter in ("parquet_dataset", "arrow_dataset"):
        members = snapshot.get("members", [])
        if not members:
            raise ProjectError(
                "Çok parçalı format için dataset klasörü veya ZIP seçin."
            )
        suffixes = (
            {".parquet"}
            if adapter == "parquet_dataset"
            else {".arrow", ".ipc", ".feather"}
        )
        if any(Path(m["name"]).suffix.lower() not in suffixes for m in members):
            raise ProjectError(
                "Dataset parçaları seçilen formatla uyuşmuyor; karma format desteklenmez."
            )
        return members
    single = input_snapshot(snapshot)
    return [
        dict(
            name=single["original"],
            path=single["path"],
            fingerprint=single["fingerprint"],
        )
    ]


def part_schema(part, settings, control):
    path, adapter = part["path"], settings.adapter_id
    if adapter == "parquet_dataset":
        schema = pq.read_schema(path)
        metadata = {}
    elif adapter == "arrow_dataset":
        with pa.memory_map(path, "r") as file:
            schema = ipc.open_file(file).schema
        metadata = {}
    elif adapter == "orc":
        file = orc.ORCFile(path)
        schema, metadata = (
            file.schema,
            dict(rows=file.nrows, stripes=file.nstripes, compression=file.compression),
        )
    elif adapter == "avro":
        schema, metadata = readers.avro_info(path)
    elif adapter in GEO_FORMATS:
        from veri_ufku.geo import readers as geo

        schema, metadata = geo.info(path, settings, control)
        metadata = {"geospatial": metadata}
    elif adapter in arrays.ARRAY_FORMATS:
        schema, metadata = arrays.info(path, settings, control)
    elif adapter == "hdf5":
        schema, metadata = readers.hdf_info(path, settings, control)
    elif adapter in ("spss", "stata", "sas"):
        schema, metadata = readers.statistical_info(path, settings)
    else:
        rows = list(islice(readers.text_records(path, settings, control), 200))
        if not rows:
            raise ProjectError("Seçilen kayıt yolunda veri yok.")
        names = list(dict.fromkeys(n for row in rows for n in row))
        if settings.types and (
            len(settings.types) != len(names)
            or settings.column_names
            and list(settings.column_names) != names
        ):
            raise ProjectError("Açık tür seçimi kayıt sütunlarıyla uyuşmuyor.")
        from veri_ufku.importers.delimited import dtype

        fields = []
        for i, name in enumerate(names):
            kind = settings.types[i] if settings.types else "text"
            arrow = (
                pl.Series(
                    name,
                    [],
                    dtype=pl.String if kind == "auto" else dtype(kind, settings),
                )
                .to_arrow()
                .type
            )
            fields.append(pa.field(name, arrow))
        schema, metadata = (
            pa.schema(fields),
            dict(
                record_path=settings.record_path,
                widths=list(settings.widths),
                width_unit="Unicode characters; spaces preserved",
                encoding=settings.encoding,
            ),
        )
    if not 1 <= len(schema) <= 256 or len(set(schema.names)) != len(schema):
        raise ProjectError("Kaynak sütunları1–256 ve benzersiz olmalı.")
    partition = (
        partitions(part["name"])
        if adapter in ("parquet_dataset", "arrow_dataset")
        else {}
    )
    if set(partition) & set(schema.names):
        raise ProjectError(
            "Partition adı fiziksel sütunla çakışıyor; sessiz üzerine yazma yok."
        )
    metadata["arrow_schema_base64"] = readers.schema_token(schema)
    metadata["partition"] = partition
    stored = pa.schema(
        [
            pa.field(
                f.name, storage_type(f.type), nullable=f.nullable, metadata=f.metadata
            )
            for f in schema
        ]
        + [pa.field(n, pa.string()) for n in partition]
    )
    return stored, metadata


def schema_plan(parts, settings, control):
    schemas, metadata, changes, blocked = [], [], [], False
    for part in parts:
        control.check()
        schema, detail = part_schema(part, settings, control)
        schemas.append(schema)
        metadata.append(
            readers.json_safe(
                dict(name=part["name"], fingerprint=part["fingerprint"], **detail)
            )
        )
    target = {f.name: f.type for f in schemas[0]}
    for part, schema in zip(parts[1:], schemas[1:], strict=True):
        incoming = {f.name: f.type for f in schema}
        if list(target) != list(incoming) or any(
            target.get(n) != t for n, t in incoming.items()
        ):
            changes.append(
                dict(
                    part=part["name"],
                    incoming={n: str(t) for n, t in incoming.items()},
                    current={n: str(t) for n, t in target.items()},
                )
            )
            if settings.schema_policy == "strict":
                blocked = True
        for name, dtype in incoming.items():
            if name not in target:
                target[name] = dtype
            elif target[name] != dtype:
                try:
                    target[name] = merge_type(target[name], dtype)
                except ProjectError as error:
                    blocked = True
                    changes.append(dict(column=name, error=str(error)))
    if len(target) > 256:
        raise ProjectError("Birleşik şema256 sütun sınırını aştı.")
    target_schema = pa.schema([pa.field(n, t) for n, t in target.items()])
    blocked = blocked or any(
        p.get("multidimensional", {}).get("cost", {}).get("blocked", False)
        for p in metadata
    )
    # Verify the physical runtime can represent the exact destination schema.
    physical = pl.from_arrow(pa.Table.from_batches([], schema=target_schema)).schema
    for dtype in physical.values():
        describe(dtype)
    return (
        target_schema,
        physical,
        dict(
            parts=metadata,
            schema_changes=changes,
            resolution="Birleştirme: eksik alanlar null; yalnız kayıpsız tür genişletmesi"
            if settings.schema_policy == "union"
            else "Farklı şemada dur: birleştirme çözümünü önce önizleyin",
            dictionaries=[],
            missing_policy="source metadata and row tags preserved; no automatic recoding",
        ),
        blocked,
    )


def raw_batches(part, settings, control, schema):
    path, adapter = part["path"], settings.adapter_id
    if adapter in ("parquet_dataset", "arrow_dataset", "orc"):
        format_id = (
            "parquet"
            if adapter == "parquet_dataset"
            else "ipc"
            if adapter == "arrow_dataset"
            else "orc"
        )
        scanner = ds.dataset(path, format=format_id).scanner(
            batch_size=readers.BATCH_ROWS,
            use_threads=False,
            batch_readahead=0,
            fragment_readahead=0,
        )
        for batch in scanner.to_batches():
            control.check()
            yield pa.Table.from_batches([batch]), [{}] * batch.num_rows
    elif adapter == "avro":
        yield from readers.avro_batches(path, control)
    elif adapter in GEO_FORMATS:
        from veri_ufku.geo import readers as geo

        yield from geo.batches(path, settings, control)
    elif adapter in arrays.ARRAY_FORMATS:
        yield from arrays.batches(path, settings, control)
    elif adapter == "hdf5":
        yield from readers.hdf_batches(path, settings, control)
    elif adapter in ("spss", "stata", "sas"):
        yield from readers.statistical_batches(path, settings, control)
    else:
        yield from readers.text_batches(path, settings, control, schema)


def align_table(table, partition, schema, metadata, member, offset):
    for name, value in partition.items():
        table = table.append_column(
            name, pa.array([value] * len(table), type=pa.string())
        )
    arrays = []
    for field in schema:
        if field.name not in table.column_names:
            arrays.append(pa.nulls(len(table), type=field.type))
            continue
        column = table[field.name]
        if pa.types.is_dictionary(column.type):
            chunk_offset = offset
            for chunk in column.chunks:
                values = chunk.dictionary.to_pylist()
                if len(values) > 10000 or len(
                    {json.dumps(readers.json_safe(v), sort_keys=True) for v in values}
                ) != len(values):
                    raise ProjectError(
                        "Dictionary vocabulary sınırı veya yinelenen etiket: kodlar güvenle korunamıyor."
                    )
                metadata["dictionaries"].append(
                    dict(
                        part=member,
                        column=field.name,
                        row_start=chunk_offset,
                        count=len(chunk),
                        values=readers.json_safe(values),
                        index_type=str(chunk.type.index_type),
                        ordered=chunk.type.ordered,
                    )
                )
                chunk_offset += len(chunk)
            column = pc.cast(column, column.type.value_type, safe=True)
        arrays.append(pc.cast(column, field.type, safe=True))
    return pa.Table.from_arrays(arrays, schema=schema)


class AdvancedAdapter:
    def __init__(self, adapter_id):
        self.adapter_id = adapter_id

    def validate_source(self, request, control=None):
        if request.adapter_id != self.adapter_id:
            raise ProjectError("Adaptör/kaynak bağı geçersiz.")
        if (
            self.adapter_id in ("parquet_dataset", "arrow_dataset")
            and request.path.is_dir()
        ):
            directory_members(request.path)
        elif not request.path.is_file():
            raise ProjectError("Adaptör/kaynak bağı geçersiz.")

    def inspect(self, snapshot, settings, control):
        if self.adapter_id in GEO_FORMATS:
            from veri_ufku.geo import readers as geo

            return geo.choices(geo.source_path(snapshot), settings, control)
        if self.adapter_id in arrays.ARRAY_FORMATS:
            return arrays.inspect(
                parts_for(snapshot, self.adapter_id)[0]["path"], settings, control
            )
        choices = dict(
            format_notice="Native türler ve format metadata korunur; desteklenmeyen varyant kontrollü reddedilir."
        )
        if self.adapter_id == "hdf5":
            choices["sheets"] = readers.hdf_keys(
                input_snapshot(snapshot)["path"], control
            )
        return choices

    def preview(self, snapshot, settings, control=None):
        return self._run(snapshot, settings, None, control or Control())

    def import_data(self, snapshot, settings, workspace, control):
        return self._run(snapshot, settings, Path(workspace), control)

    def _run(self, snapshot, settings, workspace, control):
        if self.adapter_id in arrays.ARRAY_FORMATS:
            snapshot = dict(snapshot, strict_source=True)
        verify_capture(snapshot, control)
        verify_sources(snapshot, control)
        parts = parts_for(snapshot, self.adapter_id)
        if self.adapter_id in arrays.ARRAY_FORMATS and not settings.array_variable:
            if workspace:
                raise ProjectError("Array değişkenini ve kesitini önce önizleyin.")
            return dict(
                schema=dict(
                    names=[],
                    original_headers=[],
                    types=[],
                    warnings=[
                        "Değişken seçin; tam tensor açılmadı. Kesit maliyeti veri okumadan hesaplanır."
                    ],
                ),
                rows=[],
                bad=[],
                examined=0,
                limited=False,
                suggestions=[],
                settings=settings.data(),
                capture=snapshot,
                importable=False,
                diagnostics=dict(scope="metadata"),
            )
        schema, physical, metadata, blocked = schema_plan(parts, settings, control)
        names, warnings = names_for(schema.names)
        renamed = dict(zip(schema.names, names, strict=True))
        report = dict(
            names=names,
            original_headers=schema.names,
            types=[str(t) for t in physical.values()],
            warnings=warnings,
        )
        if metadata["schema_changes"]:
            warnings.append(
                "Şema çözüm önizlemesi: "
                + json.dumps(metadata["schema_changes"], ensure_ascii=False)
            )
            warnings.append(metadata["resolution"])
        if self.adapter_id in arrays.ARRAY_FORMATS:
            cost = metadata["parts"][0]["multidimensional"]["cost"]
            warnings.append(
                f"Kesit: {cost['output_rows']} satır; tahmini {cost['estimated_bytes']} bayt. "
                f"Tam tensor: {cost['full_tensor_cells']} hücre. "
                + (
                    "Bütçe aşıldı; daha küçük kesit seçin."
                    if cost["blocked"]
                    else "İçe aktarma açık kullanıcı eylemidir."
                )
            )
        if self.adapter_id in ("spss", "stata", "sas"):
            warnings.append(
                "Etiketler değerlerin yerine geçirilmez. User-missing kodları/row tag ayrımı ve ağırlık metadata korunur; analitiklerde otomatik ağırlık veya missing dışlaması uygulanmaz. Tarihler kaynak sayısal değer + format/unit metadata olarak korunur."
            )
        if self.adapter_id in ("xml", "fixed_width"):
            warnings.append(
                "Metin alanları varsayılan String; boş metin null değildir. Tür seçimi açık; tam okumada yeni/uyumsuz alan sessiz dönüştürülmez."
            )
        if workspace and blocked:
            raise ProjectError(
                "Şema çatışması çözülmedi; union çözümünü önizleyin veya kaynak parçalarını düzeltin."
            )
        all_schema = {renamed[n]: t for n, t in physical.items()}
        all_schema.update(
            {
                "__vu_row_id": pl.String,
                "__vu_source_record_id": pl.String,
                "__vu_start_line": pl.Int64,
                "__vu_end_line": pl.Int64,
                **EXTRA,
            }
        )
        output = workspace / (uid() + ".dataset.parquet") if workspace else None
        writer, count, rows, byte_count = None, 0, [], 0
        try:
            if not blocked:
                for part, detail in zip(parts, metadata["parts"], strict=True):
                    ordinal = 0
                    for table, missing in raw_batches(part, settings, control, schema):
                        control.check()
                        if table.nbytes > min(
                            64 * 1024**2, control.budget.ram_bytes // 4
                        ):
                            raise ProjectError(
                                "Tek decoded format batch bellek sınırını aştı."
                            )
                        if not workspace:
                            remaining = 200 - count
                            table, missing = (
                                table.slice(0, remaining),
                                missing[:remaining],
                            )
                        frame = pl.from_arrow(
                            align_table(
                                table,
                                detail["partition"],
                                schema,
                                metadata,
                                part["name"],
                                ordinal + 1,
                            )
                        ).rename(renamed)
                        size = len(frame)
                        if count + size > settings.max_rows:
                            raise ProjectError(
                                "İçe aktarma açık satır sınırını aştı; kısmi yayın yok."
                            )
                        if not workspace:
                            rows.extend(
                                [
                                    [
                                        "∅" if value is None else str(value)
                                        for value in row
                                    ]
                                    for row in frame.iter_rows()
                                ]
                            )
                        else:
                            locators = [
                                json.dumps(
                                    dict(
                                        part=part["name"],
                                        sha256=part["fingerprint"]["sha256"],
                                        record=ordinal + i + 1,
                                    ),
                                    ensure_ascii=False,
                                    separators=(",", ":"),
                                )
                                for i in range(size)
                            ]
                            frame = frame.with_columns(
                                pl.Series(
                                    "__vu_row_id", ["row:" + uid() for _ in range(size)]
                                ),
                                pl.Series(
                                    "__vu_source_record_id",
                                    ["sr:" + uid() for _ in range(size)],
                                ),
                                pl.Series(
                                    "__vu_start_line",
                                    list(range(ordinal + 1, ordinal + size + 1)),
                                    dtype=pl.Int64,
                                ),
                                pl.Series(
                                    "__vu_end_line",
                                    list(range(ordinal + 1, ordinal + size + 1)),
                                    dtype=pl.Int64,
                                ),
                                pl.Series("__vu_source_locator", locators),
                                pl.Series(
                                    "__vu_missing_fields",
                                    [
                                        [
                                            renamed[n]
                                            for n in schema.names
                                            if n not in table.column_names
                                            and n not in detail["partition"]
                                        ]
                                    ]
                                    * size,
                                    dtype=pl.List(pl.String),
                                ),
                                pl.Series(
                                    "__vu_expansion_index",
                                    [
                                        json.dumps(
                                            m,
                                            ensure_ascii=False,
                                            separators=(",", ":"),
                                        )
                                        if m
                                        else "{}"
                                        for m in missing
                                    ],
                                ),
                            ).select(list(all_schema))
                            arrow = frame.to_arrow()
                            if writer is None:
                                writer = pq.ParquetWriter(
                                    output, arrow.schema, compression="zstd"
                                )
                            writer.write_table(arrow)
                            byte_count += arrow.nbytes
                            if byte_count > control.budget.temp_disk_bytes:
                                raise ProjectError(
                                    "Decoded dataset disk bütçesini aştı."
                                )
                            control.disk(workspace)
                        count += size
                        ordinal += size
                        control.progress("Format kaydı doğrulama", count, None)
                        if not workspace and count >= 200:
                            break
                    if not workspace and count >= 200:
                        break
        finally:
            if writer:
                writer.close()
        verify_capture(snapshot, control)
        verify_sources(snapshot, control)
        saved = replace(
            settings,
            format_metadata=readers.json_safe(metadata),
            native_schema={n: describe(t) for n, t in all_schema.items()}
            if workspace
            else {},
        )
        if not workspace:
            return dict(
                schema=report,
                rows=rows,
                bad=[],
                examined=count,
                limited=count >= 200,
                suggestions=report["types"],
                settings=saved.data(),
                capture=snapshot,
                importable=count > 0 and not blocked,
                diagnostics=dict(
                    format_metadata=metadata, schema_blocked=blocked, scope="sample"
                ),
            )
        if not count or pl.read_parquet_schema(output) != all_schema:
            raise ProjectError(
                "Native format çıktı şema/kayıt doğrulaması başarısız; yayın yok."
            )
        return dict(
            path=str(output),
            quarantine=None,
            artifact_fingerprint=hash_artifact(output, control),
            quarantine_fingerprint=None,
            schema=report,
            accepted=count,
            bad_count=0,
            examined=count,
            source_snapshot_id="snapshot:" + uid(),
            settings=saved.data(),
            capture=snapshot,
            adapter_id=self.adapter_id,
            diagnostics=dict(
                source_records=count,
                output_rows=count,
                scope="full",
                format_metadata=metadata,
            ),
            backend="bounded-format/arrow/polars",
            environment=tuple(
                (name, version(name))
                for name in (
                    "pyarrow",
                    {
                        "avro": "fastavro",
                        "hdf5": "h5py",
                        "spss": "pyreadstat",
                        "stata": "pyreadstat",
                        "sas": "pyreadstat",
                        "xml": "defusedxml",
                    }.get(self.adapter_id, "polars"),
                )
            ),
        )
