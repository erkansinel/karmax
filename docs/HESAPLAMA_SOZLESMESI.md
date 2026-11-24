# Hesaplama Sözleşmesi

Karmax'ın bütün modülleri bu belgedeki tanımlara uyar. Bir formül değişirse önce bu belge, sonra testler, en son kod güncellenir.

## 1. Semboller

| Sembol | Anlamı | Birim |
|---|---|---|
| P | Birim satış fiyatı (KDV hariç) | TL |
| C₀ | İlk (geçmiş) alış maliyeti | TL |
| R | Bugünkü yerine koyma maliyeti | TL |
| G | Birim ek gider (bugün ödenir) | TL |
| t_tah | Müşteri tahsilat günü | gün |
| t_ted | Yerine koyma ödemesinin günü | gün |
| r | Yıllık oran (ondalık; girdi yüzde) | – |
| B | Gün esası, 360 veya 365 | gün |
| m | Bileşik dönem sayısı (yılda) | – |
| h | Hedef kâr oranı (ondalık; girdi yüzde) | – |
| q | Satış miktarı | adet |

## 2. İskonto faktörü DF(t)

t gün sonraki 1 TL'nin bugünkü değeri.

| Yöntem | Formül | Tersi: DF(t) = k ise t = |
|---|---|---|
| Basit | 1 / (1 + r·t/B) | (1/k − 1) · B / r |
| Bileşik | (1 + r/m)^(−m·t/B) | −B · ln k / (m · ln(1 + r/m)) |
| Efektif | (1 + r)^(−t/B) | −B · ln k / ln(1 + r) |

- BD(X, t) = X · DF(t), GD(X, t) = X / DF(t)
- Efektif yıllık oran = (1 + r/m)^m − 1
- Ticari (dış) iskonto: Ödenen = X · (1 − d·t/B). **Faiz hesabı değildir**, ürün analizinde kullanılmaz.
- Tahsilat gecikmesi maliyeti = BD(X, t) − BD(X, t + gecikme)

Tersin sınır durumları: k > 1 → çözüm yok; r = 0 ve k ≤ 1 → sınırsız; k = 1 → 0 gün.

## 3. Modül 1 – Ürün analizi

**Muhasebe bakışı**
- Brüt kâr = P − C₀
- Kâr oranı (maliyet üzerinden) = (P − C₀) / C₀
- Brüt kâr marjı (satış üzerinden) = (P − C₀) / P

**Yerine koyma bakışı (zaman değeri yok)**
- Yerine koyma kârı = P − R

