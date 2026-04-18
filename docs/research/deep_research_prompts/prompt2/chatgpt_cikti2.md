# UTM CSV Parser için Vendor Bazlı Export Format Araştırması

## Kapsam ve en önemli bulgular

Bu araştırmada yalnızca kamusal olarak erişilebilen birincil vendor kaynaklarına baktım. En net ve “parser kontratı”na en yakın resmi dokümantasyon **Instron Bluehill Universal** tarafında var: export içeriği, delimiter seçenekleri, decimal symbol ve encoding seçenekleri doğrudan yayımlanmış durumda. **ZwickRoell testXpert III** tarafında resmi kaynaklar export’un **template-driven** olduğunu, `results / parameters / channels` seçimiyle ve dil/terminoloji değişimiyle çalıştığını açıkça söylüyor; fakat kamusal kaynaklarda “sabit CSV başlık satırı / sabit delimiter / sabit encoding” gibi düşük seviyeli bir dosya kontratı yayımlanmıyor. **Shimadzu TRAPEZIUM X / Lite X / X‑V** tarafında kamusal ürün sayfaları ve uygulama notları veri alanlarının ve rapor formatlarının bir kısmını gösteriyor, fakat doğrudan “CSV export dialect” ayrıntıları kamusal içerikte açık değil; ürün sayfaları ayrıca ayrıntılı **Data Processing Reference / Software Reference** kılavuzlarının varlığını doğruluyor, ancak bu incelemede o kılavuzların tam metnine erişilemedi. citeturn46view0turn14view0turn16view0turn48view0turn39search5turn41search3

Bu yüzden pratik sonuç şu: **Bluehill için kurallı bir parser**, **Zwick için template-sniffing + terminoloji eşleme**, **Shimadzu için örnek dosya-temelli doğrulama** yaklaşımı en güvenli modeldir. Özellikle Zwick ve Shimadzu’da literal kolon başlıklarını “varsayılan ve evrensel” kabul etmek yerine, **alias setleri + fingerprint + unit/locale sniffing** ile gitmek daha doğru olur. citeturn46view0turn14view0turn16view0turn30view0turn31view0

## ZwickRoell testXpert III

ZwickRoell’in resmi testXpert III belgeleri, **Export Editor** üzerinden **results, parameters ve channels**’ın “okunabilir biçime” — örnek olarak CSV — aktarılabildiğini söylüyor. Aynı belgeler master test programlarının **industry-specific terminology** kullandığını, yani aynı test tipinin seçilen terminolojiye göre farklı adlandırmalar gösterebildiğini belirtiyor. testXpert genel ürün sayfası da Export Editor ile **test data, organization data ve raw data**’nın dışa aktarılabildiğini doğruluyor. Bu yapı, parser açısından testXpert dosyalarının “tek tip, sert sözleşmeli CSV” olmaktan çok **seçilen export template’ine bağlı ASCII/CSV üretimi** olduğu anlamına gelir. citeturn14view0turn16view0turn48view0

### A–H format özeti

