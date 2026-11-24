"""Grafik eğrileri için veri üretimi.

KURAL: Bu modül YENİ FORMÜL İÇERMEZ. Eğrinin her noktası, Modül 1'in
`urun_analiz_et` fonksiyonu tek parametresi değiştirilerek çağrılarak
hesaplanır. Böylece grafik ile sonuç tablosu asla birbirinden sapamaz.
"""

from __future__ import annotations

import math

from pydantic import BaseModel

from .modeller import AnalizParametreleri, UrunGirdisi, UrunSonucu
from .urun_analizi import urun_analiz_et

VADE_UST_SINIR = 3650
NOKTA_SAYISI = 61


class VadeNoktasi(BaseModel):
    gun: int
    tahsilat_bugunku_degeri: float
    ekonomik_sonuc: float


class FiyatNoktasi(BaseModel):
    satis_fiyati: float
    ekonomik_sonuc: float


def _yuvarla_yukari(deger: float, adim: int) -> int:
    return int(math.ceil(deger / adim) * adim)


def vade_ekseni_ust_siniri(sonuc: UrunSonucu, tahsilat_gun: int) -> int:
    """Grafiğin vade ekseninin nerede biteceğini belirler (gösterim kararı)."""
    adaylar = [180.0, tahsilat_gun * 1.5]
    if sonuc.maksimum_vade_durumu == "sinirli" and sonuc.maksimum_vade_gun is not None:
        adaylar.append(sonuc.maksimum_vade_gun * 1.3)
    return min(VADE_UST_SINIR, _yuvarla_yukari(max(adaylar), 30))


def vade_egrisi(urun: UrunGirdisi, p: AnalizParametreleri, ust_gun: int) -> list[VadeNoktasi]:
    adim = max(1, round(ust_gun / (NOKTA_SAYISI - 1)))
    gunler = sorted(set(range(0, ust_gun + 1, adim)) | {ust_gun, urun.tahsilat_vadesi_gun})
    noktalar = []
    for g in gunler:
        s = urun_analiz_et(urun.model_copy(update={"tahsilat_vadesi_gun": g}), p)
        noktalar.append(VadeNoktasi(gun=g, tahsilat_bugunku_degeri=s.tahsilat_bugunku_degeri, ekonomik_sonuc=s.ekonomik_sonuc))
    return noktalar


def fiyat_araligi(sonuc: UrunSonucu, mevcut_fiyat: float) -> tuple[float, float]:
    """Fiyat ekseninin aralığı: başabaş, hedef ve mevcut fiyatın hepsi görünür."""
    alt = 0.8 * min(sonuc.basabas_satis_fiyati, mevcut_fiyat)
    ust = 1.15 * max(sonuc.hedef_satis_fiyati, mevcut_fiyat)
    return alt, ust


def fiyat_egrisi(
    urun: UrunGirdisi, p: AnalizParametreleri, alt: float, ust: float, ek_fiyatlar: tuple[float, ...] = ()
) -> list[FiyatNoktasi]:
    """`ek_fiyatlar` (başabaş, hedef, mevcut fiyat) eğriye tam değerleriyle eklenir;
    grafik bu noktaları yeniden hesaplamadan doğrudan buradan okur."""
    if not (0 < alt < ust):
        raise ValueError("Fiyat aralığı geçersiz.")
    adim = (ust - alt) / (NOKTA_SAYISI - 1)
    fiyatlar = sorted({alt + i * adim for i in range(NOKTA_SAYISI)} | {f for f in ek_fiyatlar if f > 0})
    noktalar = []
    for f in fiyatlar:
        s = urun_analiz_et(urun.model_copy(update={"satis_fiyati": f}), p)
        noktalar.append(FiyatNoktasi(satis_fiyati=f, ekonomik_sonuc=s.ekonomik_sonuc))
    return noktalar
