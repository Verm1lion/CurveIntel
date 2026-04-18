# ISO 6892-1:2019 ve Dixon Q için implementasyona hazır teknik notlar

Aşağıda, standardın **açık söylediği** kısımları normatif dayanakla, standardın **açık söylemediği** yerleri ise ayrı ayrı “uygulama önerisi” olarak verdim. ISO metnini telif nedeniyle uzun alıntılamadan, doğrudan koda çevrilebilir şekilde yeniden ifade ettim. Her başlık altında kısa pseudo-code da ekledim.

## Annex G kapsamında elastik modül hesabı

- **R1 ve R2 tanımı:** Annex G’de elastik modül için doğrusal regresyon, alt gerilme sınırı \(R_1\) ile üst gerilme sınırı \(R_2\) arasında yapılır; alternatif olarak gerilme yerine uzama sınırları \(e_1\) ve \(e_2\) kullanılabilir. Standardın önerdiği başlangıç noktaları şunlardır:  
  \[
  R_1 \approx 0.10 \times (Re_H \text{ veya } Rp_{0.2})
  \]
  \[
  R_2 \approx 0.40 \times (Re_H \text{ veya } Rp_{0.2})
  \]
  Dolayısıyla senin yazdığın “\(R_1 \approx \%10\,Rp0.2\), \(R_2 \approx \%40\,Rp0.2\)” ifadesi, **malzeme süreksiz akma göstermiyorsa** ve referans büyüklük \(Rp0.2\) seçiliyorsa doğrudur; ama standardın gerçek ifadesi “\(Re_H\) **veya** \(Rp0.2\)” şeklindedir. Ayrıca Annex A.3.7, özellikle \(Rp0.2\) değerlendirmesinde yine yaklaşık %10–%40 aralığını tavsiye eder. citeturn43view0turn42view2

- **Regresyon denklemi ve yüzde/fraction ayrımı:** Annex G’de doğrusal model,
  \[
  R = E\cdot \frac{e}{100} + b
  \]
  şeklindedir; burada \(e\) “percentage extension” yani **yüzde** cinsindedir. Kodda bunu karıştırmamak için en güvenlisi, CSV’den gelen uzamayı önce **mühendislik şekil değiştirmesi** \(\varepsilon=e/100\) biçimine çevirmek ve sonra
  \[
  R = E\varepsilon + b
  \]
  olarak fit etmektir. Standardın semboller tablosu ayrıca “yüzde değerler kullanılıyorsa 100 faktörünün gerekli” olduğunu özellikle hatırlatır. citeturn43view0turn42view1

- **Dairesel bağımlılık nasıl çözülüyor:** ISO 6892-1:2019 bu problemi zorunlu bir iterasyonla çözmüyor. Çözüm iki parçalıdır:  
  Birincisi, Annex G açıkça “\(Re_H\) veya \(Rp0.2\) seviyesine kadar eğri bilinmiyorsa, modül ölçümünden önce bir **pre-test** yapılmalıdır” der.  
  İkincisi, standardın kendisi “proof strength için elastik kısmın eğimini belirlemek üzere Annex G’yi kullanmak **zorunlu değildir**” diye not düşer; yani \(Rp0.2\) ofset doğrusunu çizmek için kullanılan \(m_E\) ile “Annex G’ye göre resmi \(E\)” aynı şey olmak zorunda değildir. Annex A.3.7 de \(Rp0.2\) değerlendirmesi için ayrı bir eğim bulma prosedürü verir. Sonuç: **standart seviye çözüm pre-test + ayrı slope hesabıdır; zorunlu iteratif çözüm değildir.** Tek bir CSV’den her ikisini birden çıkaracaksan, bu artık ISO’nun açıkça tanımlamadığı bir “yazılım politikası” olur. En güvenli yaklaşım, yazılımda iki mod açmaktır:  
  **(a)** `strict_annex_g=True` ise kullanıcıdan beklenen \(Re_H\) veya \(Rp0.2\) / pre-test metadata iste;  
  **(b)** `best_effort_single_test=True` ise önce Annex A.3.7 tarzı bir `mE_offset` hesapla, sonra \(Rp0.2\)’yi bul, sonra Annex G aralığını o tahminle başlat; ama raporda bunun “same-test approximation” olduğunu belirt. citeturn43view0turn42view0turn42view1

- **Minimum veri noktası gereksinimi:** Evet, standardın metninde fiilen **“en az 50 nokta”** şartı vardır. Annex G, örnekleme frekansının ilgili aralıkta \((R_1,R_2)\) **minimum 50 ölçüm değeri** üretecek şekilde seçilmesini ister; ayrıca regresyon kalitesi değerlendirilirken de “dikkate alınan veri noktası sayısı en az 50 olmalıdır” denir. Bu, UI’da “soft warning” değil, ben olsam doğrudan `ValidationError` yaparım. citeturn43view0

- **Örnekleme frekansı formülü:** Annex G.1’de minimum veri toplama frekansı,
  \[
  f_{\min}=\frac{N\,E\,\dot e}{R_2-R_1}
  \]
  olarak verilir. Burada \(N\) ilgili aralıktaki nokta sayısıdır; pratikte standardın söylediği minimum \(N=50\)’dir. Eğer MPa ve s\(^{-1}\) kullanıyorsan formül doğrudan Hz verir. Kod karşılığı:
  ```python
  f_min = N * E_est * strain_rate_s_inv / (R2 - R1)
  ```
  Buradaki `E_est`, ilk kaba elastik eğim tahmini olabilir; sampling plan bu değere göre kurulmalıdır. citeturn43view0

- **R² kabul eşiği:** Standarda göre \(R^2\) “1’e yakın olmalıdır” ve parantez içinde açıkça **\(>0.9995\)** denir. Aynı metin, **\(R^2 < 0.9995\)** ise modülün belirlenmemesi gerektiğini de söyler. Yani bu eşik tavsiye gibi yazılsa da, sonraki cümle onu fiilen `reject` kriterine dönüştürüyor. citeturn43view0

- **Sm(rel) formülü ve eşiği:** Standardın semboller kısmında
  \[
  S_{m(\mathrm{rel})}=\frac{S_m}{E}\times 100\%
  \]
  tanımı verilir. Annex G, bunun **%1’den küçük olması gerektiğini** söyler. Standardın açık verdiği şey \(S_{m(\mathrm{rel})}\) formülüdür; \(S_m\)’nin OLS karşılığına ait ayrıntılı istatistik formülü standarda yazılmamıştır. Kodda basit doğrusal regresyon için doğal uygulama şu olur:
  \[
  S_m=\sqrt{\frac{\sum_{i=1}^{n}(R_i-\hat R_i)^2}{(n-2)\sum_{i=1}^{n}(\varepsilon_i-\bar\varepsilon)^2}}
  \]
  ve sonra
  \[
  S_{m(\mathrm{rel})}=100\,\frac{S_m}{E}.
  \]
  Eğer \(x\) ekseninde yüzde uzama kullanıyorsan, önce slope standard error’ünü “MPa/%” olarak hesaplayıp sonra 100 ile çarparak MPa’a çevirmen gerekir. citeturn42view1turn43view0turn39view0

