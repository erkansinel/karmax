"""MODÜL 3 – Yeniden satın alma maliyeti ve parti maliyet yöntemi.

Farklı fiyatlarla alınmış partilerden satılan malın birim maliyetini
FIFO veya ağırlıklı ortalama yöntemiyle hesaplar; stoğun bugünkü yerine
koyma maliyetine göre değer değişimini gösterir.

Bulunan birim maliyet, Modül 1'deki "ilk alış maliyeti" alanına girilir.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class MaliyetYontemi(str, Enum):
    FIFO = "fifo"
    AGIRLIKLI_ORTALAMA = "agirlikli_ortalama"


class Parti(BaseModel):
    model_config = ConfigDict(extra="forbid")

    miktar: float = Field(..., gt=0)
    birim_maliyet: float = Field(..., gt=0)


class MaliyetGirdisi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partiler: list[Parti] = Field(..., min_length=1, max_length=500, description="Eskiden yeniye sıralı")
    satilan_miktar: float = Field(..., gt=0)
    yontem: MaliyetYontemi = MaliyetYontemi.FIFO
    yerine_koyma_maliyeti: float = Field(..., gt=0, description="Aynı malın bugünkü birim alış fiyatı")


class MaliyetSonucu(BaseModel):
    yontem: MaliyetYontemi
    satilan_miktar: float
    satilan_malin_maliyeti: float
    birim_maliyet: float = Field(description="Modül 1'e 'ilk alış maliyeti' olarak girilecek değer")
    kalan_miktar: float
    kalan_stok_degeri: float
    toplam_stok_miktari: float
    toplam_stok_maliyeti: float
    stok_yerine_koyma_degeri: float
    stok_deger_degisimi: float = Field(description="Tüm stoğun bugünkü yerine koyma değeri − kayıtlı maliyeti")
    fiyat_artisi_orani: float = Field(description="Yerine koyma maliyeti ÷ ağırlıklı ortalama maliyet − 1")
    varsayimlar: list[str]


def maliyet_hesapla(g: MaliyetGirdisi) -> MaliyetSonucu:
    toplam_miktar = sum(p.miktar for p in g.partiler)
    toplam_maliyet = sum(p.miktar * p.birim_maliyet for p in g.partiler)
    if g.satilan_miktar > toplam_miktar + 1e-9:
        raise ValueError(
            f"Satılan miktar ({g.satilan_miktar:g}) stoktaki toplam miktardan ({toplam_miktar:g}) fazla."
        )
    ortalama = toplam_maliyet / toplam_miktar

    if g.yontem == MaliyetYontemi.AGIRLIKLI_ORTALAMA:
        smm = g.satilan_miktar * ortalama
    else:
        kalan_satis, smm = g.satilan_miktar, 0.0
        for p in g.partiler:
            alinan = min(p.miktar, kalan_satis)
            smm += alinan * p.birim_maliyet
            kalan_satis -= alinan
            if kalan_satis <= 1e-12:
                break

    kalan_miktar = toplam_miktar - g.satilan_miktar
    yk_degeri = toplam_miktar * g.yerine_koyma_maliyeti
    return MaliyetSonucu(
        yontem=g.yontem,
        satilan_miktar=g.satilan_miktar,
        satilan_malin_maliyeti=smm,
        birim_maliyet=smm / g.satilan_miktar,
        kalan_miktar=kalan_miktar,
        kalan_stok_degeri=toplam_maliyet - smm,
        toplam_stok_miktari=toplam_miktar,
        toplam_stok_maliyeti=toplam_maliyet,
        stok_yerine_koyma_degeri=yk_degeri,
        stok_deger_degisimi=yk_degeri - toplam_maliyet,
        fiyat_artisi_orani=g.yerine_koyma_maliyeti / ortalama - 1.0,
        varsayimlar=[
            "Partiler eskiden yeniye sıralı kabul edilir.",
            "FIFO: ilk alınan mal ilk satılır. Ağırlıklı ortalama: tüm partilerin ortalama birim maliyeti.",
            "Stok değer değişimi muhasebe kârının içindeki 'fiyat artışı kazancı'dır; nakit kazanç değildir.",
        ],
    )
