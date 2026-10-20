"""Offline map calculation with immutable glyph membership and explicit denominators."""

import numpy as np
import shapely

from veri_ufku.geo import CHART_SCHEMAS as SCHEMAS
from veri_ufku.geo.core import crs, geographic_check, geometries, inspect, metric
from veri_ufku.geo.operations import metadata
from veri_ufku.storage.project_model import ProjectError

KINDS = ("map-point", "map-choropleth", "map-density", "map-raster")


def calculate(request, spec, values, numbers, add, used, details, control):
    meta = metadata(request)
    system = spec.geo_crs or meta.get("crs")
    if not system:
        raise ProjectError("Harita CRS ister; koordinat kolonlarında açık CRS seçin.")
    c = crs(system)
    if (
        meta.get("crs")
        and spec.geo_crs
        and not c.equals(crs(meta["crs"]), ignore_axis_order=True)
    ):
        raise ProjectError("Harita CRS atamaz/dönüştürmez; ayrı CRS işlemi seçin.")
    if spec.kind == "map-raster":
        if not meta.get("raster") or not meta.get("window"):
            raise ProjectError(
                "Raster haritası doğrulanmış GeoTIFF kesiti ister; tablodan raster uydurulmaz."
            )
        if used > 65536:
            raise ProjectError("Raster kesit65536hücre sınırı.")
        columns = {column["id"]: column["name"] for column in request["columns"]}
        if (
            spec.geometry
            or columns.get(spec.x) != "x"
            or columns.get(spec.y) != "y"
            or columns.get(spec.geo_measure) != "value"
        ):
            raise ProjectError(
                "Raster haritası captured x/y/value sütunlarını ister; satır/sütun indeksi veya başka ölçüm piksel yerine kullanılamaz."
            )
        x, y, z = numbers(spec.x), numbers(spec.y), numbers(spec.geo_measure)
        for i in range(used):
            if x[i] is None or y[i] is None:
                raise ProjectError("Raster koordinatı eksik.")
            if z[i] is not None:
                add(x[i], y[i], [i], z=z[i], label="pixel")
        details["geospatial"] = dict(
            meta,
            mode="raster",
            nodata_count=sum(v is None for v in z),
            scope="selected captured window; no interpolation",
            input_schema=SCHEMAS[spec.kind],
            offline=True,
            attribution=request.get("format_metadata", {})
            .get("connector", {})
            .get("spec", {})
            .get("attribution"),
            cache_policy=request.get("format_metadata", {})
            .get("connector", {})
            .get("spec", {})
            .get("cache_policy"),
        )
        return
    if used > 10000:
        raise ProjectError("Harita10000feature sınırı; açık kesit gerekir.")
    if spec.geometry:
        gs = geometries(values[spec.geometry])
    else:
        x, y = numbers(spec.x), numbers(spec.y)
        if any(v is None for v in x + y):
            raise ProjectError("Eksik koordinat; sessiz dışlama yok.")
        gs = [shapely.Point(a, b) for a, b in zip(x, y)]
    geographic_check(gs, c)
    info = inspect([g.wkt for g in gs], system)
    if spec.kind == "map-density":
        if any(g.geom_type != "Point" for g in gs):
            raise ProjectError("Yoğunluk yalnız Point geometri ister.")
        metric(gs, c)
        x = np.array([g.x for g in gs])
        y = np.array([g.y for g in gs])
        hist, xe, ye = np.histogram2d(x, y, bins=spec.grid_bins)
        xi = np.clip(np.searchsorted(xe, x, side="right") - 1, 0, len(xe) - 2)
        yi = np.clip(np.searchsorted(ye, y, side="right") - 1, 0, len(ye) - 2)
        for a, b in zip(*np.nonzero(hist)):
            members = np.flatnonzero((xi == a) & (yi == b)).tolist()
            area = (xe[a + 1] - xe[a]) * (ye[b + 1] - ye[b])
            v = float(
                hist[a, b] / area if spec.geo_measure_mode == "rate" else hist[a, b]
            )
            add(
                float((xe[a] + xe[a + 1]) / 2),
                float((ye[b] + ye[b + 1]) / 2),
                members,
                z=v,
                rect=[
                    float(xe[a]),
                    float(ye[b]),
                    float(xe[a + 1] - xe[a]),
                    float(ye[b + 1] - ye[b]),
                ],
                label="density cell",
            )
        info.update(
            mode="density",
            thresholds=[],
            x_edges=xe.tolist(),
            y_edges=ye.tolist(),
            value_semantics="count/m²" if spec.geo_measure_mode == "rate" else "count",
            unit="m",
            aggregation="histogram2d; all memberships; not KDE",
        )
    elif spec.kind == "map-choropleth":
        if any(g.geom_type not in ("Polygon", "MultiPolygon") for g in gs):
            raise ProjectError("Choropleth polygon/multipolygon ister.")
        vals = numbers(spec.geo_measure)
        if any(v is None or v < 0 for v in vals):
            raise ProjectError(
                "Choropleth sonlu/nonnegative ölçüm ister; sessiz eksik dışlama yok."
            )
        if spec.geo_measure_mode == "rate":
            den = numbers(spec.geo_denominator)
            if any(v is None or v <= 0 for v in den):
                raise ProjectError("Oran her feature için pozitif sonlu payda ister.")
            vals = [a / b for a, b in zip(vals, den)]
            info["denominator_column"] = spec.geo_denominator
        if spec.geo_classification == "manual":
            edges = list(spec.geo_thresholds)
        elif spec.geo_classification == "quantile":
            edges = np.unique(
                np.quantile(vals, np.linspace(0, 1, spec.bins + 1)[1:-1])
            ).tolist()
        else:
            edges = (
                np.linspace(min(vals), max(vals), spec.bins + 1)[1:-1].tolist()
                if min(vals) != max(vals)
                else []
            )
        for i, (g, v) in enumerate(zip(gs, vals)):
            center = g.representative_point()
            add(
                center.x,
                center.y,
                [i],
                z=float(v),
                geometry=g.wkt,
                category=int(np.searchsorted(edges, v, side="right")),
                label=str(i),
            )
        info.update(
            mode="choropleth",
            classification=spec.geo_classification,
            thresholds=edges,
            threshold_policy="left inclusive, value == threshold enters next class; quantile ties collapse classes",
            value_semantics=spec.geo_measure_mode,
            normalization="feature numerator/denominator"
            if spec.geo_measure_mode == "rate"
            else "raw count; population/area exposure not adjusted",
            MAUP="Aggregation boundaries and class thresholds change interpretation.",
        )
    else:
        if any(g.geom_type != "Point" for g in gs):
            raise ProjectError("Nokta haritası Point geometri ister.")
        for i, g in enumerate(gs):
            add(g.x, g.y, [i], geometry=g.wkt, label=str(i))
        info.update(mode="point", value_semantics="one point per source occurrence")
    info["attribution"] = (
        request.get("format_metadata", {})
        .get("connector", {})
        .get("spec", {})
        .get("attribution")
    )
    info.update(
        input_schema=SCHEMAS[spec.kind],
        offline=True,
        basemap="none; local coordinate map",
        tiles="disabled; no network on calculate/reopen",
        included_n=used,
    )
    details["geospatial"] = info


