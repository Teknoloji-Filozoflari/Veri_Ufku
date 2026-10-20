#### Verinin  Analizi

Veriyi anlamaya yönelik yapılan analizlerdir. Veri keşfi ve analizine yönelik pek çok yöntem vardır. Bunlar

- Descriptive Analysis ->Açıklayıcı analiz
- Diagnostic Analysis -> Teşhis Analizi
- Predictive Analysis -> Tahmine Dayalı Analiz
- Prescriptive Analysis -> Kuralcı Analiz
- Exploratory Data Analysis -> Keşifsel Veri Analizi

Bütün bu yöntemleri bir birinden kesin bir şekilde ayırmak doğru değildir. Birbirlerini destekleyen, birbirlerinin üzerine inşa edilen yöntemlerdir. Bunların karışımından ve olası yeni yöntemlerin dahil edilmesinden farklı analiz yaklaşımları da mümkündür.

##### Descriptive Analysis
En temel analiz tipi olan “Açıklayıcı Analiz” geçmiş verilere bakarak “neler olduğunu” anlamaya yönelik yöntemler sunar Bu yöntem ile veri içindeki genel özellikler, dağılımlar, modlar, medyanlar ve ortalamalar gibi istatistikler hesaplanır. Ayrıca, veri içindeki varyasyonlar, korelasyonlar, faktörler veya gruplar gibi ek bilgiler de elde edilir. Descriptive analysis, veriye genel bir bakış sağlar ve veri içindeki anlamlı modelleri veya trendleri ortaya çıkarır. Özellikle, veri seti büyük veya karışık ise, descriptive analiz yaparak veri içindeki önemli özellikleri veya kalıpları ortaya çıkarabilirsiniz.

##### Diagnostic Analysis
Diagnostic analysis, veri içindeki bir sorunun veya anomali nedenlerini belirlemek için kullanılan bir veri analitik yöntemidir. Bu yöntem veri içindeki hataları, eksiklikleri, yanlışlıkları veya istenmeyen sonuçları tespit etmek için kullanılır. Örneğin, bir makine öğrenimi modelinin performansının düşük olması durumunda, diagnostic analysis ile modelin neden düşük performans gösterdiğini belirleyebilirsiniz. Diagnostic analysis, veri içindeki sorunların veya anomali nedenlerinin tespit edilmesine yardımcı olarak, veri analitik sürecinin daha sonraki aşamalarında daha doğru ve etkili kararlar alınmasına olanak sağlar.

##### Predictive Analysis
Predictive analysis, gelecekteki olayların ya da sonuçların tahmin edilmesi için kullanılan bir veri analitik yöntemidir. Bu yöntem, veri içindeki modeller veya trendleri kullanarak gelecekteki olayların ya da sonuçların tahmin edilmesini amaçlar. Örneğin, bir satış trendinin tahmin edilmesi, müşterilerin davranışlarının tahmin edilmesi veya bir finansal göstergenin tahmin edilmesi gibi durumlar.
Predictive analysis, çeşitli yöntemler ve teknikler kullanarak gerçekleştirilir. Örneğin, makine öğrenimi yöntemleri arasında kullanılan yapay sinir ağları, doğal dil işleme, kümeleme veya regresyon analizi gibi tekniklerle gerçekleştirilebilir. Ayrıca, istatistiksel yöntemler arasında kullanılan lineer regresyon, logistik regresyon veya tahmin edici kalıplar gibi teknikler de kullanılabilir.

##### Prescriptive Analysis
Ne yapmalı, nasıl gerçekleştirebiliriz sorularına cevap arar. Tahmine dayalı analize benzer ancak ondan farklı olarak eylem/aksiyon için süreçleri de tanımlar. Eylem adımları Yapay Zeka gibi büyük veri ve işlem gerektiren süreçlerden sonra oluşturulabilir ve hatta eyleme geçirilebilir. Eylemler insan müdahalesi olmadan optimize edilebilir ve güncellenebilir. Örneğin, bir satış trendinin tahmin edilmesi sonucunda, en uygun ürünlerin veya hizmetlerin sunulması gerektiği yerlerin tahmin edilmesi veya müşterilerin davranışlarının tahmin edilmesi sonucunda, müşteri sadakatini arttırmak için en uygun önlemlerin belirlenmesi gibi durumlar.
Prescriptive analysis, veri içindeki modeller veya trendleri kullanarak en uygun çözümleri veya kararları belirlemek için çeşitli yöntemler ve teknikler kullanılabilir. Örneğin, optimizasyon algoritmaları, yapay sinir ağları veya doğal dil işleme gibi makine öğrenimi yöntemleri veya lineer programlama, kısıtlı en iyi uyumlu (constraint optimization) veya Monte Carlo simulasyonları gibi istatistiksel yöntemler kullanılabilir.

![[veri_analiz.PNG]]

##### Exploratory Data Analysis
Genellikle makine öğrenimi modellemesi öncesi verilere ait bir içgörü oluşturabilmek için yapılan analizlerdir. Böylece modele gönderilen verilerin bir sağlaması yapılır ve geçerliliği denetlenmiş olur ayrıca modelin çıktıları bu analize göre daha sağlıklı değerlendirilebilir. Bazen veriler ve makine öğrenimi süreci arasında tutarsızlıklar olabilir, bu durumdan kaçınmak için makine öğrenimi modellemesi için kullanılan verilerin daha iyi tanınması gerekir, işte bunun için makine öğrenimi modellemesi öncesi Keşifsel veri analizi yapmak son derece sağlıklıdır. Öte yandan daha iyi bir modelleme için hangi özelliklerin kullanılması gerektiği hakkında da içgörü sağlar. Keşifsel veri analizi veriler arasındaki ilişkileri tespit etmeye, farklı açılardan analiz etmeye yarayan yöntemleri kapsar, bu yapısıyla yukarıdaki “teşhis analizi” yöntemine çok benzer. Sonuçlar genellikle görselleştirme ve özetleme olarak sunulur. Bunun yanında eksik, hatalı verilerin tanımlanması ve düzeltilmesi gibi veri ön işleme yöntemlerini de kullanır. Temel Adımları şekilde görüldüğü gibidir.

![[keşif.PNG]]