- **Birden fazla lineer bölge varsa ne yapılmalı:** Standardın önerisi otomatik tek-adımlı bir “en iyi pencere seçicisi” değil, **interaktif yöntemdir**: least-squares ile en iyi doğru bulunur, sonra büyütülmüş diyagram üzerinde **görsel uyum** değerlendirilir, gerekli ise alt/üst sınırlar kaydırılarak yeniden hesap yapılır. Annex A.3.7 de “bilinmeyen karakteristikteki numunelerde önceden sabitlenmiş gerilme limiti kullanılmamalı”, bunun yerine kayan segment temelli yöntemler kullanılmalı ve kullanıcı temsil gücü zayıf bölgeleri dışlayabilmelidir der. Eğer malzeme “düz bir elastik doğru” sergilemiyorsa, örneğin dökme demir gibi, standarda göre **E raporlanmamalıdır**. Bu yüzden otomatik yazılımda makul davranış şudur: aday pencereleri tarayıp \(n\ge 50\), \(R^2>0.9995\), \(S_{m(rel)}<1\%\) koşullarını sağlayanları bul; birden fazla güçlü aday varsa kullanıcıyı uyar; hiçbiri yoksa `E_not_determinable` dön. citeturn43view0turn42view2

- **Pratik raporlama notu:** Annex G test raporunda \(R_1,R_2\) veya \(e_1,e_2\), aralıktaki nokta sayısı, \(E\), belirsizlik ve \(R^2\) ya da \(S_m/S_{m(rel)}\) bilgisinin bulunmasını ister. Yazılımının auditability tarafı için bunları JSON metadata olarak saklaman çok iyi olur. citeturn6view2

- **Doğrudan koda çeviri önerisi:**  
  1. CSV’den \(F,\Delta L\) oku.  
  2. \(R=F/S_0\), \(\varepsilon=\Delta L/L_e\) hesapla.  
  3. Eğer `strict_annex_g` ve `expected_yield` bilinmiyorsa hata ver; değilse kaba `yield_ref` ile \(R_1,R_2\) başlat.  
  4. OLS fit yap.  
  5. \(R^2\), \(S_{m(rel)}\), `n_points` kontrol et.  
  6. Aday pencere taraması ile sınırları gerektiğinde yukarı/aşağı kaydır.  
  7. En iyi pencereyi seç, \(E\), \(b\), \(x_{y=0}=-b/E\) hesapla.  
  8. Rapora kullanılan pencereyi ve kalite metriklerini yaz. citeturn43view0turn42view1

Standarttaki bu mantığı doğrudan uygulayan bir pseudo-code iskeleti aşağıdaki gibi kurulabilir. citeturn43view0turn42view0

```python
from dataclasses import dataclass
import numpy as np

@dataclass
class ElasticFit:
    E_MPa: float
    intercept_MPa: float
    r2: float
    sm_MPa: float
    sm_rel_pct: float
    idx_lo: int
    idx_hi: int
    n_points: int

def ols_elastic_fit(strain_frac, stress_mpa, i0, i1):
    x = strain_frac[i0:i1+1]
    y = stress_mpa[i0:i1+1]
    n = len(x)
    xbar = x.mean()
    ybar = y.mean()

    sxx = np.sum((x - xbar)**2)
    sxy = np.sum((x - xbar) * (y - ybar))
    E = sxy / sxx
    b = ybar - E * xbar

    yhat = E * x + b
    ss_res = np.sum((y - yhat)**2)
    ss_tot = np.sum((y - ybar)**2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    sm = np.sqrt(ss_res / ((n - 2) * sxx))
    sm_rel = 100.0 * sm / E

    return ElasticFit(E, b, r2, sm, sm_rel, i0, i1, n)

def annex_g_fit(strain_frac, stress_mpa, yield_ref_mpa, strict=True):
    # strict=True: pre-test / prior yield_ref zorunlu kabul edilir
    if strict and yield_ref_mpa is None:
        raise ValueError("Annex G strict mode requires expected ReH or Rp0.2 from pre-test/prior info.")

    R1 = 0.10 * yield_ref_mpa
    R2 = 0.40 * yield_ref_mpa

    candidate_windows = []
    # Tavsiye: seed etrafında birkaç pencere dene
    bands = [(0.10, 0.40), (0.10, 0.20), (0.20, 0.30), (0.30, 0.40)]
    for lo_frac, hi_frac in bands:
        lo = lo_frac * yield_ref_mpa
        hi = hi_frac * yield_ref_mpa
        idx = np.where((stress_mpa >= lo) & (stress_mpa <= hi))[0]
        if len(idx) < 50:
            continue
        fit = ols_elastic_fit(strain_frac, stress_mpa, idx[0], idx[-1])
        if fit.r2 >= 0.9995 and fit.sm_rel_pct < 1.0 and fit.n_points >= 50:
            candidate_windows.append(fit)

    if not candidate_windows:
        raise ValueError("E not determinable per Annex G quality criteria.")

    # ISO görsel/interaktif seçim istiyor; otomatik yazılım için konservatif skor:
    best = max(candidate_windows, key=lambda z: (z.r2, -z.sm_rel_pct, z.n_points))
    strain_offset_zero = -best.intercept_MPa / best.E_MPa
    return best, strain_offset_zero
```

## Annex A.3.2 kapsamında ReH ve ReL algılama

- **Annex A.3.2’nin açık algoritması:** Üst akma dayanımı \(Re_H\), kuvvet-zorlanma eğrisinde,  
  **(i)** kuvvetin en az **%0.5** düştüğü bir düşüşten **önceki en yüksek kuvvete** karşılık gelen gerilme,  
  **ve**  
  **(ii)** bu düşüşten sonra en az **%0.05 strain** boyunca kuvvetin bu önceki maksimumu aşmadığı bir bölge olması  
  koşullarıyla tanımlanır. Bu yüzden kullanıcıdaki iki koşullu anlatım öz olarak doğrudur: sayıların kendisi Annex A.3.2’de açıkça **0.5% force drop** ve **0.05% strain range** olarak yer alır. citeturn13view0

