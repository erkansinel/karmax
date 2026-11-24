"""Modül 3–7 ve toplu analiz testleri.

Beklenen değerler motor çalıştırılmadan, kesirli aritmetik veya kapalı
formüllerle ayrıca hesaplanmıştır (bkz. her testin açıklaması).
"""

import pytest
from pydantic import ValidationError

from karmax.motor import AnalizParametreleri, FaizYontemi, UrunGirdisi, urun_analiz_et
from karmax.motor.faiz import iskonto_faktoru, ortuk_yillik_oran, yillik_esdeger_oran
from karmax.motor.finansman import (
    ErkenOdemeGirdisi,
    FinansmanAlternatifi,
    FinansmanGirdisi,
    erken_odeme_analiz_et,
    finansman_karsilastir,
    odeme_plani,
)
from karmax.motor.fiyatlama import FiyatlamaGirdisi, FiyatSenaryosu, TahsilatRiski, fiyat_senaryolari, riskli_sonuc
from karmax.motor.stok import StokGirdisi, stok_analiz_et
from karmax.motor.toplu import toplu_analiz
from karmax.motor.yerine_koyma import MaliyetGirdisi, Parti, maliyet_hesapla

P40 = AnalizParametreleri(yillik_oran_yuzde=40)
TOL = 0.005


def urun(**kw):
    temel = dict(urun_kodu="REF-001", ilk_alis_maliyeti=100, yerine_koyma_maliyeti=120,
                 satis_fiyati=130, tahsilat_vadesi_gun=90)
    temel.update(kw)
    return UrunGirdisi(**temel)


# ------------------------------------------------------------ faiz yardımcıları

@pytest.mark.parametrize("yontem, beklenen", [
    (FaizYontemi.BASIT, 0.40), (FaizYontemi.BILESIK, 0.482126), (FaizYontemi.EFEKTIF, 0.40),
])
def test_yillik_esdeger_oran(yontem, beklenen):
    assert yillik_esdeger_oran(0.40, yontem=yontem) == pytest.approx(beklenen, abs=1e-6)


@pytest.mark.parametrize("yontem", list(FaizYontemi))
@pytest.mark.parametrize("oran, gun", [(0.40, 90), (0.12, 60), (0.75, 17)])
def test_ortuk_oran_faktorun_tersi(yontem, oran, gun):
    f = iskonto_faktoru(oran, gun, yontem=yontem)
    assert ortuk_yillik_oran(f, gun, yontem=yontem) == pytest.approx(oran, abs=1e-10)


def test_ortuk_oran_gecersiz():
    with pytest.raises(ValueError):
        ortuk_yillik_oran(1.2, 30)
    with pytest.raises(ValueError):
        ortuk_yillik_oran(0.9, 0)


# --------------------------------------------------------- Modül 3: maliyet

PARTILER = [Parti(miktar=100, birim_maliyet=80), Parti(miktar=200, birim_maliyet=100)]


def test_fifo_maliyeti():
    # 100 × 80 + 50 × 100 = 13.000 → 86,667 / birim
    s = maliyet_hesapla(MaliyetGirdisi(partiler=PARTILER, satilan_miktar=150, yontem="fifo", yerine_koyma_maliyeti=120))
    assert s.birim_maliyet == pytest.approx(13000 / 150)
    assert s.kalan_miktar == 150 and s.kalan_stok_degeri == pytest.approx(15000)


def test_agirlikli_ortalama_maliyeti():
    # (8.000 + 20.000) / 300 = 93,333
    s = maliyet_hesapla(MaliyetGirdisi(partiler=PARTILER, satilan_miktar=150, yontem="agirlikli_ortalama",
                                       yerine_koyma_maliyeti=120))
    assert s.birim_maliyet == pytest.approx(28000 / 300)
    assert s.satilan_malin_maliyeti + s.kalan_stok_degeri == pytest.approx(s.toplam_stok_maliyeti)


def test_stok_deger_degisimi():
    s = maliyet_hesapla(MaliyetGirdisi(partiler=PARTILER, satilan_miktar=1, yerine_koyma_maliyeti=120))
    assert s.stok_deger_degisimi == pytest.approx(300 * 120 - 28000)
    assert s.fiyat_artisi_orani == pytest.approx(120 / (28000 / 300) - 1)


def test_stoktan_fazla_satis_reddedilir():
    with pytest.raises(ValueError, match="fazla"):
        maliyet_hesapla(MaliyetGirdisi(partiler=PARTILER, satilan_miktar=301, yerine_koyma_maliyeti=120))


