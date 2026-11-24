"""Hesaplama motorunun veri modeli (girdi ve çıktı).

Birim kuralları (Hesaplama Sözleşmesi §2):
  * Tüm tutarlar BİRİM başına, TL, KDV HARİÇ girilir.
  * Oranlar YÜZDE olarak girilir: 40 = %40. Ondalığa çevirme yalnızca burada yapılır.
  * Günler takvim günüdür, tam sayıdır.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .faiz import FaizYontemi

MOTOR_SURUMU = "1.0.0"


class AnalizParametreleri(BaseModel):
    """İşletme geneli için tek finansman varsayımı."""

    model_config = ConfigDict(extra="forbid")

    yillik_oran_yuzde: float = Field(
        ..., ge=0, le=1000,
        description="Paranın yıllık maliyeti (sermaye maliyeti), yüzde. 40 = %40.",
    )
    faiz_yontemi: FaizYontemi = Field(FaizYontemi.BASIT)
    gun_esasi: Literal[360, 365] = Field(365, description="360 veya 365.")
    bilesik_donem: int = Field(12, ge=1, le=365, description="Yalnızca bileşik yöntemde: yılda kaç dönem.")

    @property
    def oran(self) -> float:
        return self.yillik_oran_yuzde / 100.0

    def faiz_argumanlari(self) -> dict:
        return {"yontem": self.faiz_yontemi, "gun_esasi": self.gun_esasi, "donem": self.bilesik_donem}


class UrunGirdisi(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    urun_kodu: str = Field(..., min_length=1, max_length=64)
    urun_adi: str = Field("", max_length=200)
    ilk_alis_maliyeti: float = Field(..., gt=0, description="Stoktaki malın geçmiş alış maliyeti (birim).")
    yerine_koyma_maliyeti: float = Field(..., gt=0, description="Aynı malı bugün yeniden almanın maliyeti (birim).")
    satis_fiyati: float = Field(..., gt=0, description="Birim satış fiyatı, KDV hariç.")
    satis_miktari: float = Field(1, gt=0)
    tahsilat_vadesi_gun: int = Field(0, ge=0, le=3650, description="Müşteriden tahsilat günü.")
    tedarikci_vadesi_gun: int = Field(0, ge=0, le=3650, description="Yerine koyma alımının ödeme günü.")
    ek_gider_birim: float = Field(0, ge=0, description="Satışa bağlı ek gider (nakliye, komisyon…), bugün ödenir.")
    hedef_kar_orani_yuzde: float = Field(30, ge=0, le=1000, description="Maliyetin bugünkü değeri üzerinden hedef kâr oranı.")


class KopruAdimi(BaseModel):
    """Muhasebe kârından ekonomik sonuca giden şelale adımı."""

    ad: str
    tutar: float
    aciklama: str


class UrunSonucu(BaseModel):
    urun_kodu: str
    urun_adi: str

    # Muhasebe bakışı (geçmiş maliyet, zaman değeri yok)
    muhasebe_brut_kari: float
    kar_orani_maliyet_uzerinden: float = Field(description="Brüt kâr ÷ ilk alış maliyeti (markup).")
    brut_kar_marji_satis_uzerinden: float = Field(description="Brüt kâr ÷ satış fiyatı (marj).")

    # Yerine koyma bakışı (bugünkü maliyet, zaman değeri yok)
    yerine_koyma_kari: float = Field(description="Satış fiyatı − yerine koyma maliyeti.")

    # Zaman değeri
    tahsilat_bugunku_degeri: float
    yerine_koyma_bugunku_degeri: float
    vade_maliyeti: float = Field(description="Satış fiyatı − tahsilatın bugünkü değeri.")
    tedarikci_vadesi_kazanci: float = Field(description="Yerine koyma maliyeti − ödemenin bugünkü değeri.")
    maliyetin_bugunku_degeri: float = Field(description="Yerine koyma ödemesinin bugünkü değeri + ek gider.")

    # Sonuç
    ekonomik_sonuc: float
    ekonomik_kar_orani: float = Field(description="Ekonomik sonuç ÷ maliyetin bugünkü değeri.")

    # Karar destek
    basabas_satis_fiyati: float
    hedef_satis_fiyati: float
    maksimum_vade_gun: float | None = Field(
        description="Ekonomik sonucu sıfırlayan tahsilat günü. Durum 'sinirli' değilse None."
    )
    maksimum_vade_durumu: str = Field(description="sinirli | sinirsiz | pesin_bile_zarar")

    # Toplamlar (birim × miktar)
    satis_miktari: float
    toplam_muhasebe_brut_kari: float
    toplam_ekonomik_sonuc: float

    kopru: list[KopruAdimi]
    varsayimlar: list[str]
    motor_surumu: str = MOTOR_SURUMU