- **Python’da doğrudan çevrimi:** En güvenli algoritma, her aday lokal maksimum için aşağıdaki kontrolü yapmaktır:  
  1. \(F_i\) aday pik.  
  2. Sonraki noktalarda ilk kez \(F \le 0.995\,F_i\) olan bir `j` bul.  
  3. `j` noktasından başlayarak en az \(0.05\%\) strain penceresi oluştur.  
  4. Bu pencerede hiçbir kuvvet \(F_i\)’yi aşmıyorsa, \(Re_H = F_i/S_0\).  
  Bu, standardı kodda kararlı biçimde karşılayan en yalın hali olur. citeturn13view0

- **Aday piki nasıl seçeceksin:** Standardın madde 11 tanımı “ilk düşüşten önceki maksimum gerilme” der; Annex A.3.2 bunu yazılıma uygun hale getirir. Dolayısıyla tüm lokal maksimumları dolaşıp, şartı sağlayan **ilk fiziksel pik** alınmalıdır; “global max before fracture” alınmamalıdır. Özellikle Lüders başlangıcında küçük noise pikleri varsa, önce hafif bir düşük-gecikmeli filtreleme veya `rolling median` uygulanması pratikte faydalı olur; ama bu filtre, standardın kendisi tarafından verilmiş bir sayı değildir. citeturn11view0turn13view0

- **ReL tanımı:** Alt akma dayanımı \(Re_L\), plastik akma sırasında görülen **en düşük gerilme**, fakat **başlangıç transient etkileri dışlanarak** belirlenir. Bu “transient maskeleme” standarda göre zorunlu bir kavramdır, fakat standardın verdiği şey yalnızca bu ifadedir; transient’in **kaç ms**, **kaç nokta** ya da **kaç strain** süreceğine dair explicit sayı verilmez. Şekil 2’de “initial transient effect” gösterilir, ama numerik maske uzunluğu verilmez. citeturn44view0turn44view3

- **Transient maskeleme için yazılım politikası:** Standardın açık vermediği bu alanı yazılımda konfigüre edilebilir yapman gerekir. Ben pratikte üç seviyeli yaklaşım öneririm:  
  **(a)** `manual_mask_end_idx` varsa onu kullan;  
  **(b)** yoksa, \(Re_H\) sonrası ilk büyük düşüşten sonra türev büyüklüğünün plato seviyesine indiği ilk indeksi “transient sonu” say;  
  **(c)** hiçbir kararlı plato bulunamazsa, ReL’yi “ambiguous” işaretle.  
  Bunun numerik eşiği ISO’dan gelmez; audit trail’de “vendor rule” olarak ayrı saklanmalıdır. Bu ayrım önemli, çünkü numeric transient lock standardın kendisinde yoktur. citeturn44view0turn44view1

- **Madde 12’deki verimlilik kısayolu:** Kullanıcıdaki ifade eksik. Standardın söylediği şey şu mantıktadır:  
  Malzeme süreksiz akma gösteriyorsa **ve** \(A_e\) belirlenecek değilse, test verimliliği için \(Re_L\), **\(Re_H\)’den sonraki ilk %0.25 strain içinde**, başlangıç transient etkisi dikkate alınmadan görülen en düşük gerilme olarak raporlanabilir. Yani doğru ifade  
  **“ilk %0.25 toplam deformasyon” değil, “\(Re_H\)’den sonraki ilk %0.25 strain”** şeklindedir. Ayrıca bu kısayol kullanıldıysa test raporuna yazılması gerekir. citeturn11view0turn44view0

- **Çift akma ile \(Rp0.2\) arasındaki karar ağacı:** Genel ISO 6892-1 mantığı şu şekildedir:  
  **(i)** malzeme süreksiz akma fenomeni gösteriyorsa öncelikli karakteristikler \(Re_H\), \(Re_L\) ve gerekiyorsa \(A_e\)’dir;  
  **(ii)** malzeme böyle bir akma fenomeni göstermiyorsa proof strength \(Rp\) kullanılır;  
  **(iii)** Clause 13.1 ayrıca, ürün standardı veya müşteri ile aksi kararlaştırılmadıkça, **süreksiz akma sırasında/sonrasında proof strength belirlemenin uygun olmadığını** söyler. Bu yüzden yazılım karar ağacında A.3.2 koşulları sağlanır sağlanmaz malzemeyi “yield-phenomenon present” diye etiketleyip \(Re_H/Re_L\)’yi birincil sonuç yapman, \(Rp0.2\)’yi ise ancak ürün standardı isterse ikincil sonuç olarak üretmen daha doğrudur. citeturn11view0turn13view0turn42view0

- **\(A_e\) formülü ve Lüders bandı genişliği karşılığı:** ISO 6892-1’de “Lüders bandı genişliği” terimi yerine **percentage yield point extension \(A_e\)** kullanılır. Tanım, akmanın başlangıcı ile üniform iş sertleşmesinin başlangıcı arasındaki uzamadır. Clause 16’ya göre \(A_e\), \(Re_H\)’deki uzamadan, üniform iş sertleşmesinin başlangıcındaki uzamanın çıkarılmasıyla bulunur ve \(L_e\)’ye göre yüzde olarak ifade edilir.  
  Kodda:
  \[
  A_e = 100\cdot \frac{\Delta L_{\text{uwh,start}}-\Delta L_{Re_H}}{L_e}
  \]
  Üniform iş sertleşmesinin başlangıcı da iki yöntemden biriyle bulunur:  
  **yatay doğru yöntemi:** yielding bölgesindeki son lokal minimumdan geçen yatay doğru;  
  **regresyon yöntemi:** uniform work-hardening öncesi yielding bölgesine regresyon doğrusu;  
  sonra bunların, iş sertleşmesinin başındaki en yüksek eğimi temsil eden doğru ile kesişimi alınır. Hangi yöntemin kullanıldığı rapora yazılmalıdır. citeturn41view0turn40view0turn10view7

- **Doğrudan koda çeviri önerisi:**  
  1. Kuvveti sıralı uzama ekseninde al.  
  2. A.3.2 ile `ReH_idx` bul.  
  3. `yield_present=True` ise `ReL_idx` için transient maskesi uygula.  
  4. `need_Ae=True` ise Clause 16 algoritmasıyla `Ae` hesapla; bu durumda %0.25 kısayolunu kullanma.  
  5. `yield_present=False` ise \(Rp0.2\) koluna geç. citeturn11view0turn13view0

Bu mantığın doğrudan pseudo-code karşılığı aşağıdaki gibi kurulabilir. Açıkça standardın numerik vermediği yer olan `transient_end_idx` ayrı fonksiyon yapılmıştır. citeturn13view0turn44view0

