# Çekme Testi Analiz Yazılımı İçin Doğrulama Temeli ve Türkiye Pazarına Giriş

## Yönetici özeti

TENSTAND, Avrupa Birliği FP5 altında yürütülen ve NPL koordinasyonundaki **“Computer controlled tensile testing machines: validation of european standard en10002 part 1”** başlıklı projedir; resmi hibe kimliği **G6RD-CT-2000-00412** olarak görünür. Projenin amacı yalnızca makine kontrolünü değil, **Young modülü, proof stress, tensile strength ve elongation at fracture** gibi parametreleri hesaplayan yazılımların doğrulanmasına uygun yöntem ve **ASCII formatlı çekme veri setleri** geliştirmektir. Kamuya açık olarak doğrulayabildiğim kaynaklara göre proje 2001-2004 arasında sürmüş, NPL sayfasında bugün de TENSTAND veri seti ve rapor bağlantıları listelenmektedir. citeturn7view1turn3view0turn3view1

TENSTAND tarafında kritik ayrım şudur: proje kapsamında **64 dosyalık tam veri seti**, bunun içinden seçilmiş **34 dosyalık yazılım karşılaştırma alt kümesi** ve ayrıca NPL sayfasında sunulan **15 “premium quality” ASCII veri dosyası + agreed values** paketi vardır. Veriler Excel/CSV değil, başlık bilgisi ve ardından **time, crosshead displacement, extensometer extension, force** sütunlarından oluşan düz **ASCII** dosyalardır. Referans değerler de her dosya için tek tip değildir; bazı dosyalarda **E**, bazılarında **Rp0.1 / Rp0.2**, bazılarında **ReH / ReL**, **Rm / Fm** ve belirli uzama ölçütleri için “agreed values” verilir. Bunlar proje raporunda çoğunlukla **sertifikalı değer** olarak değil, yazılım doğrulaması için **agreed values / accepted ranges** olarak ele alınır. citeturn6view1turn6view2turn1view1turn3view1

Türkiye tarafında, kamuya açık kaynaklarda doğrulayabildiğim resmî TÜRKAK dokümanları içinde **R20.43’ün açık erişimli resmî PDF sürümü Rev.01 ve yürürlük tarihi 31.01.2019** olan “Laboratuvarların Akreditasyonuna Dair Rehber”dir. Bu metin genel laboratuvar akreditasyonu rehberidir; içerik tablosunda yazılım doğrulamaya ayrılmış özel bir bölüm görünmez. Buna karşılık TÜRKAK’ın ayrıca **“Laboratuvar Bilgi Sistemi”** adlı bir kılavuzu vardır ve bunun açıklama metni doğrudan **TS EN ISO/IEC 17025:2017 madde 7.11** altında laboratuvarda kullanılan yazılım ve bilgisayarların nasıl ele alınacağı için hazırlandığını söyler. Bu nedenle, yazılım doğrulama açısından pratikte bakılması gereken ana eksen **R20.43 + 17025/7.11 + Laboratuvar Bilgi Sistemi kılavuzu** kombinasyonudur; yalnızca R20.43 değildir. citeturn43view0turn46search1turn46search0

TÜBİTAK UME konusunda ise, kamuya açık taramada tam adı birebir **“Çekme Deneyinde Ölçüm Belirsizliği”** olan bağımsız bir 2019 UME PDF rehberini doğrulayamadım. Buna karşın UME’nin yayın listesinde 2019’da çekme testiyle ilgili bir dizi çıktı, 2021’de UME yazarlarının **“An Approach to Uncertainty Calculation of the Modulus of Elasticity for Metallic Materials”** çalışması ve aynı yazarın 2021 tarihli **“Uygulamalı Ölçüm Belirsizliği – Mekanik Deneylerde”** kitabı açıkça izlenebiliyor. Bu kamuya açık UME kaynakları, Türkiye’de çekme deneyi belirsizlik pratiğinin hangi bileşenler etrafında kurulduğunu anlamak için yeterince güçlü bir resim veriyor; ancak kullanıcı sorusundaki 2019 başlıklı rehber için ayrıca kurum içi katalog veya doğrudan UME teyidi gerekebilir. citeturn28view0turn30view1turn36search9turn36search13turn35view0

**ACTIONable:** Türkiye’ye girecek bir çekme testi analiz yazılımı, pazara “algoritma iyi çalışıyor” söylemiyle değil, şu dört kanıt paketiyle girmelidir: **TENSTAND veya eşdeğer dijital doğrulama seti**, **fiziksel referans/CRM veya PT kanıtı**, **17025/7.11 uyumlu yazılım doğrulama dosyası**, **Türkçe belirsizlik ve kabul kriteri dokümantasyonu**. Bu dört başlık hem teknik güveni hem de denetim dayanıklılığını birlikte yükseltir. citeturn3view1turn12view1turn22search5turn46search1

## TENSTAND referans veri seti

### Projenin kimliği ve kapsamı