def test_tum_stok_satilinca_fifo_ve_ortalama_ayni():
    a = maliyet_hesapla(MaliyetGirdisi(partiler=PARTILER, satilan_miktar=300, yontem="fifo", yerine_koyma_maliyeti=120))
    b = maliyet_hesapla(MaliyetGirdisi(partiler=PARTILER, satilan_miktar=300, yontem="agirlikli_ortalama",
                                       yerine_koyma_maliyeti=120))
    assert a.birim_maliyet == pytest.approx(b.birim_maliyet)


# ------------------------------------------------------------ Modül 4: stok

STOK = StokGirdisi(yillik_satilan_mal_maliyeti=12_000_000, ortalama_stok_tutari=2_000_000,
                   tasima_maliyeti_orani_yuzde=5, alternatif_stok_gunleri=[30, 90])


def test_stok_temel_gostergeler():
    s = stok_analiz_et(STOK, P40)
    assert s.stok_devir_hizi == pytest.approx(6.0)
    assert s.stokta_bekleme_gunu == pytest.approx(60.833333, abs=1e-5)
    assert s.yillik_finansman_maliyeti == pytest.approx(800_000)
    assert s.yillik_tasima_maliyeti == pytest.approx(100_000)
    assert s.toplam_yillik_maliyet == pytest.approx(900_000)


def test_stok_senaryosu_30_gun():
    s = stok_analiz_et(STOK, P40)
    sen = next(x for x in s.senaryolar if x.stok_gunu == 30)
    assert sen.ortalama_stok == pytest.approx(986_301.369863, abs=1e-4)
    assert sen.toplam_yillik_maliyet == pytest.approx(443_835.616438, abs=1e-4)
    assert sen.mevcuda_gore_yillik_tasarruf == pytest.approx(456_164.383562, abs=1e-4)
    assert sen.serbest_kalan_nakit == pytest.approx(1_013_698.630137, abs=1e-4)


def test_stok_mevcut_senaryo_tutarli_ve_sirali():
    s = stok_analiz_et(STOK, P40)
    mevcut = [x for x in s.senaryolar if x.mevcut_durum]
    assert len(mevcut) == 1
    assert mevcut[0].mevcuda_gore_yillik_tasarruf == pytest.approx(0, abs=1e-6)
    assert mevcut[0].ortalama_stok == pytest.approx(2_000_000)
    gunler = [x.stok_gunu for x in s.senaryolar]
    assert gunler == sorted(gunler)


def test_stok_bilesik_yontemde_yillik_esdeger_oran():
    s = stok_analiz_et(STOK, AnalizParametreleri(yillik_oran_yuzde=40, faiz_yontemi="bilesik"))
    assert s.yillik_finansman_maliyeti == pytest.approx(964_252.979, abs=1e-2)


def test_stok_sifir_stok():
    s = stok_analiz_et(StokGirdisi(yillik_satilan_mal_maliyeti=1000, ortalama_stok_tutari=0), P40)
    assert s.stok_devir_hizi is None and s.stokta_bekleme_gunu == 0 and s.toplam_yillik_maliyet == 0


# ------------------------------------------------------- Modül 5: finansman

def test_erken_odeme():
    s = erken_odeme_analiz_et(ErkenOdemeGirdisi(fatura_tutari=100_000, iskonto_yuzde=2, vade_gun=60), P40)
    assert s.pesin_odeme == pytest.approx(98_000)
    assert s.vadeli_odemenin_bugunku_degeri == pytest.approx(93_830.334190, abs=1e-4)
    assert s.ortuk_yillik_oran == pytest.approx(0.124150, abs=1e-6)
    assert s.ortuk_efektif_yillik_oran == pytest.approx(0.130771, abs=1e-6)
    assert s.pesin_odemenin_kazanci < 0 and s.karar.startswith("Vadeyi kullan")


def test_erken_odeme_ortuk_oran_paranin_maliyetinden_yuksekse_pesin():
    # %5 indirim / 30 gün → örtük basit oran ≈ %64 > %40
    s = erken_odeme_analiz_et(ErkenOdemeGirdisi(fatura_tutari=100_000, iskonto_yuzde=5, vade_gun=30), P40)
    assert s.ortuk_yillik_oran > 0.40 and s.pesin_odemenin_kazanci > 0 and s.karar.startswith("Peşin öde")


def test_erken_odeme_karari_ortuk_oranla_tutarli():
    """Örtük oran paranın maliyetine eşitse iki seçenek aynıdır."""
    f = iskonto_faktoru(0.40, 45)
    s = erken_odeme_analiz_et(ErkenOdemeGirdisi(fatura_tutari=50_000, iskonto_yuzde=(1 - f) * 100, vade_gun=45), P40)
    assert s.pesin_odemenin_kazanci == pytest.approx(0, abs=1e-6)
    assert s.ortuk_yillik_oran == pytest.approx(0.40, abs=1e-9)


