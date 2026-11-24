# Karmax Kullanım Kılavuzu

## Başlamadan önce: paranın maliyeti

Sayfanın en üstündeki **Paranın maliyeti** kutusu bütün modüller için geçerlidir.

- **Yıllık oran (%)**: İşletmenin parayı bulma maliyeti. Kredi kullanıyorsan kredi faizin, nakdin varsa onu nemalandırabileceğin oran. 40 yaz, %40 demektir.
- **Faiz yöntemi**: Emin değilsen **Basit faiz** bırak. Bankanın verdiği oran efektif yıllık ise **Efektif** seç.
- **Gün esası**: Genellikle 365.

## 1. Ürün analizi

1. Ürünün bilgilerini gir. Bütün tutarlar **birim başına ve KDV hariç**.
   - *İlk alış maliyeti*: Stoktaki malı geçmişte kaça aldın?
   - *Bugünkü yeniden alış maliyeti*: Aynı malı bugün kaça alırsın?
   - *Müşteri tahsilat vadesi*: Müşteri kaç gün sonra ödüyor?
   - *Tedarikçi ödeme vadesi*: Yerine koyacağın malı kaç gün sonra ödeyeceksin?
2. Sonuçlar yazarken güncellenir. **Canlı senaryo** çubuklarıyla fiyatı, vadeyi ve oranı kaydırarak etkisini anında görebilirsin. Bu önizlemeler kaydedilmez.
3. Sonucu saklamak için **Hesapla ve kaydet**'e bas. Her kayıt bir analiz numarası alır.

**Nasıl okunur?**
- *Muhasebe brüt kârı*: Muhasebecinin göreceği kâr.
- *Ekonomik sonuç*: Malı yeniden almanın ve vadenin maliyeti düşüldükten sonra kalan gerçek kâr. Negatifse bu satış aslında para kaybettiriyor.
- *Başabaş satış fiyatı*: Bu vadede zarar etmemek için en düşük fiyat.
- *Verilebilecek en uzun vade*: Bu fiyatta en fazla kaç gün vade verebilirsin.

## 2. Toplu analiz (Excel)

1. **Excel şablonunu indir**.
2. **Ürünler** sayfasına her satıra bir ürün yaz. Başlık satırını değiştirme. Sütun açıklamaları başlıkların üzerine gelince görünür; örnek satır **Açıklamalar** sayfasındadır.
3. **Parametreler** sayfasında paranın maliyetini gir. Toplu analizde bu sayfadaki değerler kullanılır.
4. Dosyayı kaydet, Karmax'ta **Dosya seç** → **Yükle ve analiz et**.

**Hatalı satırlar** hesaplamaya alınmaz ve satır numarası, hata nedeni ve girdiğin değerle birlikte listelenir. Düzeltip dosyayı tekrar yükleyebilirsin. Aynı ürün kodu iki kez yazılmışsa ikisi de hatalı sayılır; Karmax hangisinin doğru olduğunu tahmin etmez.

**Sayı yazma:** `12,5` veya `12.5` yazabilirsin. Metin olarak yazılmış `1.250` gibi belirsiz bir sayıyı Karmax tahmin etmez, satırı hata olarak gösterir: binlik için `1250`, ondalık için `1,25` yaz.

**Sonuç Excel'ini indir** düğmesi özet, ürün sonuçları ve hatalar sayfalarını içeren bir dosya verir.

## 3. Fiyat ve tahsilat riski

Ürün bilgileri **Ürün analizi** sekmesinden alınır.

- Senaryo tablosunda fiyat ve vade kombinasyonlarını düzenle veya yenilerini ekle.
- *Peşine eşdeğer fiyat*: Bu vadede peşin satışla aynı kazancı sağlamak için istenmesi gereken fiyat.
- **Tahsilat riski**: Müşterinin ödeme olasılığını ve ortalama gecikmesini gir. *Riskli sonuç* bu riskleri hesaba katar.

## 4. Stok ve maliyet

**Stok finansmanı**: Yıllık satılan malın maliyetini ve ortalama stok tutarını (bugünkü alış fiyatlarıyla) gir. Karmax stokta bekleme süresini, yıllık stok maliyetini ve farklı stok günlerinde ne kadar nakit serbest kalacağını gösterir.

**Parti maliyeti**: Aynı malı farklı fiyatlarla aldıysan partileri eskiden yeniye yaz. Satılan malın birim maliyetini **Ürün analizine aktar** ile ürün formuna taşı.

## 5. Finansman

- **Erken ödeme iskontosu**: "Peşin öderseniz %2 indirim" teklifinin yıllık faiz karşılığını hesaplar ve peşin ödemenin mi, vadeyi kullanmanın mı daha ucuz olduğunu söyler.
- **Finansman alternatifleri**: Kredileri aynı tabloda karşılaştırır. *Efektif yıllık maliyet* masraflar dahil gerçek maliyettir. *Bugünkü değer maliyeti* negatifse kredi, işletmenin paranın maliyetinden ucuzdur. BSMV/KKDF gibi vergileri faiz oranına ekle.

## Sık sorulanlar

**Karmax.bat açılıp hemen kapanıyor.** Pencerede bir hata mesajı kalır; en sık neden Python'un kurulu olmamasıdır. Mesajdaki adımları izle.

**Tarayıcı açılmadı.** Siyah pencerede yazan adresi tarayıcına yaz. Karmax'ın adresi normalde **`http://127.0.0.1:8737/`**'dir. Bu port doluysa bir sonraki boş port (8738, 8739…) kullanılır ve pencerede yazar.

**Tarayıcıda başka bir program açıldı.** `http://127.0.0.1:8000/` gibi adresler başka projelerine ait olabilir. Karmax'ı her zaman `Karmax.bat` ile aç ya da siyah pencerede yazan adresi kullan.

**Verilerim nerede?** Bütün analizler proje klasöründeki `veri\karmax.sqlite3` dosyasında. Bilgisayar dışına hiçbir veri gönderilmez.

**Sonuçlar neyi hesaba katmıyor?** Her sonucun altındaki **Varsayımlar** listesine bak. KDV'nin zamanlaması, gelir vergisi ve enflasyon muhasebesi bu sürümde yoktur.