TENSTAND’ın resmi proje adı CORDIS’te **“Computer controlled tensile testing machines: validation of european standard en10002 part 1”** olarak yer alır; hibe kimliği **G6RD-CT-2000-00412**, başlangıç tarihi **1 Şubat 2001**, kapanış tarihi **30 Nisan 2004** ve koordinatörü **NPL Management Ltd.** olarak görünür. CORDIS hedef metni ayrıca projenin, yazılımların **Young’s Modulus, Proof Stress, Tensile Strength ve Elongation at Fracture** hesaplamalarını doğrulamak için yöntemler ve **ASCII tensile data sets** geliştireceğini açıkça söyler. citeturn7view1

NPL’nin güncel “Tensile testing” kaynağı bugün hâlâ TENSTAND başlığı altında hem proje raporunu hem de veri paketlerini listeler. Sayfada bir yandan **full ASCII data set**, öbür yandan **15 selected premium quality ASCII datafiles + agreed values** bağlantıları bulunur; yani erişim modeli en azından sayfa düzeyinde **kamuya açık indirme** mantığıyla korunmuştur. citeturn3view0turn3view1

### Hangi malzemeler, hangi koşullar, kaç test

NPL yazılım değerlendirme raporuna göre temsilî gerilme-şekil değiştirme eğrilerinin üretilmesi için **11 malzeme partisi** üzerinde **30’dan fazla çekme testi** yapıldı; ayrıca daha sonra NPL tarafından **sentetik üretilmiş veri** de eklendi. Orijinal çalışma toplam **64 veri dosyası** üretti; bunların içinden yazılım karşılaştırma egzersizi için **34 ASCII veri dosyalık** bir alt küme seçildi. citeturn6view1turn6view2

Projede kullanılan malzeme ailesi geniş tutuldu: **CRM661 Nimonic 75**, **%13 Mn çelik**, **S355 yapısal çelik**, **316L paslanmaz çelik**, **tin coated packaging steel**, **T462 sheet steel**, **DX56 galvanizli sac**, **bake hardened steel sheet**, **AA5182 hard**, **AA1050 soft** ve **AA5182 soft** alüminyum dahil farklı akma davranışları olan sınıflar kullanıldı; ayrıca **zero-noise** ve farklı yük gürültüsü seviyelerinde **sentetik dijital eğriler** hazırlandı. Testler o tarihte geçerli standart olan **EN 10002-1** koşullarına göre, **crosshead control** altında ve **izin verilen en yüksek hızlarda** yürütüldü; birincil toplama frekansı **50 Hz**, sonra yeniden örneklenmiş versiyonlar **5 Hz** olarak hazırlandı. citeturn6view1turn6view2

### Veri formatı ve erişim modeli

TENSTAND dosyaları **CSV veya Excel değil**, ASCII veri dosyalarıdır. Rapor, başlık kısmının malzemeye ve parametre tanımlarına ilişkin bilgileri içerdiğini; veri bölümünde ise ölçümlerin **time (s), crosshead displacement (mm), extensometer extension (mm) ve force (kN)** biçiminde yer aldığını söyler. Bu tasarım, yazılım karşılaştırması için özellikle elverişlidir; çünkü tedarikçiye özgü kapalı dosya biçimlerinden bağımsızdır. citeturn6view1

NPL sayfası iki pratik erişim yolu sunar: biri **tam set**, diğeri **premium quality** seçkidir. Saha kullanımında ilk uğranacak yer premium settir; çünkü üretici doğrulaması ve regresyon testleri için tüm 64 dosyanın yerine, agreed values ile eşlenmiş seçilmiş dosyalar daha verimlidir. Tam set ise algoritmanın köşe durumlarını görmek ve tekrar örnekleme/örnekleme frekansı etkisini test etmek için daha değerlidir. citeturn3view0turn3view1turn6view2

### Hangi referans değerler var ve belirsizlik nasıl ele alınmış

Proje raporundaki “premium quality” bölümünde, seçilmiş dosyalar için **agreed values** verilir. Dosyaya göre değişmek üzere bunlar **Young’s modulus E**, **proof stresses Rp0.1 / Rp0.2**, **upper/lower yield strength ReH / ReL**, **maximum force Fm / tensile strength**, ayrıca **Ag, Ae, Agt** gibi uzama tabanlı büyüklükleri kapsar. Bu, sizin yazılımınızın yalnızca **Rm** ve **Rp0.2** değil, farklı akma davranışlarında **ReH/ReL** ve farklı uzama ölçütlerini de doğru hesaplaması gerektiği anlamına gelir. citeturn1view1

Ancak burada önemli bir metrolojik ayrım vardır: TENSTAND ASCII referans dosyaları için kamuya açık NPL raporunda verilenler esasen **agreed values / kabul aralıklarıdır**; bu veri dosyaları için her parametreye bağlanmış ayrı bir **GUM-tarzı sertifikalı belirsizlik bütçesi** aynı şekilde sunulmaz. Buna karşılık projede kullanılan **CRM 661 Nimonic 75** malzemesi ayrı bir fiziksel **sertifikalı referans malzemedir** ve burada **Rp0.2 = 300 ± 7 MPa**, **Rp0.5 = 318 ± 7 MPa**, **Rm = 750 ± 13 MPa**, **A = 40.9 ± 0.9 %**, **Z = 60 ± 4 %** sertifikalı; **E = 206 ± 21 GPa** ise yalnızca **indicative value** olarak verilir. citeturn12view0turn12view1

