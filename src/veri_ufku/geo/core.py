"""Validated geometry/CRS boundary. PROJ network is always disabled."""

import math
from decimal import Decimal

import numpy as np
import pyproj
import shapely

from veri_ufku.storage.project_model import ProjectError

pyproj.network.set_network_enabled(False)


def numeric_values(values):
    """Require explicit source conversion when exact values cannot fit Float64."""
    result = []
    for value in values:
        if not isinstance(value, (int, float, Decimal)) or isinstance(value, bool):
            raise ProjectError("Mekânsal ölçüm/koordinat sonlu sayısal değer ister.")
        try:
            converted = float(value)
        except (OverflowError, ValueError) as error:
            raise ProjectError(
                "Mekânsal ölçüm/koordinat Float64 aralığını aşıyor."
            ) from error
        if not math.isfinite(converted):
            raise ProjectError("Mekânsal ölçüm/koordinat sonlu Float64 değer ister.")
        if isinstance(value, (int, Decimal)) and Decimal.from_float(
            converted
        ) != Decimal(value):
            raise ProjectError(
                "Mekânsal Integer/Decimal → Float64 hassasiyet kaybı; önce açık tür/ölçek dönüşümü seçin."
            )
        result.append(converted)
    return result


def crs(value):
    try:
        result = pyproj.CRS.from_user_input(value)
    except Exception as error:
        raise ProjectError(
            "CRS bilinmiyor; CRS atama koordinatları dönüştürmez."
        ) from error
    if not (result.is_geographic or result.is_projected) or len(result.axis_info) != 2:
        raise ProjectError("Yalnız iki boyutlu geographic/projected CRS desteklenir.")
    return result


def geometries(values, valid=True):
    try:
        result = [shapely.from_wkt(v) if v is not None else None for v in values]
    except Exception as error:
        raise ProjectError(
            "Geometri WKT çözümlenemedi; otomatik repair yok."
        ) from error
    if any(g is None or g.is_empty or g.has_z or g.has_m for g in result):
        raise ProjectError(
            "Null/empty/Z/M geometri bu işlemde desteklenmez; yalnız 2D xy."
        )
    if not np.isfinite(shapely.get_coordinates(result)).all():
        raise ProjectError("Geometri koordinatları sonlu olmalı.")
    if valid and not all(g.is_valid for g in result):
        raise ProjectError(
            "Geçersiz geometri; önce repair önizleyin, sonra açık apply."
        )
    return result


def inspect(values, coordinate_system):
    parsed = []
    invalid = []
    empty = []
    types = {}
    for i, v in enumerate(values):
        try:
            g = shapely.from_wkt(v) if v else None
        except Exception:
            g = None
            invalid.append(dict(index=i, reason="WKT parse"))
        parsed.append(g)
        if g is None or g.is_empty:
            empty.append(i)
            continue
        types[g.geom_type] = types.get(g.geom_type, 0) + 1
        if not g.is_valid:
            invalid.append(dict(index=i, reason=shapely.is_valid_reason(g)))
    usable = [g for g in parsed if g is not None and not g.is_empty]
    bounds = shapely.total_bounds(usable).tolist() if usable else None
    c = crs(coordinate_system) if coordinate_system else None
    return dict(
        crs=c.to_wkt() if c else None,
        authority=c.to_string() if c else None,
        axis_order="x,y; longitude,latitude / easting,northing",
        geometry_types=types,
        extent=bounds,
        invalid=invalid[:200],
        invalid_count=len(invalid),
        empty_count=len(empty),
        antimeridian="Crossing geometries rejected for planar operations; split explicitly in suitable CRS.",
        nodata=None,
        geometry_encoding="WKT; source bytes retained",
    )


def geographic_check(gs, c):
    if not c.is_geographic:
        return
    # always_xy uses longitude first even when the CRS declares latitude first.
    factors = np.array(
        [
            next(
                a.unit_conversion_factor
                for a in c.axis_info
                if a.direction in directions
            )
            for directions in (("east", "west"), ("north", "south"))
        ]
    ) * (180 / np.pi)
    xy = shapely.get_coordinates(gs) * factors
    if ((abs(xy[:, 0]) > 180) | (abs(xy[:, 1]) > 90)).any():
        raise ProjectError(
            "Longitude/latitude sınırı veya eksen sırası yanlış; x=longitude,y=latitude."
        )
    pending = list(gs)
    while pending:
        part = pending.pop()
        if part.geom_type.startswith("Multi") or part.geom_type == "GeometryCollection":
            pending.extend(part.geoms)
            continue
        rings = (
            list(part.interiors) + [part.exterior]
            if part.geom_type == "Polygon"
            else [part]
        )
        for r in rings:
            longitude = shapely.get_coordinates(r)[:, 0] * factors[0]
            if len(longitude) > 1 and (np.abs(np.diff(longitude)) > 180).any():
                raise ProjectError(
                    "Antimeridian geçişi: açık split/wrap gerekir; düzlemsel eşleşme yapılmadı."
                )


def metric(gs, c):
    if (
        not c.is_projected
        or c.to_epsg() == 3857
        or any(abs(a.unit_conversion_factor - 1) > 1e-12 for a in c.axis_info)
    ):
        raise ProjectError(
            "Mesafe/alan/buffer metre birimli uygun projected CRS ister; derece ve Web Mercator reddedilir."
        )
    geographic_check(gs, c)
    area = c.area_of_use
    if area:
        t = pyproj.Transformer.from_crs(c, 4326, always_xy=True, allow_ballpark=False)
        xy = shapely.get_coordinates(gs)
        x, y = t.transform(xy[:, 0], xy[:, 1], errcheck=True)
        if any(
            lon < area.west or lon > area.east or lat < area.south or lat > area.north
            for lon, lat in zip(x, y)
        ):
            raise ProjectError(
                "Geometri seçilen CRS kullanım alanı dışında; uygun yerel projeksiyon seçin."
            )


def reproject(gs, source, target):
    s, t = crs(source), crs(target)
    if any(g.has_z or g.has_m for g in gs):
        raise ProjectError(
            "CRS dönüşümü yalnız 2D xy destekler; Z/M kaybına izin verilmez."
        )
    geographic_check(gs, s)
    transformer = pyproj.Transformer.from_crs(
        s, t, always_xy=True, allow_ballpark=False, only_best=True
    )
    try:
        result = [
            shapely.transform(
                g,
                lambda x, y: transformer.transform(x, y, errcheck=True),
                interleaved=False,
            )
            for g in gs
        ]
    except Exception as error:
        raise ProjectError("CRS dönüşümü/grid başarısız; ağ indirmesi yok.") from error
    geographic_check(result, t)
    return result, dict(
        source=s.to_wkt(),
        target=t.to_wkt(),
        always_xy=True,
        operation=transformer.description,
        accuracy=transformer.accuracy,
        network=False,
    )
