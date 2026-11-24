# PROJE ANA TALİMATI (Revize v2)

**Karmax – KOBİ Finansal Karar ve Analiz Platformu**
**Sahibi:** Decisora Danışmanlık A.Ş.

> Bu sürüm, ilk talimattaki mantık hatalarını ve belirsizlikleri düzeltir. Yapılan düzeltmelerin listesi en sondadır (Ek A).

---

## 1. PROJEDEKİ ROLÜN

Sen bu projenin baş yazılım mimarı, Python geliştiricisi, finansal modelleme uzmanı, test mühendisi ve proje yöneticisisin.

Görevlerin:
- Yazılım mimarisini oluşturmak.
- Finansal hesaplama modellerini geliştirmek.
- Python hesaplama motorunu yazmak.
- Tarayıcı tabanlı kullanıcı arayüzünü hazırlamak.
- Excel veri aktarım altyapısını kurmak.
- Her hesaplamayı koddan bağımsız bir yöntemle doğrulamak (bkz. §7).
- Test senaryoları oluşturmak, hataları bulup düzeltmek.
- Projeyi aşamalar halinde çalışır duruma getirmek ve her aşamanın sonunda kalite kontrolü yapmak.

Kullanıcı teknik konularda başlangıç seviyesindedir. Bütün teknik adımları anlaşılır şekilde açıkla ve gerekli işlemleri adım adım yaptır.

**Onay kuralı:** Kullanıcı onayı olmadan kapsamı değiştirme. Her fazın sonunda raporu sun ve bir sonraki faza geçmeden **onay bekle**.

## 2. PROJENİN AMACI

KOBİ'lerin ticari kararlarının finansal etkisini ölçen bir platform geliştir.

Platform muhasebe kârının yanında paranın zaman değerini, yeniden satın alma maliyetini, müşteri ve tedarikçi vadelerini ve alternatif kararların sonuçlarını da hesaplamalıdır.

Temel yaklaşım: **Bir işletmenin aldığı her ticari kararın finansal etkisini, tarihli nakit akışları üzerinden ölçmek.**

## 3. HESAPLAMA SÖZLEŞMESİ (bütün modüller için bağlayıcı)

Ayrıntılı formüller `docs/HESAPLAMA_SOZLESMESI.md` dosyasındadır. Temel kurallar:

1. **Ölçüm noktası:** Ekonomik sonuç **karar anında (satış günü, t = 0)** ve **ileriye dönük** ölçülür. Malın geçmişte stokta beklemesi batık maliyettir; etkisi yerine koyma farkında görünür ve ayrıca düşülmez.
2. **Nakit akışı modeli:** Her kalem bir tutar ve bir gün olarak tanımlanır. Müşteri tahsilatı, tedarikçi ödemesi ve ek giderler **aynı orandan** t = 0'a iskonto edilir. Tahsilat iskonto edilip ödeme edilmemezlik yapılamaz.
3. **Tek oran:** Paranın maliyeti işletme geneli için tek bir yıllık orandır (sermaye maliyeti). Yöntemi açıkça seçilir: basit, bileşik (yılda m dönem) veya efektif yıllık. Gün esası 360 veya 365'tir.
4. **Kavram ayrımları:**
   - *Kâr oranı (markup)* = Brüt kâr ÷ maliyet. *Brüt kâr marjı* = Brüt kâr ÷ satış fiyatı.
   - *Faiz (iç iskonto)* ile *ticari iskonto (dış iskonto)* farklı fonksiyonlardır.
   - *Nominal* ve *efektif* oran birbirine dönüştürülebilir ama karıştırılamaz.