Bu yüzden ürün mesajında şu ayrımı korumak gerekir: “**TENSTAND agreed values’a karşı doğrulandı**” ifadesi sağlamdır; ama “**TENSTAND sertifikalı değerlerine karşı doğrulandı**” ifadesi, yalnızca ASCII veri setlerine bakıldığında fazla iddialı olabilir. Sertifikasyon dili daha çok **CRM 661 fiziksel malzemesi** için uygundur. citeturn1view1turn12view0

### ISO 6892-1 ile ilişkisi ve alternatif doğrulama stratejileri

Doğrulayabildiğim ISO 6892-1:2019 örnek/pre-view içeriğinde **TENSTAND adına açık referans** bulamadım; projeyi ne girişte ne de görünen normatif referanslarda ismen anıyor. Bununla birlikte standart, **Annex A** içinde bilgisayar kontrollü test makineleri için ek tavsiyeler bulunduğunu belirtir. Öte yandan NPL’nin **Good Practice Guide No. 98** dokümanı, bu rehberde kullanılan bazı verilerin TENSTAND’dan geldiğini ve TENSTAND’ın modül ölçümü ve bilgisayar kontrollü test süreçleri üzerindeki sorunları açık ettiğini yazar. Sonuç: **doğrudan standart referansı yerine güçlü tarihsel etki** söz konusu görünür. citeturn14view0turn15view0turn38view0

TENSTAND dışında doğrudan eşdeğer, serbest erişimli ve çekme test yazılım doğrulamasına özel bir NIST dijital veri seti bulamadım. NIST’in mevcut “Mechanical Properties” referans malzemeleri sayfasında görünen ürünler daha çok **seramik kırılma tokluğu**, **sertlik** ve **AFM cantilever** gibi alanlardadır; metalik oda sıcaklığı çekme için TENSTAND benzeri kamuya açık bir dijital set bu listede görünmez. Avrupa tarafında ise **JRC BCR-661B** fiziksel CRM olarak hâlâ siparişe açıktır; **BAM** referans malzeme ve **EPTIS** yetkinlik deneyi altyapısı sunar; **PTB/DKD-R 9-2** ise test makinesi doğrulama/kalibrasyonunda güçlü bir teknik çerçeve sağlar. citeturn21view0turn18search1turn18search5turn22search4turn22search5turn22search10

Aşağıdaki tablo, doğrulama açısından en pratik seçenekleri özetler:

| Doğrulama varlığı | Ne doğrular | Güçlü yanı | Sınırlaması | Kaynak |
|---|---|---|---|---|
| TENSTAND premium ASCII seti | Algoritma ve hesaplama yazılımı | Çoklu malzeme davranışı, açık ASCII, agreed values | Parametre bazında tam sertifikalı belirsizlik bütçesi yok | citeturn3view1turn6view1turn1view1 |
| TENSTAND tam seti + 5 Hz/50 Hz | Algoritma dayanıklılığı, örnekleme etkisi | Köşe durumları ve düşük örnekleme etkisi | Hepsi premium/agree edilmiş değil | citeturn3view0turn6view2 |
| BCR-661B fiziksel CRM | Uçtan uca sistem: makine + sensör + yazılım + operatör | Sertifikalı değer ve belirsizlik | Dijital regresyon testi için yavaş ve maliyetli | citeturn12view0turn12view1turn18search1 |
| EPTIS / PT programları | Laboratuvar yeterliliği ve metod performansı | Denetim ve akreditasyonda güçlü kanıt | Yazılım unit-test yerine laboratuvar performans kanıtı | citeturn22search5turn18search14turn22search7 |
| PTB DKD-R 9-2 ve EURAMET cg-4 | Kuvvet zinciri ve makine doğruluğu | Metrolojik izlenebilirlik ve kuvvet belirsizliği | Sonuç algoritmasını tek başına doğrulamaz | citeturn22search10turn38view2 |

**ACTIONable:** TENSTAND erişilemezse, en sağlam alternatif strateji üç katmanlıdır:  
- **Katman biri:** TENSTAND yapısını taklit eden kendi dijital “gold dataset” paketiniz — monotonic yield, Lüders, serrated yield, stress softening, nonlinear elastic ve sentetik gürültülü eğriler.  
- **Katman iki:** En az bir fiziksel CRM veya eşdeğer round-robin/PT kanıtı.  
- **Katman üç:** Her sürümde bağımsız bir referans script ile otomatik regresyon karşılaştırması.  
Bu kombinasyon, tek başına bir PT’ye ya da tek başına bir CRM’ye göre yazılım doğrulama açısından daha güçlüdür. citeturn6view1turn6view2turn12view1turn22search5

## TÜBİTAK UME ve çekme deneyinde belirsizlik

### Kamuya açık olarak doğrulayabildiğim UME kaynakları

