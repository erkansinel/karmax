"""Excel şablonu, içe aktarma doğrulaması ve sonuç dosyası testleri."""

import io

import pytest
from openpyxl import Workbook, load_workbook

from karmax.excel import (
    MAKS_DOSYA_BAYT,
    SUTUNLAR,
    ExcelYapiHatasi,
    excel_oku,
    sablon_olustur,
    sayi_coz,
    sonuc_excel_olustur,
    toplu_kayit_verisi,
)
from karmax.motor.toplu import toplu_analiz


def doldur(satirlar, parametreler=None, basliklar=None) -> bytes:
    wb = load_workbook(io.BytesIO(sablon_olustur()))
    ws = wb["Ürünler"]
    # Not: ws.cell(value=None) hücreyi BOŞALTMAZ; bu yüzden .value doğrudan atanır.
    if basliklar is not None:
        for c in range(1, 30):
            ws.cell(row=1, column=c).value = basliklar[c - 1] if c <= len(basliklar) else None
    for r, satir in enumerate(satirlar, start=2):
        for c, v in enumerate(satir, start=1):
            ws.cell(row=r, column=c).value = v
    if parametreler:
        pw = wb["Parametreler"]
        for r in range(2, 6):
            etiket = pw.cell(row=r, column=1).value
            if etiket in parametreler:
                pw.cell(row=r, column=2).value = parametreler[etiket]
    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


IYI = ["A1", "Ürün A", 100, 120, 130, 500, 90, 0, 0, 30]


# ------------------------------------------------------------ sayı çözümleme

@pytest.mark.parametrize("girdi, beklenen", [
    (12, 12.0), (12.5, 12.5), ("12,5", 12.5), ("12.5", 12.5), ("1.250,50", 1250.5), ("1,250.50", 1250.5),
    ("1.250.000", 1250000.0), ("%40", 40.0), ("40%", 40.0), (" 130 TL ", 130.0), ("1250", 1250.0),
])
def test_sayi_coz(girdi, beklenen):
    assert sayi_coz(girdi) == pytest.approx(beklenen)


@pytest.mark.parametrize("girdi", ["doksan", "1.250", "12,5,3", "", True])
def test_sayi_coz_hatali_veya_belirsiz(girdi):
    with pytest.raises(ValueError):
        sayi_coz(girdi)


def test_yuzde_bicimli_hucre():
    assert sayi_coz(0.3, yuzde_bicimli=True) == pytest.approx(30)


# ---------------------------------------------------------------------- şablon

def test_sablon_yapisi():
    wb = load_workbook(io.BytesIO(sablon_olustur()))
    assert wb.sheetnames == ["Ürünler", "Parametreler", "Açıklamalar"]
    ws = wb["Ürünler"]
    assert [c.value for c in ws[1]][: len(SUTUNLAR)] == [s.baslik for s in SUTUNLAR]
    assert ws.max_row == 1  # veri satırı yok: örnek satır yanlışlıkla hesaplanmaz
    assert ws["A1"].comment is not None
    assert len(ws.data_validations.dataValidation) >= 5
    aciklama = [c.value for r in wb["Açıklamalar"].iter_rows() for c in r if c.value]
    assert "TSH-001" in aciklama  # örnek satır açıklama sayfasında


def test_bos_sablon_reddedilir():
    with pytest.raises(ExcelYapiHatasi, match="hiç ürün"):
        excel_oku(sablon_olustur())


# ---------------------------------------------------------------- içe aktarma

def test_gecerli_dosya():
    y = excel_oku(doldur([IYI, ["B2", "Ürün B", "1.250,50", 1300, 1500, 10, 30, 30, "2,5", 25]]))
    assert [u.urun_kodu for _, u in y.urunler] == ["A1", "B2"]
    assert y.urunler[1][1].ilk_alis_maliyeti == 1250.5 and y.urunler[1][1].ek_gider_birim == 2.5
    assert y.hatalar == [] and y.parametreler.yillik_oran_yuzde == 40


def test_bos_opsiyonel_alanlar_varsayilan_alir():
    y = excel_oku(doldur([["A1", None, 100, 120, 130, None, None, None, None, None]]))
    u = y.urunler[0][1]
    assert (u.satis_miktari, u.tahsilat_vadesi_gun, u.ek_gider_birim, u.hedef_kar_orani_yuzde) == (1, 0, 0, 30)


def test_hatali_satirlar_tek_tek_raporlanir():
    y = excel_oku(doldur([
        IYI,
        ["C3", "Hatalı", -5, 120, 130, 1, "doksan", 0, 0, 30],   # iki hata
        ["D4", "Eksik", None, 120, 130, 1, 0, 0, 0, 30],          # zorunlu boş
        ["E5", "Ondalık gün", 100, 120, 130, 1, 30.5, 0, 0, 30],  # tam sayı değil
    ]))
    assert [u.urun_kodu for _, u in y.urunler] == ["A1"]
    hatalar = {(h.satir, h.alan) for h in y.hatalar}
    assert hatalar == {(3, "ilk_alis_maliyeti"), (3, "tahsilat_vadesi_gun"), (4, "ilk_alis_maliyeti"),
                       (5, "tahsilat_vadesi_gun")}
    mesajlar = {h.alan: h.mesaj for h in y.hatalar if h.satir == 3}
    assert mesajlar["ilk_alis_maliyeti"] == "İlk alış maliyeti: 0 değerinden büyük olmalı"
    assert mesajlar["tahsilat_vadesi_gun"] == "Müşteri tahsilat vadesi: sayı girilmeli"
    degerler = {h.alan: h.deger for h in y.hatalar if h.satir == 3}
    assert degerler == {"ilk_alis_maliyeti": "-5", "tahsilat_vadesi_gun": "doksan"}  # kullanıcının yazdığı gibi


