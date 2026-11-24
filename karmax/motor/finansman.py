"""MODÜL 5 – Borç ve finansman analizi.

1. Erken ödeme iskontosu: "%2 peşin indirim ya da 60 gün vade" teklifinde
   peşin ödemek mi, vadeyi kullanmak mı daha ucuz? Teklifin örtük yıllık faizi.
2. Finansman alternatifleri: tek ödemeli ve eşit taksitli kredilerin ödeme planı,
   efektif yıllık maliyeti (iç verim oranı) ve işletmenin paranın maliyetine göre
   bugünkü değer maliyeti.
3. Faiz duyarlılığı: işletmenin paranın maliyeti değişirse alternatiflerin sıralaması.

Varsayımlar: 1 ay = 30 gün. BSMV/KKDF gibi vergiler faiz oranına dahil edilmelidir.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .faiz import FaizYontemi, iskonto_faktoru, ortuk_yillik_oran
from .modeller import AnalizParametreleri

AY_GUN = 30


# ---------------------------------------------------------------- erken ödeme

class ErkenOdemeGirdisi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fatura_tutari: float = Field(..., gt=0)
    iskonto_yuzde: float = Field(..., ge=0, lt=100, description="Peşin ödemede yapılan indirim, %")
    vade_gun: int = Field(..., gt=0, le=3650, description="İndirim kullanılmazsa ödeme günü")


class ErkenOdemeSonucu(BaseModel):
    pesin_odeme: float
    vadeli_odemenin_bugunku_degeri: float
    pesin_odemenin_kazanci: float = Field(description="Pozitifse peşin ödemek daha ucuz")
    ortuk_yillik_oran: float = Field(description="Teklifin seçilen faiz yöntemiyle örtük yıllık oranı")
    ortuk_efektif_yillik_oran: float
    karar: str
    varsayimlar: list[str]


def erken_odeme_analiz_et(g: ErkenOdemeGirdisi, p: AnalizParametreleri) -> ErkenOdemeSonucu:
    kw = p.faiz_argumanlari()
    d = g.iskonto_yuzde / 100.0
    pesin = g.fatura_tutari * (1.0 - d)
    vadeli_bd = g.fatura_tutari * iskonto_faktoru(p.oran, g.vade_gun, **kw)
    kazanc = vadeli_bd - pesin
    faktor = 1.0 - d
    ortuk = ortuk_yillik_oran(faktor, g.vade_gun, **kw) if d > 0 else 0.0
    ortuk_efektif = ortuk_yillik_oran(faktor, g.vade_gun, yontem=FaizYontemi.EFEKTIF, gun_esasi=p.gun_esasi) if d > 0 else 0.0
    if abs(kazanc) < 0.005:
        karar = "İki seçenek aynı maliyette."
    elif kazanc > 0:
        karar = "Peşin öde: indirim, paranın maliyetinden daha yüksek bir getiri sağlıyor."
    else:
        karar = "Vadeyi kullan: indirim, paranın maliyetini karşılamıyor."
    return ErkenOdemeSonucu(
        pesin_odeme=pesin,
        vadeli_odemenin_bugunku_degeri=vadeli_bd,
        pesin_odemenin_kazanci=kazanc,
        ortuk_yillik_oran=ortuk,
        ortuk_efektif_yillik_oran=ortuk_efektif,
        karar=karar,
        varsayimlar=[
            f"Paranın maliyeti yıllık %{p.yillik_oran_yuzde:g} ({p.faiz_yontemi.value}, {p.gun_esasi} gün).",
            "Peşin ödeme bugün, vadeli ödeme vade gününde yapılır.",
            "Örtük oran: indirimi kullanmamanın yıllık faiz karşılığıdır.",
        ],
    )


# ------------------------------------------------------ finansman alternatifleri

class KrediTuru(str, Enum):
    TEK_ODEMELI = "tek_odemeli"
    ESIT_TAKSITLI = "esit_taksitli"


class FinansmanAlternatifi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ad: str = Field(..., min_length=1, max_length=80)
    tur: KrediTuru
    kullanilan_tutar: float = Field(..., gt=0)
    yillik_faiz_yuzde: float = Field(..., ge=0, le=1000, description="Kredinin yıllık nominal faizi (aylık × 12)")
    vade_ay: int = Field(..., ge=1, le=120)
    pesin_masraf: float = Field(0, ge=0, description="Dosya masrafı, komisyon vb. (kredi açılışında)")


class OdemeSatiri(BaseModel):
    donem: int
    gun: int
    odeme: float
    faiz: float
    anapara: float
    kalan_anapara: float


class AlternatifSonucu(BaseModel):
    ad: str
    tur: KrediTuru
    net_kullanilan: float
    toplam_geri_odeme: float
    toplam_faiz_ve_masraf: float
    efektif_yillik_maliyet: float = Field(description="İç verim oranı, efektif yıllık")
    odemelerin_bugunku_degeri: float
    bugunku_deger_maliyeti: float = Field(
        description="Ödemelerin BD'si − net kullanılan. Negatifse kredi, paranın maliyetinden ucuz."
    )
    odeme_plani: list[OdemeSatiri]


class FinansmanGirdisi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alternatifler: list[FinansmanAlternatifi] = Field(..., min_length=1, max_length=10)
    duyarlilik_oranlari_yuzde: list[float] = Field(default_factory=list, max_length=20)


class DuyarlilikSatiri(BaseModel):
    yillik_oran_yuzde: float
    bugunku_deger_maliyetleri: dict[str, float]
    en_ucuz: str


class FinansmanSonucu(BaseModel):
    alternatifler: list[AlternatifSonucu]
    en_dusuk_efektif_maliyet: str
    en_dusuk_bugunku_deger_maliyeti: str
    duyarlilik: list[DuyarlilikSatiri]
    varsayimlar: list[str]


def odeme_plani(a: FinansmanAlternatifi) -> list[OdemeSatiri]:
    L, n = a.kullanilan_tutar, a.vade_ay
    i = a.yillik_faiz_yuzde / 100.0 / 12.0
    if a.tur == KrediTuru.TEK_ODEMELI:
        faiz = L * i * n  # basit faiz, vade sonunda tek ödeme
        return [OdemeSatiri(donem=1, gun=n * AY_GUN, odeme=L + faiz, faiz=faiz, anapara=L, kalan_anapara=0.0)]
    taksit = L / n if i == 0 else L * i / (1.0 - (1.0 + i) ** (-n))
    plan, kalan = [], L
    for k in range(1, n + 1):
        faiz = kalan * i
        anapara = taksit - faiz
        kalan -= anapara
        plan.append(OdemeSatiri(donem=k, gun=k * AY_GUN, odeme=taksit, faiz=faiz, anapara=anapara,
                                kalan_anapara=max(kalan, 0.0) if abs(kalan) > 1e-7 else 0.0))
    return plan


def _npv_efektif(net: float, plan: list[OdemeSatiri], r: float, B: int) -> float:
    return net - sum(s.odeme * (1.0 + r) ** (-s.gun / B) for s in plan)


def ic_verim_orani(net: float, plan: list[OdemeSatiri], gun_esasi: int) -> float:
    """net = Σ ödeme·(1+r)^(−t/B) eşitliğini sağlayan efektif yıllık r (ikiye bölme yöntemi)."""
    alt, ust = -0.99, 1.0
    while _npv_efektif(net, plan, ust, gun_esasi) < 0:
        ust *= 2
        if ust > 1e6:
            raise ValueError("İç verim oranı bulunamadı.")
    # f(r) = net − BD(ödemeler) r ile artar: f(alt) < 0 < f(ust)
    if _npv_efektif(net, plan, alt, gun_esasi) > 0:
        raise ValueError("Ödemeler kullanılan tutardan az; maliyet negatif.")
    for _ in range(200):
        orta = (alt + ust) / 2
        if _npv_efektif(net, plan, orta, gun_esasi) < 0:
            alt = orta
        else:
            ust = orta
        if ust - alt < 1e-12:
            break
    return (alt + ust) / 2


def _alternatif_analiz(a: FinansmanAlternatifi, p: AnalizParametreleri, oran: float) -> AlternatifSonucu:
    plan = odeme_plani(a)
    net = a.kullanilan_tutar - a.pesin_masraf
    if net <= 0:
        raise ValueError(f"'{a.ad}': peşin masraf kullanılan tutara eşit veya fazla.")
    kw = p.faiz_argumanlari()
    bd = sum(s.odeme * iskonto_faktoru(oran, s.gun, **kw) for s in plan)
    toplam = sum(s.odeme for s in plan)
    return AlternatifSonucu(
        ad=a.ad, tur=a.tur, net_kullanilan=net, toplam_geri_odeme=toplam,
        toplam_faiz_ve_masraf=toplam - a.kullanilan_tutar + a.pesin_masraf,
        efektif_yillik_maliyet=ic_verim_orani(net, plan, p.gun_esasi),
        odemelerin_bugunku_degeri=bd, bugunku_deger_maliyeti=bd - net, odeme_plani=plan,
    )


def finansman_karsilastir(g: FinansmanGirdisi, p: AnalizParametreleri) -> FinansmanSonucu:
    adlar = [a.ad for a in g.alternatifler]
    if len(set(adlar)) != len(adlar):
        raise ValueError("Her finansman alternatifinin adı farklı olmalı.")
    sonuclar = [_alternatif_analiz(a, p, p.oran) for a in g.alternatifler]

    oranlar = g.duyarlilik_oranlari_yuzde or sorted(
        {max(0.0, p.yillik_oran_yuzde + d) for d in (-20, -10, 0, 10, 20)}
    )
    duyarlilik = []
    for o in sorted({float(x) for x in oranlar if x >= 0}):
        maliyetler = {a.ad: _alternatif_analiz(a, p, o / 100.0).bugunku_deger_maliyeti for a in g.alternatifler}
        duyarlilik.append(DuyarlilikSatiri(yillik_oran_yuzde=o, bugunku_deger_maliyetleri=maliyetler,
                                           en_ucuz=min(maliyetler, key=maliyetler.get)))

    return FinansmanSonucu(
        alternatifler=sonuclar,
        en_dusuk_efektif_maliyet=min(sonuclar, key=lambda s: s.efektif_yillik_maliyet).ad,
        en_dusuk_bugunku_deger_maliyeti=min(sonuclar, key=lambda s: s.bugunku_deger_maliyeti).ad,
        duyarlilik=duyarlilik,
        varsayimlar=[
            "1 ay = 30 gün. Eşit taksitli kredide aylık faiz = yıllık nominal ÷ 12.",
            "Tek ödemeli kredide faiz basit hesaplanır ve vade sonunda anaparayla ödenir.",
            "Peşin masraflar kredi açılışında kullanılan tutardan düşülür.",
            "BSMV, KKDF gibi vergiler kredinin faiz oranına dahil edilmelidir.",
            "Efektif yıllık maliyet, net kullanılan tutar ile ödemeleri eşitleyen iç verim oranıdır.",
            "Bugünkü değer maliyeti işletmenin paranın maliyetiyle hesaplanır; "
            "negatif değer kredinin bu maliyetten ucuz olduğunu gösterir.",
        ],
    )