Kamuya açık kaynak taramasında, kullanıcı sorusunda geçen biçimiyle **“Çekme Deneyinde Ölçüm Belirsizliği”** başlıklı bağımsız bir **2019 UME PDF rehberini** doğrulayamadım. Buna karşılık UME yayın listesi ve ilişkili kaynaklar, çekme deneyi belirsizliği çevresinde bir yayın çizgisi olduğunu açıkça gösteriyor:  
- UME yayın listesinde 2019’da çekme testi ve modül/ hız/ yeterlilik konularında konferans bildirileri görünüyor.  
- 2021’de UME yazarlarının **“An Approach to Uncertainty Calculation of the Modulus of Elasticity for Metallic Materials”** bildirisi yer alıyor.  
- Yine Bülent Aydemir’in **“Uygulamalı Ölçüm Belirsizliği – Mekanik Deneylerde”** kitabı kütüphane ve kitap kataloğu kayıtlarına göre **2021** tarihli. citeturn28view0turn30view1turn36search9turn36search13turn35view0

Bu nedenle, Türkiye’de satılacak bir yazılım için pratik yaklaşım şudur: belirsizlik kısmında “2019 UME rehberi”ni beklenen tek otorite gibi konumlandırmak yerine, **UME yazarlı kamuya açık çalışmalar + UME yayın çizgisi + uluslararası kılavuzlar** üzerinden daha savunulabilir bir teknik temel kurmak gerekir. Bu, aynı zamanda ürünün belgelerinde “resmî UME rehberi” ifadesini yalnızca gerçekten doğrulanabilen dokümanlar için kullanmanız gerektiği anlamına gelir. citeturn28view0turn30view1turn36search9

### UME kaynaklarının kapsadığı parametreler ve yöntem mantığı

UME yazarlarının kamuya açık çekme belirsizliği çalışmalarında, belirsizlik yaklaşımı çekme testinden elde edilen ana mühendislik sonuçları etrafında kurulmuştur. “Quality of Material Tensile Test” çalışması, belirsizlik hesabını **yield strength**, **tensile strength**, **percent elongation** ve **reduction of area** için ayrı ayrı bütçeler halinde verir; 2021 tarihli UME bildirisi ise **modulus of elasticity** için özel bir yaklaşım sunar ve ISO 6892-1 Annex G ile ASTM E111’i referans çerçevesine alır. citeturn31view0turn31view3turn30view1

Bu kaynaklar formel olarak “GUM’a uygundur” cümlesini her yerde açıkça yazmasa da, kullandıkları yapı **GUM-tarzı bileşen tabanlı belirsizlik bütçesi**dir: dağılım türleri, bölenler, duyarlılık katsayıları, birleşik belirsizlik ve **k = 2** ile genişletilmiş belirsizlik kullanılır. Bu yüzden uygulama mantığı bakımından **GUM-stiline yakın** bir yaklaşım söz konusudur; ancak kamuya açık olarak doğrulayabildiğim malzemelerde, kullanıcı sorusundaki belirli “2019 rehberi” için ayrıca bir **resmî GUM uygunluk beyanı** bulamadım. citeturn31view0turn31view3turn32search8

### u(Rp0.2), u(Rm), u(A%) için pratik belirsizlik bileşenleri

UME çizgisindeki kamuya açık model, **Rp0.2 / akma dayanımı** için belirsizliği şu ana bileşenlere ayırır: **numune/tekrarlanabilirlik kaynaklı test belirsizliği**, **kuvvet ölçüm cihazı**, **ekstansometre**, **ortalama kesit alanı** ve **gage length**. Yazılım açısından bunun anlamı açıktır: Rp0.2 sadece “offset-line” algoritması değildir; yük, kesit ve uzama zincirindeki her hata algoritmaya sayısal olarak taşınır. citeturn31view0turn31view3

**Rm / tensile strength** için bileşenler daha dar görünür: **test belirsizliği**, **kuvvet cihazı** ve **ortalama kesit alanı**. Çünkü Rm, Rp0.2’ye kıyasla uzama-zincirine daha az bağımlıdır; bu nedenle yazılım paketinizde Rm doğrulaması için kuvvet ve alan hesabının şeffaflığı, Rp0.2 doğrulaması için ise ayrıca eğri işleme ve strain zinciri şeffaflığı gerekir. citeturn31view0turn31view3

**A% / percent elongation** için kamuya açık UME modeli; **test belirsizliği**, **makine çözünürlüğü**, **kumpas**, **ilk ölçü uzunluğu** ve **son ölçü uzunluğu / ekstansometre** katkılarını ayırır. Bu, A% hesabında yazılımın yalnızca son sonucu değil, **hangi gauge length tanımını**, **pre-fracture mi post-fracture mi**, **manual input mu cihaz input’u mu** kullandığını açıkça kaydetmesini zorunlu kılar. citeturn31view0turn31view3

**E modülü** için 2021 UME bildirisi; belirsizliği özellikle **force measuring device**, **force range**, **strain değerlerinin elastik bölgede doğru seçimi**, **hesap yöntemi** ve **regresyon yaklaşımı** bağlamında tartışır. Bu da şu stratejik sonuca götürür: pazara girecek yazılımda E hesap modülü, Rp0.2 veya Rm modüllerinden ayrı bir “yüksek riskli hesap modülü” olarak ele alınmalıdır. citeturn30view1