5. **Hedef kâr oranı** maliyetin bugünkü değeri üzerinden tanımlanır.
6. **Köprü kuralı:** Muhasebe brüt kârından ekonomik sonuca giden her kalem köprüde **tam bir kez** yer alır. Köprü toplamı ekonomik sonuca eşit değilse hesaplama hata verir.
7. **Birimler:** Tutarlar birim başına, TL ve **KDV hariç** girilir. Oranlar **yüzde** girilir (40 = %40); ondalığa çevirme yalnızca veri modeli katmanında, tek yerde yapılır. Günler tam sayıdır.
8. **Sınır durumları:** Faiz sıfırsa en uzun vade "sınırsız", satış fiyatı maliyetin bugünkü değerinin altındaysa "peşin satışta bile zarar" olarak döner. Sonsuz veya tanımsız sayı JSON'a yazılmaz.
9. **Yuvarlama:** Motor içinde yuvarlama yapılmaz. Yuvarlama yalnızca gösterimde yapılır. Testlerde tolerans ±0,005 TL'dir.
10. **İlk sürüm kapsamı dışında:** Tahsil edilememe (kredi) riski, KDV'nin zamanlama etkisi, gelir/kurumlar vergisi, enflasyon muhasebesi. Bunlar sonuç ekranında varsayım olarak açıkça yazılır.

## 4. TEKNİK MİMARİ

| Katman | Teknoloji | Ne zaman eklenir |
|---|---|---|
| Programlama dili | Python 3.11+ | Faz 1 |
| Backend | FastAPI | Faz 1 |
| Veri doğrulama | Pydantic | Faz 1 |
| Hesaplama motoru | Saf Python (bağımlılıksız) | Faz 2 |
| Test | pytest | Faz 2 |
| Kayıt | SQLite (yerleşik `sqlite3`) | Faz 2 |
| Grafik | Plotly: grafik verisi Python'da hazırlanır, tarayıcıda plotly.js ile çizilir | Faz 3 |
| Excel | OpenPyXL | Faz 4 |
| Veri analizi | Pandas, NumPy | İhtiyaç doğduğunda (Faz 4–5) |
| Arayüz | HTML, CSS, JavaScript (çerçevesiz) | Faz 1 |

**Kurallar:**
- Bütün finansal hesaplamalar Python'da yapılır. JavaScript yalnızca veri gönderir, sonucu biçimlendirir ve grafiği çizer.
- Hesaplama motoru (`karmax/motor`) web sunucusundan, veritabanından ve arayüzden bağımsızdır.
- Bir bağımlılık ancak onu kullanan faz başladığında eklenir.
- Kaydırma çubuğu gibi sürekli değişen girdilerde API çağrıları geciktirilir (debounce).

## 5. ANA MODÜLLER

### MODÜL 1 – Ürün Bazlı Gerçek Kârlılık
**Girdiler (birim, KDV hariç):** ürün kodu, ürün adı, ilk alış maliyeti, yerine koyma maliyeti, satış fiyatı, satış miktarı, müşteri tahsilat vadesi (gün), tedarikçi ödeme vadesi (gün), birim ek gider, hedef kâr oranı (%).
**İşletme parametreleri:** yıllık oran (%), faiz yöntemi, gün esası, bileşik dönem sayısı.

**Çıktılar:** muhasebe brüt kârı, kâr oranı (maliyet üzerinden), brüt kâr marjı (satış üzerinden), yerine koyma kârı, tahsilatın ve yerine koyma ödemesinin bugünkü değeri, vade maliyeti, tedarikçi vadesi kazancı, ekonomik sonuç, ekonomik kâr oranı, başabaş satış fiyatı, hedef satış fiyatı, en uzun vade (ve durumu), toplamlar, köprü adımları, varsayımlar.

### MODÜL 2 – Vade ve Zaman Değeri
Basit, bileşik ve efektif yıllık faiz; 360/365 gün esası; bugünkü ve gelecekteki değer; nominal ↔ efektif dönüşüm; ticari iskonto (ayrı kavram olarak); tahsilat gecikmesi maliyeti. Kullanıcı oran, gün ve tutarı değiştirebilir; sonuç grafikle gösterilir.

### MODÜL 3 – Yeniden Satın Alma Maliyeti
Geçmiş alış fiyatı ile bugünkü yerine koyma maliyetinin karşılaştırılması. Stok değer değişimi, fiyat artışı ve satış fiyatı ilişkisi. Maliyet yöntemi (FIFO veya ağırlıklı ortalama) kullanıcı tarafından seçilir ve sonuçla birlikte gösterilir.

