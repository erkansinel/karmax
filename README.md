# Karmax

**Decisora Danışmanlık A.Ş.** için KOBİ finansal karar motoru.

Karmax, bir satışın muhasebe kârını yerine koyma maliyeti ve müşteri/tedarikçi vadeleriyle birlikte **ekonomik sonuca** çevirir. Ayrıca stok, finansman ve fiyat kararlarını aynı yöntemle analiz eder.

## Çalıştırma (Windows, tek tık)

1. Bilgisayarda **Python 3.11 veya üstü** kurulu olmalı. Yoksa [python.org](https://www.python.org/downloads/) adresinden kur ve kurulumun ilk ekranında **"Add python.exe to PATH"** kutusunu işaretle.
2. Proje klasöründeki **`Karmax.bat`** dosyasına çift tıkla.

İlk açılışta gerekli paketler kurulur (1–3 dakika, internet gerekir). Sonraki açılışlar birkaç saniye sürer. Tarayıcı kendiliğinden **http://127.0.0.1:8737/** adresinde açılır. Bu port doluysa bir sonraki boş port kullanılır ve siyah pencerede yazar.

Kapatmak için siyah pencereyi kapat. Karmax yalnızca bu bilgisayardan erişilebilir; ağa açılmaz.

> Masaüstüne kısayol: `Karmax.bat` dosyasına sağ tıkla → **Gönder** → **Masaüstü (kısayol oluştur)**.

## Elle çalıştırma (macOS / Linux veya geliştirici)

```bash
python3 -m venv .venv
```

```bash
.venv/bin/python -m pip install -r requirements.txt
```

```bash
.venv/bin/python baslat.py
```

## Modüller

| Sekme | Ne yapar |
|---|---|
| Ürün analizi | Muhasebe kârı → ekonomik sonuç köprüsü, başabaş fiyatı, hedef fiyat, en uzun vade, canlı senaryo ve grafikler |
| Toplu analiz (Excel) | Şablonu indir, doldur, yükle; bütün ürünlerin karşılaştırması, hatalı satır listesi, sonuç Excel'i |
| Fiyat ve tahsilat riski | Peşin/vadeli senaryolar, peşine eşdeğer vadeli fiyat, ödeme olasılığı ve gecikme etkisi |
| Stok ve maliyet | Stok devir hızı, stokta bekleme maliyeti, stok günü senaryoları; FIFO / ağırlıklı ortalama parti maliyeti |
| Finansman | Erken ödeme iskontosunun örtük faizi; kredi alternatiflerinin efektif maliyeti ve faiz duyarlılığı |

## Testler

Windows: `.venv\Scripts\python -m pytest` · macOS/Linux: `.venv/bin/python -m pytest`

Beklenen çıktı: `190 passed`.

## Belgeler

- [docs/KULLANIM_KILAVUZU.md](docs/KULLANIM_KILAVUZU.md): Adım adım kullanım
- [docs/HESAPLAMA_SOZLESMESI.md](docs/HESAPLAMA_SOZLESMESI.md): Bütün formüller
- [docs/MIMARI.md](docs/MIMARI.md): Mimari, klasörler, API
- [PROJE_TALIMATI.md](PROJE_TALIMATI.md): Revize proje talimatı
- [docs/raporlar/](docs/raporlar/): Faz raporları