| Başlık | Değerlendirme |
|---|---|
| **Header yapısı** | Kamusal Zwick belgeleri sabit bir “ilk N satır metadata” kuralı vermiyor. Resmi anlatım, export’un **results / parameters / channels** seçimiyle кurgulandığını söylüyor; bu yüzden metadata blokları template’e göre önce, sonra veya hiç olmayabilir. citeturn14view0turn16view0 |
| **Kolon adları** | Resmi belgeler literal export kolon listesini yayımlamıyor; fakat testXpert III ve ISO 6892‑1 kaynakları şu alan ailelerini açıkça destekliyor: **force, extension, stress, strain** ve standart sonuçlar olarak **ReH, ReL, Rp0.2, Rm, Ag, A, Ae**. Almanca terminolojide karşılıkları **Kraft, Längenänderung / Weg, Spannung, Dehnung** ve standart sonuç isimleridir. “Spannung bei x% Dehnung” ifadesi resmi Alman dokümanında doğrudan geçiyor; İngilizce eşleniği “stress at x% strain”. citeturn20view2turn20view3turn38search3turn38search11turn38search5turn38search1 |
| **Birimler** | Resmi kamusal dokümanlar tek sabit unit contract yayımlamıyor. Zwick’in tensile-test ve extensometer içerikleri temel olarak **force + extension** ölçümü ile **stress-strain** değerlendirmesini anlatıyor; metal çekme standardı sayfası sonuçları **MPa ve %** bağlamında tanımlar. Pratikte SI tarafında **N/kN, mm, MPa, %** beklenir; ancak literal export unit’i template ve test programına bağlıdır. citeturn38search5turn38search1turn38search3turn38search11turn18search7 |
| **Decimal separator** | İncelediğim kamusal Zwick kaynakları bunu açıkça belirtmiyor. testXpert’in çoklu dil ve online language swap desteklediği, ayrıca aynı testin farklı dillerde raporlanabildiği açık; bu nedenle locale etkisi olasıdır, fakat bu incelemede bunu resmi olarak doğrulayan bir Zwick export dokümanı bulamadım. citeturn48view0turn21view0 |
| **Encoding** | Kamusal Zwick belgelerinde ASCII/CSV export için `UTF-8 / CP1252 / ISO-8859-1` gibi açık encoding tablosu yayımlanmıyor. Sadece “readable format (e.g. csv)” deniyor. citeturn14view0turn16view0 |
| **Özel satırlar** | Resmi kaynaklar export içinde **organization data** ve **parameters** bulunabildiğini söylüyor; organization data örnekleri arasında **company name, logo, tester, certificate number** var. Bu nedenle comment-line (`#`, `;`) varsaymak yerine, **key-value metadata blokları** ve ardından veri tablosu gelebileceğini varsaymak daha doğru. citeturn14view0turn16view0turn48view0 |
| **Fingerprint** | Güçlü heuristic’ler: `testXpert`, `ZwickRoell`, Almanca metadata anahtarları olarak `Prüfer`, `Zertifikats-Nr.`, İngilizce karşılıkları `tester`, `certificate number`; metal tensile terminolojisinde `ReH`, `ReL`, `Rp0.2`, `Rm`, `Ag`, `Ae`, `A`. export template’e bağlı olduğu için tek başına kolon adına güvenmek yerine bu anahtarları birlikte kullanmak daha güvenli. citeturn16view0turn14view0turn38search3turn38search11 |
| **Birden fazla export modu** | Evet. testXpert III resmi belgeleri **ASCII export, Excel export, Word export, PDF export, ODBC export** ayrımını doğrudan veriyor. Ayrıca export wizard ile **results / parameters / channels** seçiliyor; bu fiilen “raw-ish channel export” ile “processed result export” ayrımı demektir. testXpert II de older generation’da import/export, results/channels ve terminology swapping mantığına sahipti; ancak III daha belirgin biçimde workflow‑based editor mantığına taşıyor. citeturn14view0turn16view0turn21view0 |

### İngilizce ve Almanca alan ailesi

| Kanonik alan | İngilizce / resmi bağlam | Almanca / resmi bağlam | Tipik SI birimi | Not |
|---|---|---|---|---|
| force | Force | Kraft | N, kN | Tensile test sırasında force ve extension ölçüldüğü resmi Zwick sayfalarında açık. citeturn38search5turn38search1 |
| extension / travel | Extension / force-travel diagram | Längenänderung / Kraft‑Weg bağlamı | mm | Literal export başlığı kamusal örnekte verilmemiş; kanal ailesi resmi sayfalarda var. citeturn38search5turn38search1 |
| stress | stress | Spannung | MPa | “stress at x% strain / Spannung bei x% Dehnung” resmi master test program belgelerinde geçiyor. citeturn20view2turn20view3 |
| strain | strain | Dehnung | % | Aynı resmi belgelerde ve ISO 6892‑1 sayfalarında açık. citeturn20view2turn20view3turn38search3turn38search11 |
| extensometer | extensometer | Dehnungsmessgerät / Extensometer | mm, % | Zwick’in Almanca extensometer sayfası “Dehnungsmessgerät” terimini kullanıyor. citeturn18search7 |
| tensile strength | tensile strength `Rm` | Zugfestigkeit `Rm` | MPa | ISO 6892‑1 karakteristik değerlerinden biri. citeturn38search3turn38search11 |
| proof stress | proof stress `Rp0.2` | Dehngrenze / Streckgrenze `Rp0.2` bağlamı | MPa | ISO 6892‑1 karakteristik değer listesinde. citeturn38search3turn38search11 |
| yield points | `ReH`, `ReL` | Obere / untere Streckgrenze `ReH`, `ReL` | MPa | ISO 6892‑1 karakteristik değer listesinde. citeturn38search3turn38search11 |
| elongation values | `Ag`, `A`, `Ae` | `Ag`, `A`, `Ae` | % | Uniform elongation, elongation after fracture, extensometer elongation. citeturn38search3turn38search11 |