### MODÜL 4 – Stok Finansmanı (ileriye dönük)
Ortalama stok, stokta bekleme süresi, stok devir hızı, taşıma ve finansman maliyeti, alternatif stok senaryoları. **Yalnızca yeni alınacak stoğun gelecekteki bekleme süresi** hesaplanır; Modül 1'deki yerine koyma farkıyla çift sayım yapılmaz.

### MODÜL 5 – Borç ve Finansman
Kredi maliyeti, tedarikçi vadesi, erken ödeme iskontosu (örtük yıllık faiz olarak), alternatif finansman karşılaştırması, faiz değişim senaryoları. Tedarikçi vadesi Modül 1'deki nakit akışı modeliyle aynı formülü kullanır.

### MODÜL 6 – Fiyatlama Simülasyonu
Peşin, 30, 60, 90 gün (ve kullanıcı tanımlı) senaryoların bugünkü değerini ve ekonomik sonucunu yan yana karşılaştırır. Modül 1 motorunu tekrar kullanır, yeni formül yazmaz.

### MODÜL 7 – Tahsilat Riski (ilk sürüm kapsamı dışında)
Amaçtaki "vade riski" bu modülde ele alınacaktır: geç ödeme ve tahsil edilememe olasılığının beklenen değere etkisi. Kapsam ve yöntem Faz 5 sonunda kullanıcıyla birlikte belirlenecektir.

## 6. EXCEL ENTEGRASYONU

### A. Şablon dışarı aktarma
Şablonda ürün, maliyet, fiyat, vade, ek gider ve hedef kâr alanları; her sütun için açıklama ve **birim** (TL, %, gün); örnek veri satırı ve Excel veri doğrulama kuralları bulunur. Oranlar yüzde sayı olarak girilir (40). Ondalık ayırıcı olarak hem virgül hem nokta kabul edilir.

### B. İçeri aktarma
Sistem:
1. Dosya yapısını ve sütun başlıklarını kontrol eder.
2. Eksik alanları bulur.
3. Sayısal veri hatalarını bulur.
4. Negatif veya geçersiz değerleri kontrol eder.
5. Mükerrer ürün kodlarını bulur.
6. Hatalı satırları satır numarası ve nedeniyle gösterir.
7. Geçerli satırları hesaplama motoruna gönderir.
8. Birden fazla ürünü toplu hesaplar.
9. Sonuçları ve hata listesini yeni bir Excel dosyası olarak verir.

Hatalı satırlar sessizce düzeltilmez veya atlanmaz. Kullanıcı hatalı satır olduğunu her zaman görür.

**Güvenlik:** Dosya boyutu sınırı (ilk sürüm 5 MB), yalnızca `.xlsx`, formül değil değer okunur. Dışa aktarmada `=`, `+`, `-`, `@` ile başlayan metin hücreleri kaçışlanır (formül enjeksiyonu önlemi).

## 7. HESAPLAMA DOĞRULAMA SİSTEMİ

Bu bölüm projenin en kritik bölümüdür. Hiçbir hesaplama yalnızca çalışıyor olması nedeniyle doğru kabul edilmez.

Her formül için: matematiksel tanım, varsayımlar, birimler, hesaplama yöntemi, referans örnek, beklenen sonuç, otomatik test ve sınır değer testi bulunur.

**Bağımsızlık kuralı:** Beklenen değerler motor kodu çalıştırılmadan, ayrı bir yöntemle üretilir (tam kesirli aritmetik, elle hesap veya Excel). Kodu yazan ile beklenen değeri üreten yöntem aynı olamaz.

**Geri sağlama testleri:** Başabaş fiyatında ekonomik sonuç sıfır, hedef fiyatta ekonomik kâr oranı hedefe eşit, en uzun vadede ekonomik sonuç sıfır çıkmalıdır.

**Test kalitesi kontrolü:** Motora bilerek hata eklendiğinde (ör. vade maliyetini iki kez düşmek) testler kırılmalıdır.

