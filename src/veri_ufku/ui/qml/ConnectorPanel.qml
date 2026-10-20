import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "connectorPanel"
    property string helpContext: "connector-connection"
    property bool expanded: false
    readonly property string kind: kindInput.currentText
    readonly property bool databaseSource: ["postgresql", "mysql", "mariadb", "duckdb"].indexOf(kind) >= 0
    readonly property bool sqlServer: ["postgresql", "mysql", "mariadb"].indexOf(kind) >= 0
    Layout.fillWidth: true
    spacing: Theme.md
    function request() {
        return JSON.stringify({kind: kind, endpoint: endpointInput.text, database: databaseInput.text,
            user: userInput.text, port: portInput.value, credential_ref: referenceInput.text, ca_file: caInput.text,
            schema: schemaInput.text, table: tableInput.text, key_column: keyInput.text,
            columns: columnsInput.text.length ? columnsInput.text.split(",").map(x => x.trim()) : [],
            filters: JSON.parse(filtersInput.text || "[]"), timeout: timeoutInput.value,
            max_rows: rowsInput.value, max_bytes: bytesInput.value * 1024 * 1024,
            max_pages: pagesInput.value, terms_acknowledged: terms.checked,
            allow_loopback_http: loopback.checked, field_mapping: JSON.parse(mappingInput.text || "{}"),
            bucket: bucketInput.text, object_key: objectInput.text, version_id: versionInput.text,
            object_format: objectFormat.currentText, snapshot_header: snapshotInput.text,
            attribution: attributionInput.text, cache_policy: cacheInput.checked ? "project-permitted" : "", tile_z: tileZ.value, tile_x: tileX.value, tile_y: tileY.value, records_field: recordsInput.text, next_field: nextInput.text, total_field: totalInput.text})
    }
    function submit(tables) {
        try {
            formError.text = ""
            if (tables) imports.listTables(request()); else imports.connectSource(request())
        } catch (error) { formError.text = "Filtre/eşleme JSON metnini denetleyin." }
    }
    UiButton { objectName: "connectorToggle"; text: panel.expanded ? "Bağlantı kaynağı · açık" : "Veritabanı / API / nesne depolama"; tone: "cyan"; onClicked: panel.expanded = !panel.expanded }
    ColumnLayout {
        visible: panel.expanded
        enabled: !imports.busy
        Layout.fillWidth: true
        spacing: Theme.sm
        UiLabel { text: "Bağlantı yalnız düğmeyle başlar. Veriyi önce yerel değişmez kopyaya alır; içe aktarma bu kopyadan yapılır. Temel uygulama internet istemez."; wrapMode: Text.Wrap; Layout.fillWidth: true }
        UiCombo { id: kindInput; objectName: "connectorKind"; accessibleLabel: "Bağlantı türü"; model: imports.connectorKinds; Layout.fillWidth: true; onActivated: { imports.connectionEdited(); referenceInput.text = ""; secretInput.text = ""; schemaInput.text = currentText === "duckdb" ? "main" : currentText === "mysql" || currentText === "mariadb" ? databaseInput.text : "public" } }
        UiLabel { text: panel.kind === "duckdb" ? "Yerel DuckDB dosyası" : "Sunucu / HTTPS URL"; Layout.fillWidth: true }
        ConnectorField { id: endpointInput; objectName: "connectorEndpoint"; Accessible.name: "Sunucu veya kaynak URL"; placeholderText: panel.kind === "duckdb" ? "/home/…/kaynak.duckdb" : panel.databaseSource ? "db.example.org" : "https://api.example.org/data"; Layout.fillWidth: true; enabled: !imports.busy }
        ConnectorField { id: databaseInput; objectName: "connectorDatabase"; Accessible.name: "Veritabanı adı"; visible: panel.sqlServer; placeholderText: "Veritabanı"; Layout.fillWidth: true }
        UiSpinBox { onValueModified: imports.connectionEdited(); id: portInput; objectName: "connectorPort"; Accessible.name: "Veritabanı portu · sıfır varsayılan"; visible: panel.sqlServer; from: 0; to: 65535; value: 0; Layout.fillWidth: true }
        ConnectorField { id: userInput; objectName: "connectorUser"; Accessible.name: "Salt okunur veritabanı kullanıcısı"; visible: panel.sqlServer; placeholderText: "Yalnız okuma yetkili kullanıcı"; Layout.fillWidth: true }
        ConnectorField { id: referenceInput; objectName: "connectorCredentialRef"; Accessible.name: "Keyring credential referansı"; placeholderText: "Keyring referansı · parola burada saklanmaz"; Layout.fillWidth: true }
        ConnectorField { id: secretInput; objectName: "connectorSecret"; Accessible.name: "Sistem keyring'ine kaydedilecek gizli değer"; placeholderText: "Parola / bearer token / S3 credential JSON"; echoMode: TextInput.Password; Layout.fillWidth: true }
        UiButton { objectName: "connectorSaveSecret"; text: "Gizli değeri sistem keyring'ine kaydet"; enabled: !imports.busy && referenceInput.text.length > 0 && secretInput.text.length > 0; onClicked: { imports.saveCredential(referenceInput.text, secretInput.text); secretInput.text = "" } }
        ConnectorField { id: caInput; objectName: "connectorCA"; Accessible.name: "TLS CA sertifika dosyası"; placeholderText: "CA dosyası · boşsa sistem CA · sertifika/hostname doğrulanır"; Layout.fillWidth: true; visible: panel.kind !== "duckdb" }
        UiLabel { text: "SQL metni çalıştırılmaz: ordinary tablo/sütun seçimi ve bağlı filtre değerleriyle salt okunur sorgu oluşturulur. PostgreSQL repeatable-read, MySQL/MariaDB InnoDB snapshot; yönetici/yazma yetkili hesap reddedilir."; visible: panel.databaseSource; wrapMode: Text.Wrap; Layout.fillWidth: true }
        UiButton { objectName: "connectorListTables"; text: "Bağlan ve tablo/şema listesini oku"; visible: panel.databaseSource; enabled: !imports.busy && terms.checked; onClicked: panel.submit(true) }
        UiCombo { objectName: "connectorTableChoice"; accessibleLabel: "Okunabilir tablo ve şema"; visible: panel.databaseSource && imports.connectorTables.length > 0; model: imports.connectorTables.map(x => x.schema + "." + x.table); Layout.fillWidth: true; onActivated: { imports.connectionEdited(); schemaInput.text = imports.connectorTables[currentIndex].schema; tableInput.text = imports.connectorTables[currentIndex].table } }
        ConnectorField { id: schemaInput; objectName: "connectorSchema"; Accessible.name: "Kaynak şeması"; visible: panel.databaseSource; text: "public"; placeholderText: "Şema"; Layout.fillWidth: true }
        ConnectorField { id: tableInput; objectName: "connectorTable"; Accessible.name: "Kaynak tablosu"; visible: panel.databaseSource; placeholderText: "Tablo"; Layout.fillWidth: true }
        ConnectorField { id: keyInput; objectName: "connectorKey"; Accessible.name: "Benzersiz kaynak kayıt anahtarı"; text: "id"; placeholderText: "Benzersiz, null olmayan kaynak anahtarı"; visible: panel.kind !== "s3"; Layout.fillWidth: true }
        ConnectorField { id: columnsInput; objectName: "connectorColumns"; Accessible.name: "Sorgu sütunları"; visible: panel.databaseSource; placeholderText: "Sütunlar · virgülle · boşsa tüm sütunlar"; Layout.fillWidth: true }
        ConnectorField { id: filtersInput; objectName: "connectorFilters"; Accessible.name: "Bağlı sorgu parametreleri"; property string helpContext: "connector-query"; visible: panel.databaseSource; text: "[]"; placeholderText: '[{"column":"amount","op":">=","value":10}]'; Layout.fillWidth: true }
        UiLabel { text: "HTTP yalnız GET/JSON ve same-origin next URL sayfalaması. Bearer keyring referansı desteklenir; interactive OAuth/cookie oturumu yok. Servis koşullarını kendi sağlayıcınızdan denetleyin. Token/total yoksa sayfalar tek zamanlı snapshot değildir; atlanan kayıt garantisi verilemez."; visible: (panel.kind === "http" || panel.kind === "geocoding"); wrapMode: Text.Wrap; Layout.fillWidth: true }
        ConnectorField { id: recordsInput; objectName: "connectorRecordsField"; Accessible.name: "API kayıt dizisi alanı"; text: "items"; visible: (panel.kind === "http" || panel.kind === "geocoding"); Layout.fillWidth: true }
        ConnectorField { id: nextInput; objectName: "connectorNextField"; Accessible.name: "API sonraki sayfa alanı"; text: "next"; visible: (panel.kind === "http" || panel.kind === "geocoding"); Layout.fillWidth: true }
        ConnectorField { id: totalInput; objectName: "connectorTotalField"; Accessible.name: "API toplam kayıt alanı"; text: "total"; visible: (panel.kind === "http" || panel.kind === "geocoding"); Layout.fillWidth: true }
        ConnectorField { id: snapshotInput; objectName: "connectorSnapshotHeader"; Accessible.name: "API snapshot header adı"; property string helpContext: "connector-snapshot"; placeholderText: "Snapshot header · sağlayıcı garantisi yoksa boş"; visible: (panel.kind === "http" || panel.kind === "geocoding"); Layout.fillWidth: true }
        ConnectorField { id: mappingInput; objectName: "connectorFieldMapping"; Accessible.name: "API alan eşleme JSON"; text: "{}"; visible: (panel.kind === "http" || panel.kind === "geocoding"); Layout.fillWidth: true }
        ConnectorField { id: bucketInput; objectName: "connectorBucket"; Accessible.name: "Nesne depolama bucket"; visible: panel.kind === "s3"; placeholderText: "Bucket"; Layout.fillWidth: true }
        ConnectorField { id: objectInput; objectName: "connectorObject"; Accessible.name: "Nesne anahtarı"; visible: panel.kind === "s3"; placeholderText: "Nesne anahtarı"; Layout.fillWidth: true }
        ConnectorField { id: versionInput; objectName: "connectorVersion"; Accessible.name: "Nesne sürüm kimliği"; visible: panel.kind === "s3"; placeholderText: "VersionId · boşsa HEAD/IfMatch"; Layout.fillWidth: true }
        UiCombo { id: objectFormat; objectName: "connectorObjectFormat"; accessibleLabel: "Nesne veri biçimi"; model: ["parquet", "jsonl", "csv", "ipc"]; visible: panel.kind === "s3"; Layout.fillWidth: true }
        UiLabel { text: "S3 tek nesne GET/HEAD; SigV4 veya unsigned public okuma. Keyring JSON: access_key, secret_key, isteğe bağlı session_token. Otomatik ortam credential zinciri, listing ve upload yok. VersionId/IfMatch ile nesne sabitlenir."; visible: panel.kind === "s3"; wrapMode: Text.Wrap; Layout.fillWidth: true }
        UiLabel { text: "Timeout (s), sorgu/API satır limiti, içerik (MiB), API sayfa limiti"; wrapMode: Text.Wrap; Layout.fillWidth: true }
        UiSpinBox { onValueModified: imports.connectionEdited(); id: timeoutInput; objectName: "connectorTimeout"; Accessible.name: "Bağlantı timeout saniyesi"; from: 1; to: 60; value: 10; Layout.fillWidth: true }
        UiSpinBox { onValueModified: imports.connectionEdited(); id: rowsInput; objectName: "connectorRowLimit"; Accessible.name: "Bağlantı kayıt sınırı"; from: 1; to: 1000000; value: 100000; Layout.fillWidth: true }
        UiSpinBox { onValueModified: imports.connectionEdited(); id: bytesInput; objectName: "connectorByteLimit"; Accessible.name: "Bağlantı içerik sınırı MiB"; from: 1; to: 512; value: 64; Layout.fillWidth: true }
        UiSpinBox { onValueModified: imports.connectionEdited(); id: pagesInput; objectName: "connectorPageLimit"; Accessible.name: "API sayfa sınırı"; property string helpContext: "connector-pagination"; from: 1; to: 1000; value: 100; Layout.fillWidth: true; visible: (panel.kind === "http" || panel.kind === "geocoding") }
        UiCheckBox { id: loopback; objectName: "connectorLoopback"; text: "Yalnız localhost test sunucusu için HTTP'ye izin ver"; visible: (panel.kind === "http" || panel.kind === "geocoding") || panel.kind === "s3"; Layout.fillWidth: true }
        ConnectorField { id:attributionInput;objectName:"geoOnlineAttribution";Accessible.name:"Tile geocoding attribution";visible:panel.kind==="tile"||panel.kind==="geocoding";placeholderText:"Kaynak / attribution / licence";Layout.fillWidth:true }
        UiCheckBox {id:cacheInput;objectName:"geoOnlineCache";text:"Sağlayıcı koşulları bu snapshot'ın projede saklanmasına ve exportuna izin veriyor";visible:panel.kind==="tile"||panel.kind==="geocoding";Layout.fillWidth:true}
        UiSpinBox {id:tileZ;objectName:"geoTileZ";Accessible.name:"Tile XYZ zoom";from:0;to:18;value:0;visible:panel.kind==="tile";Layout.fillWidth:true}
        UiSpinBox {id:tileX;objectName:"geoTileX";Accessible.name:"Tile XYZ x";from:0;to:262143;value:0;visible:panel.kind==="tile";Layout.fillWidth:true}
        UiSpinBox {id:tileY;objectName:"geoTileY";Accessible.name:"Tile XYZ y";from:0;to:262143;value:0;visible:panel.kind==="tile";Layout.fillWidth:true}
        UiLabel {text:"Online açık GET eylemi; yerel harita internetsiz. Public tek XYZ tile256/512; color band/window preview, RGB basemap compositor yok. Geocoding id/record-list JSON ve alan eşleme; otomatik adres gönderimi yok. Tile auth yok; geocoding yalnız mevcut keyring bearer. Attribution/cache koşulları ve API rate limit sağlayıcıya bağlı.";visible:panel.kind==="tile"||panel.kind==="geocoding";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiCheckBox { id: terms; objectName: "connectorTerms"; text: "Bu kaynağa okuma bağlantısı başlatmayı ve sağlayıcı kullanım koşullarını onaylıyorum"; Layout.fillWidth: true }
        UiLabel { id: formError; text: ""; visible: text.length > 0; color: Theme.error; wrapMode: Text.Wrap; Layout.fillWidth: true }
        UiButton { objectName: "connectorRead"; text: panel.databaseSource ? "Sorguyu oku ve snapshot önizle" : "Kaynağı oku ve snapshot önizle"; enabled: !imports.busy && terms.checked; tone: "cyan"; onClicked: panel.submit(false) }
        UiLabel { visible: imports.formatMetadata.length > 0 && ["postgresql", "mysql", "mariadb", "duckdb", "http", "s3", "tile", "geocoding"].indexOf(imports.formatId) >= 0; text: imports.formatMetadata; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
    }
}