Aşağıdaki `column_map`, resmi terminoloji ailesinden türetilmiş **pragmatik** bir normalize etme önerisidir; Zwick tarafında literal default export başlığı değil, güvenli alias seti olarak düşünmek gerekir. citeturn14view0turn16view0turn38search3turn38search11turn48view0

```python
ZWICK_COLUMN_MAP = {
    "force": [
        "force", "kraft"
    ],
    "extension": [
        "extension", "travel", "displacement", "längenänderung", "weg"
    ],
    "stress": [
        "stress", "spannung"
    ],
    "strain": [
        "strain", "tensile strain", "dehnung"
    ],
    "extensometer": [
        "extensometer", "dehnungsmessgerät"
    ],
    "tensile_strength": [
        "rm", "tensile strength", "zugfestigkeit"
    ],
    "proof_stress": [
        "rp0.2", "proof stress", "streckgrenze", "dehngrenze"
    ],
    "yield_upper": [
        "reh", "upper yield point", "obere streckgrenze"
    ],
    "yield_lower": [
        "rel", "lower yield point", "untere streckgrenze"
    ],
    "uniform_elongation": [
        "ag", "uniform elongation"
    ],
    "elongation_at_break": [
        "a", "elongation after fracture", "bruchdehnung"
    ]
}
```

Önerilen fingerprint regex’leri de template-driven doğa yüzünden **heuristic** olarak ele alınmalı: `(?im)^(testxpert(?:\s*iii|\s*ii)?|zwickroell|prüfer|tester|zertifikats-?nr\.|certificate number|reh|rel|rp0\.2|rm|ag|ae)\b`. Bu örüntüler, doğrudan resmi Zwick ekran/doküman terminolojisinden türetilmiştir. citeturn14view0turn16view0turn48view0turn38search3turn38search11

### testXpert II ve III farkı

Kamusal belgelerde görülen en önemli fark, **testXpert II**’nin eski nesil “unique import/export interfaces”, kanal ithali, 12 dil ve terminology swapping mantığıyla tanıtılması; **testXpert III**’ün ise bunu daha belirgin biçimde **workflow-based**, **Export Editor / Results Editor / Channel Editor / Layout Editor** mimarisiyle sunmasıdır. Export açısından “III” için kamusal anlatım daha açık biçimde **results / parameters / channels** seçimini vurgular. Buna karşılık, kamusal kaynaklarda II ve III için karşılaştırmalı “sabit CSV schema farkları” yayımlanmamıştır. citeturn21view0turn14view0turn16view0

## Instron Bluehill Universal ve Bluehill 3

Instron, üç vendor arasında en ayrıntılı export dokümantasyonunu kamusal olarak yayımlayan taraf. Resmi “Results and Raw Data Export Options” dokümanı, export dosyalarının **varsayılan olarak CSV** olduğunu, fakat **custom text file**’a da çevrilebildiğini; içeriğin **Method Parameters, Test Results, Results Statistics ve Raw Data** bloklarından oluşabildiğini; ayrıca **column names, units ve section titles**’ın dahil edilip hariç tutulabildiğini açıkça söylüyor. Aynı doküman **layout**, **separator**, **decimal symbol** ve **encoding** seçeneklerini de satır satır veriyor. citeturn46view0

### A–H format özeti

