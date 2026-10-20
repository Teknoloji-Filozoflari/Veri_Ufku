"""Bounded format readers. No publishing, Qt, network or executable metadata."""

import base64
import json
import math
import re
import struct
from datetime import date, datetime

import pyarrow as pa

from veri_ufku.importers.delimited import MAX_RECORD
from veri_ufku.storage.project_model import ProjectError

BATCH_ROWS = 1024


def schema_token(schema):
    return base64.b64encode(schema.serialize().to_pybytes()).decode("ascii")


def json_safe(value):
    if isinstance(value, (date, datetime)):
        return {"iso8601": value.isoformat(), "type": type(value).__name__}
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, bytes):
        return {"binary_base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": str(value)}
    if hasattr(value, "item"):
        return json_safe(value.item())
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ProjectError("Metadata türü güvenle saklanamıyor; otomatik atılmadı.")


def avro_type(spec, depth=0):
    if depth > 16:
        raise ProjectError("Avro nested derinliği16 sınırını aştı.")
    if isinstance(spec, list):
        choices = [s for s in spec if s != "null"]
        if len(choices) != 1 or len(spec) > 2:
            raise ProjectError(
                "Avro yalnız null+tek tür union destekler; çok tür union desteklenmez."
            )
        return avro_type(choices[0], depth + 1)
    if isinstance(spec, str):
        types = dict(
            null=pa.null(),
            boolean=pa.bool_(),
            int=pa.int32(),
            long=pa.int64(),
            float=pa.float32(),
            double=pa.float64(),
            bytes=pa.binary(),
            string=pa.string(),
        )
        if spec not in types:
            raise ProjectError("Avro recursive/named reference desteklenmiyor.")
        return types[spec]
    kind = spec.get("type")
    logical = spec.get("logicalType")
    if logical:
        if (
            logical == "decimal"
            and 1 <= spec.get("precision", 0) <= 38
            and 0 <= spec.get("scale", 0) <= spec["precision"]
        ):
            return pa.decimal128(spec["precision"], spec.get("scale", 0))
        if logical == "date":
            return pa.date32()
        if logical in (
            "timestamp-millis",
            "timestamp-micros",
            "local-timestamp-millis",
            "local-timestamp-micros",
        ):
            return pa.timestamp(
                "ms" if logical.endswith("millis") else "us",
                tz=None if logical.startswith("local") else "UTC",
            )
        if logical in ("time-millis", "time-micros"):
            return pa.time32("ms") if logical.endswith("millis") else pa.time64("us")
        raise ProjectError(
            "Avro logical type desteklenmiyor; bytes/metne sessiz dönüşüm yok."
        )
    if kind == "record":
        return pa.struct(
            [
                pa.field(
                    f["name"],
                    avro_type(f["type"], depth + 1),
                    nullable=isinstance(f["type"], list) and "null" in f["type"],
                )
                for f in spec["fields"]
            ]
        )
    if kind == "array":
        return pa.list_(avro_type(spec["items"], depth + 1))
    if kind == "enum":
        return pa.string()
    if kind == "fixed":
        return pa.binary()
    return avro_type(kind, depth + 1)


def avro_info(path):
    import fastavro

    with open(path, "rb") as stream:
        reader = fastavro.reader(stream)
        spec = reader.writer_schema
        dtype = avro_type(spec)
        if not pa.types.is_struct(dtype):
            raise ProjectError("Avro kökü record olmalı.")
        return pa.schema(list(dtype)), dict(
            writer_schema=spec, codec=reader.codec, metadata=json_safe(reader.metadata)
        )


def avro_batches(path, control):
    import fastavro

    schema, _ = avro_info(path)
    with open(path, "rb") as stream:
        rows = []
        for row in fastavro.reader(stream):
            control.check()
            rows.append(row)
            if len(rows) == BATCH_ROWS:
                yield pa.Table.from_pylist(rows, schema=schema), [{}] * len(rows)
                rows = []
        if rows:
            yield pa.Table.from_pylist(rows, schema=schema), [{}] * len(rows)