### UME çalışmaları ile uluslararası dokümanların karşılaştırması

Aşağıdaki karşılaştırma, Türkiye pazarı için size en yararlı belge kümesini gösterir:

| Doküman | Odağı | Yazılım için anlamı | Kaynak |
|---|---|---|---|
| UME yazarlarının çekme belirsizliği çalışmaları | Rp/Rm/A/E gibi çekme çıktıları için bileşen bazlı belirsizlik | Sonuç modüllerini belirsizlik bileşeniyle eşleştirme | citeturn31view0turn31view3turn30view1 |
| NPL Good Practice Guide No. 98 | Özellikle **E modülü** ve statik/dinamik modül ölçümleri | E modül algoritması için en güçlü teknik referanslardan biri | citeturn38view0 |
| NPL “The Determination of Uncertainties in Tensile Testing” | Çekme sonuçlarındaki belirsizliğin hesap pratiği | Belirsizlik raporlama mantığını ürün yardım dosyalarına aktarmak için iyi temel | citeturn33search2 |
| EA-4/16 | Nicel testlerde belirsizliğin ifade edilmesi | Laboratuvarların validasyon, PT ve yöntem performans verisini belirsizlikte kullanma biçimi | citeturn38view1 |
| EURAMET cg-4 | Kuvvet ölçümlerinin belirsizliği | Kuvvet kalibrasyonu ve izlenebilirliği yazılım sonuç zincirine bağlama | citeturn38view2 |

Bu tabloda kritik nokta şudur: **EA-4/16** laboratuvar seviyesi belirsizlik politikasını verir; **EURAMET cg-4** kuvvet zincirini metrolojik olarak temellendirir; **NPL GPG 98** ve UME çalışmaları ise sonuç algoritmasına en yakın teknik içeriği sunar. Türkiye’de ürünü başarılı kılacak kombinasyon da tam olarak budur. citeturn38view0turn38view1turn38view2turn31view0

### Türk laboratuvarları açısından statü

Kamuya açık olarak bulabildiğim TÜRKAK materyallerinde, belirli bir “UME çekme belirsizliği rehberi”nin **zorunlu referans doküman** ilan edildiğine dair net bir ifade bulamadım. TÜRKAK tarafında daha görünür beklenti, akreditasyon kapsamındaki büyüklükler için **yeterlilik deneyine / laboratuvarlar arası karşılaştırmaya katılım** ve ISO/IEC 17025 gereklerinin yerine getirilmesidir. UME de eğitim ve yeterlilik temelli altyapı sunmaktadır. Bu nedenle Türk laboratuvarları için doğru ifade, “**faydalı ve saygın teknik referans**”tır; “**TÜRKAK tarafından zorunlu tek referans**” demek için elimde kamuya açık yeterli kanıt yoktur. citeturn32search5turn32search6

**ACTIONable:** Yazılımınızın Türkçe teknik dosyasında, belirsizlik modülünü aşağıdaki yapı ile sunun:  
- **Rp0.2 bütçesi:** repeatability + force + extensometer + area + gauge length  
- **Rm bütçesi:** repeatability + force + area  
- **A% bütçesi:** repeatability + resolution + caliper + initial/final gauge length  
- **E bütçesi:** force chain + elastic range selection + regression method + extensometer chain  
Bu yapı, UME/NPL/EA/EURAMET çizgileriyle uyumlu ve denetimde savunulabilir bir mimari üretir. citeturn31view0turn31view3turn30view1turn38view0turn38view1turn38view2

## TÜRKAK dokümanları ve yazılım doğrulama

### R20.43’ün doğrulayabildiğim resmi sürümü ne söylüyor

Kamuya açık olarak doğrulayabildiğim resmî PDF’ye göre **TÜRKAK R20.43**, **“Laboratuvarların Akreditasyonuna Dair Rehber”** başlığını taşır, **Revizyon No: 01**’dir ve **31.01.2019** tarihinde yürürlüğe girmiştir. İçerik tablosu; giriş, başvuru, 17025 uygulamaları, laboratuvar kapsamı, tarafsızlık-gizlilik, yapısal gereklilikler, personel, donanım, dışarıdan tedarik edilen ürün ve hizmetler, numune alma, yeterlilik deneyleri / laboratuvarlar arası karşılaştırma, risk ve fırsatlar, kalite sistemi dokümantasyonu ile denetim örneklemesini kapsar. citeturn43view0

Bu resmî PDF’de doğrudan **“yazılım”, “bilgisayar”, “bilgi yönetimi” veya “7.11”** başlıklı özel bir alt bölüm bulunmadığını da not etmek gerekir. Başka bir deyişle, kullanıcı sorusundaki biçimiyle “R20.43 = yazılım doğrulama rehberi” eşlemesi, kamuya açık doğrulanabilen 2019 sürüm metniyle tam örtüşmüyor. R20.43 daha çok laboratuvar akreditasyon çerçevesini veren üst rehberdir. citeturn43view0turn44view0turn44view1turn44view2turn44view3