```python
import numpy as np

def detect_reh(force_N, strain_pct, So_mm2):
    # strain_pct: yüzde strain, ör. 0.05 = %0.05
    n = len(force_N)
    for i in range(1, n - 2):
        # kaba lokal maksimum koşulu
        if not (force_N[i] >= force_N[i-1] and force_N[i] >= force_N[i+1]):
            continue

        peak = force_N[i]
        # koşul 1: en az %0.5 düşüş
        after = np.where(force_N[i+1:] <= 0.995 * peak)[0]
        if len(after) == 0:
            continue
        j = i + 1 + after[0]

        # koşul 2: sonraki en az %0.05 strain boyunca eski maksimum aşılmamalı
        end_candidates = np.where(strain_pct[j:] >= strain_pct[j] + 0.05)[0]
        if len(end_candidates) == 0:
            continue
        k = j + end_candidates[0]

        if np.max(force_N[j:k+1]) <= peak:
            return {
                "ReH_MPa": peak / So_mm2,
                "ReH_idx": i,
                "drop_confirm_idx": j,
                "plateau_end_idx": k
            }

    return None

def transient_end_idx(force_N, strain_pct, reh_idx):
    # ISO numerik vermiyor; bu bir vendor-rule örneği
    # fikir: ilk büyük düşüşten sonraki, türevin plato seviyesine indiği nokta
    dF = np.diff(force_N)
    tail = np.abs(dF[reh_idx+1:])
    if len(tail) < 5:
        return reh_idx + 1

    # kaba plateau eşiği
    thr = np.percentile(tail, 40)
    for i in range(reh_idx + 2, len(force_N) - 1):
        if abs(force_N[i+1] - force_N[i]) <= thr:
            return i
    return reh_idx + 1

def detect_rel(force_N, strain_pct, So_mm2, reh_idx, need_Ae):
    start = transient_end_idx(force_N, strain_pct, reh_idx)

    if not need_Ae:
        # Clause 12 productivity shortcut:
        # ReH'den sonraki ilk %0.25 strain içinde minimum
        end = np.where(strain_pct >= strain_pct[reh_idx] + 0.25)[0]
        if len(end) > 0:
            end_idx = end[0]
            idx = start + np.argmin(force_N[start:end_idx+1])
            return {"ReL_MPa": force_N[idx] / So_mm2, "ReL_idx": idx, "method": "Clause12_shortcut"}

    # full lower-yield search over yielding region
    idx = start + np.argmin(force_N[start:])
    return {"ReL_MPa": force_N[idx] / So_mm2, "ReL_idx": idx, "method": "full_search"}
```

## Annex A.3.6.1 kapsamında kırılmadaki toplam uzama

- **Madde numarası ve kapsamı:** İlgili madde tam olarak **Annex A.3.6.1**’dir ve \(A_t\)’nin, Şekil A.2’deki kırılma tanımına göre belirlenmesini ister. Normatif çekirdek burada “kırılma anı”nın veri akışı içinden nasıl tespit edileceğidir. citeturn5view2turn42view2

- **Force-drop method’un iki kriteri nasıl okunmalı:** Standardın metni iki durumu ayırır:  
  **genel/sudden fracture durumu:** iki ardışık nokta arasındaki kuvvet azalışı, önceki iki nokta farkının **5 katından fazla** olacak, **ardından** kuvvet \(F_{\max}\)’in **%2’sinin altına** inecek;  
  **soft materials durumu:** kuvvetin \(F_{\max}\)’in **%2’sinin altına** inmesi tek başına yeterli kabul edilir.  
  Şekil A.2’nin anahtarında bu “and/or” gösterimiyle de desteklenir. Bu nedenle bunu evrensel “aynı anda AND” diye okumak doğru değildir. Uygulama açısından en doğru mantık:  
  - **brittle / sudden fracture branch:** `5x drop` + sonrasında `<2% Fmax` doğrulaması,  
  - **soft material branch:** yalnızca `<2% Fmax`. citeturn5view2turn42view2

- **Kriterler OR mu AND mi:** Kod düzeyinde en doğru okuma şudur:  
  - “soft material” diye etiketlenmiş ya da veriden öyle sınıflandırılmış numunede **OR mantığıyla** `<2% Fmax` tek başına yeterlidir;  
  - diğer numunelerde ise “önce ani düşüş, sonra %2 altı” sıralaması aranmalıdır.  
  Yani tek bir global boolean ifadesi yerine **duruma bağlı dallanma** kullanmak standarda daha sadıktır. citeturn5view2turn42view2

- **Sampling/filtering etkisi:** Standardın çok pratik ama önemli bir uyarısı var: örnekleme hızının artırılması ve/veya kuvvet sinyaline filtre uygulanması, kırılma noktasını etkileyebilir. Bu yüzden yazılımda şu ayrımı yapmanı öneririm:  
  - kırılma deteksiyonunda hafif bir görünürlük filtresi kullanabilirsin;  
  - ama raporlanan kırılma indeksi ve \(A_t\), mümkünse **ham sinyalde karşılığı olan indeks** üzerinden hesaplanmalı;  
  - filtre parametresi audit log’a yazılmalı. citeturn5view2

- **\(A_t\) ile \(A\) farkı:** Bunlar aynı şey değildir.  
  **\(A_t\)**, extensometer ile test sırasında elde edilen **kırılma anındaki toplam uzama**dır ve Clause 19’da
  \[
  A_t = 100\cdot \frac{\Delta L_f}{L_e}
  \]
  olarak verilir.  
  **\(A\)** ise kırılma sonrası numune fiziksel olarak birleştirilip son mastar boyu ölçülerek bulunan **percentage elongation after fracture** olup Clause 20.1’de
  \[
  A = 100\cdot \frac{L_u-L_o}{L_o}
  \]
  ile tanımlanır. Yazılım terminolojisinde bunları aynı değişken adı altında toplama. Biri “in-test extensometer property”, diğeri “post-fracture physical measurement”dir. citeturn41view0

- **Force-drop method ile bulunan değerin etiketi:** Force-drop yöntemiyle bulduğun property, ISO 6892-1:2019 altında **\(A_t\)**’dir. Standardın bu bağlamda “\(A_f\)” diye ayrı bir etiket kullandığı bir yer yoktur. Sembol listesi de \(A_t\)’yi “percentage total extension at fracture” olarak verir. citeturn41view0turn42view1

- **Extensometer çıkarılmışsa ne yapılır:** Annex A.3.6.3, extensometer maksimum kuvvetten sonra çıkarılmışsa veya uzama ölçümü kırılmadan önce kesilmişse, kırılmaya kadar olan **ek uzamanın crosshead displacement ile belirlenmesine izin verir**; ancak kullanılan yöntem **doğrulanabilir/verifiable** olmalıdır. Bu yüzden kodda `extension_mode = "extensometer"` ve `extension_mode = "extensometer+crosshead_fallback"` gibi açık modlar tutmak gerekir. Fallback kullanılmışsa sonuç metadata’sına yazılmalıdır. citeturn42view2