def hdf_keys(path, control):
    import h5py

    keys, visited = [], set()
    with h5py.File(path, "r") as file:

        def walk(group, prefix, depth):
            control.check()
            if depth > 16 or len(visited) > 4096:
                raise ProjectError("HDF5 nesne/derinlik sınırı aşıldı.")
            address = h5py.h5o.get_info(group.id).addr
            if address in visited:
                return
            visited.add(address)
            for name in group:
                control.check()
                link = group.get(name, getlink=True)
                if not isinstance(link, h5py.HardLink):
                    raise ProjectError("HDF5 external/soft link desteklenmez.")
                obj = group[name]
                key = prefix + "/" + name
                if isinstance(obj, h5py.Group):
                    walk(obj, key, depth + 1)
                elif isinstance(obj, h5py.Dataset):
                    if obj.is_virtual or obj.external:
                        raise ProjectError("HDF5 virtual/external veri desteklenmez.")
                    if obj.ndim == 1 and obj.dtype.names:
                        keys.append(key)

        walk(file, "", 0)
    return keys


def hdf_schema(dataset):
    import h5py

    fields = []
    for name in dataset.dtype.names:
        dt = dataset.dtype.fields[name][0]
        if dt.subdtype or dt.names or dt.kind in "OVcmM":
            raise ProjectError(
                "HDF5 vlen/reference/array/complex/nested tablo alanı desteklenmez."
            )
        enum = h5py.check_enum_dtype(dt)
        if dt.kind == "S":
            dtype = pa.binary()
        else:
            dtype = pa.from_numpy_dtype(dt)
        fields.append(
            pa.field(
                name,
                dtype,
                nullable=False,
                metadata={b"hdf5.enum": json.dumps(enum).encode()} if enum else None,
            )
        )
    return pa.schema(fields)


def hdf_info(path, settings, control):
    import h5py

    keys = hdf_keys(path, control)
    if not settings.sheet or settings.sheet not in keys:
        raise ProjectError("HDF5 tablo key seçin; otomatik ilk key seçilmez.")
    with h5py.File(path, "r") as file:
        dataset = file[settings.sheet]
        # Filters never trigger a dynamic plugin loader from input files.
        plist = dataset.id.get_create_plist()
        if any(
            plist.get_filter(i)[0] not in (1, 2, 3) for i in range(plist.get_nfilters())
        ):
            raise ProjectError("HDF5 özel filtre/plugin desteklenmez.")
        if (
            dataset.chunks
            and math.prod(dataset.chunks) * dataset.dtype.itemsize > 16 * 1024**2
        ):
            raise ProjectError("HDF5 chunk16MiB sınırını aştı.")
        return hdf_schema(dataset), dict(
            key=settings.sheet,
            rows=len(dataset),
            attributes=json_safe(dict(dataset.attrs)),
            root_attributes=json_safe(dict(file.attrs)),
            dtype=dataset.dtype.descr,
            enums={
                name: json_safe(h5py.check_enum_dtype(dataset.dtype.fields[name][0]))
                for name in dataset.dtype.names
                if h5py.check_enum_dtype(dataset.dtype.fields[name][0])
            },
            compression=dataset.compression,
        )


def hdf_batches(path, settings, control):
    import h5py

    schema, _ = hdf_info(path, settings, control)
    with h5py.File(path, "r") as file:
        dataset = file[settings.sheet]
        for offset in range(0, len(dataset), BATCH_ROWS):
            control.check()
            records = dataset[offset : offset + BATCH_ROWS]
            yield (
                pa.Table.from_arrays(
                    [pa.array(records[f.name].tolist(), type=f.type) for f in schema],
                    schema=schema,
                ),
                [{}] * len(records),
            )


class BoundedXML:
    def __init__(self, stream, control):
        self.stream, self.control = stream, control
        self.segment_bytes = 0

    def read(self, size=-1):
        self.control.check()
        raw = self.stream.read(min(65536, size) if size >= 0 else 65536)
        pieces = raw.split(b"<")
        self.segment_bytes += len(pieces[0])
        if self.segment_bytes > MAX_RECORD or any(
            len(p) > MAX_RECORD for p in pieces[1:]
        ):
            raise ProjectError("XML metin/markup alanı1MiB sınırını aştı.")
        if len(pieces) > 1:
            self.segment_bytes = len(pieces[-1])
        return raw