| Başlık | Değerlendirme |
|---|---|
| **Header yapısı** | Sabit değildir. Export dosyası **Method Parameters**, **Test Results**, **Results Statistics** ve/veya **Raw Data** içerebilir. `Column names`, `Units`, `Section titles` satırları dahil/haric edilebilir; layout yatay veya dikey olabilir. Bu yüzden veri ilk satırda başlayabileceği gibi birkaç metadata/section satırından sonra da başlayabilir. Varsayılan export formatı CSV’dir. citeturn46view0turn47view0 |
| **Kolon adları** | Resmi brochure’larda Bluehill’in temel alan aileleri **Force / Displacement / Time / Results** ve grafik eksenleri olarak **force vs. displacement** ile **stress vs. strain** şeklinde verilir. Alman brochure’da bunlar **Kraft / Verfahrweg / Zeit / Spannungs-/Dehnungs-Daten** olarak görünür. Ayrıca sonuç bağlamında `operator name`, `specimen break location`, `specific specimen properties`, `material ID`, `machine direction` alanları da resmi dokümanlarda geçer. citeturn47view0turn26view0 |
| **Birimler** | Export’ta unit satırı isteğe bağlıdır; dahil veya hariç bırakılabilir. Resmi export dokümanı tek sabit unit contract vermiyor. Kamusal Instron uygulama literatürü ve brochure’lar SI örneklerinde **kN/N, mm, MPa, %, s** bağlamını destekliyor. Dolayısıyla parser’ın unit’i kolon adından değil, dosyada varsa unit row’dan veya parantez içinden çekmesi en güvenlisidir. citeturn46view0turn47view0turn24search4 |
| **Decimal separator** | Resmi olarak **Use system symbol / Decimal / Comma** seçenekleri var. Yani locale’e veya export config’e bağlı olabilir; parser nokta ve virgülü ikisini de desteklemelidir. citeturn46view0 |
| **Encoding** | Resmi olarak **Default, ASCII, UTF‑16, UTF‑8** seçenekleri var. citeturn46view0 |
| **Özel satırlar** | `Section titles`, `Column names`, `Units` dahil/haric olabilir. `Method Parameters` blokları specimen/sample bilgilerini, test method ayarlarını ve file-naming için kullanılan sample inputs’u taşıyabilir. Comment-line karakteri yerine section/block mantığı vardır. citeturn46view0turn47view0 |
| **Fingerprint** | Güçlü imzalar: `BLUEHILL`, `Method Parameters`, `Results Table 1`, `Results Table 2`, `Raw Data`, `Sample name`, `operator name`, `specimen break location`, `material ID`, `machine direction`. Alman locale’de `Kraft`, `Verfahrweg`, `Zeit`, `Bruchposition`, `Probeneigenschaften` de iyi ipuçlarıdır. citeturn46view0turn47view0turn26view0 |
| **Birden fazla export modu** | Evet. **Bluehill Universal** her method için **1 veya 2 custom file + 1 Bluehill report** export edebilir. Ayrıca Results, Statistics ve Raw Data ayrı bloklar hâlinde export edilebilir. **Bluehill 3**’te yalnızca sonuç ve ham veri için `.CSV` export olduğu; **Bluehill Universal**’ın ise aynı default CSV’yi üretebildiği veya output’u tamamen özelleştirebildiği resmi upgrade dokümanında yazılıdır. citeturn46view0turn23search5turn23search6 |

### İngilizce ve Almanca alan ailesi

| Kanonik alan | İngilizce | Almanca | Tipik SI birimi | Not |
|---|---|---|---|---|
| force | Force | Kraft | N, kN | Live Displays ve graph bağlamında resmi. citeturn47view0turn26view0 |
| displacement | Displacement | Verfahrweg | mm | Resmi brochure’da açık. citeturn47view0turn26view0 |
| time | Time | Zeit | s | Resmi brochure’da açık. citeturn47view0turn26view0 |
| stress | Stress | Spannung | MPa | `stress vs. strain` resmi brochure’da açık. citeturn47view0turn26view0 |
| strain | Strain | Dehnung | % | `Spannungs-/Dehnungs-Daten` resmi Alman brochure’da açık. citeturn26view0turn47view0 |
| results | Results / Results Table | Ergebnisse / Ergebnistabelle | method-dependent | Results table ve Results Table 1–2 export blokları resmi. citeturn46view0turn26view0turn47view0 |
| operator | operator name | Bedienername | text | Results sorting alanı. citeturn47view0turn26view0 |
| specimen break location | specimen break location | Bruchposition | text | Results sorting alanı. citeturn47view0turn26view0 |
| specimen properties | specific specimen properties | spezielle Probeneigenschaften | text/numeric | Results sorting alanı. citeturn47view0turn26view0 |
| sample/specimen ID | sample name / specimen info / material ID | Probe / Material‑ID | text | File naming ve grouping için kullanılır. citeturn46view0turn47view0turn26view0 |

