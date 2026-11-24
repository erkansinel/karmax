# Faz 3–7 Raporu: Tamamlanan Platform

**Proje:** Karmax · Decisora Danışmanlık A.Ş.
**Motor sürümü:** 1.0.0

## 1. Tamamlanan işler

| Faz | İçerik | Durum |
|---|---|---|
| 3 – Arayüz ve grafikler | Şelale, vade eğrisi, fiyat/başabaş grafiği (Plotly, veri Python'da); kaydırma çubuklarıyla canlı senaryo; kaydetmeyen önizleme; Türkçe API hata mesajları | Tamam |
| 4 – Excel ve toplu hesap | Şablon (açıklamalar, örnek satır, veri doğrulama), güvenli yükleme, satır bazında hata raporu, mükerrer kod kontrolü, toplu hesap, sonuç Excel'i | Tamam |
| 5 – Çoklu ürün karşılaştırma | İşletme özeti (gizli fark, zarar eden ürünler), kötüden iyiye sıralama, karşılaştırma grafiği | Tamam |
| 6 – Diğer modüller | M3 parti maliyeti (FIFO/ortalama), M4 stok finansmanı, M5 erken ödeme ve kredi karşılaştırması, M6 fiyat senaryoları, M7 tahsilat riski | Tamam |
| 7 – Nihai test ve sürüm | Uçtan uca tarayıcı testi, hata ekleme testleri, kullanım kılavuzu, tek tıkla başlatma (`Karmax.bat`) | Tamam |

## 2. Oluşturulan / değişen dosyalar
Yeni: `Karmax.bat`, `baslat.py`, `karmax/motor/{egriler,yerine_koyma,stok,finansman,fiyatlama,toplu}.py`, `karmax/{grafikler,excel,hatalar}.py`, `tests/{test_egriler_grafikler,test_moduller,test_excel}.py`, `docs/KULLANIM_KILAVUZU.md`.
Güncellenen: `karmax/motor/faiz.py` (yıllık eşdeğer ve örtük oran), `karmax/api/main.py`, `arayuz/*`, `requirements.txt`, belgeler.

## 3. Çalıştırma
`Karmax.bat` dosyasına çift tıklamak yeterli (ayrıntı: README).

## 4. Yapılan testler
- **190 otomatik test**: faiz (23), ürün analizi (49), eğri ve grafikler (21), Modül 3–7 ve toplu (41), Excel (34), API (22).
- **Bağımsız beklenen değerler**: kesirli aritmetik, kapalı formüller (ör. masrafsız eşit taksitte efektif maliyet = (1 + aylık)^(365/30) − 1) ve geri sağlama (başabaş, hedef, iç verim oranı, eşdeğer fiyat, riskli başabaş).
- **Hata ekleme testi**: 6 farklı modüle bilerek hata eklendi; hepsi testler tarafından yakalandı.
- **Uçtan uca tarayıcı testi**: 5 sekmenin hepsi, Excel yükleme ve indirme, hatalı girdi, kaydırma çubukları, parti maliyetini ürüne aktarma, 390 px telefon genişliği.
- **Windows uyumluluğu**: Bütün paketlerin Windows için hazır kurulum dosyası Python 3.11, 3.12, 3.13 ve 3.14'te doğrulandı.

## 5. Test sonuçları
- `pytest`: **190 geçti, 0 başarısız.**
- Hata ekleme: vade çift sayımı 66, stok %1 sapma 2, taksit dönem hatası 2, gecikmeyi unutma 1, FIFO→LIFO 2, mükerrer kod kaçırma 1 testi kırdı.
- Tarayıcı: konsol hatası yok, telefonda yatay taşma yok.

## 6. Tespit edilen ve düzeltilen sorunlar
- Fiyat grafiğinde hedef noktasının yüksekliği grafik katmanında hesaplanıyordu (kural ihlali). Motorun eğri verisine taşındı.
- Excel'de bir satırdaki ikinci hata raporlanmıyordu; artık bir satırın bütün hataları listeleniyor.
- Metin olarak yazılmış "1.250" gibi belirsiz sayılar sessizce yorumlanabilirdi; artık açık bir hata mesajıyla reddediliyor.
- Hata mesajlarında sınır değerleri "0.0" yazıyordu; Türkçe biçime çevrildi.
- Plotly'nin varsayılan teması her grafiğe ~8 KB ekliyordu; kaldırıldı.
- Windows'ta `.venv/bin` yolu çalışmıyordu; başlatma `Karmax.bat` ile tek tıka indirildi.

## 7. Bilinen sınırlar
- `Karmax.bat` bu geliştirme ortamında Windows olmadığı için doğrudan çalıştırılamadı; içindeki adımlar (`baslat.py`, paket kurulumu) ayrı ayrı test edildi. İlk gerçek Windows çalıştırmasında çıkan mesajlar paylaşılmalı.
- Pandas ve NumPy, revize talimatın "ihtiyaç doğduğunda" kuralı gereği eklenmedi; hiçbir hesap gerektirmedi.
- Kapsam dışı (varsayım olarak gösteriliyor): KDV zamanlaması, gelir vergisi, enflasyon muhasebesi, kısmi tahsilat ve hukuki takip masrafı.
- Referans tablonun bir kez Excel'de elle kontrol edilmesi önerisi geçerliliğini koruyor.

## 8. Kabul kriterleri
- [x] 190/190 otomatik test geçiyor
- [x] Referans senaryo −1,6708 TL; bütün modüllerde geri sağlamalar geçiyor
- [x] Excel şablonu indiriliyor, dolu dosya yükleniyor, hatalı satırlar ayrı listeleniyor, sonuç Excel'i indiriliyor
- [x] Bütün sekmeler tarayıcıda çalışıyor, JavaScript hesap yapmıyor
- [x] Her analiz kayıt numarası ve motor sürümüyle saklanıyor
- [ ] **Kullanıcı:** `Karmax.bat` ile Windows'ta ilk çalıştırma