def text_records(path, settings, control):
    if settings.adapter_id == "fixed_width":
        if (
            not settings.widths
            or not settings.column_names
            or len(settings.column_names) != len(settings.widths)
        ):
            raise ProjectError(
                "Sabit genişlik için sütun adları ve karakter genişliklerini seçin."
            )
        if len(set(settings.column_names)) != len(settings.column_names) or any(
            not n for n in settings.column_names
        ):
            raise ProjectError("Sütun adları boş/yinelenen olamaz.")
        with open(path, encoding=settings.encoding, errors="strict") as stream:
            for line in iter(lambda: stream.readline(MAX_RECORD + 1), ""):
                control.check()
                line = line.rstrip("\r\n")
                if len(line.encode(settings.encoding)) > MAX_RECORD or len(line) != sum(
                    settings.widths
                ):
                    raise ProjectError(
                        "Sabit genişlik satırı seçilen genişlikle uyuşmuyor veya1MiB sınırında değil."
                    )
                offset, row = 0, {}
                for name, width in zip(
                    settings.column_names, settings.widths, strict=True
                ):
                    row[name] = line[offset : offset + width]
                    offset += width
                yield row
        return
    from defusedxml.ElementTree import iterparse

    if not re.fullmatch(
        r"/[A-Za-z_][\w.-]*(?:/[A-Za-z_][\w.-]*)+", settings.record_path
    ):
        raise ProjectError(
            "XML kayıt yolunu seçin (ör. /root/record); XPath/namespace bu varyantta yok."
        )
    stack, elements, record_bytes = [], [], 0
    with open(path, "rb") as stream:
        for event, elem in iterparse(
            BoundedXML(stream, control),
            events=("start", "end"),
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        ):
            control.check()
            if event == "start":
                stack.append(elem.tag)
                elements.append(elem)
                if len(stack) > 16 or len(elem.attrib) > 256:
                    raise ProjectError("XML derinlik/alan sınırı aşıldı.")
                if (
                    len(elements) > 1
                    and "/" + "/".join(stack[:-1]) == settings.record_path
                    and len(elements[-2]) > 256
                ):
                    raise ProjectError("XML kayıt child256 sınırını aştı.")
                if "/" + "/".join(stack) == settings.record_path:
                    record_bytes = sum(len(k) + len(v) for k, v in elem.attrib.items())
                continue
            current_path = "/" + "/".join(stack)
            matched = current_path == settings.record_path
            if current_path.startswith(settings.record_path + "/"):
                record_bytes += len(elem.text or "") + len(elem.tail or "")
                if record_bytes > MAX_RECORD:
                    raise ProjectError("XML kayıt1MiB sınırını aştı.")
            if matched:
                if (elem.text or "").strip() or any(
                    (child.tail or "").strip() for child in elem
                ):
                    raise ProjectError(
                        "XML mixed-content desteklenmez; metin kaybedilmedi."
                    )
                if any(list(child) or child.attrib for child in elem):
                    raise ProjectError(
                        "XML kayıt yalnız düz child metin ve kayıt attribute destekler; nested/repeated alanı açıkça reddeder."
                    )
                row = {"@" + k: v for k, v in elem.attrib.items()}
                for child in elem:
                    if child.tag in row:
                        raise ProjectError("XML tekrar eden alan desteklenmiyor.")
                    row[child.tag] = child.text if child.text is not None else ""
                if (
                    len(row) > 256
                    or sum(len(k) + len(v) for k, v in row.items()) > MAX_RECORD
                ):
                    raise ProjectError("XML tek kayıt/sütun sınırı aşıldı.")
                yield row
            stack.pop()
            elements.pop()
            # Keep children only while inside a selected record, remove completed
            # branches so iterparse does not accumulate millions of empty nodes.
            if matched or (
                not current_path.startswith(settings.record_path + "/")
                and not settings.record_path.startswith(current_path + "/")
            ):
                elem.clear()
                if elements:
                    elements[-1].remove(elem)


def text_batches(path, settings, control, schema):
    from veri_ufku.importers.native import selected_value

    rows = []
    for row in text_records(path, settings, control):
        if set(row) - set(schema.names):
            raise ProjectError(
                "Tam okumada yeni XML alanı bulundu; alan şeması önizlemeyle uyuşmuyor."
            )
        converted = {}
        for index, field in enumerate(schema):
            value = row.get(field.name)
            kind = settings.types[index] if settings.types else "text"
            converted[field.name] = (
                value
                if kind in ("auto", "text")
                else selected_value(value, kind, settings)
            )
        rows.append(converted)
        if len(rows) == BATCH_ROWS:
            yield pa.Table.from_pylist(rows, schema=schema), [{}] * len(rows)
            rows = []
    if rows:
        yield pa.Table.from_pylist(rows, schema=schema), [{}] * len(rows)