- **Yumuşak vs kırılgan malzeme ayrımı için öneri:** Standard only says “soft materials” for the 2% rule; bunu otomatik sınıflandırmak istiyorsan, kırılma çevresinde şu heuristiği kullanabilirsin:  
  - ani kopuş ve kuvvette tek-adım benzeri büyük çöküş varsa `soft_mode=False`,  
  - necking sonrası yavaş kuvvet sönümü varsa `soft_mode=True`.  
  Bu sınıflandırma ISO’dan gelmez; ama standardın verdiği iki dalı yazılımda seçmek için gereklidir. Eğer deterministik istersen `soft_mode`’u kullanıcı/ürün standardı metadata’sından alman daha güvenlidir. citeturn5view2turn42view2

- **Doğrudan koda çeviri önerisi:**  
  1. \(F_{\max}\)’i bul.  
  2. \(\Delta F_n = F_{n+1}-F_n\) dizisini hesapla.  
  3. `soft_mode=True` ise ilk `F < 0.02*Fmax` noktasını kırılma say.  
  4. Değilse ilk `abs(ΔF[n]) > 5*abs(ΔF[n-1])` olayını bul ve bundan sonra gelen ilk `<2% Fmax` noktasını kırılma say.  
  5. Extensometer aktifse \(\Delta L_f\)’yi o indeksten al; değilse crosshead fallback uygula.  
  6. \(A_t = 100\,\Delta L_f/L_e\). citeturn5view2turn42view2

Standardın bu mantığını doğrudan uygulayan bir pseudo-code şöyle olabilir. citeturn5view2turn42view2

```python
import numpy as np

def detect_fracture_idx(force_N, soft_mode=False):
    F = np.asarray(force_N, dtype=float)
    Fmax = np.max(F)
    low_thr = 0.02 * Fmax
    dF = np.diff(F)

    # soft materials: Fn+1 < 0.02 Fmax yeterli
    if soft_mode:
        hits = np.where(F < low_thr)[0]
        if len(hits):
            return int(hits[0])
        raise ValueError("Fracture not detected by soft-material criterion.")

    # general branch: sudden drop followed by fall below 2% Fmax
    for n in range(1, len(F) - 1):
        sudden = abs(F[n+1] - F[n]) > 5.0 * abs(F[n] - F[n-1])
        if not sudden:
            continue

        later = np.where(F[n+1:] < low_thr)[0]
        if len(later):
            return int(n + 1 + later[0])

    # ihtiyari fallback: veri sudden criterion üretmiyorsa yine 2% altını dene
    hits = np.where(F < low_thr)[0]
    if len(hits):
        return int(hits[0])

    raise ValueError("Fracture not detected per Annex A.3.6.1 criteria.")

def at_from_extensometer(extension_mm, Le_mm, fracture_idx):
    return 100.0 * extension_mm[fracture_idx] / Le_mm

def at_with_crosshead_fallback(ext_mm_until_remove, crosshead_mm, remove_idx, fracture_idx, Le_mm):
    ext_at_remove = ext_mm_until_remove[remove_idx]
    extra = crosshead_mm[fracture_idx] - crosshead_mm[remove_idx]
    delta_Lf = ext_at_remove + extra
    return 100.0 * delta_Lf / Le_mm
```

## Annex K kapsamında ölçüm belirsizliği

- **Annex K gerçekten var mı:** Evet. ISO 6892-1:2019’da **Annex K** gerçekten vardır ve başlığı “Estimation of the uncertainty of measurement”tır. Annex H ise bambaşka bir konudur: **specified elongation < 5% ise kırılma sonrası uzama ölçümünde alınacak önlemler** ile ilgilidir; belirsizlik eki değildir. “Belirsizlik Annex H’de” ifadesi 2019 baskısı için yanlıştır. citeturn8view0turn45view0

- **Belirsizlik standardın neresinde ele alınıyor:** Gövde metinde Clause 23, ölçüm belirsizliğinin yararlı olduğunu ama ürün uygunluk değerlendirmesinde sonuçlarla birleştirilmemesi gerektiğini söyler; Annex K ise belirsizlik tahmini için rehber verir. Ayrıca elastik modül için Annex G.7’de, belirsizliğin **CWA 15261-2:2005 A.5’e göre veya Annex K’ye göre** hesaplanabileceği açıkça belirtilir. Yani \(E\) için detaylı örnek bütçe Annex G içindedir; diğer çekme parametreleri için genel çerçeve Annex K’dadır. citeturn41view0turn43view0

- **Hangi parametreler için tablo verir:** Annex K’nin Table K.1’i ölçüm cihazlarından gelen katkıları şu sonuçlar için verir: **\(Re_H\), \(Re_L\), \(R_m\), \(R_p\), \(A\), \(Z\)**. Dikkat: Table K.1’de **\(A_t\)** için ayrı bir satır yoktur; **\(E\)** de K tablosunda ana sütun olarak verilmez. \(E\) için özel örnek bütçe Annex G.7.3 / Table G.2’dedir. Bu yüzden yazılımda parametre bazlı destek matrisi şöyle olmalıdır:  
  - `ReH/ReL/Rm/A/Z`: Annex K templated support  
  - `Rp0.2`: Annex K çerçeve var ama kapalı form yok  
  - `E`: Annex G.7 examples + Annex K logic  
  - `At`: Annex K’de explicit template yok; lab-specific budget gerekir. citeturn8view1turn9view1turn43view0

- **Annex K’nin temel hesap çerçevesi GUM uyumlu mu:** Evet. Annex K doğrudan ISO/IEC Guide 98-3’e yani **GUM**’a referans verir. Verdiği temel yapı:  
  - Type A:
    \[
    u=\frac{s}{\sqrt{n}}
    \]
  - Type B, rectangular:
    \[
    u=\frac{a}{\sqrt{3}}
    \]
  - birleşik standart belirsizlik:
    \[
    u(y)=\sqrt{u(x_1)^2+u(x_2)^2+\cdots+u(x_n)^2}
    \]
  - genişletilmiş belirsizlik:
    \[
    U = k\,u_c,\qquad k=2 \text{ (yaklaşık %95)}
    \]
  Dolayısıyla yazılım motorunu doğrudan “component + distribution + sensitivity + RSS” mantığında kurabilirsin. citeturn8view0turn9view0turn8view3

