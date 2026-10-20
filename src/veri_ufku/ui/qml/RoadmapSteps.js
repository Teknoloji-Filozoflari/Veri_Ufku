.pragma library

// Navigation describes the complete lifecycle; planned tools never run a placeholder.
var stages = [
    {id:"data", section:1, route:"profile", title:"Veriyi tanı", caption:"Doğru soruyla başla, kaynağını tanı.", icon:"table", tone:"cyan", steps:[
        {title:"Problemi ve amacı belirleme", detail:"Proje amacını kaydet.", section:0},
        {title:"Veri toplama ve içe aktarma", detail:"Dosyanı seç, önizlemeyi incele.", section:1, tab:1},
        {route:"profile", title:"Türler, ölçümler ve veri profili", detail:"Her sütunun neyi anlattığını öğren.", section:1, tab:0},
        {route:"values", title:"Sütun değerlerini inceleme", detail:"Farklı değerleri ve tekrar sayılarını gör.", section:1, tab:0},
        {route:"describe", title:"Özet istatistikler", detail:"Ölçümlerin sayısını, merkezini ve yayılımını tanı.", section:1, tab:0},
        {route:"notes", title:"Sütunların anlamı ve notlar", detail:"Birimleri ve kategori kodlarını kendi açıklamanla kaydet.", section:1, tab:0},
        {title:"Kaynak ve veri sürümleri", detail:"Projenin kaynağını ve geçmişini koru.", section:0}
    ]},
    {id:"analysis", section:3, title:"Sorular sor ve keşfet", caption:"Ne oldu, neden olabilir, ne olabilir?", icon:"chart", tone:"mint", steps:[
        {title:"Açıklayıcı Analiz", english:"Descriptive Analysis", detail:"Ne oldu? Özetler ve dağılımlarla incele.", section:1, tab:0},
        {title:"Teşhis Analizi", english:"Diagnostic Analysis", detail:"Neden olabilir? Karşılaştır; ilişki tek başına nedeni kanıtlamaz.", section:4},
        {title:"Tahmine Dayalı Analiz", english:"Predictive Analysis", detail:"Ne olabilir? Sayısal hedef için tahmin kur.", section:5},
        {title:"Kuralcı Analiz", english:"Prescriptive Analysis", detail:"Ne yapmalı? Gelişmiş senaryo ve optimizasyon araçlarını aç.", section:5, route:"scenario", advanced:true},
        {title:"Keşifsel Veri Analizi", english:"Exploratory Data Analysis", detail:"Veriyi tanı, desenleri ve yeni soruları keşfet.", section:3}
    ]},
    {id:"cleaning", route:"clean", section:2, title:"Veriyi hazırla", caption:"Güvenilir bir çalışma verisi hazırla.", icon:"prepare", tone:"violet", steps:[
        {route:"clean", title:"Temizleme", detail:"Eksikleri, tekrarları ve aykırı kayıtları incele.", section:2},
        {route:"join", title:"Birleştirme", detail:"Tabloları anahtarlarıyla birleştir.", section:2},
        {route:"transform", title:"Dönüştürme", detail:"Türleri ve alanları amaca uygun düzenle.", section:2},
        {route:"preparation", title:"İndirgeme", detail:"Model hazırlığında özellik seçimi; genel boyut indirgeme planlanan bir yoldur.", section:5}
    ]},
    {id:"visualization", section:3, title:"Desenleri görünür kıl", caption:"Sayıları görünür, desenleri anlaşılır kıl.", icon:"chart", tone:"cyan", steps:[
        {title:"Dağılımlar ve aykırı değerler", detail:"Histogram ve kutu grafiğiyle veriyi tanı.", section:3},
        {title:"Karşılaştırma grafikleri", detail:"Grupları ve ölçümleri yan yana gör.", section:3},
        {title:"Zaman ve trendler", detail:"Zaman içindeki değişimi incele.", section:3},
        {title:"Grafikleri inceleme", detail:"Grafik ekranını aç.", section:3}
    ]},
    {id:"relations", section:4, title:"İlişkileri araştır", caption:"Değişkenler birbirine nasıl eşlik ediyor?", icon:"compare", tone:"mint", steps:[
        {title:"Korelasyon ve saçılım", detail:"Sayısal değişkenlerin birlikte değişimini incele.", section:3},
        {title:"Pearson ve Spearman ilişkileri", detail:"İlişkinin gücünü, yönünü ve belirsizliğini değerlendir.", section:4},
        {title:"İlişkileri karşılaştırma", detail:"İstatistik ekranını aç.", section:4}
    ]},
    {id:"statistics", section:4, title:"Farkı ve belirsizliği değerlendir", caption:"Farkı ve belirsizliği birlikte değerlendir.", icon:"compare", tone:"violet", steps:[
        {title:"Grupları karşılaştırma", detail:"Soruna ve veri yapına uygun yöntemi seç.", section:4},
        {title:"Eşleşmiş ölçümler", detail:"Aynı kişi veya varlığın ölçümlerini doğru eşleştir.", section:4},
        {title:"Etki büyüklüğü ve güven aralığı", detail:"Yalnız p değerine bakmadan sonucu yorumla.", section:4}
    ]},
    {id:"modeling", route:"preparation", section:5, title:"Model kur", caption:"Amacına uygun, sınırları belli bir model kur.", icon:"model", tone:"violet", steps:[
        {route:"preparation", title:"Model için veri hazırlığı", detail:"Hedefi ve özellikleri seç; öğrenilen işlemleri eğitim katında tut.", section:5},
        {route:"regression", title:"Sayısal tahmin · Regresyon", detail:"Baseline, doğrusal, Ridge ve sınırlı RandomForest adayları.", section:5},
        {route:"classification", title:"Sınıflandırma", detail:"Bir kategori tahmin etme; baseline, LogisticRegression ve sınırlı RandomForest.", section:5},
        {route:"clustering", title:"Kümeleme", detail:"KMeans/DBSCAN ile benzer kayıtları keşfet; gerçek sınıf değildir.", section:5},
        {route:"text", title:"Metin incelemesi", detail:"Yerel token/n-gram/TF-IDF ve etiketli metin için eğitim vocab.", section:5},
        {route:"timeseries", title:"Zaman serisi", detail:"Sıklık, trend, geçmişten geleceğe doğrulama ve gerçek baseline.", section:5},
        {route:"anomaly", title:"Anomali tespiti", detail:"IsolationForest veya tek sütun IQR adaylarını işaretle; kayıt silinmez.", section:5}
    ]},
    {id:"evaluation", route:"validation", section:5, title:"Modelini sınayarak değerlendir", caption:"Modelin yeni veride ne kadar işe yarıyor?", icon:"model", tone:"warm", steps:[
        {route:"validation", title:"Train / validation / test", detail:"Kayıt yapısına uygun, ayrı bölümler kur.", section:5},
        {route:"validation", title:"Grup ve zaman planı", detail:"Aynı varlığı ve gelecekteki bilgiyi doğru ayır.", section:5},
        {route:"validation", title:"Çapraz doğrulama ve baseline", detail:"Adayları yalnız geliştirme verisinde karşılaştır.", section:5},
        {route:"validation", title:"Final test ve hata yorumlama", detail:"Son seçimi ayrı değerlendir; test kullanımını kaydet.", section:5}
    ]},
    {id:"sharing", section:6, title:"Bulgularını paylaş", caption:"Sonucunu kaynağı ve sınırlarıyla anlat.", icon:"report", tone:"warm", steps:[
        {title:"Rapor oluşturma", detail:"Bulguları, grafikleri ve geçmişi bir araya getir.", section:6},
        {title:"Veriyi dışa aktarma", detail:"Amacına uygun formatı ve alanları seç.", section:6},
        {title:"Proje kaydı ve tekrar üretilebilirlik", detail:"Veri sürümünü, ayarları ve sonuçları birlikte sakla.", section:0}
    ]},
    {id:"monitoring", section:5, route:"monitoring", advanced:true, title:"Yeni verilerle yeniden değerlendir", caption:"Yeni bilgi geldikçe yeniden sor, yeniden değerlendir.", icon:"sprout", tone:"mint", steps:[
        {title:"Yeni veride performans izleme", detail:"Sonuçların zamanla nasıl değiştiğini takip et.", section:5, route:"monitoring", advanced:true},
        {title:"Veri dağılımındaki değişim", detail:"Yeni verinin önceki veriden uzaklaşmasını izle.", section:5, route:"monitoring", advanced:true},
        {title:"Modeli ve kararları güncelleme", detail:"Yeni değerlendirme planıyla sürece geri dön.", section:5, route:"validation"}
    ]}
]
