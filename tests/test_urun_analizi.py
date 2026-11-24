"""Modül 1 – Ürün bazlı gerçek kârlılık testleri."""

from fractions import Fraction

import pytest
from pydantic import ValidationError

from karmax.motor import AnalizParametreleri, FaizYontemi, UrunGirdisi, urun_analiz_et
from tests import referans_degerler as ref

TOL = ref.TOLERANS


def urun(**kw) -> UrunGirdisi:
    temel = dict(
        urun_kodu="REF-001",
        urun_adi="Referans ürün",
        ilk_alis_maliyeti=ref.TEMEL["ilk_alis"],
        yerine_koyma_maliyeti=ref.TEMEL["yerine_koyma"],
        satis_fiyati=ref.TEMEL["satis"],
        tahsilat_vadesi_gun=90,
    )
    temel.update(kw)
    return UrunGirdisi(**temel)


def param(**kw) -> AnalizParametreleri:
    temel = dict(yillik_oran_yuzde=ref.TEMEL["oran_yuzde"])
    temel.update(kw)
    return AnalizParametreleri(**temel)


# ---------- Referans senaryo ----------

def test_referans_senaryo():
    s = urun_analiz_et(urun(), param())
    assert s.tahsilat_bugunku_degeri == pytest.approx(118.329177, abs=TOL)
    assert s.ekonomik_sonuc == pytest.approx(-1.670823, abs=TOL)
    assert s.vade_maliyeti == pytest.approx(11.670823, abs=TOL)
    assert s.basabas_satis_fiyati == pytest.approx(ref.BASABAS_FIYATI_90_GUN, abs=TOL)
    assert s.hedef_satis_fiyati == pytest.approx(ref.HEDEF_FIYAT_90_GUN_YUZDE30, abs=TOL)
    assert s.maksimum_vade_gun == pytest.approx(ref.MAKS_VADE_BASIT, abs=1e-4)
    assert s.maksimum_vade_durumu == "sinirli"


@pytest.mark.parametrize("gun, beklenen", ref.VADE_TABLOSU.items())
def test_pesin_30_60_90_gun(gun, beklenen):
    bd, ekonomik, vade = beklenen
    s = urun_analiz_et(urun(tahsilat_vadesi_gun=gun), param())
    assert s.tahsilat_bugunku_degeri == pytest.approx(bd, abs=TOL)
    assert s.ekonomik_sonuc == pytest.approx(ekonomik, abs=TOL)
    assert s.vade_maliyeti == pytest.approx(vade, abs=TOL)


def test_360_gun_esasi():
    s = urun_analiz_et(urun(), param(gun_esasi=360))
    assert s.ekonomik_sonuc == pytest.approx(ref.GUN_ESASI_360_90_GUN[1], abs=TOL)


# ---------- Kavram ayrımları ----------

def test_kar_orani_ile_kar_marji_ayri():
    s = urun_analiz_et(urun(), param())
    assert s.muhasebe_brut_kari == pytest.approx(ref.BRUT_KAR)
    assert s.kar_orani_maliyet_uzerinden == pytest.approx(ref.KAR_ORANI_MALIYET, abs=1e-6)
    assert s.brut_kar_marji_satis_uzerinden == pytest.approx(ref.BRUT_KAR_MARJI, abs=1e-6)


def test_brut_kar_ile_ekonomik_sonuc_ayri():
    s = urun_analiz_et(urun(), param())
    assert s.muhasebe_brut_kari > 0 > s.ekonomik_sonuc


def test_yerine_koyma_maliyeti_dogru_uygulanir():
    s = urun_analiz_et(urun(tahsilat_vadesi_gun=0), param())
    assert s.yerine_koyma_kari == pytest.approx(10.0)
    assert s.ekonomik_sonuc == pytest.approx(10.0)  # peşin, ek gider yok → yerine koyma kârına eşit


# ---------- Çift sayım ----------

@pytest.mark.parametrize("tahsilat, tedarikci, gider", [(90, 0, 0), (90, 60, 0), (45, 120, 3.5), (0, 0, 7)])
def test_kopru_toplami_ekonomik_sonuca_esit(tahsilat, tedarikci, gider):
    s = urun_analiz_et(
        urun(tahsilat_vadesi_gun=tahsilat, tedarikci_vadesi_gun=tedarikci, ek_gider_birim=gider), param()
    )
    assert sum(a.tutar for a in s.kopru) == pytest.approx(s.ekonomik_sonuc, abs=1e-9)
    adlar = [a.ad for a in s.kopru]
    assert len(adlar) == len(set(adlar)), "Bir kalem köprüde iki kez yer alıyor"


def test_vade_maliyeti_bir_kez_dusulur():
    """Ekonomik sonuç = yerine koyma kârı − vade maliyeti (başka hiçbir kalem yokken)."""
    s = urun_analiz_et(urun(), param())
    assert s.ekonomik_sonuc == pytest.approx(s.yerine_koyma_kari - s.vade_maliyeti, abs=1e-9)


def test_tedarikci_vadesi_hesaba_katilir():
    s = urun_analiz_et(urun(tedarikci_vadesi_gun=60), param())
    assert s.yerine_koyma_bugunku_degeri == pytest.approx(ref.TEDARIKCI_60_BD_YERINE_KOYMA, abs=TOL)
    assert s.ekonomik_sonuc == pytest.approx(ref.TEDARIKCI_60_EKONOMIK, abs=TOL)


# ---------- Başabaş, hedef, maksimum vade: geri sağlama ----------