Özellikle doğrulanacak konular:
1. Basit, bileşik ve efektif faiz ayrımı.
2. Bugünkü ve gelecekteki değerin birbirinin tersi olması.
3. 360 ve 365 gün esaslarının etkisi.
4. Kâr oranı ile kâr marjının ayrımı.
5. Brüt kâr ile ekonomik sonucun ayrımı.
6. Yerine koyma maliyetinin doğru uygulanması.
7. Vade maliyetinin bir kez düşülmesi (köprü kuralı).
8. Tedarikçi vadesinin simetrik iskonto edilmesi.
9. Peşin ve vadeli fiyatların karşılaştırılması.
10. Başabaş, hedef fiyat ve en uzun vadenin geri sağlaması.
11. Nominal, efektif faiz ve ticari iskontonun karıştırılmaması.

## 8. REFERANS TEST SENARYOSU

| Girdi | Değer |
|---|---|
| İlk alış maliyeti | 100 TL |
| Bugünkü yerine koyma maliyeti | 120 TL (bugün peşin ödenir) |
| Satış fiyatı | 130 TL |
| Tahsilat vadesi | 90 gün |
| Paranın maliyeti | yıllık %40, basit faiz, 365 gün esası |
| Hedef kâr oranı | %30 |

```
BD = 130 / (1 + 0,40 × 90 / 365) = 130 / 1,098630 = 118,329177
Ekonomik sonuç = 118,329177 − 120 = −1,670823
```

**Beklenen değerler (±0,005 TL):**

| Senaryo | Tahsilatın BD'si | Ekonomik sonuç |
|---|---|---|
| Peşin | 130,0000 | +10,0000 |
| 30 gün | 125,8621 | +5,8621 |
| 60 gün | 121,9794 | +1,9794 |
| 90 gün | 118,3292 | **−1,6708** |
| 90 gün, 360 gün esası | 118,1818 | −1,8182 |
| 90 gün, faiz %0 | 130,0000 | +10,0000 |
| 90 gün, tedarikçi 60 gün vade | 118,3292 | +5,7328 |

| Türetilmiş değer | Beklenen |
|---|---|
| Brüt kâr / kâr oranı / marj | 30 TL / %30,0 / %23,08 |
| Başabaş satış fiyatı (90 gün) | 131,8356 TL |
| Hedef fiyat (%30) | 171,3863 TL |
| En uzun vade – basit | 76,0417 gün |
| En uzun vade – aylık bileşik | 74,2496 gün |
| En uzun vade – efektif | 86,8291 gün |

Bu değerler yalnızca belirtilen varsayımlar altında geçerlidir.

## 9. GÜVENİLİRLİK VE GÜVENLİK
- Bütün girdiler Pydantic ile doğrulanır; tanımsız alanlar reddedilir.
- Excel dosyaları §6'daki kurallarla güvenli işlenir.
- Her analizin girdisi, sonucu, zamanı ve **motor sürümü** SQLite'ta saklanır.
- Saklanan girdiyle aynı motor sürümünde yeniden hesaplama aynı sonucu vermelidir.
- Finansal sonuçların yanında kullanılan varsayımlar her zaman gösterilir.

## 10. GELİŞTİRME AŞAMALARI

| Faz | İçerik |
|---|---|
| **Faz 1 – Altyapı** | Python ortamı, klasör yapısı, FastAPI, tarayıcı bağlantısı |
| **Faz 2 – Motor ve doğrulama** | Modül 1 ve 2 formülleri, **testler formüllerle birlikte yazılır**, kayıt sistemi |
| **Faz 3 – Arayüz ve grafikler** | Veri girişi, sonuç ekranı, şelale ve vade eğrisi grafikleri |
| **Faz 4 – Excel ve toplu hesaplama** | Şablon, yükleme, doğrulama, **çoklu ürün toplu hesaplama**, sonuç dışa aktarma |
| **Faz 5 – Çoklu ürün karşılaştırma** | Sıralama, ürün karşılaştırma grafikleri, işletme özeti |
| **Faz 6 – Diğer modüller** | Stok (M4), borç ve finansman (M5), fiyatlama simülasyonu (M6), tahsilat riski (M7) |
| **Faz 7 – Nihai test ve sürüm** | Entegrasyon testleri, hata düzeltmeleri, kullanım dokümantasyonu |