- **\(Re_H, Re_L, R_m, A, Z\) için cihaz katkıları:** Table K.1 şu bağımlılıkları verir:  
  - \(Re_H, Re_L, R_m\): **force + \(S_o\)**  
  - \(Rp\): **force + extension + gauge length + \(S_o\) + curve-dependent effects**  
  - \(A\): **extension + gauge length**  
  - \(Z\): **\(S_o + S_u\)**  
  Ayrıca K.4, test sıcaklığı, test hızı, numune geometrisi/işleme, kavrama ve eksenellik, makine karakteristikleri, insan ve yazılım hataları, extensometer montaj geometrisi gibi malzeme/prosedür kaynaklı ek bileşenlerin de laboratuvar tarafından gerekli ise eklenmesini ister. citeturn8view1turn9view2

- **\(Rp0.2\) için kapalı formül var mı:** Hayır; Annex K’de **genel geçer kapalı bir \(u(Rp0.2)\) formülü yoktur**. Standardın çok önemli uyarısı şu: \(Rp\) belirsizliğinde, yalnızca cihaz sınıflarından gelen katkıları kök-toplam-kare ile toplamak uygun değildir; force-extension eğrisi incelenmelidir. Çünkü uzama ölçüm belirsizliğinin kuvvet sonucuna etkisi, \(Rp\)’nin bulunduğu bölgedeki eğrinin lokal eğimine bağlıdır; ayrıca elastik kısmın eğimi \(m_E\) düz bir doğru değilse \(Rp\) sonucunu etkiler. Bu yüzden yazılım için en doğru yaklaşım **sayısal belirsizlik yayılımı**dır:  
  - lokal duyarlılık katsayıları ile first-order propagation, veya  
  - Monte Carlo ile force / extension / area / slope perturbation. citeturn9view1turn14view0turn14view2

- **\(E\) için Annex G örnek bütçesi:** Annex G.7.3 / Table G.2, \(E\) için bilgi amaçlı örnek katkılar verir:  
  - \(S_{m(rel)}\): 0.2%  
  - \(S_X\): 3%  
  - \(S_Y\): 1%  
  - \(L_e\): 0.5%  
  - \(S_o\): 1%  
  Bunların RSS birleşimi 1.9% olur; \(k=2\) ile expanded uncertainty örneği 3.8% verilir. Bu tablo normatif sabitler değildir, fakat kod doğrulama için çok yararlı sanity-check vektörüdür. citeturn6view0turn6view1

- **\(R_m\) için basit relatif bütçe nasıl yazılır:** Table K.1 mantığına göre
  \[
  R_m = \frac{F_m}{S_o}
  \]
  olduğundan, bağımsız relatif standart belirsizlikler varsayılırsa yaklaşık:
  \[
  u_{rel}(R_m)=\sqrt{u_{rel}(F)^2+u_{rel}(S_o)^2}
  \]
  olur. Annex K’nin örnek değerleriyle \(Re_H/Re_L/R_m/A\) için birleşik belirsizlik 0.91%, genişletilmiş belirsizlik 1.82% olarak gösterilir. Bunu regression-free parametreler için doğrudan kullanabilirsin. citeturn8view3turn14view5

- **\(A_t\) için ne yapmalı:** Standardın Annex K tablosu \(A_t\) için ayrı varsayılan bütçe vermez. Bu nedenle yazılım tarafında `At_uncertainty_model`’i laboratuvar politikası olarak tanımlamak gerekir. En mantıklı bileşenler:  
  - extensometer extension uncertainty,  
  - gauge length uncertainty,  
  - fracture-point detection uncertainty,  
  - soft/brittle branch selection uncertainty,  
  - extensometer removed ise crosshead fallback calibration uncertainty.  
  Bunlar K.4’ün “test procedure / software / mounting geometry” başlığı altında laboratuvar tarafından eklenebilir. Bu bölüm ISO tarafından ayrıntılı kapalı formda verilmez. citeturn9view2turn42view2

- **Sonuçlarla belirsizliği birleştirme konusu:** Clause 23.3 çok nettir: tahmin edilen ölçüm belirsizlikleri, ürün spesifikasyonuna uygunluk değerlendirmesi için ölçülen sonuçlarla birleştirilmemelidir. Yazılımında bu yüzden iki ayrı çıktı alanı bulunsun:  
  - `reported_value`  
  - `info_only_uncertainty`  
  ve conformity engine yalnızca birincisini kullansın. citeturn41view0

- **CWA 15261-2 ve daha yeni kaynak ilişkisi:** ISO 6892-1:2019, özellikle \(E\) için CWA 15261-2:2005’e açık referans verir. Buna ek olarak ISO’nun 2024 tarihli **ISO/TR 15263** teknik raporu da oda sıcaklığı ve yüksek sıcaklıktaki çekme deneylerinde belirsizlik değerlendirmesini tarif eden güncel bir tamamlayıcı kaynaktır. Eğer yazılımına “uncertainty engine” ekleyeceksen, Annex K + CWA 15261-2 + ISO/TR 15263 üçlüsünü referans mimari olarak görmek mantıklıdır. citeturn43view0turn15search7

- **TÜBİTAK UME ile ilişki:** Bu aramada UME’nin kamuya açık, doğrudan “çekme deneyinde ölçüm belirsizliği” başlıklı bir rehberini doğrulayamadım. Bulabildiğim kamuya açık UME materyalleri ise belirsizlik ifadelerinde açıkça **GUM uyumu** ve **\(k=2\), yaklaşık %95 güven düzeyi** yaklaşımını kullanıyor. Dolayısıyla yazılımı “UME-benzeri” raporlayacaksan, GUM temelli \(u_c\) ve \(U=k u_c\) mimarisi kurmak doğru yöndür; fakat bunu doğrudan UME’ye atfetmek için kamuya açık spesifik çekme rehberi ayrıca doğrulanmalıdır. citeturn18search8

- **Doğrudan koda çeviri önerisi:**  
  1. Her ölçülen büyüklük için `UncertaintyComponent(name, kind, value, distribution, sensitivity)` nesnesi oluştur.  
  2. Type A / Type B standard uncertainty dönüştürmesini yap.  
  3. Gerekirse sensitivity coefficient uygula.  
  4. RSS ile \(u_c\) hesapla.  
  5. `k=2` ile \(U\) hesapla.  
  6. Sonucu `info_only` alanında raporla.  
  7. \(Rp0.2\) ve \(A_t\) için explicit formula bekleme; sayısal yayılım kullan. citeturn9view0turn9view1turn41view0

Bu mantığı doğrudan kodlayan iki kısa iskelet aşağıda veriyorum: biri genel GUM motoru, diğeri \(Rp0.2\) için Monte Carlo fikri. citeturn9view0turn9view1