def statistical_reader(adapter, path):
    import pyreadstat

    if adapter == "spss":
        return pyreadstat.read_sav
    if adapter == "stata":
        return pyreadstat.read_dta
    with open(path, "rb") as stream:
        if stream.read(20).startswith(b"HEADER RECORD"):
            raise ProjectError(
                "SAS XPORT tagged missing korunumu henüz doğrulanmadı; sas7bdat seçin."
            )
    return pyreadstat.read_sas7bdat


def statistical_options(reader):
    import inspect

    options = dict(output_format="dict", disable_datetime_conversion=True)
    if "user_missing" in inspect.signature(reader).parameters:
        options["user_missing"] = True
    return options


def statistical_info(path, settings):
    reader = statistical_reader(settings.adapter_id, path)
    _, meta = reader(path, metadataonly=True, **statistical_options(reader))
    schema = pa.schema(
        [
            pa.field(
                name,
                pa.string()
                if meta.readstat_variable_types[name] in ("string", "string_ref")
                else pa.float64(),
            )
            for name in meta.column_names
        ]
    )
    metadata = json_safe(vars(meta))
    metadata["value_label_entries"] = {
        n: [
            dict(value=json_safe(value), label=label) for value, label in labels.items()
        ]
        for n, labels in meta.variable_value_labels.items()
    }
    weight = None
    if settings.adapter_id == "spss":
        with open(path, "rb") as stream:
            header = stream.read(100)
        endian = "<" if struct.unpack("<i", header[64:68])[0] == 2 else ">"
        index = struct.unpack(endian + "i", header[76:80])[0]
        metadata["weight_physical_index"] = index
        if index:
            position = 1
            for name in meta.column_names:
                if position == index:
                    weight = name
                    break
                position += max(
                    1, math.ceil(meta.variable_storage_width.get(name, 8) / 8)
                )
            if weight is None:
                raise ProjectError(
                    "SPSS ağırlık fiziksel indeksi çözülemedi; metadata sessiz kaybedilmedi."
                )
    if settings.weight_column and settings.weight_column not in schema.names:
        raise ProjectError("Seçilen ağırlık sütunu yok.")
    metadata["weight_definition"] = dict(
        source_column=weight,
        declared_column=settings.weight_column or None,
        automatically_applied=False,
        kind="source-defined; statistical meaning requires user choice"
        if weight
        else "not declared by source format",
    )
    metadata["missing_storage"] = (
        "numeric user-missing codes remain values; tagged missing become null plus row __vu_expansion_index user_missing map; system-missing null"
    )
    metadata["character_missing_storage"] = (
        "Stata/SAS blank strings remain raw strings plus row system_missing flag; SPSS user-missing strings retain missing_ranges"
    )
    return schema, metadata


def statistical_batches(path, settings, control):
    reader = statistical_reader(settings.adapter_id, path)
    schema, _ = statistical_info(path, settings)
    offset = 0
    while True:
        control.check()
        data, meta = reader(
            path, row_offset=offset, row_limit=BATCH_ROWS, **statistical_options(reader)
        )
        count = len(data[schema.names[0]])
        if not count:
            break
        missing = [{} for _ in range(count)]
        arrays = []
        for field in schema:
            values = []
            tags = meta.missing_user_values.get(field.name, [])
            for index, value in enumerate(data[field.name]):
                if (
                    field.type == pa.float64()
                    and isinstance(value, str)
                    and value in tags
                ):
                    missing[index].setdefault("user_missing", {})[field.name] = value
                    value = None
                if (
                    settings.adapter_id in ("stata", "sas")
                    and pa.types.is_string(field.type)
                    and isinstance(value, str)
                    and not value.strip()
                ):
                    missing[index].setdefault("system_missing", {})[field.name] = (
                        "blank"
                    )
                if isinstance(value, float) and math.isnan(value):
                    value = None
                values.append(value)
            arrays.append(pa.array(values, type=field.type))
        yield pa.Table.from_arrays(arrays, schema=schema), missing
        offset += count
        if count < BATCH_ROWS:
            break
