.pragma library

// UX V2 aşama kimlikleri — navigasyon yardımcısı; zorunlu sihirbaz değil.
var stages = [
    { id: "goal", title: "Amaç ve kaynak", shortTitle: "Amaç", section: 0, pane: "", symbol: "home", tone: "warm" },
    { id: "load", title: "Yükle ve kontrol et", shortTitle: "Yükle", section: 1, pane: "import", symbol: "table", tone: "cyan" },
    { id: "columns", title: "Sütunları tanı", shortTitle: "Sütunlar", section: 1, pane: "profile", symbol: "table", tone: "cyan" },
    { id: "summary", title: "Temel veri özeti", shortTitle: "Özet", section: 1, pane: "describe", symbol: "table", tone: "cyan" },
    { id: "missing", title: "Eksik veri", shortTitle: "Eksik", section: 1, pane: "quality", symbol: "table", tone: "cyan" },
    { id: "explore", title: "Desenleri keşfet", shortTitle: "Keşfet", section: 3, pane: "", symbol: "chart", tone: "violet" },
    { id: "outliers", title: "Aykırı değerleri incele", shortTitle: "Aykırı", section: 2, pane: "", symbol: "prepare", tone: "violet" },
    { id: "prepare", title: "Veriyi hazırla", shortTitle: "Hazırla", section: 2, pane: "", symbol: "prepare", tone: "violet" },
    { id: "model", title: "Yöntem ve model", shortTitle: "Model", section: 5, pane: "", symbol: "model", tone: "violet" },
    { id: "report", title: "Bulguları anlat", shortTitle: "Rapor", section: 6, pane: "", symbol: "report", tone: "warm" }
]

function indexForSection(section, pane) {
    if (section === 1) {
        if (pane === "import") return 1
        if (pane === "describe") return 3
        if (pane === "quality") return 4
        if (pane === "values" || pane === "rows") return 2
        return 2
    }
    if (section === 0) return 0
    if (section === 3) return 5
    if (section === 2) return 7
    if (section === 4) return 5
    if (section === 5) return 8
    if (section === 6) return 9
    if (section === 7) return 0
    return 0
}

function stageAt(index) {
    if (index < 0 || index >= stages.length) return stages[0]
    return stages[index]
}
