"""MODÜL 1 – Ürün bazlı gerçek kârlılık.

Ölçüm noktası (Hesaplama Sözleşmesi §3):
    Karar anı = satış günü (t = 0). Sonuç İLERİYE DÖNÜKTÜR.
    Malın geçmişte stokta beklemesi batık maliyettir; etkisi zaten
    "yerine koyma farkı" içinde görünür ve ayrıca düşülmez.

Nakit akışları (hepsi aynı orandan t = 0'a iskonto edilir):
    + Satış fiyatı           → tahsilat_vadesi_gun günü girer
    − Yerine koyma maliyeti   → tedarikci_vadesi_gun günü çıkar
    − Ek gider                → bugün (t = 0) çıkar

    Ekonomik sonuç = BD(satış) − BD(yerine koyma) − ek gider

Köprü (muhasebe kârından ekonomik sonuca):
      Muhasebe brüt kârı          (P − C0)
    − Yerine koyma farkı          (R − C0)
    − Ek gider                    (G)
    − Vade maliyeti               (P − BD(P))
    + Tedarikçi vadesi kazancı    (R − BD(R))
    = Ekonomik sonuç              BD(P) − BD(R) − G
Her kalem tam olarak bir kez yer alır. Toplam tutmazsa hesaplama durdurulur.
"""

from __future__ import annotations

import math

from .faiz import FaizYontemi, faktore_ulasilan_gun, iskonto_faktoru
from .modeller import AnalizParametreleri, KopruAdimi, UrunGirdisi, UrunSonucu

KOPRU_TOLERANSI = 1e-9


class TutarsizHesapHatasi(RuntimeError):
    """Köprü adımlarının toplamı ekonomik sonuca eşit değilse fırlatılır."""


def _yontem_metni(p: AnalizParametreleri) -> str:
    if p.faiz_yontemi == FaizYontemi.BASIT:
        return "basit faiz"
    if p.faiz_yontemi == FaizYontemi.BILESIK:
        return f"bileşik faiz (yılda {p.bilesik_donem} dönem)"
    return "efektif yıllık faiz"


def urun_analiz_et(urun: UrunGirdisi, p: AnalizParametreleri) -> UrunSonucu:
    r = p.oran
    kw = p.faiz_argumanlari()

    P = urun.satis_fiyati
    C0 = urun.ilk_alis_maliyeti
    R = urun.yerine_koyma_maliyeti
    G = urun.ek_gider_birim
    h = urun.hedef_kar_orani_yuzde / 100.0

    df_tahsilat = iskonto_faktoru(r, urun.tahsilat_vadesi_gun, **kw)
    df_odeme = iskonto_faktoru(r, urun.tedarikci_vadesi_gun, **kw)

    # Muhasebe bakışı
    brut = P - C0
    kar_orani = brut / C0
    marj = brut / P

    # Zaman değeri
    bd_satis = P * df_tahsilat
    bd_yerine_koyma = R * df_odeme
    vade_maliyeti = P - bd_satis
    tedarikci_kazanci = R - bd_yerine_koyma
    maliyet_bd = bd_yerine_koyma + G

    ekonomik = bd_satis - maliyet_bd

    # Köprü – çift sayım kontrolü
    kopru = [
        KopruAdimi(ad="Muhasebe brüt kârı", tutar=brut, aciklama="Satış fiyatı − ilk alış maliyeti"),
        KopruAdimi(ad="Yerine koyma farkı", tutar=-(R - C0), aciklama="Malı bugün yeniden almanın ek maliyeti"),
        KopruAdimi(ad="Ek giderler", tutar=-G, aciklama="Satışa bağlı ek giderler"),
        KopruAdimi(
            ad="Vade maliyeti", tutar=-vade_maliyeti,
            aciklama=f"Tahsilatın {urun.tahsilat_vadesi_gun} gün beklemesinin maliyeti",
        ),
        KopruAdimi(
            ad="Tedarikçi vadesi kazancı", tutar=tedarikci_kazanci,
            aciklama=f"Yerine koyma ödemesinin {urun.tedarikci_vadesi_gun} gün ertelenmesinin kazancı",
        ),
    ]
    kopru_toplami = sum(a.tutar for a in kopru)
    if abs(kopru_toplami - ekonomik) > KOPRU_TOLERANSI * max(1.0, abs(P)):
        raise TutarsizHesapHatasi(
            f"Köprü toplamı ({kopru_toplami}) ekonomik sonuçla ({ekonomik}) eşleşmiyor."
        )

    # Karar destek
    basabas = maliyet_bd / df_tahsilat
    hedef = maliyet_bd * (1.0 + h) / df_tahsilat

    gun = faktore_ulasilan_gun(maliyet_bd / P, r, **kw)
    if gun is None:
        maks_vade, durum = None, "pesin_bile_zarar"
    elif math.isinf(gun):
        maks_vade, durum = None, "sinirsiz"
    else:
        maks_vade, durum = gun, "sinirli"

    varsayimlar = [
        "Tutarlar birim başına, TL ve KDV hariçtir.",
        f"Paranın maliyeti yıllık %{p.yillik_oran_yuzde:g}, {_yontem_metni(p)}, {p.gun_esasi} gün esası.",
        "Sonuç satış günü itibarıyla ölçülür; geçmiş stok bekleme maliyeti ayrıca düşülmez.",
        f"Müşteri tahsilatı {urun.tahsilat_vadesi_gun}. gün, yerine koyma ödemesi {urun.tedarikci_vadesi_gun}. gün yapılır.",
        "Ek giderler satış günü ödenir.",
        f"Hedef fiyat, maliyetin bugünkü değeri üzerine %{urun.hedef_kar_orani_yuzde:g} kâr oranıyla hesaplanır.",
        "Tahsil edilememe riski, KDV zamanlaması ve gelir vergisi bu sürümde hesaba katılmaz.",
    ]

    return UrunSonucu(
        urun_kodu=urun.urun_kodu,
        urun_adi=urun.urun_adi,
        muhasebe_brut_kari=brut,
        kar_orani_maliyet_uzerinden=kar_orani,
        brut_kar_marji_satis_uzerinden=marj,
        yerine_koyma_kari=P - R,
        tahsilat_bugunku_degeri=bd_satis,
        yerine_koyma_bugunku_degeri=bd_yerine_koyma,
        vade_maliyeti=vade_maliyeti,
        tedarikci_vadesi_kazanci=tedarikci_kazanci,
        maliyetin_bugunku_degeri=maliyet_bd,
        ekonomik_sonuc=ekonomik,
        ekonomik_kar_orani=ekonomik / maliyet_bd,
        basabas_satis_fiyati=basabas,
        hedef_satis_fiyati=hedef,
        maksimum_vade_gun=maks_vade,
        maksimum_vade_durumu=durum,
        satis_miktari=urun.satis_miktari,
        toplam_muhasebe_brut_kari=brut * urun.satis_miktari,
        toplam_ekonomik_sonuc=ekonomik * urun.satis_miktari,
        kopru=kopru,
        varsayimlar=varsayimlar,
    )
