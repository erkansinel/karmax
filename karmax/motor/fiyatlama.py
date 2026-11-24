"""MODÜL 6 – Fiyatlama simülasyonu ve MODÜL 7 – Tahsilat riski.

Modül 6 yeni formül yazmaz: her senaryo Modül 1 ile hesaplanır. Ek olarak
"peşin fiyata eşdeğer vadeli fiyat" verilir:

    Eşdeğer vadeli fiyat(g) = Peşin fiyat ÷ DF(g)

Bu fiyattan g gün vadeyle satmak, peşin satışla aynı ekonomik sonucu verir.

Modül 7 (beklenen değer yaklaşımı):
    p = ödeme olasılığı, d = beklenen gecikme günü
    Beklenen tahsilat BD'si   = p · P · DF(t + d)
    Riskli ekonomik sonuç     = Beklenen tahsilat BD'si − Maliyetin BD'si
    Risk maliyeti             = Modül 1 ekonomik sonucu − Riskli ekonomik sonuç
    Riskli başabaş fiyatı     = Maliyetin BD'si ÷ (p · DF(t + d))
p = %100 ve d = 0 iken sonuçlar Modül 1 ile aynıdır.
Varsayım: ödenmeyen alacaktan hiçbir şey tahsil edilemez (kısmi tahsilat ve
hukuki takip masrafı dahil değildir).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .faiz import iskonto_faktoru
from .modeller import AnalizParametreleri, UrunGirdisi
from .urun_analizi import urun_analiz_et


class FiyatSenaryosu(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ad: str = Field(..., min_length=1, max_length=60)
    satis_fiyati: float = Field(..., gt=0)
    tahsilat_vadesi_gun: int = Field(..., ge=0, le=3650)


class TahsilatRiski(BaseModel):
    model_config = ConfigDict(extra="forbid")

    odeme_olasiligi_yuzde: float = Field(100, gt=0, le=100)
    beklenen_gecikme_gun: int = Field(0, ge=0, le=3650)


class FiyatlamaGirdisi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urun: UrunGirdisi
    senaryolar: list[FiyatSenaryosu] = Field(default_factory=list, max_length=12)
    risk: TahsilatRiski = Field(default_factory=TahsilatRiski)


class SenaryoSonucu(BaseModel):
    ad: str
    satis_fiyati: float
    tahsilat_vadesi_gun: int
    tahsilat_bugunku_degeri: float
    vade_maliyeti: float
    ekonomik_sonuc: float
    ekonomik_kar_orani: float
    pesine_esdeger_vadeli_fiyat: float = Field(description="Peşin fiyatla aynı sonucu veren vadeli fiyat")
    gerekli_vade_farki_orani: float = Field(description="Eşdeğer vadeli fiyat ÷ peşin fiyat − 1")
    riskli_ekonomik_sonuc: float
    risk_maliyeti: float
    riskli_basabas_fiyati: float


class FiyatlamaSonucu(BaseModel):
    pesin_referans_fiyati: float
    senaryolar: list[SenaryoSonucu]
    en_iyi_senaryo: str
    risk: TahsilatRiski
    varsayimlar: list[str]


def varsayilan_senaryolar(fiyat: float) -> list[FiyatSenaryosu]:
    return [
        FiyatSenaryosu(ad="Peşin", satis_fiyati=fiyat, tahsilat_vadesi_gun=0),
        FiyatSenaryosu(ad="30 gün", satis_fiyati=fiyat, tahsilat_vadesi_gun=30),
        FiyatSenaryosu(ad="60 gün", satis_fiyati=fiyat, tahsilat_vadesi_gun=60),
        FiyatSenaryosu(ad="90 gün", satis_fiyati=fiyat, tahsilat_vadesi_gun=90),
    ]


def riskli_sonuc(urun: UrunGirdisi, p: AnalizParametreleri, risk: TahsilatRiski) -> dict:
    """Modül 7: tek bir ürün/senaryo için tahsilat riskli sonuç."""
    s = urun_analiz_et(urun, p)
    olas = risk.odeme_olasiligi_yuzde / 100.0
    df = iskonto_faktoru(p.oran, urun.tahsilat_vadesi_gun + risk.beklenen_gecikme_gun, **p.faiz_argumanlari())
    beklenen_bd = olas * urun.satis_fiyati * df
    riskli = beklenen_bd - s.maliyetin_bugunku_degeri
    return {
        "analiz": s,
        "beklenen_tahsilat_bugunku_degeri": beklenen_bd,
        "riskli_ekonomik_sonuc": riskli,
        "risk_maliyeti": s.ekonomik_sonuc - riskli,
        "riskli_basabas_fiyati": s.maliyetin_bugunku_degeri / (olas * df),
    }


def fiyat_senaryolari(g: FiyatlamaGirdisi, p: AnalizParametreleri) -> FiyatlamaSonucu:
    senaryolar = g.senaryolar or varsayilan_senaryolar(g.urun.satis_fiyati)
    adlar = [s.ad for s in senaryolar]
    if len(set(adlar)) != len(adlar):
        raise ValueError("Senaryo adları birbirinden farklı olmalı.")
    pesin = g.urun.satis_fiyati
    kw = p.faiz_argumanlari()
    sonuclar = []
    for sen in senaryolar:
        u = g.urun.model_copy(update={"satis_fiyati": sen.satis_fiyati, "tahsilat_vadesi_gun": sen.tahsilat_vadesi_gun})
        r = riskli_sonuc(u, p, g.risk)
        s = r["analiz"]
        esdeger = pesin / iskonto_faktoru(p.oran, sen.tahsilat_vadesi_gun, **kw)
        sonuclar.append(SenaryoSonucu(
            ad=sen.ad, satis_fiyati=sen.satis_fiyati, tahsilat_vadesi_gun=sen.tahsilat_vadesi_gun,
            tahsilat_bugunku_degeri=s.tahsilat_bugunku_degeri, vade_maliyeti=s.vade_maliyeti,
            ekonomik_sonuc=s.ekonomik_sonuc, ekonomik_kar_orani=s.ekonomik_kar_orani,
            pesine_esdeger_vadeli_fiyat=esdeger, gerekli_vade_farki_orani=esdeger / pesin - 1.0,
            riskli_ekonomik_sonuc=r["riskli_ekonomik_sonuc"], risk_maliyeti=r["risk_maliyeti"],
            riskli_basabas_fiyati=r["riskli_basabas_fiyati"],
        ))
    risk_var = g.risk.odeme_olasiligi_yuzde < 100 or g.risk.beklenen_gecikme_gun > 0
    anahtar = (lambda s: s.riskli_ekonomik_sonuc) if risk_var else (lambda s: s.ekonomik_sonuc)
    return FiyatlamaSonucu(
        pesin_referans_fiyati=pesin,
        senaryolar=sonuclar,
        en_iyi_senaryo=max(sonuclar, key=anahtar).ad,
        risk=g.risk,
        varsayimlar=[
            "Her senaryo ürün analiziyle (Modül 1) aynı formülle hesaplanır.",
            f"Peşine eşdeğer vadeli fiyat, ürün formundaki {pesin:g} TL peşin fiyat referans alınarak hesaplanır.",
            f"Tahsilat riski: ödeme olasılığı %{g.risk.odeme_olasiligi_yuzde:g}, "
            f"beklenen gecikme {g.risk.beklenen_gecikme_gun} gün.",
            "Ödenmeyen alacaktan hiçbir şey tahsil edilemeyeceği varsayılır; hukuki takip masrafı dahil değildir.",
            "En iyi senaryo" + (" riskli ekonomik sonuca" if risk_var else " ekonomik sonuca") + " göre seçilir.",
        ],
    )
