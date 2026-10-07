import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "cleaningOptions"
    signal helpRequested(var origin, string context)
    property var kinds: ["fill", "missing_rows", "missing_columns", "dedup", "trim", "map_categories", "convert", "ordered_fill", "outlier"]
    property string kind: kinds[method.currentIndex]
    property var selected: []
    property var groups: []
    property var mapping: []
    property var advice: ({
        fill: "Eksikleri tamamlar; dağılım ve değişkenlik yapay biçimde değişebilir. Genel temizleme tam veriden öğrenir; ML pipeline doldurması ileride yalnız eğitim katında öğrenilmelidir.",
        missing_rows: "Eksik kayıtları çıkarır; kayıt sayısı ve temsil gücü azalabilir. Null ve NaN aynı değildir; kapsamı açık seçin.",
        missing_columns: "Eksikliği olan alanları çıkarır; o alandaki tüm bilgi kaybolur. Varsayılan yalnız tüm değerleri eksik alanları kaldırır.",
        dedup: "Tekrarları açık anahtara göre azaltır; aynı içerik meşru ayrı olay olabilir. Tutulacak kayıt seçtiğiniz sıranın ilk/son kaydıdır; görüntü sırası kullanılmaz.",
        trim: "Metnin başındaki/sonundaki boşluğu kırpar; anlamlı boşluklar kaybolabilir. Harf veya iç boşluk değişmez; boş metin null olmaz.",
        map_categories: "Yalnız açık eski → yeni çiftlerini eşler. Yazım veya harf büyüklüğü otomatik birleştirilmez; farklı kategoriler aynı hedefe bağlanırsa ayrım kaybolur.",
        convert: "Türü açık hedefe dönüştürür. Varsayılan hata tüm işlemi durdurur; açık yeni null seçimiyle hatalar sayılır. Sessiz yuvarlama, tarih düzeltme veya timezone silme yoktur.",
        ordered_fill: "Grup içindeki önceki/sonraki değeri taşır; gruplar arasında geçiş yapmaz. Geri doldurma veya azalan sırada ileri doldurma geleceği kullanabilir ve ML sızıntısı yaratabilir.",
        outlier: "IQR istatistiksel aday üretir; hatalı kayıt kanıtı değildir. Varsayılan yalnız işaretler. Filtreleme meşru uç gözlemleri kaldırabilir; sabit kolonda aday yoktur."
    })
    property string helpContext: kind === "fill" ? ["clean.fill.constant", "clean.fill.mean", "clean.fill.median", "clean.fill.mode"][fillMethod.currentIndex] : kind === "ordered_fill" ? ["clean.ordered-fill.forward", "clean.ordered-fill.backward"][direction.currentIndex] : ({fill: "clean.fill", missing_rows: "clean.missing-rows", missing_columns: "clean.missing-columns", dedup: "clean.dedup", trim: "clean.trim", map_categories: "clean.map-categories", convert: "clean.convert", ordered_fill: "clean.ordered-fill", outlier: "clean.outlier"})[kind]
    spacing: Theme.md
    function invalidate() { operations.discardPreview() }
    function preview() {
        let ids = (root.kind === "dedup" && allColumns.checked) ? dataView.datasetColumns.map(c => c.id) : (root.kind !== "outlier" && multi.checked) ? selected : [column.currentValue || ""]
        let missing = missingMode.currentIndex === 0 ? "null" : "null_nan"
        let p = {}
        if (kind === "fill") p = {method: ["constant", "mean", "median", "mode"][fillMethod.currentIndex], missing: missing, value: fillValue.text, tie_policy: modeTie.currentIndex === 0 ? "reject" : "choose"}
        else if (kind === "missing_rows" || kind === "missing_columns") p = {missing: missing, rule: missingRule.currentIndex === 0 ? "all" : "any"}
        else if (kind === "trim") p = {side: ["both", "left", "right"][trimSide.currentIndex]}
        else if (kind === "map_categories") p = {mapping: mapping, unmapped: unmapped.currentIndex === 0 ? "keep" : "reject"}
        else if (kind === "convert") {
            let target = {kind: ["String", "Int64", "UInt64", "Float64", "Boolean", "Decimal", "Date", "Datetime"][targetType.currentIndex]}
            if (target.kind === "Decimal") { target.precision = precision.value; target.scale = scale.value }
            if (target.kind === "Datetime") { target.unit = "us"; target.zone = timezone.text.length ? timezone.text : null }
            p = {target: target, on_error: onError.currentIndex === 0 ? "reject" : "null", date_format: dateFormat.text, dst_policy: ["reject", "earliest", "latest"][dst.currentIndex]}
        } else if (kind === "dedup" || kind === "ordered_fill") {
            p = {order_columns: orderColumn.currentValue ? [orderColumn.currentValue] : [], descending: descending.checked, tie_policy: "input_order_then_rowid", null_order: "reject"}
            if (kind === "dedup") { p.keep = keep.currentIndex === 0 ? "first" : "last"; p.equality = "v1:null_equal;nan_equal;zero_equal;decimal_numeric;timezone_instant;text_exact" }
            else { p.direction = direction.currentIndex === 0 ? "forward" : "backward"; p.missing = missing; p.group_columns = groups }
        } else if (kind === "outlier") {
            p = {action: outlierAction.currentIndex === 0 ? "mark" : "filter", multiplier: multiplier.text, flag_name: flagName.text, flag_column_id: operations.newColumnId()}
        }
        operations.previewCleaning(kind, JSON.stringify(ids), JSON.stringify(p), destination.currentIndex === 0 ? "chain" : "copy")
    }
    UiCombo { id: method; objectName: "cleaningMethod"; Layout.fillWidth: true; model: ["Eksik değer doldur", "Eksik satır kaldır", "Eksik sütun kaldır", "Tekrar kaldır", "Metin kırp", "Kategori eşle", "Tür / tarih dönüştür", "Grup içinde ileri / geri doldur", "Aykırı adayı işaretle / filtrele"]; enabled: !operations.busy; onActivated: { root.selected = []; root.groups = []; allColumns.checked = false; multi.checked = false; root.invalidate() } }
    Label { text: root.advice[root.kind]; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
    Label { text: "İşlem hedefi" }
    UiCombo { id: destination; objectName: "cleaningDestination"; Layout.fillWidth: true; model: ["Mevcut zincirde yeni sürüm", "Ayrı kopya dataset'te yeni zincir"]; onActivated: root.invalidate() }
    Label { text: destination.currentIndex === 0 ? "Eski sürüm korunur; çalışma verisi yeni sürüme geçer." : "Mevcut dataset değişmez; ayrı dataset seçilir. Kopyada geri alma, kopyanın başlangıcına döner."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    CheckBox { id: allColumns; objectName: "cleaningAllColumns"; text: "Tüm veri sütunlarını anahtar olarak kullan"; visible: root.kind === "dedup"; onToggled: root.invalidate() }
    CheckBox { id: multi; text: "Birden çok sütun seç"; visible: root.kind !== "outlier" && !allColumns.checked; onToggled: root.invalidate() }
    UiCombo { id: column; objectName: "cleaningColumn"; model: dataView.datasetColumns; textRole: "name"; valueRole: "id"; Layout.fillWidth: true; visible: !multi.checked && !(allColumns.checked && root.kind === "dedup"); onActivated: root.invalidate() }
    Repeater {
        model: multi.checked && root.kind !== "outlier" && !allColumns.checked ? dataView.datasetColumns : []
        delegate: CheckBox {
            required property var modelData
            text: modelData.name; checked: root.selected.indexOf(modelData.id) >= 0
            onToggled: { let ids = root.selected.filter(id => id !== modelData.id); if (checked) ids.push(modelData.id); root.selected = ids; root.invalidate() }
        }
    }
    UiCombo { id: missingMode; objectName: "cleaningMissing"; model: ["Yalnız null — eksik değer", "Null ve NaN — açık birlikte seçim"]; Layout.fillWidth: true; visible: ["fill", "missing_rows", "missing_columns", "ordered_fill"].indexOf(root.kind) >= 0; onActivated: root.invalidate() }
    UiCombo { id: missingRule; model: ["Seçili alanların / değerlerin tümü eksikse", "Seçili alanların / değerlerin herhangi biri eksikse"]; Layout.fillWidth: true; visible: root.kind === "missing_rows" || root.kind === "missing_columns"; onActivated: root.invalidate() }
    ColumnLayout {
        visible: root.kind === "fill"; Layout.fillWidth: true
        UiCombo { id: fillMethod; objectName: "cleaningFillMethod"; model: ["Sabit değer", "Ortalama", "Medyan", "En sık değer — mod"]; Layout.fillWidth: true; onActivated: root.invalidate() }
        Label { text: "Sabit değer veya eşit modda seçilecek değer"; visible: fillMethod.currentIndex === 0 || fillMethod.currentIndex === 3 }
        TextField { id: fillValue; objectName: "cleaningValue"; Accessible.name: "Doldurma değeri"; maximumLength: 4096; Layout.fillWidth: true; visible: fillMethod.currentIndex === 0 || fillMethod.currentIndex === 3; onTextEdited: root.invalidate() }
        UiCombo { id: modeTie; objectName: "cleaningModeTie"; model: ["Mod eşitliğinde durdur", "Yazdığım mod adayını seç"]; visible: fillMethod.currentIndex === 3; Layout.fillWidth: true; onActivated: root.invalidate() }
        Label { text: "Tümü eksikse ortalama/medyan/mod durur; sabit seçilebilir. Kesirli sonuç tam sayı veya decimal ölçeğine tam uymuyorsa işlem reddedilir. Önce açık tür dönüşümü seçin. Sayısal kimliklere ortalama uygulamayın."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    }
    UiCombo { id: trimSide; model: ["İki uç", "Sol", "Sağ"]; visible: root.kind === "trim"; Layout.fillWidth: true; onActivated: root.invalidate() }
    ColumnLayout {
        visible: root.kind === "map_categories"; Layout.fillWidth: true
        TextField { id: fromValue; objectName: "cleaningFrom"; placeholderText: "Eski kategori (tam metin)"; Accessible.name: "Eski kategori"; Layout.fillWidth: true }
        TextField { id: toValue; objectName: "cleaningTo"; placeholderText: "Yeni kategori"; Accessible.name: "Yeni kategori"; Layout.fillWidth: true }
        UiButton { objectName: "cleaningAddMapping"; text: "Eşleme çiftini ekle"; onClicked: { root.mapping = root.mapping.concat([{from: fromValue.text, to: toValue.text}]); root.invalidate() } }
        Repeater { model: root.mapping; delegate: Label { required property var modelData; text: modelData.from + " → " + modelData.to; Layout.fillWidth: true; wrapMode: Text.WordWrap } }
        UiButton { text: "Eşleme listesini temizle"; onClicked: { root.mapping = []; root.invalidate() } }
        UiCombo { id: unmapped; model: ["Eşlenmeyeni koru", "Eşlenmeyen varsa durdur"]; Layout.fillWidth: true; onActivated: root.invalidate() }
    }
    ColumnLayout {
        visible: root.kind === "convert"; Layout.fillWidth: true
        UiCombo { id: targetType; objectName: "cleaningTarget"; model: ["Metin", "Tam sayı — Int64", "Pozitif tam sayı — UInt64", "Kayan sayı — Float64", "Doğru/yanlış", "Kesin ondalık — Decimal", "Tarih", "Tarih ve saat"]; Layout.fillWidth: true; onActivated: root.invalidate() }
        Label { text: "Decimal toplam basamak / ondalık basamak"; visible: targetType.currentIndex === 5 }
        RowLayout { visible: targetType.currentIndex === 5; SpinBox { id: precision; from: 1; to: 38; value: 38; onValueModified: root.invalidate() } SpinBox { id: scale; from: 0; to: precision.value; value: 6; onValueModified: root.invalidate() } }
        Label { text: "Tarih biçimi (boş: ISO); örnek %Y-%m-%d"; visible: targetType.currentIndex >= 6 }
        TextField { id: dateFormat; objectName: "cleaningDateFormat"; Accessible.name: "Tarih biçimi"; Layout.fillWidth: true; visible: targetType.currentIndex >= 6; maximumLength: 100; onTextEdited: root.invalidate() }
        TextField { id: timezone; placeholderText: "IANA timezone (örn. Europe/Istanbul); boş: saat dilimsiz"; Accessible.name: "Saat dilimi"; Layout.fillWidth: true; visible: targetType.currentIndex === 7; maximumLength: 100; onTextEdited: root.invalidate() }
        UiCombo { id: dst; model: ["DST belirsizliğinde durdur", "Çift zamanın erken anını seç", "Çift zamanın geç anını seç"]; visible: targetType.currentIndex === 7; Layout.fillWidth: true; onActivated: root.invalidate() }
        UiCombo { id: onError; objectName: "cleaningOnError"; model: ["Hata varsa bütün işlemi durdur", "Hataları açıkça yeni null yap ve raporla"]; Layout.fillWidth: true; onActivated: root.invalidate() }
        Label { text: "Var olmayan DST saati düzeltilmez. 0.1 gibi binary float'ta tam temsil edilmeyen kesin değerler için Decimal seçin. ns → us hassasiyet kaybı ve saat dilimi silme reddedilir."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    }
    ColumnLayout {
        visible: root.kind === "ordered_fill" || root.kind === "dedup"; Layout.fillWidth: true
        Label { text: "Tutulacak kaydı / zaman akışını belirleyen sıra sütunu"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        UiCombo { id: orderColumn; objectName: "cleaningOrder"; model: dataView.datasetColumns; textRole: "name"; valueRole: "id"; currentIndex: -1; onModelChanged: currentIndex = -1; Layout.fillWidth: true; onActivated: root.invalidate() }
        CheckBox { id: descending; text: "Azalan sıra (geleceği kullanma riskini kontrol edin)"; onToggled: root.invalidate() }
        UiCombo { id: keep; objectName: "cleaningKeep"; model: ["Seçilen sıranın ilk kaydını tut", "Seçilen sıranın son kaydını tut"]; visible: root.kind === "dedup"; Layout.fillWidth: true; onActivated: root.invalidate() }
        Label { text: "Eşit sıra anahtarında özgün giriş sırası + RowId. Null/NaN/inf sıra anahtarı reddedilir. Dedup: null=null, NaN=NaN fakat null≠NaN; +0=−0; decimal sayısal; timezone aynı an; metin tam eşitlik, otomatik kırpma yok."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        UiCombo { id: direction; objectName: "cleaningDirection"; model: ["İleri — önceki değer", "Geri — sonraki değer"]; visible: root.kind === "ordered_fill"; Layout.fillWidth: true; onActivated: root.invalidate() }
        Label { text: "Grup sütunlarını açıkça seç (en az bir)"; visible: root.kind === "ordered_fill"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        Repeater {
            model: root.kind === "ordered_fill" ? dataView.datasetColumns : []
            delegate: CheckBox {
                required property var modelData
                text: modelData.name; checked: root.groups.indexOf(modelData.id) >= 0
                onToggled: { let ids = root.groups.filter(id => id !== modelData.id); if (checked) ids.push(modelData.id); root.groups = ids; root.invalidate() }
            }
        }
    }
    ColumnLayout {
        visible: root.kind === "outlier"; Layout.fillWidth: true
        UiCombo { id: outlierAction; objectName: "cleaningOutlierAction"; model: ["Yalnız aday sütunuyla işaretle", "Adayları açık seçimle filtrele"]; Layout.fillWidth: true; onActivated: root.invalidate() }
        Label { text: "IQR çarpanı" }
        TextField { id: multiplier; text: "1.5"; Accessible.name: "IQR çarpanı"; Layout.fillWidth: true; onTextEdited: root.invalidate() }
        TextField { id: flagName; text: "Aykırı_adayı"; Accessible.name: "Aday sütunu adı"; visible: outlierAction.currentIndex === 0; Layout.fillWidth: true; onTextEdited: root.invalidate() }
    }
    UiButton { text: "Yöntem ne işe yarar?"; onClicked: root.helpRequested(this, root.helpContext) }
}
