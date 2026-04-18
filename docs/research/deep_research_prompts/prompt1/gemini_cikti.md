ISO 6892-1:2019 Standardına Göre Universal Çekme Testi Verilerinin Analizi ve Python İmplementasyonu: Algoritmik ve İstatistiksel Altyapı RaporuModern malzeme bilimi ve kalite kontrol süreçlerinde, universal çekme testi makinelerinden (UTM) elde edilen ham verilerin insan müdahalesi olmadan, tam otonom yazılımlar aracılığıyla işlenmesi kritik bir gerekliliktir. Bu gereklilik, özellikle yüksek hacimli endüstriyel üretim hatlarında ve akredite laboratuvarlarda, operatör bağımlı hataları ortadan kaldırmak amacıyla doğmuştur. Geliştirmekte olduğunuz Python tabanlı stress-strain (gerilme-gerinim) analiz yazılımı, doğrudan bu ihtiyaca yanıt vermekte olup, uluslararası geçerliliğe sahip olabilmesi için ISO 6892-1:2019 standardının tüm normatif ve informatif eklerine (özellikle Annex G, Annex A ve Annex K) matematiksel düzeyde sadık kalmalıdır.Bu rapor, yazılımınızın çekirdek algoritmalarını oluşturacak olan beş temel mekanik ve istatistiksel hesaplama prosedürünü, standardın talep ettiği toleranslar, matematiksel iterasyonlar ve Python implementasyon stratejileri bağlamında en ince ayrıntısına kadar incelemektedir. Raporda sunulan teorik altyapı, doğrudan koda dönüştürülebilir mantıksal operatörler ve sözde kod (pseudo-code) bloklarıyla desteklenmiştir.KONU 1: ISO 6892-1:2019 Annex G — Elastik Modül (E) Hesaplama ProsedürüMetalik malzemelerin elastik bölgesindeki gerilme-gerinim ilişkisi, Hooke Yasası gereği teorik olarak doğrusaldır. Ancak fiziksel bir çekme testinde, numunenin makine çenelerine (grips) oturması sırasındaki kaymalar, ekstansometre bıçaklarının malzemeye nüfuz etme süreci ve makinenin kendi yapısal esnekliği (machine compliance) nedeniyle, testin en başındaki veriler ciddi oranda lineer olmayan (non-linear) mekanik gürültü içerir. Bu gürültülü başlangıç bölgesine literatürde "toe region" adı verilir. Elastisite Modülünün ($E$) yazılımsal hesaplamasında, bu bölgenin filtrelenmesi ve gerçek elastik deformasyonun gerçekleştiği lineer aralığın bulunması, $R_{p0.2}$ (offset akma dayanımı) hesaplamasının doğruluğunu doğrudan belirler. ISO 6892-1:2019 standardı, bu analizin otomatize edilebilmesi için Annex G (Normative) bölümünde çok kesin regresyon kuralları belirlemiştir.R1 ve R2 Aralığının Tanımı ve Orijinal Standart İfadesiYazılım geliştirme sürecinde genellikle ampirik olarak benimsenen "$R_1 \approx \%10 R_{p0.2}$ ve $R_2 \approx \%40 R_{p0.2}$" kuralı, endüstriyel pratiklerle şekillenmiş olsa da, ISO 6892-1:2019 Annex G'nin orijinal metniyle tam olarak örtüşmez. Standart (Referans  atfı ve Annex G metni kapsamında), lineer regresyon işlemi için sınırları şu şekilde tanımlamaktadır :Alt Sınır ($R_1$ veya $e_1$): Yaklaşık $\%10 R_{p0.2}$ civarında bir gerilme değerinden başlatılmalıdır. Bu sınırın amacı, az önce bahsedilen "toe region" içerisindeki hizalama (misalignment) hatalarını ve çene oturtma dinamiklerini hesaplamanın dışında bırakmaktır.Üst Sınır ($R_2$ veya $e_2$): Yaklaşık $\%50 R_{p0.2}$ civarında bir gerilme değerinde sonlandırılmalıdır. Üst sınırın %50 gibi görünüşte düşük bir değere çekilmesinin çok temel bir metalürjik nedeni vardır: Proportional Limit (Orantı Sınırı) ile Elastic Limit (Elastik Sınır) aynı şey değildir. Birçok malzeme, tam akma noktasına gelmeden çok önce mikro-plastik deformasyonlara (dislokasyon hareketlerine) başlar ve eğri yavaşça doğrusallıktan sapar. Sınırı %50'de tutmak, regresyonun tamamen Hookean (tam lineer) bölgede kalmasını garanti altına alır.Yazılım mimarinizde $R_1$ ve $R_2$ değerleri, sabit ve değişmez (hardcoded) parametreler olmamalıdır. Bunlar, dinamik optimizasyon algoritmasının arama uzayı (search space) sınırları olarak yapılandırılmalıdır. Standart, eğrinin durumuna göre bu sınırların kaydırılabileceğini açıkça belirtmektedir.Dairesel Bağımlılık (Circular Dependency) Problemi ve İteratif Çözüm AlgoritmasıYazılımınızın mimarisini kurarken karşılaşacağınız en karmaşık paradoks şudur:$E$ modülünü hesaplamak için $R_1$ ve $R_2$ sınırlarına ihtiyacınız vardır.$R_1$ ve $R_2$ sınırlarını belirleyebilmek için $R_{p0.2}$ değerine (offset yield) ihtiyacınız vardır.Ancak $R_{p0.2}$'nin matematiksel olarak bulunabilmesi için, gerilme-gerinim eğrisinin $\%0.2$ sağından E eğimine paralel bir doğru çizilmesi, yani $E$ modülünün halihazırda bilinmesi gerekir.Bu matematiksel tavuk-yumurta problemi (dairesel bağımlılık), ISO 6892-1:2019 Annex G'de net bir şekilde ele alınmış ve çözüm olarak iteratif (recalculation) prosedürü şart koşulmuştur. Sektörde bazı basit ve ucuz yazılımların yaptığı gibi "Eğrinin en dik yerini bul ve geç" veya sabit bir yüzde kullanmak standarda uygun değildir. Standart, "daha kesin veriler elde etmek için elastik çizgi kontrol edilmeli ve gerekirse diğer limitlerle yeniden hesaplanmalıdır" (recalculated with other limits) der.Yazılımın Python implementasyonunda bu döngü şu şekilde tasarlanmalıdır:Heuristik Başlangıç (Initial Guess): Veri setinin ilk %20'lik diliminde gerilmenin gerinime göre birinci türevi ($d\sigma/d\epsilon$) alınır. Savitzky-Golay filtresi gibi bir düzeltici uygulanarak türevin en stabil (varyansı en düşük) ve en yüksek olduğu noktanın eğimi geçici bir $E_{guess}$ olarak atanır.Geçici $R_{p0.2}$ Hesabı: Bu $E_{guess}$ eğimi kullanılarak, $\epsilon_{offset} = \epsilon - \frac{\sigma}{E_{guess}} + 0.002$ formülü üzerinden sanal bir paralel doğru oluşturulur. Bu doğrunun asıl test verisini (interpolation yoluyla) kestiği nokta kaba bir $R_{p0.2(guess)}$ olarak hesaplanır.Dinamik Sınırların Atanması: Bulunan bu geçici hedefe göre $R_1 = 0.10 \times R_{p0.2(guess)}$ ve $R_2 = 0.50 \times R_{p0.2(guess)}$ sınırları belirlenir.OLS Regresyonu ve Güncelleme: Veri seti maskelenerek sadece $R_1$ ve $R_2$ aralığında kalan noktalar izole edilir. Bu noktalar üzerinde "Ordinary Least Squares" (OLS) regresyonu çalıştırılarak yeni bir $E_{new}$ bulunur.Yakınsama (Convergence) Testi: $|E_{new} - E_{guess}| < \text{Tolerans}$ şartı aranır. Eğer tolerans sağlanmıyorsa, $E_{guess}$ değeri $E_{new}$ ile güncellenerek 2. adıma geri dönülür. Genellikle 3 veya 4 iterasyon sonunda algoritma asimptotik olarak mükemmel sonuca yakınsar.OLS Regresyonu İçin Minimum Veri Noktası (N $\ge$ 50 Kuralı)Standart, yukarıda izole edilen $R_1$ ve $R_2$ aralığında makinenin veri toplama (sampling) frekansının yeterli olup olmadığını denetler. ISO 6892-1:2019 Ek G.4.1.3 maddesi uyarınca, test sisteminin veri çözünürlüğü değerlendirme aralığında en az 50 bağımsız ölçüm noktasını (N $\ge$ 50) kaydedebilecek düzeyde olmalıdır.Yazılımınızın mimarisinde bu kural doğrudan bir istisna fırlatıcı (exception handler) olarak yer almalıdır. Eğer CSV dosyasındaki frekans (örneğin 10 Hz) düşükse ve $R_1$-$R_2$ aralığı çok hızlı geçildiği için maskelenmiş array'in boyutu 50'den küçükse (len(stress_window) < 50), yazılım OLS regresyonunu çalıştırmadan önce kullanıcıya "Uyarı: ISO 6892-1 G.4.1.3 İhlali - Değerlendirme aralığında yeterli veri noktası yok (N<50). Test frekansını artırın veya analiz güvenilirliğini düşürün" şeklinde spesifik bir log düşmelidir. Bu kural, OLS istatistiğindeki serbestlik derecesinin (degrees of freedom) anlamlı olabilmesi için Nyquist-Shannon örnekleme teorisine benzer bir gereksinimdir.R² ve Sm(rel) İstatistiksel Kabul EşikleriSıradan bir lineer regresyon kodu yazmak yeterli değildir; ISO 6892-1:2019, çizilen doğrunun kalitesinin matematiksel olarak ispatlanmasını zorunlu tutar. Bunun için yazılımın iki temel kalite metriğini hesaplaması ve denetlemesi şarttır:Belirleme Katsayısı ($R^2$): İngilizce metinde "Coefficient of determination" olarak geçen bu değer, veri noktalarının çizilen ideal doğruya ne kadar mükemmel oturduğunu gösterir. Standardın G.7.2 maddesi, $R^2$ değerinin "1'e çok yakın olması, tercihen $> 0.9995$ olması gerektiğini" açıkça (explicit) ifade eder. Python'da scipy.stats.linregress kullanıldığında dönen r_value parametresinin karesi alınarak bulunur.Eğimin Bağıl Standart Sapması ($S_{m(rel)}$): Standart tarafından en kritik görülen tolerans metriğidir. Standarda göre bu değerin $\%1$'den küçük ($< 1\%$) olması hedeflenmelidir.
Hesaplanma formülü şu şekildedir:
$$S_{m(rel)} = \left( \frac{S_m}{E} \right) \times 100$$
Burada $S_m$ (Standart deviation of the slope), regresyon doğrusunun eğiminin standart hatasıdır. İstatistiksel olarak $S_m$, artıkların (residuals) varyansına ve gerinim değerlerinin dağılımına bağlıdır:
$$S_m = \sqrt{ \frac{\sum (\sigma_i - \hat{\sigma_i})^2}{(N-2) \sum (\epsilon_i - \bar{\epsilon})^2} }$$Python'daki linregress fonksiyonu bu değeri stderr (standart error) olarak doğrudan döndürür. Yazılımınız, $S_{m(rel)}$ değerini hesapladıktan sonra eğer bu değer 1.0'dan büyükse, mevcut $R_1-R_2$ aralığının gürültülü olduğunu varsaymalı ve farklı bir bölge aramalıdır.Çoklu Doğrusal Bölge (Multiple Linear Regions) ve "Sliding Window" YaklaşımıUygulamada, test edilen malzemenin mikro yapısına (örneğin dual-phase çelikler), makine çenelerinin kaymasına veya ekstansometrenin titremesine bağlı olarak elastik bölge içinde birden fazla lineer eğim oluşabilir. ISO 6892-1:2019 bu gibi durumlarda, en uygun doğrunun bulunabilmesi için alt veya üst limitlerin değiştirilerek denemeler yapılmasını (recalculation with other limits) önerir.Yazılımınızda bunu çözmenin en profesyonel yolu Kayan Pencere (Sliding Window) algoritmasıdır. Eğer iteratif algoritma sonucu bulunan bölgede $R^2 < 0.9995$ veya $S_{m(rel)} > 1.0\%$ ise, yazılım dinamik bir arama başlatmalıdır. Örneğin, N=50 genişliğinde bir pencere oluşturulup, bu pencere $\%5 R_{p0.2}$'den başlayıp $\%60 R_{p0.2}$'ye kadar her bir veri noktası adımında (stride=1) kaydırılır. Her adımda OLS uygulanır, $R^2$ ve $S_{m(rel)}$ kaydedilir. Tüm bölge tarandıktan sonra standardın toleranslarına en uygun metrikleri sunan (örneğin $S_{m(rel)}$'i minimize eden) alt-bölge, nihai $E$ modülü bölgesi olarak kilitlenir.Python Uygulama Mimarisi (Pseudo-Code)Aşağıdaki yapı, yukarıda anlatılan tüm matematiksel ve standardizasyon kısıtlarını kapsayan sağlamlaştırılmış bir fonksiyon şemasıdır:Pythonimport numpy as np
from scipy.stats import linregress

def find_intersection_stress(strain, stress, E_slope, offset_val=0.002):
    """ E eğimine ve %0.2 offsete sahip doğrunun asıl eğriyi kestiği noktayı bulur. """
    # Gerçek uygulamada spline veya lineer interpolasyon kullanılır.
    # Burada basitleştirilmiş bir yaklaşım gösterilmektedir.
    offset_strain = strain - (stress / E_slope)
    idx = np.argmin(np.abs(offset_strain - offset_val))
    return stress[idx]

def calculate_iso_modulus(strain, stress, tol=1e-4, max_iter=15):
    """ ISO 6892-1:2019 Annex G uyarınca iteratif E modülü hesabı. """
    # 1. Heuristik Başlangıç
    d_stress = np.gradient(stress, strain)
    # Gürültüyü azaltmak için hareketli ortalama uygulanabilir
    E_guess = np.median(np.sort(d_stress)[-int(len(d_stress)*0.05):]) # En yüksek eğimlerin medyanı
    
    for i in range(max_iter):
        # 2. Geçici Rp0.2 hesabı
        Rp02_guess = find_intersection_stress(strain, stress, E_guess, 0.002)
        
        # 3. R1 ve R2 Sınırları (%10 ve %50)
        R1 = 0.10 * Rp02_guess
        R2 = 0.50 * Rp02_guess
        
        # Sınır maskelemesi
        mask = (stress >= R1) & (stress <= R2)
        strn_window = strain[mask]
        strs_window = stress[mask]
        
        # N >= 50 kuralı kontrolü
        if len(strn_window) < 50:
            raise ValueError("ISO 6892-1 İhlali: Değerlendirme aralığında N<50 veri noktası (G.4.1.3).")
            
        # 4. OLS Regresyonu
        slope, intercept, r_value, p_value, stderr = linregress(strn_window, strs_window)
        E_new = slope
        
        # 5. İstatistik Hesapları
        r_squared = r_value**2
        sm_rel = (stderr / E_new) * 100.0
        
        # 6. Yakınsama (Convergence) Kontrolü
        if abs(E_new - E_guess) / E_guess < tol:
            # ISO kalite kontrolleri
            if r_squared <= 0.9995 or sm_rel >= 1.0:
                print(f"Uyarı: İstatistiksel metrikler düşük. R^2={r_squared:.4f}, Sm(rel)={sm_rel:.2f}%")
                # İleri seviye: Burada Sliding Window algoritması tetiklenebilir.
            
            return E_new, Rp02_guess, r_squared, sm_rel
            
        # Güncelleme ve devam
        E_guess = E_new

    raise RuntimeError("Maksimum iterasyona ulaşıldı, modül yakınsamadı.")
KONU 2: ISO 6892-1:2019 Annex A.3.2 — ReH/ReL (Çift Akma) Algılama AlgoritmasıMetalik malzemelerde, özellikle tavlanmış düşük karbonlu çeliklerde, karbon ve azot atomlarının dislokasyonların etrafında toplanarak "Cottrell Atmosferleri" oluşturması, malzemenin deformasyona direnmesine neden olur. Bu direnç kırıldığında, dislokasyonlar aniden serbest kalır ve gerilmede ani bir düşüş yaşanır. Gerilme-gerinim eğrisinde gözlemlenen bu benzersiz fenomene "kesintili akma" (discontinuous yielding) denir. Eğride bir Üst Akma Dayanımı ($R_{eH}$), ardından gerilmenin dalgalandığı bir Alt Akma Dayanımı ($R_{eL}$) ve bir Lüders platosu ($A_e$) oluşur.Yazılımınızın en zorlu görevlerinden biri, eğriye bakarak malzemenin sürekli mi yoksa kesintili mi akma gösterdiğine matematiksel olarak karar vermesidir. Çünkü sürekli akmada sadece $R_{p0.2}$ aranırken, kesintili akmada $R_{eH}$, $R_{eL}$ ve $A_e$ raporlanmak zorundadır.Annex A.3.2'nin Tam Algoritma Tanımı (ReH Tespiti)ISO 6892-1:2019 Ek A.3.2 uyarınca, bir veri noktasının yazılım tarafından resmi olarak Üst Akma Dayanımı ($R_{eH}$) olarak etiketlenebilmesi için, rastgele elektriksel veya mekanik gürültüleri elimine eden iki kesin koşulun ardışık ve entegre olarak sağlanması zorunludur :Düşüş Kriteri ($\ge \%0.5$): Eğride tespit edilen lokal bir maksimum noktadan sonra, kuvvet veya gerilme değerinde en az %0.5 oranında ($\ge 0.5\%$) net bir düşüş yaşanmalıdır. Eğer sistemdeki gürültü bu seviyeden düşükse (örneğin %0.1'lik bir titreşim varsa), yazılım bunu akma noktası olarak algılamaz.Gerinim Penceresi Kriteri ($\ge \%0.05$ Uzama): Sadece anlık bir düşüş yeterli değildir. Bu düşüşü takiben gelen verilerde, kuvvetin az önce ulaşılan maksimum noktayı en az $\%0.05$ gerinim ($\Delta\epsilon \ge 0.05\%$) aralığı boyunca aşmaması şarttır.Bu iki kural, makinedeki anlık atalet sarsıntılarını, elektrik şebekesindeki dalgalanmaları veya çenedeki bir dişte yaşanan ani mikro-kaymayı akma olgusuyla karıştırmamak için geliştirilmiş mükemmel bir State Machine (Durum Makinesi) filtresidir.Çift Yield İle Rp0.2 Arasındaki Karar AğacıYazılım algoritmasında bu yapı, veriyi okuyan ve karar veren bir akış diyagramına dönüşmelidir.Adım 1: Veri setinin elastik bölgesi bittikten sonra, yazılım her yeni noktayı max_force olarak günceller ve düşüşleri izler.Adım 2: Kuvvet max_force değerinin %99.5'inin altına inerse (yani %0.5 düşerse), algoritma "Aday $R_{eH}$ Bulundu" durumuna geçer ve o anki gerinim değerini $\epsilon_{start}$ olarak kaydeder.Adım 3: Yazılım, gerinim $\epsilon_{start} + 0.0005$ ($\%0.05$ uzama) değerine ulaşana kadar gelen verileri okumaya devam eder. Eğer bu pencere içindeki hiçbir kuvvet değeri max_force değerini aşmazsa, koşul doğrulanır. Malzeme Süreksiz Akma (Discontinuous Yielding) karakteristiğindedir. $R_{eH}$ kesinleşir, yazılım hemen $R_{eL}$ aramaya geçer.Adım 4: Eğer kuvvet eğrisi bu %0.05'lik pencere tamamlanmadan yeniden max_force değerini aşıp yukarı tırmanmaya devam ederse, bu bir gürültüdür. Yazılım max_force aramaya geri döner.Adım 5: Test maksimum kuvvete ($F_m$) kadar devam eder ve eğride hiçbir zaman $\ge \%0.5$ düşüş ve $\ge \%0.05$ plato gözlemlenmezse, algoritma malzemenin Sürekli Akma (Continuous Yielding) karakterinde olduğuna hükmeder ve $R_{eH}$ modülünü kapatıp Konu 1'de anlattığımız $\%0.2$ offset yöntemiyle $R_{p0.2}$ hesaplar. Standart bu durumda $R_{eH}/R_{eL}$ raporlanmasını yasaklar.ReL Hesaplaması ve "Transient Maskeleme" KavramıAlt akma dayanımı ($R_{eL}$), $R_{eH}$ noktasından sonra gelen plastik akma bölgesi içindeki en düşük gerilme değeridir. Ancak standart metninde çok kritik bir ibare yer alır: "ignoring any initial transient effects" (herhangi bir ilk geçici etkiyi göz ardı ederek).Üst akma noktasında dislokasyonlar serbest kaldığında, malzeme aniden boşalır ve load cell (yük hücresi) bu ani atalete sönümlenerek (ringing effect) tepki verir. Eğride çok keskin bir "v" şeklinde dip oluşur. Bu dip noktası, malzemenin gerçek alt akma davranışı değil, mekanik sistemin transient (geçici rejim) tepkisidir.Standardda Explicit (Açık) Bir Değer Var Mı? Hayır. ISO 6892-1:2019, bu transient bölgenin ne kadar süreceğine dair matematiksel bir oran veya explicit bir yüzde vermez. Bunun sebebi, geçici etkinin test makinesinin rijitliğine (compliance) ve numune geometrisine göre değişmesidir. Algoritmik implementasyonda bu durum "Türevsel Stabilizasyon" veya "Hareketli Ortalama (Moving Average)" ile çözülmelidir. Genellikle, $R_{eH}$ noktasından sonra gelen ilk derivatif sıfır noktası (minimum dip noktası) ve sonrasındaki yüksek frekanslı salınım bölgesi ($\approx \%0.02$ ile $\%0.05$ gerinim arası) maskelenir. Yazılım, bu maskelenmiş transient bölgesini geçtikten sonra, plato boyunca (Lüders uzaması bitene kadar) okunan gerilme verilerinin en düşük olanını (veya stabil lokal minimumların ortalamasını) $R_{eL}$ olarak raporlar.Madde 12 "Verimlilik Kısayolu" ve %0.25 Deformasyon YanılgısıSektörde yazılım mühendisleri arasında dolaşan "İlk %0.25 deformasyon içindeki minimum değeri ReL olarak alalım, standardın 12. maddesi buna izin veriyor" şeklindeki ifade tamamen asılsız ve yanlıştır. ISO 6892-1:2019 Madde 12 (Clause 12) veya ilgili diğer kısımlarda böyle bir "verimlilik kısayolu" (efficiency shortcut) tanımı kesinlikle yoktur.Peki bu "%0.25" rakamı nereden gelmektedir? Bu değer, standardın Test Hızı Kontrolü bölümünde (Madde 10.3.3.2) yer alan hız limitlerinden yanlış kopyalanmış bir kavram karmaşasıdır. Standart, $R_{eL}$ bölgesinde testin Metot B'ye göre (Range 2) yürütülmesi durumunda, paralel uzunluk üzerindeki hedef gerinim hızının (strain rate) saniyede 0.00025 $s^{-1}$ olmasını ister. Bu bir deformasyon sınırı değil, kinematik bir HIZ ($ds/dt$) birimidir. Algoritmanız asla "ilk %0.25 gerinime bak ve bitir" şeklinde tasarlanmamalıdır. Doğrusu; akma platosunun tamamını (ki bazen %1.5'e kadar sürebilir) taramak ve minimumu bulmaktır.Lüders Bandı Genişliği (Ae) Hesaplama FormülüKesintili akma gösteren malzemelerde, $R_{eL}$ platosu bitip malzemenin tekrar toparlanarak yük taşımaya (uniform work-hardening / homojen iş-sertleşmesi) başladığı noktaya kadarki uzamaya Yüzde Akma Noktası Uzaması ($A_e$ - Lüders Strain) denir.$A_e$'nin bittiği noktayı bulmak gözle kolay olsa da algoritmik olarak karışıktır, çünkü geçiş yumuşaktır. Standart, bunun analitik tespiti için regresyon kesişim yöntemini (intersection of regression lines) önerir :Yatay Doğru: $R_{eL}$ seviyesinden geçen yatay bir regresyon doğrusu (veya ortalama plato seviyesi) çizilir.Teğet Doğru: Eğrinin yeniden tırmanışa geçtiği iş-sertleşmesi (work-hardening) bölgesinin ilk kısımlarında, türevin en yüksek olduğu noktanın eğimi (maksimum eğim çizgisi) bulunur ve bir teğet doğrusu oluşturulur.Kesişim: Bu yatay doğru ile tırmanış teğeti doğrusunun kesiştiği (intersect) noktanın gerinim değeri alınır. Bu değerden testin elastik uzama bileşeni çıkarıldığında kalan net yüzde, $A_e$ değeri olarak hesaplanır.Python Uygulama Mimarisi (Pseudo-Code)Pythonimport numpy as np

def detect_yielding_phenomena(strain, stress, drop_threshold=0.005, window_strain=0.0005):
    """
    ISO 6892-1:2019 Annex A.3.2 uyarınca ReH ve ReL tespiti.
    Sürekli akma ise (None, None) döner.
    """
    max_stress_so_far = stress
    candidate_ReH_idx = None
    ReH = None
    ReH_idx = None
    
    # 1. ReH Araması (State Machine)
    for i in range(1, len(stress)):
        if stress[i] > max_stress_so_far:
            max_stress_so_far = stress[i]
            candidate_ReH_idx = i
        else:
            # Kuvvet düştü, %0.5 kriterini kontrol et
            drop_ratio = (max_stress_so_far - stress[i]) / max_stress_so_far
            
            if drop_ratio >= drop_threshold:
                # 1. Kriter sağlandı. Şimdi %0.05 Strain Penceresi kriterini kontrol et
                start_strain = strain
                target_strain = start_strain + window_strain
                
                # Pencere içindeki verileri analiz et
                window_mask = (strain >= start_strain) & (strain <= target_strain)
                
                # Eğer pencere henüz dolmamışsa döngüye devam etmesi gerekir
                # (Gerçek veri akışında bu mantık bir buffer ile çözülür)
                if np.any(window_mask):
                    stress_in_window = stress[window_mask]
                    # Eğer penceredeki hiçbir değer ReH'ı aşmıyorsa, tespit başarılıdır
                    if np.all(stress_in_window <= max_stress_so_far):
                        ReH = max_stress_so_far
                        ReH_idx = candidate_ReH_idx
                        break # Discontinuous Yielding kanıtlandı!

    # 2. Karar Ağacı
    if ReH is None:
        # Sürekli akma. Rp0.2 algoritmasını çağırmak üzere geri dön.
        return None, None
        
    # 3. ReL Araması ve Transient Maskeleme
    # İlk transient düşüşünü atlamak için ReH'dan sonraki türevin ilk pozitife döndüğü
    # dip noktasını bul ve oraya kadar olan kısmı maskele.
    sub_stress = stress
    sub_strain = strain
    
    transient_end_idx = 0
    for j in range(1, len(sub_stress)-1):
        if sub_stress[j] < sub_stress[j-1] and sub_stress[j] < sub_stress[j+1]:
            transient_end_idx = j # İlk lokal minimum (Ringing effect dibi)
            break
            
    # Transient sonrası Lüders platosundaki minimum değer ReL olarak atanır
    # Plato genellikle work hardening (iş sertleşmesi) başlayana kadar sürer.
    plato_stress = sub_stress[transient_end_idx:]
    ReL = np.min(plato_stress)
    
    return ReH, ReL
KONU 3: ISO 6892-1:2019 Annex A.3.6.1 — Kırılmadaki Toplam Uzama (At) TespitiTestin sonlanma anı olan "Kopma" (Fracture) hadisesini yazılımsal olarak yakalamak, sanıldığı kadar trivial (basit) bir problem değildir. Malzeme koptuğunda load cell sıfıra anında düşmez; makinenin mekanik ataleti, çenelerin sekmesi ve numunenin elastik geri yaylanması (springback) nedeniyle kuvvet verisinde sönümlenen bir gürültü profili oluşur. Ayrıca boyun verme (necking) işlemi sırasında kuvvet zaten düşüş eğilimindedir. Yazılımınız, yavaş bir boyun verme düşüşü ile asıl kopma sarsıntısını birbirinden ayırmak zorundadır.Bu otonom tespiti sağlayabilmek için ISO 6892-1:2019 Ek A.3.6.1, Force-drop method (Kuvvet Düşüşü Metodu) isimli standart bir matematiksel filtre tanımlamıştır.Force-Drop Method'un Tam Tanımı ve İki Ana KriterStandart, kırılmanın "etkili" (effective) kabul edilebilmesi için veri toplama yazılımının art arda gelen ardışık ölçüm noktaları arasındaki değişimleri denetlemesini ve aşağıdaki iki koşuldan yola çıkmasını öngörür :Ani Düşüş Kriteri (Türevsel İvme): Birinci kriter, kuvvetin düşüş ivmesiyle ilgilidir. Kısaca, mevcut adımdaki kuvvet düşüşünün, bir önceki adımdaki kuvvet düşüşünden 5 kat daha şiddetli olması gerekir. Formülasyon:
$|F_{n+1} - F_n| > 5 \times |F_n - F_{n-1}|$
Matematiksel olarak bu durum, kuvvet-zaman eğrisinin ikinci türevinin aniden büyük bir pik yapmasıdır (jerk). Boyun verme sırasında kuvvet yavaşça düşer, düşüş hızı stabildir ($F_{drop} \approx 1x$). Ancak parça ortadan yarıldığında kuvvet bir anda sıfıra yığılır ve düşüş ivmesi bir anda önceki adımın 5 katını aşar. Standart, bu 5x düşüşün hemen ardından kuvvetin maksimum çekme kuvvetinin ($F_m$) %2'sinin altına inmesiyle bu kırılmanın teyit edilmesini bekler.%2 Kriteri (Mutlak Eşik): İkinci kriter, düşüş ivmesinden bağımsız olarak mutlak kuvvet değerine bakar. O anki ölçülen kuvvet ($F_{n+1}$), test boyunca kaydedilen maksimum çekme kuvvetinin (Ultimate Tensile Strength - $F_m$) %2'sinden küçük olmalıdır.$F_{n+1} < 0.02 \times F_m$AND mi OR İlişkisi mi? Yumuşak vs. Sert Malzeme AyrımıKullanıcı sorusunda belirtilen en büyük kafa karışıklığı bu iki kriterin nasıl bağlanacağıdır (Aynı anda mı yoksa OR ilişkisi mi?). ISO standardının orijinal metninde "ve/veya" (and/or) mantıksal mimarisi vardır. Bu durum OR (Veya) ilişkisi olarak implemente edilmelidir. Nedenleri tamamen malzeme bilimiyle ilgilidir:Sert ve Gevrek (Brittle) Malzemeler: Yüksek mukavemetli çelikler, karbon fiber kompozitler veya titanyum alaşımları boyun vermez; test sırasında aniden, bir patlama sesiyle koparlar. Ani bir "snap" gerçekleşir. Bu malzemelerde Kriter 1 (5x ani düşüş) devreye girer ve kopmayı milisaniyeler içinde yakalar.Yumuşak ve Sünek (Ductile) Malzemeler: Tavlanmış alüminyum, kurşun veya çok düşük karbonlu çelikler koparken aniden ayrılmazlar. Sakız gibi uzarlar, boyun verme bölgesi incelir, incelir ve iki parça yavaşça birbirinden kopar. Bu durumda 5 katı hızlı bir ivme sıçraması (Kriter 1) hiçbir zaman oluşmayabilir. Bu noktada yazılım kopmayı kaçırmamak için Kriter 2'ye (%2 mutlak eşiğe) güvenir. Kuvvet yavaşça süzülüp maksimum kuvvetin %2'sinin altına indiğinde yazılım testi sonlandırır.Bu bağlamda yazılıma dışarıdan "Bu malzeme sünek mi, sert mi?" diye sormaya gerek yoktur. İki kriter de if (condition_1) or (condition_2): şeklinde aynı andaki OR kapısına bağlandığında tüm malzeme spektrumu yakalanmış olur.At ve A Arasındaki Resmi Farklılıklar (Etiketleme Standardizasyonu)Test bittikten sonra yazılımın veri tabanına yazacağı çıktı parametrelerinin isimlendirmesi, ISO validasyonu için çok önemlidir.$A_t$ (Kırılmadaki Toplam Yüzde Uzama - Percentage total elongation at fracture): Force-drop algoritmasının kırılmayı algıladığı "tam o an"daki ekstansometre (uzama) değeridir. Bu değerin içinde hem malzemenin yediği kalıcı (plastik) deformasyon, hem de o an hala numunenin içinde yüklü olan elastik deformasyon enerjisi (yaylanma payı) bir aradadır.$A$ (Kırılma Sonrası Yüzde Uzama - Percentage elongation after fracture): Parça koptuktan, kuvvet sıfıra düştükten ve numune rahatlayıp elastik olarak geri yaylandıktan (springback) sonra parçanın üzerinde kalan "sadece kalıcı" uzamadır. Genellikle teknisyenler kopan parçaları masaya alıp birleştirerek kumpasla ($L_u - L_0$) ölçer. Ancak gelişmiş UTM yazılımları, $A_t$ değerinden elastik uzamayı ($\frac{Stress_{fracture}}{E}$) matematiksel olarak çıkararak $A$ değerini tahmin edebilir.Force-drop metoduyla bulunan ham uzama verisi, raporlara kesinlikle $A_t$ olarak etiketlenmelidir. ASTM standartlarında benzer bir durum için $A_f$ terimi kullanılabilse de, ISO 6892-1:2019'da tanımlanan resmi sembol $A_t$'dir.Python Uygulama Mimarisi (Kırılma Tespiti)Pythonimport numpy as np

def detect_fracture_point(force):
    """
    ISO 6892-1:2019 Annex A.3.6.1 Force-drop algoritması.
    Kırılma anının indeksini döndürür.
    """
    if len(force) < 3:
        return len(force) - 1
        
    Fm_max = np.max(force)
    threshold_2_percent = 0.02 * Fm_max
    
    # 0 ve 1. indekslerde önceki delta ölçülemeyeceği için 2'den başlıyoruz
    for n in range(2, len(force) - 1):
        
        # O anki kuvvet değeri
        F_next = force[n+1]
        
        # Delta hesaplamaları (Mutlak düşüş hızları)
        delta_F_current = abs(force[n+1] - force[n])
        delta_F_prev = abs(force[n] - force[n-1])
        
        # KRİTER 1: Ani ivmeli düşüş (>5x) AND sonrasında %2'nin altına inme beklentisi
        # (Yazılımın gerçek zamanlı çalışmasında 5x yakalandığında test hemen sonlandırılır)
        condition_1 = (delta_F_current > 5.0 * delta_F_prev)
        
        # KRİTER 2: Yumuşak malzemeler için %2 mutlak düşüş limiti
        condition_2 = (F_next < threshold_2_percent)
        
        if condition_1 or condition_2:
            # Kırılma tespit edildi!
            return n+1 
            
    # Eğer döngü biter ve bulunamazsa, testin son noktası kırılma kabul edilir
    return len(force) - 1
KONU 4: ISO 6892-1:2019 Annex K — Ölçüm Belirsizliği BütçesiSanayi 4.0 ve kalite akreditasyonları (özellikle ISO/IEC 17025) kapsamında, bir UTM yazılımının sadece test sonuçlarını vermesi artık yeterli görülmemektedir. Akredite laboratuvarlar, yazılımın hesapladığı $R_{p0.2}$ veya $E$ gibi değerlerin yanında bir $\pm U$ (Ölçüm Belirsizliği) değeri de talep etmektedir. Yazılımınızın küresel pazarda "Premium" seviyede konumlanabilmesi için GUM (Guide to the Expression of Uncertainty in Measurement) entegrasyonu şarttır.Annex K'nın Varlığı ve EvrimiEski nesil mühendisler belirsizlik konusunu ISO 6892-1'in eski (2009) versiyonlarındaki Annex J veya Annex H üzerinden hatırlayabilir. Ancak yazılımınızın taban aldığı güncel ISO 6892-1:2019 standardında, yapısal bir revizyon yapılmış ve Ölçüm Belirsizliği tahminleri tamamen Annex K (Informative) - Estimation of the uncertainty of measurement başlığı altında toplanmıştır. Kullanıcının veya piyasadaki bazı eski kaynakların "Annex H" iddiası geçersizdir; 2019 versiyonunda Annex K doğrudan GUM dokümanına (ISO/IEC Guide 98-3) atıfta bulunarak prosedürü açıklar.Bu yapı, ülkemizdeki TÜBİTAK UME (Ulusal Metroloji Enstitüsü) tarafından yayınlanan "Çekme Deneyinde Ölçüm Belirsizliği" rehberleriyle de %100 uyumludur; çünkü UME rehberleri de doğrudan GUM standartlarını Türkçeleştirerek referans almaktadır. Yazılımınızın belirsizlik modülü GUM'un kısmi türevler (partial derivatives) ve hassasiyet katsayıları (sensitivity coefficients) yaklaşımını kullandığı sürece, tüm ulusal ve uluslararası denetimlerden geçecektir.Belirsizlik Bütçesi Formüle Edilen Parametreler ve BileşenleriAnnex K uyarınca belirsizlik bütçesinin (uncertainty budget) oluşturulması beklenen temel mekanik parametreler şunlardır:Elastisite Modülü ($E$)Akma Dayanımları ($R_{eH}, R_{eL}, R_{p0.2}$)Çekme Dayanımı ($R_m$)Kırılma Sonrası Yüzde Uzama ($A$) ve Kesit Daralması ($Z$).Bu nihai sonuçların belirsizliğini (Type A ve Type B birleşik belirsizliklerini) bulabilmek için yazılımın dışarıdan girdi varyanslarına ihtiyacı vardır. Girdi belirsizlik bileşenleri şunlardır:Kuvvet Ölçümü ($u(F)$): Load cell'in kalibrasyon sertifikasından ve standardından (ISO 7500-1) gelir. Örneğin, Sınıf 1 bir makine için kuvvet ölçüm hatası %1 civarındadır.Uzama Ölçümü ($u(L_e)$): Ekstansometrenin (ISO 9513) çözünürlüğünden ve sınıfından gelir. (Örn: Sınıf 0.5)Kesit Alanı ($u(S_0)$): Numune boyutlarını ölçen mikrometrenin kalibrasyonundan kaynaklanır.Algoritmik Sapma ($u_{slope}$ veya $S_{m}$): Sadece donanım değil, algoritmanın kendisi de bir belirsizlik yaratır. Konu 1'de hesapladığımız regresyon eğim sapması ($S_m$), doğrudan belirsizlik bütçesine eklenir.Modül E ve Rp0.2 İçin Hesaplama FormülüAnnex K ve onun atıfta bulunduğu CWA 15261-2 dokümanı, Elastisite Modülünün bağıl birleşik standart belirsizliğini ($u_c(E)/E$), bileşenlerin karelerinin toplamının karekökü (GUM kuralı) ile şu formülasyonla tanımlar :$$\frac{u_c(E)}{E} = \sqrt{ \left( \frac{u(L_e)}{L_e} \right)^2 + \left( \frac{u(S_0)}{S_0} \right)^2 + \left( \frac{u(S_{slope})}{S_{slope}} \right)^2 }$$Burada:$L_e$: Ekstansometrenin temel ölçüm uzunluğu.$S_0$: Numunenin başlangıç kesit alanı.$S_{slope}$: Kuvvet-uzama eğrisinin hesaplanan algoritmik eğimi.$u(x)$ değerleri, her bir değişkenin ilgili Type B (kalibrasyon) standart belirsizlikleridir.$R_{p0.2}$ (offset yield) için hesaplama formülü biraz daha karmaşıktır çünkü $R_{p0.2}$, hem gerilme formülüne ($\sigma = F/S_0$) hem de yatay offset kaymasından dolayı $E$ modülüne bağımlıdır. GUM uyarınca $R_{p0.2}$'nin belirsizliği, kısmi türevlerle şu şekilde türetilir:$$\frac{u_c(R_{p0.2})}{R_{p0.2}} = \sqrt{ \left( \frac{u(F)}{F} \right)^2 + \left( \frac{u(S_0)}{S_0} \right)^2 + \left( c_E \cdot \frac{u(E)}{E} \right)^2 }$$Yazılım mimarinizde, kullanıcının UI üzerinden "Load Cell Accuracy (%)", "Extensometer Accuracy (%)" ve "Micrometer Tolerance (mm)" gibi parametreleri girebileceği bir "Settings" paneli olmalıdır. Yazılım test sonunda bu formülleri işleterek $\pm U(R_{p0.2})$ Genişletilmiş Belirsizlik (Expanded Uncertainty, $k=2, \%95$ güven) değerini rapora otomatik yansıtmalıdır.KONU 5: Dixon Q Testi — Batch Kalite Kontrol Modülü İçin Outlier (Aykırı Değer) TespitiEndüstriyel laboratuvarlarda tek bir test yapılmaz; genellikle bir üretim partisinden (batch) alınan örneğin 5 adet çelik çekme numunesi test edilir. Bu 5 testin $R_m$ sonuçları şu şekilde gelebilir: ``. İnsan gözüyle "390" değerinin numunedeki bir döküm boşluğundan (porozite) veya operatör hatasından kaynaklanan bir aykırı değer (outlier) olduğu açıktır. Ancak parti ortalamasını müşteriye gönderecek olan yazılımın, bu 390 değerini istatistiksel bir ispatla listeden atması gerekir. Yazılımınızın kalite kontrol modülü için Dixon Q testi en uygun seçimdir.N $\le$ 5 Durumunda Neden Grubbs Yerine Dixon Tercih Edilmelidir?Sektörde sıklıkla bilinen Grubbs testi, veri setinin genel ortalaması (mean) ve standart sapması (standard deviation) üzerinden çalışır. Gauss dağılımına oturan $N > 10$ gibi büyük örneklem gruplarında Grubbs mükemmel çalışır. Ancak çekme testleri gibi $N=3, 4, 5$ adet yapılan deneylerde Grubbs testi çok tehlikeli bir istatistiksel zaafiyete düşer: Swamping (Bataklık) Etkisi. Örneklem küçücük olduğu için, 390 gibi bir ekstrem değerin varlığı, tüm veri setinin genel ortalamasını kendisine doğru çeker ve standart sapmayı devasa bir oranda şişirir. Bu şişme nedeniyle, Grubbs algoritması 390 değerinin bir "aykırı değer" olduğunu fark edemeyip testi normal kabul eder.Dixon Q Testi ise standart sapma veya ortalama kullanmaz. Parametrik olmayan (rank-based) mantığıyla çalışır. Sadece şüpheli değerin en yakın komşusuna olan mesafesinin, verinin toplam açıklığına (range) bölünmesi prensibiyle çalışır. Bu nedenle, çok küçük numune gruplarındaki (özellikle $N=3$ ila $7$) aşırı uçları bulmakta Dixon Q Testi istatistiksel olarak çok daha güçlü ve güvenilirdir.Dixon Q Testi Varyantları (Q10, Q11, Q21) ve FormülasyonlarıMatematikçi W. J. Dixon tarafından 1950'lerde önerilen bu test, veri sayısına göre küçük varyantlara sahiptir. Gözlem verileri küçükten büyüğe sıralandıktan ($X_1 \le X_2 \le \dots \le X_n$) sonra şu formüller kullanılır :$r_{10}$ (veya $Q_{10}$) Varyantı ($3 \le n \le 7$ için): Bir uçtaki tek bir değeri test etmek için kullanılır. UTM yazılımınızda $n \le 5$ olacağı için kullanılacak yegane formül budur.Eğer en küçük değer ($X_1$) şüpheliyse: $Q_{exp} = \frac{X_2 - X_1}{X_n - X_1}$Eğer en büyük değer ($X_n$) şüpheliyse: $Q_{exp} = \frac{X_n - X_{n-1}}{X_n - X_1}$$r_{11}$ ($Q_{11}$) Varyantı ($8 \le n \le 10$ için): Karşıt uçta da bir şüpheli değer olma ihtimalini absorbe etmek için payda (range) daraltılır.$r_{21}$ ($Q_{21}$) Varyantı ($11 \le n \le 13$ için): Aynı yığılmada birden fazla şüpheli değer olması ihtimaline karşı tasarlanmıştır.N=3, 4, 5, 6, 7 İçin Q Critical Values (Kritik Değerler) TablosuHesaplanan $Q_{exp}$ değeri, laboratuvarın belirlediği anlamlılık düzeyindeki (Alpha, $\alpha$) kritik tablo değerinden ($Q_{crit}$) büyükse, o veri noktası resmi olarak aykırı değer kabul edilir. UTM yazılımınızın kod tabanında gömülü olması gereken (hard-coded) Dixon tablo değerleri şöyledir :Test Sayısı (n)α=0.05 (%95 Güven Düzeyi)α=0.01 (%99 Güven Düzeyi)30.9700.99440.8290.92650.7100.82160.6250.74070.5680.680İteratif Uygulama (Bir Outlier Çıkarıp Tekrar Test) Mümkün mü?Mühendislerin aklına sıklıkla gelen "Bir hatalı numuneyi çıkardım, listede $N=4$ kaldı. Kalanlara bir daha Dixon testi uygulayayım mı?" sorusunun yanıtı istatistik biliminde "Masking Effect" (Maskeleme Etkisi) tehlikesidir.Dixon Q testi iteratif olarak uygulandığında, eğer veri setinde birbirine çok yakın bozuk iki tane uç değer varsa (örneğin iki tane üst üste binmiş 390 ve 391 değeri), test bu ikisini birbirinin en yakın komşusu olarak görecek ve pay (gap) sıfıra yaklaşacaktır. Bu maskeleme nedeniyle test, "İkisi de arızalı" demek yerine "İkisi de normal" çıktısı verebilir. Bu nedenle yazılım algoritmanız, Dixon testini aynı küme üzerinde sadece tek bir pass (tek sefer) olarak çalıştıracak şekilde kilitlenmelidir.ISO 5725 ve ISO/IEC 17025 Bağlamında ReferansıGeliştirdiğiniz yazılımın kullanacağı bu Dixon outlier eliminasyon modülü, uluslararası normlardan yoksundur sanılmamalıdır. Ölçüm metotlarının doğruluğu, tekrarlanabilirliği ve laboratuvarlar arası karşılaştırmaların standartı olan ISO 5725-2 (Accuracy of measurement methods and results) metni, laboratuvar verilerindeki straggler (sapan) ve statistical outlier (istatistiksel aykırı değer) elemesi için Grubbs ile birlikte Dixon Q testini resmi metodoloji olarak kabul eder. Yazılımın UI (kullanıcı arayüzü) kısmında bir "Outlier Filtering (ISO 5725-2 Compliant)" butonu eklemek, uygulamanızın mühendislik itibarını yükseltecektir.Python Uygulama Mimarisi (Batch Outlier Kontrolü)Aşağıdaki Python algoritması, bir parti numune kümesindeki mekanik değerleri alıp ISO 5725 referanslı bir Q-10 filtrelemesinden geçirerek güvenilir ortalamayı döndürmeye hazırdır:Pythonimport numpy as np

def filter_outliers_dixon(data_list, confidence_level='95'):
    """
    N=3 ila 7 arasındaki veri setlerinde Dixon's Q test (Q10) uygulayarak
    aykırı değeri (outlier) listeden filtreler. Sadece tek iterasyon çalışır.
    """
    n = len(data_list)
    if n < 3 or n > 7:
        # N>7 ise bu fonksiyon Grubbs testine veya Q11/Q21'e havale etmelidir.
        return data_list, None
        
    # Dixon Kritik Değerler Tablosu (N: Qcrit)
    q_dict_95 = {3: 0.970, 4: 0.829, 5: 0.710, 6: 0.625, 7: 0.568}
    q_dict_99 = {3: 0.994, 4: 0.926, 5: 0.821, 6: 0.740, 7: 0.680}
    
    Q_crit = q_dict_95[n] if confidence_level == '95' else q_dict_99[n]
    
    # İstatistiksel analizler için sıralı (ranked) array gereklidir
    sorted_arr = np.sort(data_list)
    val_range = sorted_arr[-1] - sorted_arr
    
    if val_range == 0:
        return data_list, None # Bütün değerler birbirinin tamamen aynısı
        
    # En küçük ve en büyük şüpheli adaylar için Q değerlerinin hesaplanması
    # Q10 formulasyonu: Gap / Range
    Q_min_candidate = (sorted_arr - sorted_arr) / val_range
    Q_max_candidate = (sorted_arr[-1] - sorted_arr[-2]) / val_range
    
    # Maskeleme etkisini kırmak için sadece en büyük sapma gösteren ucu test et
    outlier_value = None
    filtered_data = list(sorted_arr)
    
    if Q_max_candidate > Q_crit and Q_max_candidate >= Q_min_candidate:
        outlier_value = filtered_data.pop(-1)
    elif Q_min_candidate > Q_crit and Q_min_candidate > Q_max_candidate:
        outlier_value = filtered_data.pop(0)
        
    # Geriye filtrelenmiş N-1 liste ve atılan değer döndürülür
    return filtered_data, outlier_value