def draw(result, spec, fig, palette):
    from matplotlib import colormaps, colors
    from matplotlib.patches import PathPatch, Rectangle
    from matplotlib.path import Path

    ax = fig.add_subplot(111)
    point_axes = {}
    points = result["points"]
    geo = result["details"]["geospatial"]
    cmap = colormaps["Greys" if spec.palette == "grayscale" else "viridis"]
    z = [p["z"] for p in points if "z" in p]
    norm = (
        colors.Normalize(min(z), max(z) if max(z) != min(z) else min(z) + 1)
        if z
        else None
    )
    if geo["mode"] == "choropleth":
        n = len(geo["thresholds"]) + 1
        for p in points:
            g = shapely.from_wkt(p["geometry"])
            for part in shapely.get_parts(g):
                verts = []
                codes = []
                # Orient holes opposite exterior for the nonzero fill rule.
                part = shapely.orient_polygons(part, exterior_cw=False)
                for ring in [part.exterior, *part.interiors]:
                    coordinates = list(ring.coords)
                    verts += coordinates
                    codes += (
                        [Path.MOVETO]
                        + [Path.LINETO] * (len(coordinates) - 2)
                        + [Path.CLOSEPOLY]
                    )
                ax.add_patch(
                    PathPatch(
                        Path(verts, codes),
                        facecolor=cmap((p["category"] + 0.5) / n),
                        edgecolor="black",
                        linewidth=0.5,
                    )
                )
            point_axes[p["point_id"]] = ax
        from matplotlib.patches import Patch

        edges = geo["thresholds"]
        labels = (
            [f"< {edges[0]:g}" if edges else "all values"]
            + [f"[{edges[i]:g}, {edges[i + 1]:g})" for i in range(len(edges) - 1)]
            + ([f"≥ {edges[-1]:g}"] if edges else [])
        )
        ax.legend(
            handles=[
                Patch(facecolor=cmap((i + 0.5) / n), label=label)
                for i, label in enumerate(labels)
            ],
            title=geo["value_semantics"],
        )
    elif geo["mode"] == "density":
        for p in points:
            ax.add_patch(
                Rectangle(
                    p["rect"][:2],
                    p["rect"][2],
                    p["rect"][3],
                    facecolor=cmap(norm(p["z"])),
                )
            )
            point_axes[p["point_id"]] = ax
    elif geo["mode"] == "raster":
        a, b, c, d, e, f, *_ = geo["transform"]
        if abs(b) > 1e-12 or abs(d) > 1e-12:
            raise ProjectError(
                "Raster rotated/sheared preview desteklenmez; source warp işlemi gerekli."
            )
        col, row, width, height = geo["window"]
        grid = np.ma.masked_all((height, width), dtype=float)
        for p in points:
            ci = int(round((p["x"] - c) / a - 0.5)) - col
            ri = int(round((p["y"] - f) / e - 0.5)) - row
            if not (0 <= ci < width and 0 <= ri < height):
                raise ProjectError("Raster point/window metadata uyuşmazlığı.")
            grid[ri, ci] = p["z"]
            point_axes[p["point_id"]] = ax
        left = c + a * col
        right = left + a * width
        top = f + e * row
        bottom = top + e * height
        ax.imshow(
            grid,
            extent=[left, right, bottom, top],
            origin="upper",
            cmap=cmap,
            norm=norm,
            interpolation="nearest",
        )

    else:
        ax.scatter(
            [p["x"] for p in points], [p["y"] for p in points], s=24, color=palette[0]
        )
        point_axes = {p["point_id"]: ax for p in points}
    if norm is not None and geo["mode"] != "choropleth":
        from matplotlib.cm import ScalarMappable

        fig.colorbar(
            ScalarMappable(norm=norm, cmap=cmap),
            ax=ax,
            label=geo.get("value_semantics", "value"),
        )
    ax.autoscale_view()
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title(spec.title or spec.kind)
    ax.set_xlabel(
        "x / longitude" if crs(geo["crs"]).is_geographic else "Easting (CRS unit)"
    )
    ax.set_ylabel(
        "y / latitude" if crs(geo["crs"]).is_geographic else "Northing (CRS unit)"
    )
    return [ax], point_axes
