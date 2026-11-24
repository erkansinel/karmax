"""API testleri: doğrulama, hesaplama, kayıt ve tekrar üretilebilirlik."""

import pytest
from fastapi.testclient import TestClient

from karmax.api.main import uygulama_olustur
from karmax.motor import MOTOR_SURUMU
from tests import referans_degerler as ref

ORNEK = {
    "parametreler": {"yillik_oran_yuzde": 40, "faiz_yontemi": "basit", "gun_esasi": 365},
    "urun": {
        "urun_kodu": "REF-001",
        "urun_adi": "Referans ürün",
        "ilk_alis_maliyeti": 100,
        "yerine_koyma_maliyeti": 120,
        "satis_fiyati": 130,
        "tahsilat_vadesi_gun": 90,
    },
}


@pytest.fixture()
def istemci(tmp_path):
    return TestClient(uygulama_olustur(tmp_path / "test.sqlite3"))


def test_saglik(istemci):
    yanit = istemci.get("/api/saglik")
    assert yanit.status_code == 200
    assert yanit.json() == {"durum": "ok", "motor_surumu": MOTOR_SURUMU}


def test_urun_analizi_referans(istemci):
    yanit = istemci.post("/api/urun-analizi", json=ORNEK)
    assert yanit.status_code == 200
    sonuc = yanit.json()["sonuc"]
    assert sonuc["ekonomik_sonuc"] == pytest.approx(-1.670823, abs=ref.TOLERANS)
    assert sonuc["maksimum_vade_durumu"] == "sinirli"
    assert len(sonuc["varsayimlar"]) >= 5


def test_kayit_saklanir_ve_tekrar_uretilir(istemci):
    ilk = istemci.post("/api/urun-analizi", json=ORNEK).json()
    kayit = istemci.get(f"/api/analizler/{ilk['kayit_id']}").json()
    assert kayit["motor_surumu"] == MOTOR_SURUMU
    assert kayit["girdi"]["urun"]["satis_fiyati"] == 130
    # Saklanan girdiyle yeniden hesapla, aynı sonuç çıkmalı
    tekrar = istemci.post("/api/urun-analizi", json=kayit["girdi"]).json()
    assert tekrar["sonuc"] == kayit["sonuc"]


def test_sinirsiz_vade_json_ile_uyumlu(istemci):
    govde = {**ORNEK, "parametreler": {**ORNEK["parametreler"], "yillik_oran_yuzde": 0}}
    sonuc = istemci.post("/api/urun-analizi", json=govde).json()["sonuc"]
    assert sonuc["maksimum_vade_gun"] is None
    assert sonuc["maksimum_vade_durumu"] == "sinirsiz"


@pytest.mark.parametrize(
    "bozuk",
    [
        {"urun": {**ORNEK["urun"], "satis_fiyati": -10}},
        {"urun": {**ORNEK["urun"], "satis_fiyati": "yüz otuz"}},
        {"parametreler": {**ORNEK["parametreler"], "gun_esasi": 300}},
        {"parametreler": {**ORNEK["parametreler"], "faiz_yontemi": "sihirli"}},
    ],
)
def test_gecersiz_istek_422(istemci, bozuk):
    yanit = istemci.post("/api/urun-analizi", json={**ORNEK, **bozuk})
    assert yanit.status_code == 422


def test_hata_mesajlari_turkce(istemci):
    govde = {**ORNEK, "urun": {**ORNEK["urun"], "satis_fiyati": -10, "tahsilat_vadesi_gun": "doksan"}}
    detay = istemci.post("/api/urun-analizi", json=govde).json()["detail"]
    mesajlar = {d["alan"]: d["mesaj"] for d in detay}
    assert mesajlar["satis_fiyati"] == "Satış fiyatı: 0 değerinden büyük olmalı"
    assert mesajlar["tahsilat_vadesi_gun"] == "Müşteri tahsilat vadesi: sayı girilmeli"


def test_analiz_grafikleri_doner(istemci):
    veri = istemci.post("/api/urun-analizi", json=ORNEK).json()
    assert set(veri["grafikler"]) == {"selale", "vade", "fiyat"}


def test_onizleme_kaydetmez(istemci):
    kayit = istemci.app.state.kayit
    once = kayit.sayi()
    veri = istemci.post("/api/onizleme", json=ORNEK).json()
    assert veri["kayit_id"] is None
    assert veri["sonuc"]["ekonomik_sonuc"] == pytest.approx(-1.670823, abs=ref.TOLERANS)
    assert kayit.sayi() == once
    istemci.post("/api/urun-analizi", json=ORNEK)
    assert kayit.sayi() == once + 1


def test_onizleme_ve_analiz_ayni_sonucu_verir(istemci):
    a = istemci.post("/api/onizleme", json=ORNEK).json()
    b = istemci.post("/api/urun-analizi", json=ORNEK).json()
    assert a["sonuc"] == b["sonuc"] and a["grafikler"] == b["grafikler"]


def test_plotly_js_yerelden_sunulur(istemci):
    yanit = istemci.get("/kutuphane/plotly.min.js")
    assert yanit.status_code == 200 and len(yanit.content) > 1_000_000


def test_olmayan_kayit_404(istemci):
    assert istemci.get("/api/analizler/99999").status_code == 404