TAKSITLI = FinansmanAlternatifi(ad="Banka A", tur="esit_taksitli", kullanilan_tutar=1_000_000,
                                yillik_faiz_yuzde=42, vade_ay=12)
TEK = FinansmanAlternatifi(ad="Banka B", tur="tek_odemeli", kullanilan_tutar=1_000_000, yillik_faiz_yuzde=45, vade_ay=6)


def test_esit_taksit_tutari_ve_plan():
    plan = odeme_plani(TAKSITLI)
    assert len(plan) == 12
    assert plan[0].odeme == pytest.approx(103_483.949264, abs=1e-5)
    assert sum(s.anapara for s in plan) == pytest.approx(1_000_000, abs=1e-6)
    assert plan[-1].kalan_anapara == pytest.approx(0, abs=1e-6)
    assert [s.gun for s in plan] == [30 * k for k in range(1, 13)]


def test_ic_verim_orani_kapali_formulle():
    s = finansman_karsilastir(FinansmanGirdisi(alternatifler=[TAKSITLI, TEK]), P40)
    a, b = s.alternatifler
    # Masrafsız eşit taksitte efektif yıllık = (1 + aylık)^(365/30) − 1
    assert a.efektif_yillik_maliyet == pytest.approx(0.519757, abs=1e-6)
    # Tek ödemede: (1,225)^(365/180) − 1
    assert b.toplam_geri_odeme == pytest.approx(1_225_000)
    assert b.efektif_yillik_maliyet == pytest.approx(0.509108, abs=1e-6)
    assert s.en_dusuk_efektif_maliyet == "Banka B"


def test_masraf_efektif_maliyeti_artirir():
    masrafli = TAKSITLI.model_copy(update={"ad": "Masraflı", "pesin_masraf": 10_000})
    s = finansman_karsilastir(FinansmanGirdisi(alternatifler=[TAKSITLI, masrafli]), P40)
    assert s.alternatifler[1].efektif_yillik_maliyet > s.alternatifler[0].efektif_yillik_maliyet
    assert s.alternatifler[1].net_kullanilan == 990_000


def test_irr_noktasinda_bugunku_deger_maliyeti_sifir():
    s = finansman_karsilastir(FinansmanGirdisi(alternatifler=[TAKSITLI]), P40)
    irr = s.alternatifler[0].efektif_yillik_maliyet
    p = AnalizParametreleri(yillik_oran_yuzde=irr * 100, faiz_yontemi="efektif")
    s2 = finansman_karsilastir(FinansmanGirdisi(alternatifler=[TAKSITLI]), p)
    assert s2.alternatifler[0].bugunku_deger_maliyeti == pytest.approx(0, abs=1e-4)


def test_faizsiz_kredi():
    sifir = FinansmanAlternatifi(ad="Faizsiz", tur="esit_taksitli", kullanilan_tutar=12_000, yillik_faiz_yuzde=0, vade_ay=12)
    s = finansman_karsilastir(FinansmanGirdisi(alternatifler=[sifir]), P40)
    assert s.alternatifler[0].efektif_yillik_maliyet == pytest.approx(0, abs=1e-9)
    assert s.alternatifler[0].bugunku_deger_maliyeti < 0  # paranın maliyetinden ucuz


def test_duyarlilik_ve_ayni_ad_hatasi():
    s = finansman_karsilastir(FinansmanGirdisi(alternatifler=[TAKSITLI, TEK], duyarlilik_oranlari_yuzde=[0, 40, 80]), P40)
    assert [d.yillik_oran_yuzde for d in s.duyarlilik] == [0, 40, 80]
    assert set(s.duyarlilik[1].bugunku_deger_maliyetleri) == {"Banka A", "Banka B"}
    with pytest.raises(ValueError, match="farklı"):
        finansman_karsilastir(FinansmanGirdisi(alternatifler=[TEK, TEK]), P40)


def test_masraf_tutardan_buyukse_hata():
    with pytest.raises(ValueError):
        finansman_karsilastir(FinansmanGirdisi(alternatifler=[TEK.model_copy(update={"pesin_masraf": 2e6})]), P40)


# --------------------------------------------- Modül 6–7: fiyat ve risk

def test_varsayilan_senaryolar_modul1_ile_ayni():
    s = fiyat_senaryolari(FiyatlamaGirdisi(urun=urun(tahsilat_vadesi_gun=0)), P40)
    assert [x.ad for x in s.senaryolar] == ["Peşin", "30 gün", "60 gün", "90 gün"]
    for x in s.senaryolar:
        m1 = urun_analiz_et(urun(tahsilat_vadesi_gun=x.tahsilat_vadesi_gun), P40)
        assert x.ekonomik_sonuc == m1.ekonomik_sonuc
        assert x.riskli_ekonomik_sonuc == pytest.approx(m1.ekonomik_sonuc, abs=1e-12)  # risk yok
    assert s.en_iyi_senaryo == "Peşin"