Aşağıdaki `column_map`, Bluehill’in resmi export ve UI terminolojisinden türetilmiş normalize setidir. Literal header, method template’e göre biraz farklı olabilir; özellikle `Load (kN)` ile `Force` aynı kanonik alanda toplanmalıdır. Bu bir parser sentezidir. citeturn46view0turn47view0turn26view0turn24search4

```python
BLUEHILL_COLUMN_MAP = {
    "force": [
        "force", "load", "kraft"
    ],
    "displacement": [
        "displacement", "extension", "travel", "verfahrweg"
    ],
    "time": [
        "time", "zeit"
    ],
    "stress": [
        "stress", "tensile stress", "spannung"
    ],
    "strain": [
        "strain", "tensile strain", "dehnung"
    ],
    "operator": [
        "operator name", "bedienername"
    ],
    "specimen_break_location": [
        "specimen break location", "bruchposition"
    ],
    "specimen_properties": [
        "specific specimen properties", "probeneigenschaften"
    ],
    "sample_name": [
        "sample name", "sample", "specimen", "material id"
    ]
}
```

Bluehill için önerilen fingerprint regex’i daha kuvvetlidir: `(?im)^(bluehill(?: universal)?|method parameters|results table 1|results table 2|results statistics|raw data|sample name)\b`. Alman locale eklenecekse `kraft|verfahrweg|zeit|bruchposition|probeneigenschaften` de ikinci katman fingerprint olarak işe yarar. Bu regex’ler resmi export ve brochure terminolojisine dayanır. citeturn46view0turn47view0turn26view0

## Shimadzu Trapezium X ve TrapeziumLite

Shimadzu tarafında kamusal ürün sayfaları, veri alanlarının bir kısmını ve yazılım modlarını iyi gösteriyor; fakat doğrudan “CSV export dialect” ayrıntıları Bluehill kadar açık değil. Resmi sayfalar **TRAPEZIUM X** için **Single / Cycle / Control / Texture** olmak üzere dört yazılım tipi, **TRAPEZIUM X‑V** için buna ek olarak **Spring** tipi olmak üzere beş yazılım tipi olduğunu; ayrıca rapor çıktılarının **PDF, Word, Excel ve HTML** olabildiğini söylüyor. Aynı sayfalar ayrıntılı **Data Processing Reference / Software Reference** kılavuzlarının varlığını da doğruluyor. Ancak bu incelemede kamusal erişimle, Zwick/Instron’daki kadar düşük seviyeli CSV delimiter/encoding/header sözleşmesini doğrudan okuyamadım. citeturn29search1turn29search0turn30view0turn31view0turn39search5turn41search3

### A–H format özeti