```python
from dataclasses import dataclass
from math import sqrt

@dataclass
class Component:
    name: str
    kind: str              # "A", "B_rect", "B_norm"
    value: float           # s (Type A) or half-width a (B_rect) or sigma (B_norm)
    n: int | None = None
    sensitivity: float = 1.0
    rel: bool = True       # relative standard uncertainty mı?

def std_unc(c: Component) -> float:
    if c.kind == "A":
        return c.value / sqrt(c.n)
    if c.kind == "B_rect":
        return c.value / sqrt(3.0)
    if c.kind == "B_norm":
        return c.value
    raise ValueError(c.kind)

def combined_uncertainty(components, k=2.0):
    terms = [(c.sensitivity * std_unc(c))**2 for c in components]
    uc = sqrt(sum(terms))
    U = k * uc
    return uc, U
```

```python
import numpy as np

def monte_carlo_u_rp02(raw_force, raw_ext, So, Le, device_model, n_mc=20000):
    rp_samples = []

    for _ in range(n_mc):
        F = device_model.perturb_force(raw_force)
        ext = device_model.perturb_extension(raw_ext)
        So_i = device_model.perturb_area(So)
        Le_i = device_model.perturb_gauge_length(Le)

        stress = F / So_i
        strain = ext / Le_i

        # elastic slope for proof-strength evaluation, Annex A.3.7 style
        mE = estimate_offset_slope(strain, stress)   # yazılım politikası
        rp02 = intersection_with_offset_line(strain, stress, slope=mE, offset=0.002)
        rp_samples.append(rp02)

    rp_samples = np.asarray(rp_samples)
    uc = rp_samples.std(ddof=1)
    U95 = 2.0 * uc
    return uc, U95
```

## Dixon Q testi ve kritik değerler

- **Önce notasyon düzeltmesi:** Yaygın kimya/pratik kullanımındaki “Dixon Q testi” çoğunlukla **\(Q_{10}\)** ya da \(r_{10}\) istatistiğini ifade eder. NIST ve CRAN `dixonTest` dokümantasyonu, pratik kullanımda otomatik varyant seçimini şöyle özetler:  
  - \(r_{10}\): \(3 \le n \le 7\)  
  - \(r_{11}\): \(8 \le n \le 10\)  
  - \(r_{21}\): \(11 \le n \le 13\)  
  - \(r_{22}\): \(14 \le n \le 30\)  
  Yani **modern standart kullanımda \(Q_{11}\) ve \(Q_{21}\), \(n\le 5\) için tercih edilen varyantlar değildir**. Bununla birlikte Dixon ailesinin genel formülleri daha geniştir ve küçük \(n\) için de matematiksel olarak tanımlanabilir. Batch QC’de \(n=3\)–7 aralığında çoğu zaman kullanman gereken varyant **\(Q_{10}\)**’dur. citeturn20view0turn24view0turn25search15

- **Genel Dixon oranı:** Sıralı veri \(x_1 \le x_2 \le \dots \le x_n\) için McBane’in verdiği genel aile biçimi:
  \[
  r_{j,i-1}=\frac{x_n-x_{n-j}}{x_n-x_i}
  \]
  (üst uç testinde) şeklindedir. Alt uç için simetrik biçimi kullanılır. Birinci alt indis üst uçta şüpheli uç gözlem sayısını, ikinci alt indis alt uçta şüpheli uç gözlem sayısını temsil eder. \(r_{10}\), yani klasik \(Q\), bu ailenin en yaygın özel halidir. citeturn33view0turn24view0

- **\(Q_{10}\), \(Q_{11}\), \(Q_{21}\) formülleri:**  
  **Şüpheli maksimum** için:
  \[
  Q_{10}=\frac{x_n-x_{n-1}}{x_n-x_1}
  \]
  \[
  Q_{11}=\frac{x_n-x_{n-1}}{x_n-x_2}
  \]
  \[
  Q_{21}=\frac{x_n-x_{n-2}}{x_n-x_2}
  \]
  **Şüpheli minimum** için:
  \[
  Q_{10}=\frac{x_2-x_1}{x_n-x_1}
  \]
  \[
  Q_{11}=\frac{x_2-x_1}{x_{n-1}-x_1}
  \]
  \[
  Q_{21}=\frac{x_3-x_1}{x_{n-1}-x_1}
  \]
  Uygulanabilirlik alt sınırı doğal olarak \(Q_{10}\) için \(n\ge 3\), \(Q_{11}\) için \(n\ge 4\), \(Q_{21}\) için \(n\ge 5\)’tir. Ancak tekrar vurgulayayım: küçük örnek QC için yaygın tablo desteği esasen **\(Q_{10}\)** üzerindedir. citeturn24view0turn33view0

- **\(n=3\)–7 için kritik değerler:** Aşağıdaki tablo, yaygın kullanılan **tek-şüpheli gözlem \(Q_{10}\)** kritik değerlerini verir. Buradaki \(\alpha\) sütunları, “şüpheli outlier’ı yanlış reddetme olasılığı” biçimindeki yaygın kullanımdır. citeturn22view0

| \(n\) | \(Q_{crit}\) at \(\alpha=0.05\) | \(Q_{crit}\) at \(\alpha=0.01\) |
|---|---:|---:|
| 3 | 0.970 | 0.994 |
| 4 | 0.829 | 0.926 |
| 5 | 0.710 | 0.821 |
| 6 | 0.625 | 0.740 |
| 7 | 0.568 | 0.680 |

- **Alpha/güven düzeyi etiketleme uyarısı:** Dixon literatüründe bir karışıklık noktası var: McBane, Dixon’ın özgün tablolarındaki \(\alpha\) sütunlarının **tek kuyruklu** yorumla verildiğini, oysa analitik kimya pratiğinde bunların sık sık **iki kuyruklu güven düzeyi** şeklinde etiketlendiğini özellikle not eder. O yüzden yazılım dokümantasyonunda “\(Q_{crit}\) tablosu hangi konvansiyona göre hardcode edildi?” sorusunun cevabını açık yaz. Yukarıdaki değerler, analitik kimyada yaygın kullanılan \(Q_{10}\) tablosuyla uyumludur. citeturn33view0turn22view0

- **Neden çok küçük \(n\)’de Dixon düşünülür:** Statik gerekçe “Dixon her zaman en güçlü testtir” değildir; tersine ASTM E178, çoğu durumda Dixon kriterinin standart sapma tabanlı kritere göre **daha az güçlü** olduğunu açıkça söyler. Buna rağmen küçük örneklerde Dixon’ın tercih edilmesinin iki pratik nedeni vardır:  
  - test istatistiği yalnızca uçtaki boşluk/range oranına dayanır ve çok küçük örneklerde uygulanması/tablolanması kolaydır;  
  - Dean & Dixon’ın orijinal bağlamı zaten “small numbers of observations”tır.  
  Yani \(n\le 5\) için Dixon kullanımı daha çok **geleneksel small-sample convenience** ve exact-tabulation kolaylığı nedeniyledir; “Grubbs’tan daha güçlü olduğu” gerekçesiyle değil. Batch QC yazılımında bu nedenle ben `n<=5 -> Dixon optional`, `n>=6 -> Grubbs default, Dixon supplementary` mantığını tercih ederim. citeturn26view0turn20view0turn33view0

