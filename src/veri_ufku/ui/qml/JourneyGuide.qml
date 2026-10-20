import QtQuick
import QtQuick.Layouts

Rectangle {
    id: guide
    objectName: "journeyGuide"
    property int section: 1
    signal navigate(int section)
    signal learnRequested(string articleId, var origin)
    readonly property var steps: [
        {},
        {title:"Veriyi tanı", question:"Her satır kimi veya neyi temsil ediyor?", action:"Dosyanı önizle; satırları, sütun türlerini ve eksik değerleri incele.", result:"Kaynağı belli bir veri tablosu ve sütunların anlamı.", example:"Yolcu tablosunda yaş bir ölçüm, bilet sınıfı bir kategoridir. Eksik yaş sıfır yaş demek değildir.", article:"data", next:3, nextLabel:"Dağılımları keşfet"},
        {title:"Veriyi hazırla", question:"Hangi kayıtlar veya değerler inceleme gerektiriyor?", action:"Eksik, tekrar ve tür sorunları için önce önizlemeye bak; değişikliği açıkça uygula.", result:"Kaynağı korunmuş yeni bir veri sürümü ve işlem geçmişi.", example:"Eksik yaşları doldurmak bir varsayımdır. Model kuracaksan doldurma değerini yalnız eğitim verisinden öğren.", article:"missing", next:3, nextLabel:"Hazırladığın veriyi incele"},
        {title:"Desenleri keşfet", question:"Dağılım nasıl; gruplar arasında ne değişiyor?", action:"Önce tek sütunu histogramla tanı, sonra grupları ve iki değişkeni karşılaştır.", result:"Bir grafik, kullanılan kayıt sayısı ve araştırılacak yeni bir soru.", example:"Yaş dağılımını ve bilet sınıflarını ayrı incele. Görülen bir ilişki tek başına neden-sonuç göstermez.", article:"analysis-exploratory", next:2, nextLabel:"Veriyi hazırlamaya geç"},
        {title:"Farkı ve belirsizliği değerlendir", question:"Gördüğün fark ne kadar büyük; ne kadar belirsiz?", action:"Soruna uygun karşılaştırmayı seç; varsayımları, etki büyüklüğünü ve güven aralığını oku.", result:"Yöntemi ve sınırları belli bir karşılaştırma.", example:"İki grubun ortalaması farklı olabilir; örneklem büyüklüğü ve belirsizlik de yorumun parçasıdır.", article:"statistics", next:5, nextLabel:"Tahmin kurmayı keşfet"},
        {title:"Model kur ve değerlendir", question:"Yeni kayıtlarda da işe yarayan bir tahmin yapabilir misin?", action:"Hedefi seç; grup/zaman yapısına uygun ayırma planını kur, baseline ile karşılaştır.", result:"Eğitim geçmişi ve ayrı değerlendirmesi olan bir model.", example:"Aynı kişiye ait kayıtları iki tarafa dağıtmak sızıntı yaratabilir. Final test model seçmek için değildir.", article:"prediction", next:6, nextLabel:"Bulgularını anlat"},
        {title:"Bulgularını paylaş", question:"Ne buldun; sonucun hangi koşullarda geçerli?", action:"Grafiği, yöntemi, varsayımları ve sınırlılıkları rapora ekle; dışa aktarım önizlemesini incele.", result:"Kaynağına bağlı ve açıklaması olan bir rapor.", example:"Keşif sırasında fark ettiğin bir deseni önceden belirlenmiş hipotez testi gibi sunma.", article:"export", next:0, nextLabel:"Projeni kaydet"}
    ]
    readonly property var step: steps[section] || ({})
    implicitHeight: content.implicitHeight + 32
    color: Theme.surface
    radius: Theme.radius
    border.color: Theme.border
    ColumnLayout {
        id: content
        x:16; y:16; width:parent.width-32
        spacing:Theme.sm
        UiLabel { text:guide.step.title || ""; color:Theme.dataTone; font.bold:true; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiLabel { text:guide.step.question || ""; font.pixelSize:Theme.subheading; font.bold:true; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiLabel { text:guide.step.action || ""; Layout.fillWidth:true; wrapMode:Text.Wrap }
        UiLabel { text:"Elde edeceğin: " + (guide.step.result || ""); Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.secondary }
        UiLabel { text:"Örnek düşünce · " + (guide.step.example || ""); Layout.fillWidth:true; wrapMode:Text.Wrap; color:Theme.secondary }
        Flow {
            Layout.fillWidth:true; spacing:Theme.sm
            UiButton { objectName:"journeyLearn"; text:"Kavramları Öğren'de aç"; tone:"mint"; onClicked:guide.learnRequested(guide.step.article,this) }
            UiButton { objectName:"journeyNext"; text:guide.step.nextLabel || ""; quiet:true; onClicked:guide.navigate(guide.step.next) }
            UiButton { text:"Yol haritasına dön"; quiet:true; onClicked:guide.navigate(0) }
        }
    }
}
