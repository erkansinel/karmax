"""Faz 3: eğri verileri ve grafik tanımlarının testleri."""

import json
import math

import pytest

from karmax.grafikler import fiyat_grafigi, grafik_paketi, selale_grafigi, vade_grafigi
from karmax.motor import AnalizParametreleri, FaizYontemi, UrunGirdisi, urun_analiz_et
from karmax.motor.egriler import (
    VADE_UST_SINIR,
    fiyat_araligi,
    fiyat_egrisi,
    vade_egrisi,
    vade_ekseni_ust_siniri,
)
from tests import referans_degerler as ref


def urun(**kw):
    temel = dict(urun_kodu="REF-001", ilk_alis_maliyeti=100, yerine_koyma_maliyeti=120,
                 satis_fiyati=130, tahsilat_vadesi_gun=90)
    temel.update(kw)
    return UrunGirdisi(**temel)


P = AnalizParametreleri(yillik_oran_yuzde=40)


# ---------- Eğri verileri motorla tutarlı ----------

def test_vade_egrisi_referans_noktalarini_icerir():
    noktalar = {n.gun: n for n in vade_egrisi(urun(), P, 180)}
    for gun, (bd, eko, _) in ref.VADE_TABLOSU.items():
        assert noktalar[gun].tahsilat_bugunku_degeri == pytest.approx(bd, abs=ref.TOLERANS)
        assert noktalar[gun].ekonomik_sonuc == pytest.approx(eko, abs=ref.TOLERANS)


def test_vade_egrisi_mevcut_vadeyi_her_zaman_icerir():
    gunler = [n.gun for n in vade_egrisi(urun(tahsilat_vadesi_gun=47), P, 180)]
    assert 47 in gunler and gunler == sorted(gunler) and gunler[0] == 0 and gunler[-1] == 180


@pytest.mark.parametrize("yontem", list(FaizYontemi))
def test_vade_egrisi_azalan(yontem):
    p = AnalizParametreleri(yillik_oran_yuzde=40, faiz_yontemi=yontem)
    degerler = [n.tahsilat_bugunku_degeri for n in vade_egrisi(urun(), p, 360)]
    assert all(a > b for a, b in zip(degerler, degerler[1:]))


def test_vade_egrisi_her_noktasi_motorla_ayni():
    for n in vade_egrisi(urun(), P, 240):
        s = urun_analiz_et(urun(tahsilat_vadesi_gun=n.gun), P)
        assert n.ekonomik_sonuc == s.ekonomik_sonuc


def test_fiyat_egrisi_ozel_noktalari_tam_icerir():
    s = urun_analiz_et(urun(), P)
    alt, ust = fiyat_araligi(s, 130)
    noktalar = fiyat_egrisi(urun(), P, alt, ust, (s.basabas_satis_fiyati, s.hedef_satis_fiyati, 130))
    harita = {n.satis_fiyati: n.ekonomik_sonuc for n in noktalar}
    assert harita[s.basabas_satis_fiyati] == pytest.approx(0, abs=1e-9)
    assert harita[130] == pytest.approx(ref.VADE_TABLOSU[90][1], abs=ref.TOLERANS)
    assert harita[s.hedef_satis_fiyati] == pytest.approx(0.30 * s.maliyetin_bugunku_degeri, abs=1e-9)


def test_fiyat_egrisi_artan_ve_araligi_kapsar():
    s = urun_analiz_et(urun(), P)
    alt, ust = fiyat_araligi(s, 130)
    assert alt < s.basabas_satis_fiyati < s.hedef_satis_fiyati < ust and alt < 130 < ust
    y = [n.ekonomik_sonuc for n in fiyat_egrisi(urun(), P, alt, ust)]
    assert all(a < b for a, b in zip(y, y[1:]))


def test_fiyat_egrisi_gecersiz_aralik():
    with pytest.raises(ValueError):
        fiyat_egrisi(urun(), P, 150, 100)