| Başlık | Değerlendirme |
|---|---|
| **Header yapısı** | Kamusal içerikte sabit “ilk N satır metadata” yapısı yayımlanmıyor. Resmi özellik sayfaları **report information**, **specimen dimensions**, **specimen information**, **date/specimen/batch statistics** gibi blokların varlığını gösteriyor. Bu da export/report türevlerinde metadata bloklarının mümkün olduğunu, fakat kamusal olarak sabit bir CSV satır kontratı verilmediğini gösteriyor. citeturn30view0turn31view0 |
| **Kolon adları** | Kamusal resmi kaynaklarda görülen əsas alanlar: **test force / 試験力**, **stroke / ストローク**, **strain / ひずみ**, **stress / 応力**, **extensometer / 伸び計**, **displacement / 変位**, **specimen / 試験片**, **batch / バッチ**. Uygulama notlarında ayrıca **Tensile Strength / 引張強さ**, **Elastic Modulus / 弾性率**, **Upper Yield Point / 上降伏点** açıkça görülür. citeturn30view0turn36search3turn36search0turn35view0turn37search0 |
| **Birimler** | Resmi uygulama notlarında **Stress [MPa]**, **Strain [%]**, **Tensile Strength [MPa]**, **Elastic Modulus [GPa]** net olarak gösterilir. Ürün ve uygulama sayfaları ayrıca test speed’in **mm/min** bağlamında kullanıldığını ve load cell kapasitesinin **kN** olduğunu gösterir. Dolayısıyla tipik SI aileleri **N/kN, mm, MPa, %, GPa, s** yönündedir; fakat kamusal bir “default CSV units row” kontratı yayımlanmamıştır. citeturn35view0turn34view0turn37search0 |
| **Decimal separator** | İncelediğim kamusal Shimadzu sayfaları ve arama sonuçları bunu açıkça belirtmiyor. Locale bağı kamuya açık bir CSV dokümanıyla doğrulanamadı. citeturn30view0turn31view0turn39search5 |
| **Encoding** | Kamusal içerikte açık encoding tablosu bulamadım. citeturn39search5turn41search3 |
| **Özel satırlar** | Report designer ve statistics mantığı nedeniyle `report information`, `specimen information`, `batch` ve tarih gibi satırların rapor/excel türevlerinde bulunması makul; fakat kamusal CSV kuralı yayımlanmadığı için `#`, `;`, `//` tipi comment satırlarını varsaymak yerine metadata bloklarını sniff etmek gerekir. Resmi sayfalar en azından specimen, dimensions, report info, batch/date istatistiği alanlarının bulunduğunu doğruluyor. citeturn30view0turn31view0 |
| **Fingerprint** | Güçlü ipuçları: `TRAPEZIUM X`, `TRAPEZIUMX-V`, `TRAPEZIUM LITE X`, `SHIMADZU`, Japonca alanlar olarak `試験力`, `ひずみ`, `応力`, `試験片`, `引張強さ`, `弾性率`, `バッチ`. Bu string’ler resmi ürün ve uygulama sayfalarında doğrudan görünüyor. citeturn29search1turn29search0turn30view0turn36search0turn35view0turn37search0 |
| **Birden fazla export modu** | Evet; en azından yazılım modu olarak **Single / Cycle / Control / Texture** ve X‑V’de **Spring** ayrımı var. Ayrıca kamusal sayfalar rapor çıktısını **PDF / Word / Excel / HTML** olarak doğruluyor. CSV tarafında ise kamusal ayrıntı net değil; fakat entegre **TRViewX** için strain data’nın CSV olarak kaydedilebildiği açıkça yazıyor. citeturn29search1turn29search0turn30view0turn31view0turn33search11turn32search0 |

### İngilizce ve Japonca alan ailesi

| Kanonik alan | İngilizce | Japonca | Tipik SI birimi | Not |
|---|---|---|---|---|
| force | test force | 試験力 | N, kN | Resmi Japanese features sayfasında. citeturn30view0turn36search3 |
| stroke | stroke | ストローク | mm | Resmi Japanese features sayfasında. citeturn30view0turn36search3 |
| strain | strain | ひずみ | % | Resmi basics page ve app note grafiklerinde. citeturn36search0turn35view0 |
| stress | stress | 応力 | MPa | Resmi basics page ve app note grafiklerinde. citeturn36search0turn35view0 |
| extensometer | extensometer | 伸び計 | mm, % | Resmi features ve accessory bağlamında. citeturn30view0turn37search4 |
| displacement | displacement | 変位 | mm | Japanese features sayfasındaki monitoring açıklamasında displacement ailesi geçiyor. citeturn30view0turn36search3 |
| specimen | specimen | 試験片 | text | Resmi features/applications içeriğinde. citeturn31view0turn37search0 |
| batch | batch | バッチ | text | Resmi features sayfası istatistik bağlamında. citeturn30view0 |
| tensile strength | tensile strength | 引張強さ | MPa | Uygulama notlarında resmi olarak mevcut. citeturn35view0turn37search0 |
| elastic modulus | elastic modulus | 弾性率 | GPa | Uygulama notlarında resmi olarak mevcut. citeturn35view0turn37search0 |
| upper yield point | yield strength / upper yield point | 上降伏点 | MPa | Japon application note sonucunda geçiyor. citeturn37search0 |

