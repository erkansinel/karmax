# Mimari

```
Tarayıcı (arayuz/)                      Python
┌────────────────────────┐   JSON    ┌───────────────────────────┐
│ index.html · 5 sekme   │ ────────▶ │ karmax/api/main.py        │  doğrula → hesapla → kaydet
│ uygulama.js (hesap YOK)│ ◀──────── │   (hesap YOK)             │
│ plotly.js (yalnız çizer)│  Excel   └──────┬──────────┬─────────┘
└────────────────────────┘                  │          │
                                            ▼          ▼
                    ┌───────────────────────────┐  ┌─────────────────────┐
                    │ karmax/motor/ (saf Python)│  │ karmax/grafikler.py │ Plotly figürleri
                    │  faiz.py          M2      │  │ karmax/excel.py     │ şablon, okuma, yazma
                    │  urun_analizi.py  M1      │  │ karmax/hatalar.py   │ Türkçe hata mesajları
                    │  yerine_koyma.py  M3      │  └─────────────────────┘
                    │  stok.py          M4      │
                    │  finansman.py     M5      │  ┌─────────────────────┐
                    │  fiyatlama.py     M6–M7   │  │ karmax/kayit.py     │ SQLite: girdi, sonuç,
                    │  toplu.py, egriler.py     │  │  → veri/            │ motor sürümü
                    └───────────────────────────┘  └─────────────────────┘
```

## Klasör yapısı

```
karmax/
├── Karmax.bat                 Windows'ta tek tıkla başlatma
├── baslat.py                  Port bulur, sunucuyu başlatır, tarayıcıyı açar
├── PROJE_TALIMATI.md          Revize proje talimatı
├── README.md
├── requirements.txt           Sabitlenmiş bağımlılıklar
├── karmax/
│   ├── motor/                 Hesaplama motoru (arayüzden bağımsız)
│   ├── api/main.py            REST API
│   ├── grafikler.py           Plotly grafik tanımları
│   ├── excel.py               Excel şablonu / içe aktarma / dışa aktarma
│   ├── hatalar.py             Türkçe doğrulama mesajları
│   └── kayit.py               SQLite analiz kaydı
├── arayuz/                    Tarayıcı arayüzü (Decisora markalı)
├── tests/                     190 otomatik test
├── docs/                      Sözleşme, mimari, kılavuz, raporlar
└── veri/                      SQLite dosyası (ilk çalıştırmada oluşur)
```

## Teknoloji gerekçeleri

| Seçim | Neden |
|---|---|
| Saf Python motor | Test etmesi kolay; API, Excel ve grafik katmanı aynı motoru kullanır |
| FastAPI + Pydantic | Girdi doğrulama ve otomatik API belgesi (`/docs`) |
| Plotly (Python + plotly.js) | Grafik verisi Python'da hazırlanır; plotly.js Python paketinden sunulur, internet gerekmez |
| OpenPyXL | Excel okuma/yazma; formülleri çalıştırmadan yalnızca değerleri okur |
| SQLite (yerleşik) | Kurulum gerektirmez; her analiz tekrar üretilebilir |
| Pandas / NumPy kullanılmadı | Hesapların hiçbiri gerektirmedi; Windows kurulumunu hafif tutar |

## API uç noktaları

| Yöntem | Yol | Modül |
|---|---|---|
| GET | `/api/saglik` | – |
| POST | `/api/urun-analizi` | M1–M2 (kaydeder) |
| POST | `/api/onizleme` | M1–M2 (kaydetmez, kaydırma çubukları için) |
| POST | `/api/maliyet-yontemi` | M3 |
| POST | `/api/stok-analizi` | M4 |
| POST | `/api/finansman/erken-odeme` | M5 |
| POST | `/api/finansman/karsilastir` | M5 |
| POST | `/api/fiyat-senaryolari` | M6–M7 |
| GET | `/api/excel/sablon` | Excel şablonu |
| POST | `/api/toplu-analiz` | Excel yükleme + toplu hesap |
| GET | `/api/toplu-analiz/{id}/excel` | Sonuç Excel'i |
| GET | `/api/analizler/{id}` | Kayıtlı analiz |
| GET | `/docs` | Otomatik API belgesi |