@pytest.mark.parametrize(
    "kw, beklenen_en_az",
    [(dict(), 180), (dict(tahsilat_vadesi_gun=300), 450), (dict(satis_fiyati=200), 1)],
)
def test_vade_ekseni_ust_siniri(kw, beklenen_en_az):
    u = urun(**kw)
    s = urun_analiz_et(u, P)
    ust = vade_ekseni_ust_siniri(s, u.tahsilat_vadesi_gun)
    assert ust >= beklenen_en_az and ust % 30 == 0 and ust <= VADE_UST_SINIR
    if s.maksimum_vade_durumu == "sinirli":
        assert ust >= s.maksimum_vade_gun


# ---------- Grafik tanımları ----------

def test_selale_grafigi_kopruyle_ayni():
    s = urun_analiz_et(urun(tedarikci_vadesi_gun=30, ek_gider_birim=2), P)
    w = selale_grafigi(s)["data"][0]
    assert w["type"] == "waterfall"
    assert w["measure"][0] == "absolute" and w["measure"][-1] == "total"
    assert sum(w["y"][:-1]) == pytest.approx(s.ekonomik_sonuc, abs=1e-9)
    assert w["x"][-1] == "Ekonomik sonuç"


def test_selale_sifir_adimlari_gostermez_ama_toplam_dogru():
    s = urun_analiz_et(urun(), P)  # ek gider ve tedarikçi vadesi sıfır
    w = selale_grafigi(s)["data"][0]
    assert "Ek giderler" not in w["x"] and "Tedarikçi vadesi kazancı" not in w["x"]
    assert sum(w["y"][:-1]) == pytest.approx(s.ekonomik_sonuc, abs=1e-9)


def test_vade_grafigi_isaretleri():
    u = urun()
    s = urun_analiz_et(u, P)
    fig = vade_grafigi(s, vade_egrisi(u, P, 180), 90)
    metinler = [t.get("text", [""])[0] for t in fig["data"] if t.get("text")]
    assert any("başabaş: 76 gün" in m for m in metinler)
    assert any("senin vaden: 90 gün" in m for m in metinler)
    zarar = [sh for sh in fig["layout"]["shapes"] if sh.get("type") == "rect"]
    assert zarar and zarar[0]["x0"] == pytest.approx(s.maksimum_vade_gun)


def test_fiyat_grafigi_isaretleri_motor_degerlerini_kullanir():
    u = urun()
    s = urun_analiz_et(u, P)
    alt, ust = fiyat_araligi(s, 130)
    fig = fiyat_grafigi(s, fiyat_egrisi(u, P, alt, ust, (s.basabas_satis_fiyati, s.hedef_satis_fiyati, 130)), 130)
    isaretler = {t["text"][0].split(":")[0]: (t["x"][0], t["y"][0]) for t in fig["data"] if t.get("text")}
    assert isaretler["başabaş"][1] == pytest.approx(0, abs=1e-9)
    assert isaretler["hedef"][0] == pytest.approx(ref.HEDEF_FIYAT_90_GUN_YUZDE30, abs=ref.TOLERANS)
    assert "131,84 TL" in [t["text"][0] for t in fig["data"] if t.get("text")][0]


@pytest.mark.parametrize(
    "kw, oran",
    [(dict(), 40), (dict(), 0), (dict(satis_fiyati=110), 40), (dict(tahsilat_vadesi_gun=0), 40),
     (dict(tahsilat_vadesi_gun=3650), 40)],
)
def test_grafik_paketi_sinir_durumlarinda_gecerli_json(kw, oran):
    u = urun(**kw)
    p = AnalizParametreleri(yillik_oran_yuzde=oran)
    paket = grafik_paketi(u, p, urun_analiz_et(u, p))
    metin = json.dumps(paket, allow_nan=False)  # NaN / sonsuz varsa hata verir
    assert set(paket) == {"selale", "vade", "fiyat"}
    assert len(metin) < 30_000
    for fig in paket.values():
        for iz in fig["data"]:
            for eksen in ("x", "y"):
                for v in iz.get(eksen, []):
                    assert not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))