def test_mukerrer_kodlarin_hepsi_reddedilir():
    y = excel_oku(doldur([IYI, ["B2"] + IYI[1:], ["a1"] + IYI[1:]]))
    assert [u.urun_kodu for _, u in y.urunler] == ["B2"]
    assert {h.satir for h in y.hatalar} == {2, 4}
    assert all("Mükerrer" in h.mesaj for h in y.hatalar)


def test_bos_satirlar_atlanir_ve_sayilir():
    y = excel_oku(doldur([IYI, [None] * 10, ["B2"] + IYI[1:]]))
    assert len(y.urunler) == 2 and y.bos_satir_sayisi >= 1 and y.okunan_satir_sayisi == 2


def test_formul_calistirilmaz():
    y = excel_oku(doldur([["A1", "=1+1", 100, 120, "=100+30", 1, 0, 0, 0, 30]]))
    # Kayıtlı değeri olmayan formül boş sayılır; zorunlu alansa hata verir
    assert y.urunler == [] and y.hatalar[0].alan == "satis_fiyati"


def test_parametre_hatalari():
    with pytest.raises(ExcelYapiHatasi, match="Gün esası"):
        excel_oku(doldur([IYI], {"Gün esası": 300}))
    with pytest.raises(ExcelYapiHatasi, match="eksik"):
        excel_oku(doldur([IYI], {"Yıllık oran (%)": None}))
    y = excel_oku(doldur([IYI], {"Faiz yöntemi": "Bileşik", "Yıllık oran (%)": "%45"}))
    assert y.parametreler.faiz_yontemi.value == "bilesik" and y.parametreler.yillik_oran_yuzde == 45


def test_eksik_zorunlu_sutun():
    with pytest.raises(ExcelYapiHatasi, match="Satış fiyatı"):
        excel_oku(doldur([["A1", 100, 120]], basliklar=["Ürün kodu", "İlk alış maliyeti", "Bugünkü yeniden alış maliyeti"]))


def test_basliklar_esnek_eslesir_ve_eksik_opsiyonel_uyari_verir():
    y = excel_oku(doldur([["A1", 100, 120, 130, 45]],
                         basliklar=["urun kodu", "ILK ALIŞ MALİYETİ", "Bugünkü yeniden alış maliyeti",
                                    "Satış fiyatı (TL)", "Müşteri tahsilat vadesi"]))
    assert y.urunler[0][1].tahsilat_vadesi_gun == 45
    assert any("Satış miktarı" in u for u in y.uyarilar)


@pytest.mark.parametrize("icerik, mesaj", [
    (b"merhaba", ".xlsx"),
    (b"PK" + b"0" * 100, "açılamadı"),
    (b"PK" + b"0" * (MAKS_DOSYA_BAYT + 1), "büyük"),
])
def test_gecersiz_dosyalar(icerik, mesaj):
    with pytest.raises(ExcelYapiHatasi, match=mesaj):
        excel_oku(icerik)


def test_yanlis_sayfa():
    wb = Workbook()
    tampon = io.BytesIO()
    wb.save(tampon)
    with pytest.raises(ExcelYapiHatasi, match="Ürünler"):
        excel_oku(tampon.getvalue())


# ------------------------------------------------------------- sonuç dosyası

def _kayit(satirlar):
    y = excel_oku(doldur(satirlar))
    t = toplu_analiz([u for _, u in y.urunler], y.parametreler)
    girdi, sonuc = toplu_kayit_verisi(y, t)
    return {"id": 7, "olusturma": "2026-11-24T10:00:00+00:00", "motor_surumu": "test", "girdi": girdi, "sonuc": sonuc}


def test_sonuc_dosyasi():
    kayit = _kayit([IYI, ["C3", "Hatalı", -5, 120, 130, 1, 0, 0, 0, 30]])
    wb = load_workbook(io.BytesIO(sonuc_excel_olustur(kayit)))
    assert wb.sheetnames[:3] == ["Özet", "Sonuçlar", "Hatalar"]
    rs = wb["Sonuçlar"]
    basliklar = [c.value for c in rs[1]]
    eko = rs.cell(row=2, column=basliklar.index("Ekonomik sonuç (birim)") + 1).value
    assert eko == pytest.approx(-1.670823, abs=0.005)
    assert wb["Hatalar"].cell(row=2, column=1).value == 3


def test_sonuc_dosyasinda_formul_enjeksiyonu_yok():
    kayit = _kayit([["=HYPERLINK(\"http://x\")", "=1+1", 100, 120, 130, 1, 0, 0, 0, 30]])
    # Formülün kayıtlı değeri yok → ürün kodu boş hatası; adı da metin olarak kalmalı.
    kayit["sonuc"]["hatalar"].append({"satir": 99, "urun_kodu": "=cmd|' /C calc'!A0", "alan": None,
                                      "mesaj": "+deneme", "deger": "@SUM(1)"})
    wb = load_workbook(io.BytesIO(sonuc_excel_olustur(kayit)))
    for ws in wb.worksheets:
        for satir in ws.iter_rows():
            for c in satir:
                assert c.data_type != "f", f"{ws.title}!{c.coordinate} formül içeriyor"
    hs = wb["Hatalar"]
    degerler = [c.value for r in hs.iter_rows(min_row=2) for c in r]
    assert "=cmd|' /C calc'!A0" in degerler  # metin olarak, aynen