Aşağıdaki `column_map`, resmi Shimadzu ürün sayfaları ve uygulama notlarında görülen terimlerden türetilmiş normalize setidir. Özellikle TRAPEZIUM tarafında literal default CSV header’ı olarak değil, **robust alias map** olarak kullanılması gerekir. citeturn30view0turn31view0turn35view0turn37search0turn36search0

```python
SHIMADZU_COLUMN_MAP = {
    "force": [
        "test force", "force", "試験力"
    ],
    "stroke": [
        "stroke", "ストローク"
    ],
    "stress": [
        "stress", "応力"
    ],
    "strain": [
        "strain", "ひずみ"
    ],
    "extensometer": [
        "extensometer", "伸び計"
    ],
    "displacement": [
        "displacement", "変位"
    ],
    "specimen": [
        "specimen", "試験片"
    ],
    "batch": [
        "batch", "バッチ"
    ],
    "tensile_strength": [
        "tensile strength", "引張強さ"
    ],
    "elastic_modulus": [
        "elastic modulus", "弾性率"
    ],
    "upper_yield_point": [
        "upper yield point", "上降伏点"
    ]
}
```

Fingerprint regex önerisi: `(?im)^(trapezium(?:x-v| x| lite x)?|shimadzu|試験力|応力|ひずみ|試験片|引張強さ|弾性率|バッチ)\b`. Bu da ürün ve uygulama notlarındaki resmi string’lerden türetilmiştir. citeturn29search1turn29search0turn30view0turn35view0turn37search0

### AGS‑X, AG‑IS, Autograph serileri arasında beklenen fark

Kamusal resmi içerik, **TRAPEZIUM Lite X**’in **AGS‑X** ve **EZ‑Test**’e bağlanabildiğini, **TRAPEZIUMX‑V**’nin ise **AGX‑V, AG‑X, AGS‑X ve EZ‑X** ile uyumlu olduğunu gösteriyor. Bu, dosya formatı tarafında temel farkın load frame modelinden çok **yazılım nesli ve seçilen method/report template’inden** gelme olasılığını güçlendirir. İncelediğim kamusal kaynaklarda “AGS‑X export CSV şöyle, AG‑IS böyle” şeklinde ayrı dosya kontratları yayımlanmamış. citeturn28search1turn39search13turn39search2

## Bonus vendorlar için kısa notlar

**Tinius Olsen Horizon** resmi sayfalarında test verisinin “outside source”a export edilebildiği, ayrıca **results, limits, statistics ve curve points**’in external file’a aktarılabildiği yazıyor. Brochure snippet’inde grafik örnekleri olarak **stress v strain** ve **load v time** geçiyor. Buna göre parser tarafında beklenebilecek alan aileleri `load/force`, `time`, `stress`, `strain`, `statistics`, `curve points` olur. Delimiter kamusal sayfalarda yayınlanmıyor; Horizon çıktıları yöntem ve output editor ile biçimlendirilebiliyor. citeturn43search1turn43search0turn43search15

**MTS TestSuite** için kamusal resmi eğitim ve ürün içerikleri, yazılımın **reports, results ve raw data** export ettiğini; kullanıcıların **data collection**, **primary tension test properties** ve **data export** konularında çalıştığını doğruluyor. Ancak incelediğim kamusal içerik default CSV kolonlarını veya delimiter’ı açık seçik vermiyor. Bu nedenle kısa cevap: `force/displacement/strain/stress benzeri primary tension properties + result/export template`, fakat delimiter **kamusal dokümanda net değil**. citeturn42search8turn42search9turn42search6turn42search5

**DEVOTRANS CKS‑III** için resmi sayfa çok daha somut: program test sırasında elde edilen verileri standarda göre analiz ediyor; **kuvvet, uzama, ekstansometrik uzama, gerilme** değerlerini birlikte yönetebiliyor; birimler olarak **gf, kgf, N, kN, lb**, ayrıca **N/mm², kPa, MPa** ve **mm, cm, dm, m, inç, %** veriyor; sonuçlar arasında **E‑modülü, akma sınırı, %0.2 sınırı, max. kuvvet, kopma mukavemeti, max. ekstansometrik uzama** bulunuyor; raporlar **PDF** olarak alınabiliyor ve veriler **Excel’e** aktarılabiliyor. Kamusal sayfada CSV delimiter bilgisi verilmediği için separator alanı **net değil**; en güvenlisi Excel/XLSX veya vendor-format sniffing kabul etmektir. citeturn45view0

