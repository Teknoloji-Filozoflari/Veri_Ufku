"""Local vector figure composer and frozen interactive SVG adapter."""

import base64
import copy
import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.text import Text

from veri_ufku.charts.dashboard import FigureSpec, validate_axis_policy
from veri_ufku.charts.plot import PALETTE, render
from veri_ufku.exports.files import publish
from veri_ufku.importers.delimited import Control
from veri_ufku.storage.project_model import ProjectError

PALETTES = {
    "accessible": PALETTE,
    "colorblind": ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"),
    "grayscale": ("#222222", "#555555", "#888888", "#BBBBBB"),
}
FONTS = ("DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono")


def build(spec, chart_results, control=None):
    control = control or Control()
    spec = spec if isinstance(spec, FigureSpec) else FigureSpec(**spec)
    spec.validate()
    if spec.font not in FONTS or len(chart_results) != len(spec.chart_result_ids):
        raise ProjectError("Figure font veya seçili grafik sayısı geçersiz.")
    if spec.width * spec.height * 120**2 * 16 > control.budget.ram_bytes // 2:
        raise ProjectError("Figure piksel/boyut RAM bütçesini aşıyor.")
    fig = Figure(figsize=(spec.width, spec.height), dpi=120, facecolor="white")
    FigureCanvasAgg(fig)
    # Reserve parent space for shared legend and caption: panel footers live inside
    # their SubFigures and must never occupy the same coordinates as this context.
    grid = fig.add_gridspec(
        spec.rows + 1,
        spec.columns,
        height_ratios=[0.77 / spec.rows] * spec.rows + [0.23],
    )
    panels = [
        fig.add_subfigure(grid[row, col])
        for row in range(spec.rows)
        for col in range(spec.columns)
    ]
    group_names = list(
        dict.fromkeys(
            g
            for result in chart_results
            for g in result.get("details", {}).get("group_order", [])
            + result.get("details", {}).get("series_order", [])
            + [p.get("group", "") for p in result.get("points", [])]
            if g
        )
    )
    colors = {
        g: PALETTES[spec.palette][i % len(PALETTES[spec.palette])]
        for i, g in enumerate(group_names)
    }
    legends, notices = {}, []
    for expected, result, panel in zip(spec.chart_result_ids, chart_results, panels):
        control.check()
        if result.get("id") != expected or not result.get("points"):
            raise ProjectError(
                "Figure kayıtlı hesaplanmış grafik koordinatları ister; raster panel vektör gibi sunulmaz."
            )
        validate_axis_policy(result.get("spec", {}))
        data = copy.deepcopy(result)
        data["spec"].update(
            font=spec.font,
            font_size=spec.font_size,
            palette="accessible" if spec.palette == "colorblind" else spec.palette,
        )
        groups = (
            data.get("details", {}).get("series_order")
            or data.get("details", {}).get("group_order")
        ) or list(dict.fromkeys(p.get("group", "") for p in data["points"]))
        axes = render(
            data,
            ".",
            control=control,
            figure=panel,
            palette_override=[colors.get(g, PALETTES[spec.palette][0]) for g in groups]
            + list(PALETTES[spec.palette]) * 2,
        )
        # Keep all explicit legends, including twinx/composition warning legends.
        for ax in panel.axes:
            handles, labels = ax.get_legend_handles_labels()
            for handle, label in zip(handles, labels):
                if spec.shared_legend and label in legends:
                    # A label may have incompatible semantics in separate datasets.
                    previous_color = str(
                        getattr(legends[label], "get_color", lambda: "")()
                    )
                    new_color = str(getattr(handle, "get_color", lambda: "")())
                    if previous_color != new_color:
                        raise ProjectError(
                            "Ortak legend aynı etiket için farklı kodlama içeriyor; ortak legend seçimini kapatın."
                        )
                legends.setdefault(label, handle)
            if spec.shared_legend and handles and ax.get_legend() is not None:
                ax.get_legend().remove()
        if len(panel.axes) > len(axes):
            # Colorbars also add axes; explicit twinx are identifiable by shared x.
            twins = [
                ax
                for ax in panel.axes
                if any(
                    ax is not other and ax.get_shared_x_axes().joined(ax, other)
                    for other in panel.axes
                )
            ]
            if twins:
                panel.text(
                    0.02,
                    0.96,
                    "ÇİFT EKSEN: ayrı ölçekler; eğim/büyüklük doğrudan karşılaştırılmaz.",
                    fontsize=spec.font_size - 1,
                )
                notices.append("Çift eksen açık uyarı ve ayrı legend ile gösterilir.")
        context = data.get("dashboard_context", {})
        if context.get("freshness") == "stale":
            panel.text(0.02, 0.92, "ESKİ SÜRÜM · güncel veri değildir", color="#991B1B")
    if spec.shared_legend and legends:
        fig.legend(
            list(legends.values()),
            list(legends),
            loc="lower center",
            bbox_to_anchor=(0.5, 0.105),
            ncol=min(4, len(legends)),
        )
    context = " | ".join(
        (
            spec.caption or "Caption: belirtilmedi",
            "Unit: " + (spec.unit or "grafik eksenlerine bakın"),
            "Source: " + (spec.source or "bağlı dataset snapshotları"),
            "Statik dışa aktarım etkileşimi korumaz.",
        )
    )
    from textwrap import wrap

    fig.text(
        0.02,
        0.02,
        "\n".join(wrap(context, max(40, int(spec.width * 12)))),
        fontsize=spec.font_size,
        va="bottom",
    )
    for text in fig.findobj(match=Text):
        text.set_fontfamily(spec.font)
    return fig, {
        "font": spec.font,
        "font_size": spec.font_size,
        "legend": list(legends),
        "notices": notices,
        "context": context,
        "vector_content": True,
        "interactive": False,
    }