### Yazılım doğrulama için asıl kritik TÜRKAK izi

TÜRKAK’ın kamuya açık başka bir kılavuzu olan **“Laboratuvar Bilgi Sistemi”** dokümanı ise tam tersine çok nettir: açıklama metni, bu kılavuzun laboratuvarda kullanılan yazılım ve bilgisayarların çeşitli uygulamalarda kullanılması hâlinde **TS EN ISO/IEC 17025:2017 madde 7.11’in nasıl ele alınacağına** yönelik hazırlandığını söyler. Snippet’te kapsanan örnek kullanımlar arasında basit kayıt oluşturma, yönetim el kitabı ve prosedürler, organizasyon şeması, personel ve eğitim verileri gibi alanlar da sayılır. Bu, TÜRKAK’ın yazılım/doğrulama beklentisini **R20.43 yerine 7.11 ekseninde** somutlaştırdığını gösteren en güçlü kamuya açık işarettir. citeturn46search1

ISO tarafında da 17025:2017’nin yeni sürümünün **IT techniques** ve dijital süreçlerle ilgili değişiklikler getirdiği resmi ISO açıklamasında belirtilir. Dolayısıyla Türkiye pazarında yazılım ürününü konumlandırırken doğru normatif anlatı şudur: **“ISO/IEC 17025:2017 madde 7.11 ve TÜRKAK laboratuvar bilgi sistemi beklentilerini destekleyen yazılım”**. citeturn46search0turn46search4

### ISO/IEC 17025 madde 7.11 ile ilişki

ISO/IEC 17025:2017, test ve kalibrasyon laboratuvarlarının yetkinliği, tarafsızlığı ve tutarlı işletimi için üst standarttır; 2017 revizyonunda bilgi teknolojileri ve kalite süreçlerindeki gelişmelerin kapsama alındığı ISO tarafından açıkça belirtilir. TÜRKAK’ın 7.11 için ayrı laboratuvar bilgi sistemi kılavuzu yayımlamış olması, yazılım doğrulamanın Türkiye’de laboratuvarlar açısından **“isteğe bağlı kalite artısı” değil, standardın bilgi yönetimi ekseninin bir parçası** olarak görüldüğünü düşündürür. citeturn46search0turn46search4turn46search1

Buradan çıkan pratik sonuç: bir laboratuvarın kullandığı çekme analizi yazılımı, yalnızca doğru sonuç üretmekle kalmamalı; aynı zamanda **hangi sürümün kullanıldığı**, **kimlerin yetkisi olduğu**, **ham verinin değişmeden saklanıp saklanmadığı**, **hesap formüllerinin değişiklik kontrolü**, **yedekleme/geri yükleme**, **raporlama çıktılarının izlenebilirliği** gibi 7.11 mantığına da cevap vermelidir. Bu son cümle, TÜRKAK kılavuzunun kapsamından ve ISO 17025’in IT vurgusundan çıkarılmış bir uygulama yorumudur. citeturn46search1turn46search4

### Talep edilen belgeler ve IQ/OQ/PQ meselesi

Doğrulayabildiğim açık erişimli **R20.43** metninde **IQ/OQ/PQ şablonları** veya bu isimlerle hazırlanmış ekler görünmüyor. Bu nedenle “TÜRKAK R20.43 içinde hazır IQ/OQ/PQ template var” demek için elimde kamuya açık kanıt yok. Uygulamada laboratuvarlar bu boşluğu çoğu zaman kendi validasyon prosedürleri, tedarikçi test raporları ve risk bazlı kabul kayıtları ile doldurur; ancak bu son cümle genel akreditasyon pratiğine dayalı bir uygulama yorumudur. Resmî olarak doğrulayabildiğim kısım, R20.43’ün bu şablonları içermediğidir. citeturn43view0

Yazılım tedarikçisi açısından laboratuvara verilmesi gereken en güçlü paket, şablon beklemek yerine şu kanıtları taşımalıdır: **intended use tanımı**, **yazılım sürüm bilgisi**, **değişiklik geçmişi**, **fonksiyonel test raporları**, **beklenen sonuçlu referans veri seti**, **kurulum önkoşulları**, **erişim/yetki matrisi**, **yedekleme ve veri bütünlüğü açıklaması**, **kullanıcı kabul testi formu**. Bu liste normatif bir TÜRKAK annex’i değil, 7.11 mantığına dayalı en savunulabilir tedarikçi paketidir. citeturn46search1turn46search0

### Ticari yazılım ile özel geliştirilmiş yazılım ayrımı

Kamuya açık doğrulanabilir TÜRKAK snippet’lerinde “ticari yazılım” ve “özel geliştirilen yazılım” için ayrı ayrı yazılmış zorunlu bir matris bulamadım. Bununla birlikte, 7.11 mantığı açısından laboratuvarın sorusu çoğu zaman aynı kalır: kullanılan yazılım **amaçlanan kullanım için uygun mu**, **değişiklik sonrası hâlâ uygun mu**, **çıktılar izlenebilir mi**? Bu yüzden ürününüz ticari olsa bile laboratuvar tarafında “vendor-supplied but locally validated” modeli daha gerçekçidir; laboratuvar çoğu durumda tedarikçi testlerini kendi kabul doğrulamasıyla tamamlamak isteyecektir. Bu cümle, TÜRKAK 7.11 odağı ve akreditasyon pratiğine dayalı bir çıkarımdır. citeturn46search1turn46search4