# ---------------------------------------------------------------- Faz 4–6

P = {"yillik_oran_yuzde": 40, "faiz_yontemi": "basit", "gun_esasi": 365}


def _excel_dosyasi(satirlar):
    from tests.test_excel import doldur
    return {"dosya": ("urunler.xlsx", doldur(satirlar),
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}


def test_sablon_indirme(istemci):
    yanit = istemci.get("/api/excel/sablon")
    assert yanit.status_code == 200 and yanit.content[:2] == b"PK"
    assert "karmax-sablon.xlsx" in yanit.headers["content-disposition"]


def test_toplu_analiz_ve_excel_indirme(istemci):
    satirlar = [
        ["A1", "Ürün A", 100, 120, 130, 500, 90, 0, 0, 30],
        ["B2", "Ürün B", 100, 120, 200, 10, 0, 0, 0, 30],
        ["C3", "Hatalı", -5, 120, 130, 1, 0, 0, 0, 30],
    ]
    veri = istemci.post("/api/toplu-analiz", files=_excel_dosyasi(satirlar)).json()
    assert veri["ozet"]["urun_sayisi"] == 2
    assert [s["urun_kodu"] for s in veri["sonuclar"]] == ["A1", "B2"]  # kötüden iyiye
    assert veri["sonuclar"][0]["toplam_ekonomik_sonuc"] == pytest.approx(-1.670823 * 500, abs=0.01)
    assert veri["hatalar"][0]["satir"] == 4
    assert veri["grafik"]["data"][0]["type"] == "bar"
    dosya = istemci.get(f"/api/toplu-analiz/{veri['kayit_id']}/excel")
    assert dosya.status_code == 200 and dosya.content[:2] == b"PK"


def test_toplu_analiz_yapi_hatasi_turkce(istemci):
    yanit = istemci.post("/api/toplu-analiz", files={"dosya": ("x.csv", b"a;b;c", "text/csv")})
    assert yanit.status_code == 422
    assert ".xlsx" in yanit.json()["detail"][0]["mesaj"]


def test_toplu_excel_yanlis_kayit_404(istemci):
    kayit_id = istemci.post("/api/urun-analizi", json=ORNEK).json()["kayit_id"]
    assert istemci.get(f"/api/toplu-analiz/{kayit_id}/excel").status_code == 404


def test_maliyet_yontemi_ve_is_kurali_hatasi(istemci):
    govde = {"partiler": [{"miktar": 100, "birim_maliyet": 80}, {"miktar": 200, "birim_maliyet": 100}],
             "satilan_miktar": 150, "yontem": "fifo", "yerine_koyma_maliyeti": 120}
    veri = istemci.post("/api/maliyet-yontemi", json=govde).json()
    assert veri["sonuc"]["birim_maliyet"] == pytest.approx(13000 / 150)
    yanit = istemci.post("/api/maliyet-yontemi", json={**govde, "satilan_miktar": 999})
    assert yanit.status_code == 422 and "fazla" in yanit.json()["detail"][0]["mesaj"]


def test_stok_analizi(istemci):
    veri = istemci.post("/api/stok-analizi", json={"parametreler": P, "stok": {
        "yillik_satilan_mal_maliyeti": 12_000_000, "ortalama_stok_tutari": 2_000_000,
        "tasima_maliyeti_orani_yuzde": 5}}).json()
    assert veri["sonuc"]["toplam_yillik_maliyet"] == pytest.approx(900_000)
    assert veri["kayit_id"] > 0 and veri["grafik"]["data"]


def test_finansman_uc_noktalari(istemci):
    e = istemci.post("/api/finansman/erken-odeme", json={"parametreler": P, "girdi": {
        "fatura_tutari": 100_000, "iskonto_yuzde": 2, "vade_gun": 60}}).json()
    assert e["sonuc"]["ortuk_yillik_oran"] == pytest.approx(0.124150, abs=1e-6)
    f = istemci.post("/api/finansman/karsilastir", json={"parametreler": P, "girdi": {"alternatifler": [
        {"ad": "Banka B", "tur": "tek_odemeli", "kullanilan_tutar": 1_000_000, "yillik_faiz_yuzde": 45, "vade_ay": 6},
    ]}}).json()
    assert f["sonuc"]["alternatifler"][0]["efektif_yillik_maliyet"] == pytest.approx(0.509108, abs=1e-6)
    hata = istemci.post("/api/finansman/karsilastir", json={"parametreler": P, "girdi": {"alternatifler": [
        {"ad": "X", "tur": "kira", "kullanilan_tutar": 1, "yillik_faiz_yuzde": 1, "vade_ay": 1}]}})
    assert hata.status_code == 422 and hata.json()["detail"][0]["mesaj"].startswith("Tür:")


def test_fiyat_senaryolari(istemci):
    veri = istemci.post("/api/fiyat-senaryolari", json={"parametreler": P, "girdi": {
        "urun": ORNEK["urun"], "risk": {"odeme_olasiligi_yuzde": 95, "beklenen_gecikme_gun": 15}}}).json()
    assert [s["ad"] for s in veri["sonuc"]["senaryolar"]] == ["Peşin", "30 gün", "60 gün", "90 gün"]
    assert len(veri["grafik"]["data"]) == 2  # risk varken iki seri