@pytest.mark.parametrize("yontem", list(FaizYontemi))
@pytest.mark.parametrize("gider, tedarikci", [(0, 0), (4, 30)])
def test_basabas_fiyatinda_ekonomik_sonuc_sifir(yontem, gider, tedarikci):
    p = param(faiz_yontemi=yontem)
    ilk = urun_analiz_et(urun(ek_gider_birim=gider, tedarikci_vadesi_gun=tedarikci), p)
    tekrar = urun_analiz_et(
        urun(ek_gider_birim=gider, tedarikci_vadesi_gun=tedarikci, satis_fiyati=ilk.basabas_satis_fiyati), p
    )
    assert tekrar.ekonomik_sonuc == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize("yontem", list(FaizYontemi))
def test_hedef_fiyatta_hedef_kar_orani_saglanir(yontem):
    p = param(faiz_yontemi=yontem)
    ilk = urun_analiz_et(urun(hedef_kar_orani_yuzde=25), p)
    tekrar = urun_analiz_et(urun(hedef_kar_orani_yuzde=25, satis_fiyati=ilk.hedef_satis_fiyati), p)
    assert tekrar.ekonomik_kar_orani == pytest.approx(0.25, abs=1e-9)


@pytest.mark.parametrize("yontem", list(FaizYontemi))
def test_maksimum_vadede_ekonomik_sonuc_sifir(yontem):
    p = param(faiz_yontemi=yontem)
    ilk = urun_analiz_et(urun(), p)
    # Motor gün olarak tam sayı alır; ondalık günü doğrudan faiz fonksiyonuyla doğrula
    from karmax.motor.faiz import iskonto_faktoru

    df = iskonto_faktoru(p.oran, ilk.maksimum_vade_gun, **p.faiz_argumanlari())
    assert 130 * df - ilk.maliyetin_bugunku_degeri == pytest.approx(0, abs=1e-9)


# ---------- Sınır durumları ----------

def test_sifir_faiz():
    s = urun_analiz_et(urun(), param(yillik_oran_yuzde=0))
    assert s.vade_maliyeti == 0
    assert s.ekonomik_sonuc == pytest.approx(10.0)
    assert s.maksimum_vade_durumu == "sinirsiz"
    assert s.maksimum_vade_gun is None


def test_satis_fiyati_maliyetin_altinda():
    s = urun_analiz_et(urun(satis_fiyati=115), param())
    assert s.maksimum_vade_durumu == "pesin_bile_zarar"
    assert s.maksimum_vade_gun is None


@pytest.mark.parametrize("oran", [10, 25, 40, 60, 100])
def test_oran_arttikca_ekonomik_sonuc_azalir(oran):
    dusuk = urun_analiz_et(urun(), param(yillik_oran_yuzde=oran))
    yuksek = urun_analiz_et(urun(), param(yillik_oran_yuzde=oran + 5))
    assert yuksek.ekonomik_sonuc < dusuk.ekonomik_sonuc


def test_toplamlar_miktarla_carpilir():
    s = urun_analiz_et(urun(satis_miktari=250), param())
    assert s.toplam_ekonomik_sonuc == pytest.approx(s.ekonomik_sonuc * 250)
    assert s.toplam_muhasebe_brut_kari == pytest.approx(30 * 250)


@pytest.mark.parametrize(
    "alan, deger",
    [
        ("satis_fiyati", 0),
        ("satis_fiyati", -5),
        ("ilk_alis_maliyeti", 0),
        ("tahsilat_vadesi_gun", -1),
        ("ek_gider_birim", -1),
        ("urun_kodu", ""),
        ("bilinmeyen_alan", 1),
    ],
)
def test_gecersiz_urun_girdisi_reddedilir(alan, deger):
    with pytest.raises(ValidationError):
        urun(**{alan: deger})


@pytest.mark.parametrize("kw", [dict(gun_esasi=300), dict(yillik_oran_yuzde=-1), dict(bilesik_donem=0)])
def test_gecersiz_parametre_reddedilir(kw):
    with pytest.raises(ValidationError):
        param(**kw)


# ---------- Bağımsız kesirli hesapla karşılaştırma ----------

def _bagimsiz_basit(P, C0, R, G, t_tah, t_ted, r_yuzde, B):
    """Motordan bağımsız, tam kesirli (Fraction) basit faiz hesabı."""
    P, R, G = Fraction(P), Fraction(R), Fraction(G)
    r = Fraction(r_yuzde) / 100
    bd_p = P / (1 + r * t_tah / B)
    bd_r = R / (1 + r * t_ted / B)
    return float(bd_p - bd_r - G)


@pytest.mark.parametrize(
    "P, C0, R, G, t_tah, t_ted, r, B",
    [
        (130, 100, 120, 0, 90, 0, 40, 365),
        (250, 180, 205, 6, 120, 45, 55, 360),
        (19.9, 12.4, 14.75, 0.8, 30, 15, 38.5, 365),
        (1000, 1100, 950, 25, 0, 90, 47, 365),
    ],
)
def test_motor_bagimsiz_kesirli_hesapla_ayni(P, C0, R, G, t_tah, t_ted, r, B):
    s = urun_analiz_et(
        urun(
            satis_fiyati=P, ilk_alis_maliyeti=C0, yerine_koyma_maliyeti=R, ek_gider_birim=G,
            tahsilat_vadesi_gun=t_tah, tedarikci_vadesi_gun=t_ted,
        ),
        param(yillik_oran_yuzde=r, gun_esasi=B),
    )
    assert s.ekonomik_sonuc == pytest.approx(_bagimsiz_basit(P, C0, R, G, t_tah, t_ted, r, B), abs=1e-9)