### Denetimde sorulabilecek tipik başlıklar

TÜRKAK’ın 7.11 odaklı laboratuvar bilgi sistemi kılavuzunu ve ISO 17025’in IT vurgusunu birlikte okuduğunuzda, denetimde tipik odak başlıklarının aşağıdaki eksende toplanması beklenir: yazılım envanteri, hangi yazılımın hangi sonucu etkilediği, sürüm kontrolü, kullanıcı yetkileri, veri bütünlüğü, otomatik hesap formüllerinin doğrulanması, yedekleme ve değişiklik sonrası yeniden doğrulama. Bu maddeler, kamuya açık snippet’lerden çıkarılmış **uygulama tahmini**dir; yani “resmî soru listesi” değil, fakat ürününüzün hazırlık dosyasında mutlaka karşılık vermesi gereken başlıklardır. citeturn46search1turn46search4

### R10.06 ve “ISO 17025 compliant” söyleminin risk analizi

TÜRKAK başvuru sayfasında **R10.06**, **“TÜRKAK Akreditasyon Markasının Akredite Kuruluşlarca Kullanılmasına İlişkin Şartlar”** olarak listelenir. Aynı kamuya açık sayfa, laboratuvar akreditasyonu için temel standardın **TS EN ISO/IEC 17025** olduğunu gösterir; ISO da 17025’in laboratuvarlar için bir standart olduğunu açıkça belirtir. Buradan çıkan temel ilke şudur: **17025 bir laboratuvar yeterlilik standardıdır; yazılım ürün sertifikası değildir.** citeturn39search3turn46search0turn46search11

Bu nedenle bir yazılım üreticisinin doğrudan **“ISO 17025 compliant software”** etiketi kullanması, özellikle Türkçe pazarlama materyalinde, ürünün akredite edildiği veya TÜRKAK/ISO tarafından onaylandığı izlenimini doğurursa risklidir. Buna karşılık şu dil çok daha savunulabilir olur: **“ISO/IEC 17025:2017 madde 7.11 doğrultusunda laboratuvarların yazılım doğrulama süreçlerini destekleyen özellikler içerir”** veya **“akredite laboratuvarlar için doğrulama kanıt paketi sunar.”** Bu paragraf bir hukuk görüşü değil, kamuya açık doküman başlıkları ve standardın kapsamına dayalı **reklam ve mevzuat riski analizi**dir. citeturn39search3turn46search0turn46search1turn46search4

**ACTIONable:** Türkiye’de pazarlama dilini şu üç seviyeye ayırın:  
- **Kullanılabilir:** “ISO/IEC 17025:2017 madde 7.11’e yönelik doğrulama desteği sağlar.”  
- **Koşullu kullanılabilir:** “Akredite laboratuvarların validasyon süreçleri için uygundur.”  
- **Kaçınılmalı:** “ISO 17025 sertifikalı yazılım”, “TÜRKAK uyumlu yazılım” veya akreditasyon çağrışımı yapan logo/işaretler.  
Bu ayrım, ürününüzü gereksiz hukuki ve denetimsel tartışmadan uzak tutar. citeturn39search3turn46search0turn46search4

## Türkiye pazarı için uygulanabilir yol haritası

### Ürün konumlandırması

Türkiye pazarında sizi öne çıkaracak şey “çekme eğrisini çiziyoruz” değil, **“algoritma + metroloji + denetim kanıtı”** üçlüsüdür. Çünkü burada hedef müşteri yalnız kalite laboratuvarı değildir; aynı zamanda akredite laboratuvar, akreditasyona hazırlanan laboratuvar ve denetimde sorgulanacak kurumsal sistemdir. TENSTAND size algoritma doğrulama zemini, UME çizgisi sonuç-belirsizlik dilini, TÜRKAK 7.11 ise yazılım kanıt paketinin biçimini verir. citeturn3view1turn31view0turn46search1

### Ürüne gömmeniz gereken çekirdek özellikler

Aşağıdaki özellikler, Türkiye’de satış yapabilen bir çekme analizi yazılımı için “nice to have” değil, fiilen **satış öncesi gereklilik** olarak görülmelidir:

