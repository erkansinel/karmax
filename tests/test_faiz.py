"""Faiz ve iskonto fonksiyonlarının testleri (Modül 2 temeli)."""

import math

import pytest

from karmax.motor.faiz import (
    FaizYontemi,
    bugunku_deger,
    efektif_yillik_oran,
    faktore_ulasilan_gun,
    gelecekteki_deger,
    iskonto_faktoru,
    tahsilat_gecikmesi_maliyeti,
    ticari_iskonto_tutari,
)
from tests import referans_degerler as ref

TOL = ref.TOLERANS


@pytest.mark.parametrize("gun, beklenen", [(g, v[0]) for g, v in ref.VADE_TABLOSU.items()])
def test_basit_faiz_bugunku_deger_tablosu(gun, beklenen):
    assert bugunku_deger(130, 0.40, gun) == pytest.approx(beklenen, abs=TOL)


def test_360_ve_365_gun_esasi_farkli_sonuc_verir():
    bd365 = bugunku_deger(130, 0.40, 90, gun_esasi=365)
    bd360 = bugunku_deger(130, 0.40, 90, gun_esasi=360)
    assert bd360 == pytest.approx(ref.GUN_ESASI_360_90_GUN[0], abs=TOL)
    assert bd360 < bd365  # 360 esasında aynı gün daha uzun bir yıl kesridir


def test_basit_ve_bilesik_faiz_ayrimi():
    basit = bugunku_deger(130, 0.40, 90, yontem=FaizYontemi.BASIT)
    bilesik = bugunku_deger(130, 0.40, 90, yontem=FaizYontemi.BILESIK, donem=12)
    efektif = bugunku_deger(130, 0.40, 90, yontem=FaizYontemi.EFEKTIF)
    assert bilesik == pytest.approx(ref.BILESIK_AYLIK_BD, abs=TOL)
    assert efektif == pytest.approx(ref.EFEKTIF_BD, abs=TOL)
    assert len({round(basit, 4), round(bilesik, 4), round(efektif, 4)}) == 3


def test_nominal_ve_efektif_oran_karistirilmaz():
    """%40 nominal aylık bileşik = %48,21 efektif. İkisi aynı BD'yi vermeli."""
    efektif = efektif_yillik_oran(0.40, 12)
    assert efektif == pytest.approx(ref.EFEKTIF_YILLIK_AYLIK_BILESIK, abs=1e-6)
    a = bugunku_deger(130, 0.40, 90, yontem=FaizYontemi.BILESIK, donem=12)
    b = bugunku_deger(130, efektif, 90, yontem=FaizYontemi.EFEKTIF)
    assert a == pytest.approx(b, abs=1e-9)


@pytest.mark.parametrize("yontem", list(FaizYontemi))
def test_bugunku_ve_gelecekteki_deger_birbirinin_tersi(yontem):
    bd = bugunku_deger(1000, 0.35, 137, yontem=yontem)
    assert gelecekteki_deger(bd, 0.35, 137, yontem=yontem) == pytest.approx(1000, abs=1e-9)


@pytest.mark.parametrize("yontem", list(FaizYontemi))
def test_sifir_gun_ve_sifir_faiz(yontem):
    assert iskonto_faktoru(0.40, 0, yontem=yontem) == 1.0
    assert iskonto_faktoru(0.0, 180, yontem=yontem) == 1.0


def test_ticari_iskonto_bugunku_degerden_farklidir():
    ticari = ticari_iskonto_tutari(130, 0.40, 90)
    assert ticari == pytest.approx(ref.TICARI_ISKONTO_TUTARI, abs=TOL)
    assert ticari < bugunku_deger(130, 0.40, 90)


def test_ticari_iskonto_anlamsiz_vadede_hata_verir():
    with pytest.raises(ValueError):
        ticari_iskonto_tutari(130, 0.40, 1000)


def test_tahsilat_gecikmesi_maliyeti():
    maliyet = tahsilat_gecikmesi_maliyeti(130, 0.40, 60, 30)
    beklenen = ref.VADE_TABLOSU[60][0] - ref.VADE_TABLOSU[90][0]
    assert maliyet == pytest.approx(beklenen, abs=TOL)


@pytest.mark.parametrize(
    "yontem, beklenen",
    [
        (FaizYontemi.BASIT, ref.MAKS_VADE_BASIT),
        (FaizYontemi.BILESIK, ref.MAKS_VADE_BILESIK_AYLIK),
        (FaizYontemi.EFEKTIF, ref.MAKS_VADE_EFEKTIF),
    ],
)
def test_faktorun_tersi(yontem, beklenen):
    gun = faktore_ulasilan_gun(120 / 130, 0.40, yontem=yontem)
    assert gun == pytest.approx(beklenen, abs=1e-4)
    # Geri sağlama: bulunan günde faktör hedefe eşit olmalı
    assert iskonto_faktoru(0.40, gun, yontem=yontem) == pytest.approx(120 / 130, abs=1e-12)


def test_faktorun_tersi_sinir_durumlari():
    assert faktore_ulasilan_gun(1.05, 0.40) is None          # peşin bile yetmez
    assert math.isinf(faktore_ulasilan_gun(0.9, 0.0))         # faiz yok, vade sınırsız
    assert faktore_ulasilan_gun(1.0, 0.40) == 0.0


@pytest.mark.parametrize(
    "kw",
    [dict(oran=-0.1, gun=30), dict(oran=0.4, gun=-1), dict(oran=0.4, gun=30, gun_esasi=300)],
)
def test_gecersiz_girdiler_reddedilir(kw):
    with pytest.raises(ValueError):
        iskonto_faktoru(**kw)