def compose(
    spec,
    chart_results,
    destination,
    fmt,
    project_root=None,
    workspace=None,
    control=None,
):
    control = control or Control()
    if (
        fmt not in ("svg", "png", "pdf")
        or Path(destination).suffix.lower() != "." + fmt
    ):
        raise ProjectError(
            "Statik figure için SVG/PNG/PDF seçin; HTML yerel SVG adapter ile ayrıca üretilir."
        )
    fig, metadata = build(spec, chart_results, control)
    path = Path(destination)
    if path.exists() or path.is_symlink():
        raise ProjectError("Mevcut çıktı korunur; yeni dosya seçin.")
    if project_root is not None:
        temporary = Path(workspace) / ("figure." + fmt)
        fig.savefig(
            temporary,
            format=fmt,
            metadata={"Creator": "Veri_Ufku local figure composer"},
        )
        published = publish(temporary, destination, project_root, control)
    else:
        # Standalone API also uses exclusive publication, never overwrites a file.
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory) / ("figure." + fmt)
            fig.savefig(temporary, format=fmt)
            published = publish(temporary, destination, directory, control)
    return {
        **metadata,
        **published,
        "format": fmt,
        "notice": "Statik dışa aktarım etkileşimi korumaz.",
    }


def interactive_export(result, destination, project_root, workspace, control=None):
    control = control or Control()
    if Path(destination).suffix.lower() != ".html":
        raise ProjectError("Etkileşimli çıktı için yeni .html dosyası seçin.")
    payload = {
        "widgets": [],
        "mappings": result["spec"]["filter_mappings"],
        "keys": result.get("mapping_keys", {}),
    }
    panels = []
    for widget in result["widgets"]:
        control.check()
        ident = widget["id"]
        payload["widgets"].append(
            {key: widget[key] for key in ("id", "dataset_version", "row_ids")}
        )
        data = payload["widgets"][-1]
        data.update(
            memberships=widget.get("memberships", {}),
            render=widget.get("chart", {}).get("render", {}),
        )
        body = ""
        if widget.get("image_path"):
            svg = Path(widget["chart"]["paths"]["svg"]).read_bytes()
            body = (
                '<img alt="Grafik · noktaya/sütuna tıklayarak satır seçin" src="data:image/svg+xml;base64,'
                + base64.b64encode(svg).decode()
                + '">'
            )
        elif widget["kind"] == "table":
            body = (
                "<table><thead><tr>"
                + "".join(
                    "<th>" + html.escape(c["name"]) + "</th>" for c in widget["columns"]
                )
                + "</tr></thead><tbody>"
            )
            for row in widget["rows"]:
                body += (
                    '<tr tabindex="0" data-row="'
                    + html.escape(row["row_id"], quote=True)
                    + '">'
                    + "".join(
                        "<td>" + html.escape(cell) + "</td>" for cell in row["cells"]
                    )
                    + "</tr>"
                )
            body += "</tbody></table>"
        elif widget["kind"] == "kpi":
            body = (
                "<p>"
                + html.escape(str(widget["kpi"]["value"]))
                + "</p><p>"
                + html.escape(widget["kpi"]["definition"])
                + "</p>"
            )
        else:
            body = (
                "<p>"
                + html.escape(widget.get("text", widget.get("empty", "")))
                + "</p>"
            )
        panels.append(
            '<section data-widget="'
            + html.escape(ident, quote=True)
            + '" style="grid-row:'
            + str(widget["grid"][0] + 1)
            + " / span "
            + str(widget["grid"][2])
            + ";grid-column:"
            + str(widget["grid"][1] + 1)
            + " / span "
            + str(widget["grid"][3])
            + '"><h2>'
            + html.escape(widget["title"] or widget["kind"])
            + "</h2><p>"
            + html.escape(widget["status_text"] + " | " + widget["dataset_version"])
            + '</p><p class="selection"></p>'
            + body
            + "</section>"
        )
    script = (Path(__file__).parent / "local_svg_adapter.js").read_text()
    serialized = (
        json.dumps(payload, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace("&", "\\u0026")
    )
    font_data = base64.b64encode(
        (Path(__file__).parents[1] / "assets/fonts/DejaVuSans.ttf").read_bytes()
    ).decode()
    figure = result["spec"].get("figure", {})
    export_context = " | ".join(
        (
            "Caption: " + (figure.get("caption") or "belirtilmedi"),
            "Unit: " + (figure.get("unit") or "grafik eksenlerine bakın"),
            "Source: " + (figure.get("source") or "bağlı dataset snapshotları"),
        )
    )
    document = (
        "<!doctype html><html lang=\"tr\"><meta charset=\"utf-8\"><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; img-src data:; font-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'\"><title>"
        + html.escape(result["spec"]["name"])
        + "</title><style>@font-face{font-family:DashboardFont;src:url(data:font/ttf;base64,"
        + font_data
        + ")}body{font-family:DashboardFont,sans-serif;margin:2em}main{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));grid-auto-rows:minmax(70px,auto);gap:1em}section{border:1px solid #777;padding:1em;overflow:auto;position:relative}img{width:100%;cursor:crosshair}td,th{padding:.4em;border:1px solid #aaa}tr.selected{background:#ffdba8}.selection{font-weight:bold}</style><h1>"
        + html.escape(result["spec"]["name"])
        + "</h1><p>"
        + html.escape(export_context)
        + '</p><p>Yerel SVG adapter/v1 · dondurulmuş snapshot ve kayıtlı filtreler; yeni veri alınmaz. Seçim tablolar/grafikler arasında RowId ve açık eşlemeyle bağlanır; agregasyonlar değişmez.</p><button id="clear">Seçimi temizle</button><main>'
        + "".join(panels)
        + "</main><details><summary>Veri, filtre ve kaynak bağlamı</summary><pre>"
        + html.escape(json.dumps(result["spec"], ensure_ascii=False, indent=2))
        + '</pre></details><script type="application/json" id="dashboard-data">'
        + serialized
        + "</script><script>"
        + script
        + "</script></html>"
    )
    path = Path(workspace) / "dashboard.html"
    path.write_text(document)
    return {
        **publish(path, destination, project_root, control),
        "interactive": True,
        "adapter": "local-svg/v1",
        "network": False,
    }