| Özellik | Neden gerekli | Kaynak |
|---|---|---|
| ASCII/CSV ham veri içe aktarma ve değişmeden saklama | TENSTAND ve benzeri açık veri setleriyle doğrulama, denetimde ham veri korunumu | citeturn6view1turn3view1turn46search1 |
| Sürüm kontrollü algoritma motoru | 7.11 kapsamında yazılım değişikliklerinin izlenmesi | citeturn46search1turn46search4 |
| E, Rp0.2, ReH/ReL, Rm, Agt/A gibi çoklu sonuç modülleri | TENSTAND ve ISO 6892-1 çıktılarının tümünü kapsamak | citeturn1view1turn14view0 |
| Yöntem seçimi görünürlüğü | Özellikle E modül hesabında regresyon/elastic range etkisi | citeturn30view1turn38view0 |
| Kullanıcı yetkileri, audit trail, backup/restore | 17025/7.11 ve bilgi yönetimi mantığı | citeturn46search1turn46search4 |
| Belirsizlik rapor şablonları | UME/NPL/EA çizgisine uygun raporlama | citeturn31view0turn38view1turn33search2 |
| Referans veri regresyon testi | Her sürümde otomatik doğrulama kanıtı üretmek | citeturn3view1turn6view2 |

### Tedarikçi olarak vermeniz gereken belge seti

Sahada en işe yarayan belge seti aşağıdaki paket olacaktır:

- **Yazılım Tanım Dosyası:** amaçlanan kullanım, desteklenen standartlar, desteklenen çıktı parametreleri.  
- **Algoritma Doğrulama Dosyası:** TENSTAND premium seti ve/veya kendi gold dataset’inize karşı beklenen-sonuç karşılaştırmaları.  
- **Sürüm ve Değişiklik Kontrolü Dosyası:** release notes, bug fixes, algoritma değişikliği etkisi.  
- **Kurulum ve Sistem Gereksinimleri:** işletim sistemi, bağımlılıklar, veri tabanı, zaman damgası mantığı.  
- **Kullanıcı Yetki Matrisi:** admin/analyst/reviewer rollerinin sınırları.  
- **Veri Bütünlüğü ve Backup Notu:** ham veri, işlenmiş veri, rapor çıktısı ve geri yükleme prosedürü.  
- **Laboratuvar Kabul Testi Paketi:** müşteri laboratuvarının yerinde yapacağı kısa OQ/PQ benzeri test senaryoları.  
- **Belirsizlik Destek Notu:** yazılımın hangi bileşenleri hesapladığı, hangi bileşenlerin laboratuvara/cihaza ait kaldığı.  

Bu paketin tamamı, kamuya açık TÜRKAK 7.11 yaklaşımı ve çekme testi belirsizlik literatürüyle uyumludur; ayrıca satış süresini kısaltır, çünkü laboratuvarın “biz bunu denetçiye nasıl anlatacağız?” sorusunu baştan cevaplar. citeturn46search1turn31view0turn30view1

### Türkiye pazarına giriş mesajı nasıl olmalı

Türkiye’de en güvenli değer önerisi şu eksende kurulmalıdır:  
**“Çekme testinde sonuç hesaplama yazılımı”** değil,  
**“TENSTAND/CRM/PT tabanlı doğrulama kanıtı sunan, ISO/IEC 17025 madde 7.11’e uygun yazılım doğrulama dosyasıyla gelen çekme testi analiz platformu.”**  

Bu söylem, hem kalite müdürüne hem laboratuvar teknik sorumlusuna hem de akreditasyon/denetim gündemine aynı anda hitap eder. Ayrıca ürünün farklılaşmasını ZwickRoell gibi büyük markalara karşı “donanım değil, doğrulanabilir yazılım kanıt paketi” üzerinden kurmanıza izin verir. citeturn7view1turn3view1turn12view1turn46search1

**ACTIONable:** Pazara giriş için en rasyonel sıralama şöyledir:  
1. **TENSTAND premium validasyon raporu** üretin.  
2. **Bir Türkçe 17025/7.11 yazılım doğrulama dosyası** hazırlayın.  
3. **Belirsizlik şablonlarını** UME/NPL mantığıyla paketleyin.  
4. Mümkünse **CRM 661 veya PT/ILC tabanlı saha demo** ekleyin.  
5. Pazarlamada “ISO 17025 compliant software” yerine **“17025 laboratuvarları için doğrulama desteği”** dilini kullanın. citeturn3view1turn12view1turn31view0turn46search1turn39search3

### Son yargı

Bu araştırmanın sonucunda ortaya çıkan en önemli ticari içgörü şu: **Türkiye’de çekme testi yazılımı satmak, aslında bir “compliance evidence pack” satmaktır.** TENSTAND, algoritmanızı uluslararası teknik zeminde ispatlar; UME çizgisi, belirsizlik ve yerel teknik dil ihtiyacını karşılar; TÜRKAK 7.11 yaklaşımı ise yazılımı laboratuvarın yönetim sistemi içine yerleştirir. Bu üçü bir araya gelmeden ürün teknik olarak iyi olsa bile denetim ve satın alma sürecinde zayıf kalır. citeturn3view1turn30view1turn46search1

Not olarak, iki noktada kaynak sınırlaması var: kamuya açık taramada tam adıyla bağımsız bir **2019 UME çekme belirsizliği rehberi** doğrulanamadı; ayrıca **R20.43’ün 2019 sonrası resmî güncel sürüm PDF’si** açık erişimde teyit edilemedi. Buna karşılık resmî olarak doğrulanabilen kaynaklar, pratik ürün stratejisini kurmak için yeterince güçlü ve tutarlı bir çerçeve sağlıyor. citeturn43view0turn28view0turn36search9