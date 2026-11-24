"""MODÜL 4 – Stok finansmanı (işletme düzeyi, ileriye dönük).

Soru: "Ortalama olarak ne kadar stok tutuyorum ve bu bana yılda kaça mal oluyor?
Stok günümü değiştirirsem ne kadar nakit serbest kalır?"

Çift sayım notu (Hesaplama Sözleşmesi §4): Bu modül Modül 1'den bağımsızdır.
Modül 1 tek bir satışı satış anında ölçer ve geçmiş bekleme maliyetini düşmez.
Bu modül işletmenin önümüzdeki bir yıl için stokta bağlayacağı paranın
maliyetini ölçer. İki sonuç birbirine EKLENMEZ.

Formüller (B = gün esası):
    Stok devir hızı           = Yıllık SMM ÷ Ortalama stok
    Stokta bekleme günü        = Ortalama stok ÷ Yıllık SMM × B
    Yıllık finansman oranı     = 1 / DF(B) − 1   (seçilen faiz yöntemiyle)
    Yıllık finansman maliyeti  = Ortalama stok × yıllık finansman oranı
    Yıllık taşıma maliyeti     = Ortalama stok × taşıma oranı
    Senaryo stoğu (g gün)      = Yıllık SMM × g ÷ B
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .faiz import yillik_esdeger_oran
from .modeller import AnalizParametreleri


class StokGirdisi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    yillik_satilan_mal_maliyeti: float = Field(..., gt=0, description="Yıllık SMM, bugünkü alış fiyatlarıyla (TL)")
    ortalama_stok_tutari: float = Field(..., ge=0, description="Bugünkü alış fiyatlarıyla ortalama stok (TL)")
    tasima_maliyeti_orani_yuzde: float = Field(0, ge=0, le=100, description="Depo, sigorta, fire: stoğun yıllık %'si")
    alternatif_stok_gunleri: list[int] = Field(
        default_factory=lambda: [15, 30, 45, 60, 90], max_length=20,
        description="Karşılaştırılacak stok günleri",
    )


class StokSenaryosu(BaseModel):
    stok_gunu: float
    ortalama_stok: float
    yillik_finansman_maliyeti: float
    yillik_tasima_maliyeti: float
    toplam_yillik_maliyet: float
    mevcuda_gore_yillik_tasarruf: float
    serbest_kalan_nakit: float
    mevcut_durum: bool


class StokSonucu(BaseModel):
    stok_devir_hizi: float | None
    stokta_bekleme_gunu: float
    yillik_finansman_orani: float
    yillik_finansman_maliyeti: float
    yillik_tasima_maliyeti: float
    toplam_yillik_maliyet: float
    gunluk_stok_maliyeti: float = Field(description="Bir günlük stok tutmanın yıllık maliyeti")
    senaryolar: list[StokSenaryosu]
    varsayimlar: list[str]


def stok_analiz_et(g: StokGirdisi, p: AnalizParametreleri) -> StokSonucu:
    B = p.gun_esasi
    f = yillik_esdeger_oran(p.oran, **_kw(p))
    t = g.tasima_maliyeti_orani_yuzde / 100.0
    smm, stok = g.yillik_satilan_mal_maliyeti, g.ortalama_stok_tutari

    mevcut_gun = stok / smm * B
    mevcut_maliyet = stok * (f + t)

    def senaryo(gun: float, mevcut: bool) -> StokSenaryosu:
        s = smm * gun / B
        fin, tas = s * f, s * t
        return StokSenaryosu(
            stok_gunu=gun, ortalama_stok=s, yillik_finansman_maliyeti=fin, yillik_tasima_maliyeti=tas,
            toplam_yillik_maliyet=fin + tas, mevcuda_gore_yillik_tasarruf=mevcut_maliyet - (fin + tas),
            serbest_kalan_nakit=stok - s, mevcut_durum=mevcut,
        )

    gunler = sorted({float(x) for x in g.alternatif_stok_gunleri if x >= 0})
    senaryolar = [senaryo(x, False) for x in gunler if abs(x - mevcut_gun) > 1e-9]
    senaryolar.append(senaryo(mevcut_gun, True))
    senaryolar.sort(key=lambda s: s.stok_gunu)

    return StokSonucu(
        stok_devir_hizi=(smm / stok) if stok > 0 else None,
        stokta_bekleme_gunu=mevcut_gun,
        yillik_finansman_orani=f,
        yillik_finansman_maliyeti=stok * f,
        yillik_tasima_maliyeti=stok * t,
        toplam_yillik_maliyet=mevcut_maliyet,
        gunluk_stok_maliyeti=smm / B * (f + t),
        senaryolar=senaryolar,
        varsayimlar=[
            "Stok ve SMM bugünkü alış fiyatlarıyla girilir.",
            f"Yıllık finansman oranı seçilen yönteme göre %{f * 100:.2f} (1 yıl = {B} gün).".replace(".", ",", 1),
            "Satışların yıl içinde düzenli dağıldığı varsayılır.",
            "Bu sonuç ürün analizindeki ekonomik sonuca eklenmez; işletme düzeyinde ayrı bir maliyettir.",
        ],
    )


def _kw(p: AnalizParametreleri) -> dict:
    return p.faiz_argumanlari()
