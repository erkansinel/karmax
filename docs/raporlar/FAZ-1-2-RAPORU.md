# Faz 1–2 Raporu: Altyapı, Hesaplama Motoru ve Doğrulama

**Proje:** Karmax · Decisora Danışmanlık A.Ş.
**Motor sürümü:** 0.1.0

## 1. Tamamlanan işler
- İlk talimattaki 16 sorun düzeltildi, revize talimat yazıldı (`PROJE_TALIMATI.md`, Ek A).
- Hesaplama sözleşmesi yazıldı: semboller, formüller, köprü kuralı, sınır durumları.
- Python ortamı, klasör yapısı ve FastAPI sunucusu kuruldu.
- **Modül 2 temeli:** basit, bileşik ve efektif faiz; 360/365 gün esası; bugünkü/gelecekteki değer; nominal → efektif dönüşüm; ticari iskonto; tahsilat gecikmesi maliyeti; iskonto faktörünün tersi.
- **Modül 1:** ürün bazlı gerçek kârlılık; köprü kuralıyla çift sayım koruması; başabaş fiyatı, hedef fiyat, en uzun vade.
- Tedarikçi vadesi nakit akışı modeline eklendi (simetrik iskonto).
- Her analiz girdi, sonuç ve motor sürümüyle SQLite'a kaydediliyor.
- Decisora markalı tarayıcı arayüzü: form, sonuç özeti, köprü tablosu, karar destek ve varsayımlar. JavaScript hesap yapmıyor.

## 2. Oluşturulan dosyalar
`karmax/motor/faiz.py`, `karmax/motor/modeller.py`, `karmax/motor/urun_analizi.py`, `karmax/kayit.py`, `karmax/api/main.py`, `arayuz/index.html`, `arayuz/stil.css`, `arayuz/uygulama.js`, `tests/referans_degerler.py`, `tests/test_faiz.py`, `tests/test_urun_analizi.py`, `tests/test_api.py`, `PROJE_TALIMATI.md`, `docs/HESAPLAMA_SOZLESMESI.md`, `docs/MIMARI.md`, `README.md`, `requirements.txt`.

## 3. Çalıştırma talimatları
README'deki "Kurulum" ve "Çalıştırma" adımları.

## 4. Yapılan testler

| Grup | Ne doğrulanıyor |
|---|---|
| Faiz (`test_faiz.py`) | Peşin/30/60/90 gün BD tablosu, 360↔365, basit/bileşik/efektif ayrımı, nominal↔efektif eşdeğerliği, BD↔GD tersliği, ticari iskonto ayrımı, gecikme maliyeti, ters fonksiyon ve geri sağlaması, geçersiz girdi |
| Ürün analizi (`test_urun_analizi.py`) | Referans senaryo, vade tablosu, kâr oranı ↔ marj, brüt ↔ ekonomik, köprü toplamı ve tekrarsızlığı, vadenin bir kez düşülmesi, tedarikçi vadesi, başabaş/hedef/en uzun vade geri sağlaması (3 faiz yöntemi), sıfır faiz, maliyet altı fiyat, oran duyarlılığı, miktar, geçersiz girdi, koddan bağımsız kesirli hesapla karşılaştırma |
| API (`test_api.py`) | Sağlık, referans sonucu, kayıt ve aynı girdiyle tekrar üretim, sınırsız vadenin JSON uyumu, 422 doğrulama hataları, 404 |
| Tarayıcı (Playwright, elle) | Sayfa açılışı, referans sonucu, hatalı fiyatta Türkçe hata mesajı, tedarikçi vadesi senaryosu, 390 px genişlikte yatay kaydırma olmaması |
| Test kalitesi | Motora bilerek "vade maliyetini iki kez düşme" hatası eklendi |

## 5. Test sonuçları
- `pytest`: **81 geçti, 0 başarısız.**
- Bilerek eklenen çift sayım hatasında **36 test kırıldı**, hata geri alınınca 81/81 geçti.
- Arayüz: ekonomik sonuç −1,67 TL, başabaş 131,84 TL, hedef 171,39 TL, en uzun vade 76 gün; tedarikçi 60 gün senaryosunda +5,73 TL. Hepsi referansla aynı.

## 6. Tespit edilen sorunlar
- İlk talimattaki referans değer (118,30 / −1,70) yanlış yuvarlanmıştı. Doğrusu 118,33 / −1,67. Düzeltildi.
- Pydantic doğrulama mesajları İngilizce geliyordu; arayüzde Türkçeleştirildi. API yanıtı hâlâ İngilizce mesaj içeriyor (Faz 3'te ele alınabilir).
- Arayüzde ondalık virgül yalnızca ilk virgülü noktaya çeviriyor. Binlik ayırıcılı girişler ("1.250,50") Faz 4'teki Excel ayrıştırıcısıyla birlikte ele alınacak.
- "Bağımsız" beklenen değerler kesirli aritmetikle üretildi ama aynı geliştirici tarafından. Kullanıcının referans tabloyu bir kez Excel'de elle kontrol etmesi önerilir.

## 7. Bir sonraki aşama: Faz 3 – Arayüz ve grafikler
- Plotly ile şelale grafiği ve vade eğrisi (veri Python'dan, çizim plotly.js ile)
- Fiyat ve başabaş grafiği
- Kaydırma çubuklarıyla canlı senaryo (debounce ile)
- API hata mesajlarının Türkçeleştirilmesi

## 8. Kabul kriterleri (Faz 1–2)
- [x] `pytest` komutu 81/81 geçiyor
- [x] Referans senaryo −1,6708 TL (±0,005)
- [x] Köprü toplamı her senaryoda ekonomik sonuca eşit
- [x] Başabaş, hedef ve en uzun vade geri sağlamaları üç faiz yönteminde geçiyor
- [x] Tarayıcı açılınca sunucuya bağlanıyor ve referans sonucu gösteriyor
- [x] Her analiz kaydediliyor ve aynı girdiyle aynı sonuç yeniden üretilebiliyor
- [ ] **Kullanıcı onayı:** Faz 3'e geçmeden önce