- **İteratif uygulanabilir mi:** ASTM E178, tek-outlier testlerinin **recursive** uygulanabileceğini söyler; yani bir outlier bulunduysa çıkarıp tekrar test etmek mümkündür. Ancak aynı metin masking nedeniyle bunun sorunlu olabileceğini, ilk işaret önemliyse çoklu-outlier testlerine geçmenin daha doğru olduğunu söyler. NIST de tek outlier testlerini ardışık uygulamanın masking/swamping yüzünden başarısız olabileceğini açıkça uyarır ve çoklu outlier şüphesi varsa Tietjen-Moore veya generalized ESD önerir. Sonuç:  
  - **evet, iteratif uygulanabilir**,  
  - ama **validasyonlu üretim mantığında kör tekrar** olarak değil,  
  - daha çok investigative workflow içinde kullanılmalıdır.  
  Eğer batch QC modülünde otomatik iterasyon yapacaksan, `max_removed=1` gibi sert bir sınır koymak daha savunulabilir olur. citeturn26view0turn20view0

- **ISO 5725 / ISO 17025 bağlamı:** Bulabildiğim ISO 5725 kaynaklarında interlaboratuvar outlier işlemleri için referanslar **Grubbs ve Cochran** testleri ile, daha yeni yaklaşımlarda da **robust methods** ile ilişkilidir; Dixon’a açık bir ISO 5725 referansı bulamadım. ISO/IEC 17025 ise yöntem-agnostiktir: laboratuvarların uygun yöntem/prosedürleri ve uygulanabildiği yerde istatistiksel teknikleri kullanmasını ister, ama özel olarak Dixon adını vermez. Bu yüzden Dixon Q, ISO-mandated bir test değil; 17025 kapsamında ancak **laboratuvarın doğrulanmış kendi istatistiksel prosedürü** olarak kullanılabilir. citeturn36search1turn36search8turn34search2turn35search1

- **Batch QC için doğrudan koda çeviri önerisi:**  
  1. Veriyi sırala.  
  2. Önce normalite/tek-outlier varsayımı için en azından grafiksel kontrol veya Shapiro-like flag üret.  
  3. \(3\le n\le 7\) ise \(Q_{10}\) kullan.  
  4. `side="auto"` ise min ve max için ayrı \(Q\) hesapla, büyüğünü şüpheli aday say.  
  5. \(Q > Q_{crit}\) ise outlier adayı işaretle.  
  6. Fiziksel neden/traceability kaydı yoksa otomatik silme yerine “review required” döndür.  
  7. Çoklu outlier şüphesi varsa Dixon iterasyonuna geçmek yerine Tietjen-Moore/ESD’ye yönel. citeturn20view0turn26view0

Bu mantığın basit bir Python iskeleti aşağıdaki gibi olabilir. Kritik değer tablosu doğrudan küçük örnek QC için hard-code edilmiştir. citeturn22view0turn24view0

```python
import numpy as np

Q10_CRIT = {
    0.05: {3: 0.970, 4: 0.829, 5: 0.710, 6: 0.625, 7: 0.568},
    0.01: {3: 0.994, 4: 0.926, 5: 0.821, 6: 0.740, 7: 0.680},
}

def dixon_q10(x, side="auto", alpha=0.05):
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if not (3 <= n <= 7):
        raise ValueError("This hard-coded table is for Q10 with n=3..7.")

    q_min = (x[1] - x[0]) / (x[-1] - x[0])
    q_max = (x[-1] - x[-2]) / (x[-1] - x[0])

    if side == "min":
        q = q_min
        suspect_idx = 0
    elif side == "max":
        q = q_max
        suspect_idx = n - 1
    else:
        if q_max >= q_min:
            q = q_max
            suspect_idx = n - 1
            side = "max"
        else:
            q = q_min
            suspect_idx = 0
            side = "min"

    crit = Q10_CRIT[alpha][n]
    reject = q > crit

    return {
        "n": n,
        "side": side,
        "q": q,
        "q_crit": crit,
        "reject": reject,
        "suspect_value": float(x[suspect_idx]),
    }

def dixon_q_family(x, variant="Q10", side="max"):
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if side == "max":
        if variant == "Q10":
            return (x[-1] - x[-2]) / (x[-1] - x[0])
        if variant == "Q11":
            return (x[-1] - x[-2]) / (x[-1] - x[1])
        if variant == "Q21":
            return (x[-1] - x[-3]) / (x[-1] - x[1])
    else:
        if variant == "Q10":
            return (x[1] - x[0]) / (x[-1] - x[0])
        if variant == "Q11":
            return (x[1] - x[0]) / (x[-2] - x[0])
        if variant == "Q21":
            return (x[2] - x[0]) / (x[-2] - x[0])
    raise ValueError("Unsupported Dixon variant / side.")
```

## Sonuç olarak yazılım mimarisi için en güvenli tasarım

- **Annex G ile \(Rp0.2\) slope’unu ayır:** `E_annex_g` ve `mE_for_offset` ayrı alanlar olsun. İlki yüksek doğruluk / pre-test odaklı, ikincisi \(Rp0.2\) ofset çizgisi için pratik eğim olsun. Standardın kendi notları bu ayrımı destekliyor. citeturn42view0turn42view1turn42view2

- **Yield karar ağacını deterministik yap:** A.3.2 koşulu sağlanıyorsa önce \(Re_H/Re_L/A_e\) koluna gir; sağlanmıyorsa \(Rp0.2\) koluna geç. `product_standard_override` alanı ekleyip ürün standardı isterse proof strength üret. citeturn11view0turn13view0

- **Fracture detection modunu açıkça etiketle:** `fracture_detection_mode = sudden_drop_confirmed | soft_material_2pct | electrical_interrupt | crosshead_fallback` gibi bir enum, kalite yönetimi açısından çok işe yarar. Standardın Annex A.3.6.1 ve A.3.6.3 metni bu ayrımı destekler. citeturn5view2turn42view2

- **Belirsizlik motorunu parametre-agnostik kur:** Type A / Type B / RSS / \(k\) tabanlı genel bir motor üzerine, her property için farklı “measurement model” oturt. Annex K ve Annex G.7 bunu teknik olarak destekliyor. citeturn9view0turn43view0

- **Outlier modülünde Dixon’u küçük \(n\) için yardımcı test, Grubbs’ı ana test yap:** ISO 5725 bağlamı, ASTM ve NIST uyarıları birlikte okunduğunda bu en savunulabilir tasarım. citeturn36search1turn36search8turn26view0turn20view0