**Hegewald & Peschke LabMaster** resmi sayfası, sonuçlar ve istatistiklerin seçili file format’lara export edilebildiğini ve **real-time data**’nın **configurable ASCII file** olarak kaydedilebildiğini söylüyor. Bu yüzden beklenen alan ailesi `results`, `statistics`, `real-time data` ve tipik tensile tarafında `force/displacement/stress/strain` benzeri kanallardır; separator ise **ASCII output configurable** olduğu için sabit kabul edilmemelidir. citeturn42search0

## Parser tasarımı için ortak strateji

Bu araştırmanın en pratik sonucu, vendor-agnostic parser’ı **“tek universal CSV schema”** varsayımıyla değil, **vendor fingerprint → section sniffing → column alias normalization → unit/locale sniffing** zinciriyle kurmaktır. Bluehill için resmi export dokümanı size doğrudan `separator`, `decimal symbol`, `encoding`, `section titles`, `units` gibi kontrol noktaları veriyor. Zwick’te export, resmi olarak `results / parameters / channels` ve organization data mantığıyla template-driven; Shimadzu’da ise kamusal sayfalarda veri alanları ve rapor blokları görülüyor ama CSV dialect ayrıntıları public değil. citeturn46view0turn14view0turn16view0turn48view0turn30view0turn31view0

Bu yüzden güvenli sıralama şöyle olmalı: önce dosyanın ilk 50–100 satırında vendor fingerprint ara; sonra delimiter sniffing’i `,`, `;`, `\t`, `|` adaylarıyla yap; sonra section başlıklarını ve metadata bloklarını tespit et; en sonda kolon adlarını normalize et. **Bluehill**’de `decimal symbol` nokta veya virgül olabilir; **Zwick** ve **Shimadzu** için kamusal kaynakta net veri olmadığından, sayısal token dağılımına göre otomatik tespit daha güvenlidir. citeturn46view0turn14view0turn16view0

Aşağıdaki birleşik fingerprint haritası, yukarıdaki resmi terminolojiye dayanan pratik bir başlangıç setidir. Bluehill tarafı daha deterministik; Zwick ve Shimadzu tarafı ise özellikle sample export’larla doğrulanırsa daha güçlü olur. citeturn46view0turn14view0turn16view0turn29search1turn29search0

```python
VENDOR_FINGERPRINTS = {
    "zwick_testxpert": [
        r"(?im)\btestxpert(?:\s*iii|\s*ii)?\b",
        r"(?im)\bzwickroell\b",
        r"(?im)\bprüfer\b",
        r"(?im)\btester\b",
        r"(?im)\bzertifikats-?nr\.?\b",
        r"(?im)\bcertificate number\b",
        r"(?im)\bReH\b|\bReL\b|\bRp0\.2\b|\bRm\b|\bAg\b|\bAe\b"
    ],
    "instron_bluehill": [
        r"(?im)\bbluehill(?:\s*universal)?\b",
        r"(?im)^method parameters\b",
        r"(?im)^results table 1\b",
        r"(?im)^results table 2\b",
        r"(?im)^raw data\b",
        r"(?im)^sample name\b"
    ],
    "shimadzu_trapezium": [
        r"(?im)\btrapezium(?:x-v| x| lite x)?\b",
        r"(?im)\bshimadzu\b",
        r"(?im)試験力|応力|ひずみ|試験片|引張強さ|弾性率|バッチ"
    ]
}
```

Son olarak, **doğrudan kamusal resmi kaynaklarla %100 doğrulanabilen en güçlü dosya kontratı Bluehill’de**; **Zwick** ve özellikle **Shimadzu** tarafında ise public materyaller daha çok “hangi veri aileleri ve hangi editor/report mantığı var?” sorusunu cevaplıyor. Eğer amacınız yüksek doğrulukla otomatik tespit yapmaksa, bu araştırmanın gösterdiği en sağlam yaklaşım şudur: **Bluehill’i format-rule ile**, **Zwick’i terminology/template-rule ile**, **Shimadzu’yu sample-backed heuristic ile** parse etmek. citeturn46view0turn14view0turn16view0turn39search5turn41search3