import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id:panel
    objectName:"guidePanel"
    signal helpRequested(var origin, string context)
    function chooseExample(kind) { exampleKind = kind; exampleFolder.open() }
    property bool compactHome: false
    property string exampleKind:"sales"
    property var instructions:[
        "Dosya seçin, önizleme ve türleri kontrol edip İçe aktar seçin. Önce Başlangıç → Yeni proje ile proje oluşturun. Kaynak dosyanız korunur.",
        "Bir sütun seçin; profil kapsamını belirleyip Profili hesapla seçin. Profil kaydını taslağa ekleyebilirsiniz. Kimlik sütununu ölçüm gibi yorumlamayın.",
        "Kaliteyi tara seçin. Bulguların gerekçesini okuyun; raporu taslağa ekleyin. Öneri veriyi kendiliğinden değiştirmez.",
        "İhtiyacınız varsa bir temizlik seçin. Önizle ile etkiyi görün; yalnız istediğiniz işlemi uygulayın. Geri al ve geçmiş korunur; bu adım atlanabilir.",
        "Grafik ayarlarını açıp tür ve ölçümü seçin. Kapsam/örneklem görünürdür. Grafiği oluşturun; isterseniz projeye kaydedin.",
        "Rapor amacını yazın; HTML veya PDF için yeni bir dosya seçin. Kaynak, geçmiş, kalite ve grafikler kayıtlı sürümleriyle rapora girer. Projeyi kaydet geçmişi korur."
    ]
    UiLabel { visible: !panel.compactHome || guide.active; text:qsTr("Dosyamı anlamak istiyorum"); font.pixelSize:Theme.subheading; font.bold:true; Layout.fillWidth:true; wrapMode:Text.Wrap }
    UiLabel { visible: !panel.compactHome || guide.active; text:guide.message; Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.secondary }
    ColumnLayout {
        visible:guide.active; Layout.fillWidth:true
        UiCombo { accessibleLabel: qsTr("Rehber adımı"); objectName:"guideStep"; model:["1 · Dosya içe aktar","2 · Profili incele","3 · Kaliteyi tara","4 · Seçtiğin temizlik","5 · Grafik oluştur","6 · Rapor üret"]; currentIndex:guide.step; Layout.fillWidth:true; onActivated:guide.go(currentIndex) }
        UiLabel { objectName:"guideInstruction"; text:panel.instructions[guide.step]; Layout.fillWidth:true; wrapMode:Text.Wrap }
        Flow { Layout.fillWidth:true; spacing:Theme.sm
            UiButton { text:qsTr("Önceki"); enabled:guide.step>0 && !projects.busy; onClicked:guide.go(guide.step-1) }
            UiButton { objectName:"guideNext"; text:qsTr("Sonraki / bu adımı atla"); enabled:guide.step<5 && !projects.busy; onClicked:guide.go(guide.step+1) }
            UiButton { text:qsTr("Rehberi kapat"); onClicked:guide.close() }
            UiButton { visible: false; tone: "mint"; text:qsTr("Bu ne işe yarar?"); helpContext:"guide"; onClicked:panel.helpRequested(this,"guide") }
        }
    }
    Flow { visible:!guide.active; Layout.fillWidth:true; spacing:Theme.sm
        UiButton { objectName:"guideStart"; text:qsTr("Kendi dosyamla başla"); primary:true; onClicked:guide.go(0) }
        UiButton { objectName:"salesExample"; text:qsTr("Satış örnek projesi"); enabled:!projects.busy && !guide.busy; onClicked:{ panel.exampleKind="sales"; exampleFolder.open() } }
        UiButton { objectName:"problemExample"; text:qsTr("Problemli veri örnek projesi"); enabled:!projects.busy && !guide.busy; onClicked:{ panel.exampleKind="problem"; exampleFolder.open() } }
    }
    UiLabel { visible:!guide.active && !panel.compactHome; text:qsTr("Örnekler küçük ve sentetiktir (CC0). Seçeceğiniz üst klasörde yeni, ayrı proje oluşturulur; açık projeyi önce kaydedip kapatın."); Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.secondary }
    FolderPicker { id:exampleFolder; objectName:"exampleFolderPicker"; title:qsTr("Örnek projesi için üst klasörü seçin"); onChosen:function(folder){guide.createExample(panel.exampleKind,folder)} }
}