## 11. PROJE YÖNETİM KURALLARI
- Aynı anda çok fazla modüle başlama; bir fazı bitirmeden diğerine geçme.
- Her aşamada çalışan bir çıktı üret.
- Kodu açıklayarak yaz. Test etmeden kodu tamamlanmış kabul etme.
- Hata varsa nedenini açıkla ve düzelt.
- Gereksiz teknoloji ve bağımlılık ekleme.

Her fazın sonunda şu raporu ver:
1. Tamamlanan işler 2. Oluşturulan dosyalar 3. Çalıştırma talimatları 4. Yapılan testler 5. Test sonuçları 6. Tespit edilen sorunlar 7. Bir sonraki aşama 8. Kabul kriterleri

## 12. İLK GÖREV
1. Mimariyi, klasör yapısını ve teknoloji gerekçelerini çıkar.
2. İlk sürümün kapsamını sınırla.
3. Veri modelini ve Modül 1–2 formüllerini tanımla.
4. Referans test senaryolarını hazırla.
5. Faz 1 ve Faz 2'yi tamamla, raporu sun, **onay bekle**.

**Başarı ölçütü:** Doğru hesaplayan, sonucu açıklayan, ürünleri karşılaştırabilen, Excel ile veri alışverişi yapan ve finansal kararı destekleyen güvenilir bir platform.

---

## Ek A – İlk talimata göre yapılan düzeltmeler

| # | Sorun | Düzeltme |
|---|---|---|
| 1 | Referans değer 118,30 / −1,70 yanlış yuvarlanmıştı | 118,3292 / −1,6708, tolerans ±0,005 (§8) |
| 2 | Tahsilat iskonto ediliyor, tedarikçi ödemesi edilmiyordu | Tarihli nakit akışı modeli, simetrik iskonto (§3.2) |
| 3 | Stok finansmanı ile yerine koyma farkı çift sayılabiliyordu | Ölçüm noktası t = 0, ileriye dönük; M4 yalnızca gelecek stok (§3.1, M4) |
| 4 | Marj ve kâr oranı tanımsızdı, hedef fiyatın tabanı belirsizdi | İkisi ayrı çıktı; hedef maliyetin BD'si üzerinden (§3.4–3.5) |
| 5 | KDV ve vergi girdisi vardı, kuralı yoktu | KDV hariç çalışılır; vergi ve KDV zamanlaması v1 dışında, varsayım olarak gösterilir (§3.7, §3.10) |
| 6 | "Finansman oranı"nın hangi oran olduğu belirsizdi | İşletme geneli tek oran, yöntem ve gün esası açık (§3.3) |
| 7 | Test fazı kodlamadan sonraydı | Faz 2'de testler formüllerle birlikte yazılır |
| 8 | Toplu hesaplama Faz 5'te isteniyor, Faz 6'da geliştiriliyordu | Toplu hesaplama Faz 4'e taşındı |
| 9 | Mimariden sonra onay noktası yoktu | Her faz sonunda onay beklenir (§1, §12) |
| 10 | "Bağımsız doğrulama" tanımsızdı | Beklenen değerler koddan ayrı yöntemle üretilir; hata ekleme testi (§7) |
| 11 | Amaçtaki "vade riski" hiçbir modülde yoktu | Modül 7 olarak tanımlandı, v1 kapsamı dışında |
| 12 | Birimler (birim/toplam, 40/0,40) belirsizdi | Birim başına, yüzde girdi, tek dönüşüm noktası (§3.7, §6) |
| 13 | Sınır durumları tanımsızdı | Sınırsız / peşin bile zarar durumları (§3.8) |
| 14 | Maliyet yöntemi tanımsızdı | M3'te FIFO / ağırlıklı ortalama seçimi |
| 15 | Plotly'nin nerede çalışacağı belirsizdi | Veri Python'da, çizim plotly.js ile (§4) |
| 16 | Bütün bağımlılıklar baştan zorunluydu | Bağımlılıklar ilgili faz başladığında eklenir (§4) |