def test_pesine_esdeger_vadeli_fiyat():
    s = fiyat_senaryolari(FiyatlamaGirdisi(urun=urun()), P40)
    otuz = next(x for x in s.senaryolar if x.ad == "30 gün")
    assert otuz.pesine_esdeger_vadeli_fiyat == pytest.approx(134.273973, abs=1e-5)
    # Eşdeğer fiyattan vadeli satmak peşin satışla aynı ekonomik sonucu vermeli
    pesin = urun_analiz_et(urun(tahsilat_vadesi_gun=0), P40).ekonomik_sonuc
    esdeger = urun_analiz_et(urun(tahsilat_vadesi_gun=30, satis_fiyati=otuz.pesine_esdeger_vadeli_fiyat), P40)
    assert esdeger.ekonomik_sonuc == pytest.approx(pesin, abs=1e-9)


def test_tahsilat_riski():
    risk = TahsilatRiski(odeme_olasiligi_yuzde=95, beklenen_gecikme_gun=15)
    r = riskli_sonuc(urun(tahsilat_vadesi_gun=0), P40, risk)
    assert r["riskli_ekonomik_sonuc"] == pytest.approx(1.502695, abs=1e-5)
    assert r["riskli_basabas_fiyati"] == pytest.approx(128.392213, abs=1e-5)
    assert r["risk_maliyeti"] == pytest.approx(10 - 1.502695, abs=1e-5)
    # Geri sağlama: riskli başabaş fiyatında riskli sonuç sıfır
    r2 = riskli_sonuc(urun(tahsilat_vadesi_gun=0, satis_fiyati=r["riskli_basabas_fiyati"]), P40, risk)
    assert r2["riskli_ekonomik_sonuc"] == pytest.approx(0, abs=1e-9)


def test_ozel_senaryolar_ve_en_iyi_secim():
    s = fiyat_senaryolari(FiyatlamaGirdisi(urun=urun(), senaryolar=[
        FiyatSenaryosu(ad="Ucuz peşin", satis_fiyati=125, tahsilat_vadesi_gun=0),
        FiyatSenaryosu(ad="Pahalı vadeli", satis_fiyati=150, tahsilat_vadesi_gun=60),
    ]), P40)
    # 125 − 120 = 5 ; 150 / (1 + 0,4·60/365) − 120 = 20,74
    assert s.en_iyi_senaryo == "Pahalı vadeli"
    with pytest.raises(ValueError):
        fiyat_senaryolari(FiyatlamaGirdisi(urun=urun(), senaryolar=[
            FiyatSenaryosu(ad="A", satis_fiyati=1, tahsilat_vadesi_gun=0)] * 2), P40)


@pytest.mark.parametrize("kw", [dict(odeme_olasiligi_yuzde=0), dict(odeme_olasiligi_yuzde=101),
                                dict(beklenen_gecikme_gun=-1)])
def test_gecersiz_risk(kw):
    with pytest.raises(ValidationError):
        TahsilatRiski(**kw)


# --------------------------------------------------------------- toplu

def test_toplu_analiz_ozet_ve_siralama():
    urunler = [
        urun(urun_kodu="A", satis_miktari=10),                                 # −1,6708 × 10
        urun(urun_kodu="B", satis_fiyati=200, satis_miktari=5),                # kârlı
        urun(urun_kodu="C", satis_fiyati=115, tahsilat_vadesi_gun=0, satis_miktari=2),  # −5 × 2
    ]
    t = toplu_analiz(urunler, P40)
    assert [s.urun_kodu for s in t.sonuclar][0] == "A"  # en kötü: −16,708
    assert [s.urun_kodu for s in t.sonuclar][-1] == "B"
    beklenen_eko = sum(urun_analiz_et(u, P40).toplam_ekonomik_sonuc for u in urunler)
    assert t.ozet.toplam_ekonomik_sonuc == pytest.approx(beklenen_eko)
    assert t.ozet.toplam_ciro == pytest.approx(130 * 10 + 200 * 5 + 115 * 2)
    assert t.ozet.zarar_eden_urun_sayisi == 2
    assert t.ozet.gizli_fark == pytest.approx(t.ozet.toplam_muhasebe_brut_kari - t.ozet.toplam_ekonomik_sonuc)
    assert t.ozet.en_kotu_urunler == ["A", "C"] and t.ozet.en_iyi_urunler == ["B"]