**Ekonomik bakış (t = 0'da, tarihli nakit akışları)**
- BD_satış = P · DF(t_tah)
- BD_yk = R · DF(t_ted)
- Maliyetin BD'si: M = BD_yk + G
- **Ekonomik sonuç E = BD_satış − M**
- Ekonomik kâr oranı = E / M

**Köprü** (her kalem tam bir kez):

| Adım | Tutar |
|---|---|
| Muhasebe brüt kârı | P − C₀ |
| Yerine koyma farkı | −(R − C₀) |
| Ek giderler | −G |
| Vade maliyeti | −(P − BD_satış) |
| Tedarikçi vadesi kazancı | +(R − BD_yk) |
| **Toplam** | **= E** |

Toplam E'ye eşit değilse motor `TutarsizHesapHatasi` fırlatır.

**Karar destek**
- Başabaş fiyatı = M / DF(t_tah)
- Hedef fiyat = M · (1 + h) / DF(t_tah)
- En uzun vade: DF(t) = M / P eşitliğinin çözümü (bkz. §2 tersi)
  - `sinirli`: gün değeri döner
  - `sinirsiz`: r = 0 ve P ≥ M
  - `pesin_bile_zarar`: P < M

**Toplamlar:** Brüt kâr × q, E × q.

## 4. Neden geçmiş stok bekleme maliyeti düşülmez?

Malı 3 ay önce 100 TL'ye aldık. Bugün satarken karar şudur: "Bu malı 130 TL'ye 90 gün vadeyle satıp yerine 120 TL'lik yenisini almalı mıyım?" 3 ay önce harcanan para geri gelmez (batık maliyet). Bu sürede fiyatın 100'den 120'ye çıkması, yerine koyma farkında zaten görünür. Aynı dönem için ayrıca bir de "stok finansman maliyeti" düşmek aynı etkiyi iki kez saymak olur.

Stok finansmanı (Modül 4) yalnızca **yeni alınacak** malın gelecekte stokta bekleyeceği süre için hesaplanır.

## 5. Ek faiz fonksiyonları
- Yıllık eşdeğer oran = 1 / DF(B) − 1 (basit: r · bileşik: (1 + r/m)^m − 1 · efektif: r)
- Örtük yıllık oran (DF(t) = f eşitliğinden oranı bulur):
  basit (1/f − 1)·B/t · bileşik m·(f^(−B/(m·t)) − 1) · efektif f^(−B/t) − 1

## 6. Modül 3 – Parti maliyeti
- FIFO: satılan miktar en eski partiden başlayarak tüketilir.
- Ağırlıklı ortalama: Σ(miktar × maliyet) ÷ Σ miktar.
- Stok değer değişimi = toplam miktar × yerine koyma maliyeti − toplam kayıtlı maliyet.
- Fiyat artışı = yerine koyma maliyeti ÷ ağırlıklı ortalama maliyet − 1.
- Bulunan birim maliyet Modül 1'e "ilk alış maliyeti" olarak girer. **Ekonomik sonucu değiştirmez**, yalnızca muhasebe kârını değiştirir.

## 7. Modül 4 – Stok finansmanı (işletme düzeyi)
- Devir hızı = yıllık SMM ÷ ortalama stok · Bekleme günü = ortalama stok ÷ yıllık SMM × B
- Yıllık maliyet = ortalama stok × (yıllık eşdeğer oran + taşıma oranı)
- Senaryo stoğu (g gün) = yıllık SMM × g ÷ B
- Bu sonuç Modül 1'in ekonomik sonucuna **eklenmez** (bkz. §4).

## 8. Modül 5 – Finansman
- Erken ödeme: peşin = F·(1 − d); vadeli BD = F·DF(n); kazanç = vadeli BD − peşin. Örtük oran §5'teki fonksiyonla bulunur.
- Eşit taksit: i = yıllık nominal ÷ 12; taksit = L·i / (1 − (1 + i)^−n); ödeme günleri 30·k.
- Tek ödemeli: L·(1 + i·n), 30·n. günde.
- Efektif yıllık maliyet (iç verim oranı): net kullanılan = Σ ödeme·(1 + r)^(−t/B), ikiye bölme yöntemiyle çözülür.
- BD maliyeti = Σ ödeme·DF(t) − net kullanılan (işletmenin paranın maliyetiyle). Negatifse kredi bu maliyetten ucuzdur.

## 9. Modül 6–7 – Fiyat senaryoları ve tahsilat riski
- Her senaryo Modül 1 ile hesaplanır.
- Peşine eşdeğer vadeli fiyat(g) = peşin fiyat ÷ DF(g).
- Beklenen tahsilat BD = p · P · DF(t + gecikme); riskli sonuç = beklenen BD − maliyetin BD'si.
- Riskli başabaş = maliyetin BD'si ÷ (p · DF(t + gecikme)).
- p = %100 ve gecikme = 0 iken Modül 1 ile aynı sonucu verir.

## 10. Hesaba katılmayanlar
- Ödenmeyen alacaktan kısmi tahsilat ve hukuki takip masrafı
- KDV'nin tahsilat ve beyan zamanlaması
- Gelir ve kurumlar vergisi
- Enflasyon muhasebesi düzeltmeleri

Bunlar her sonuç ekranında varsayım olarak yazılır.
