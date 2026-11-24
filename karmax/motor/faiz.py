"""Paranın zaman değeri fonksiyonları.

Bu modül Karmax'ın en alt katmanıdır. Arayüzden, veritabanından ve
web sunucusundan habersizdir; yalnızca sayı alır, sayı döndürür.

Temel kavram: İSKONTO FAKTÖRÜ (DF)
    t gün sonra elde edilecek 1 TL'nin bugünkü değeridir.
    Bugünkü değer  = Gelecekteki tutar × DF(t)
    Gelecekteki değer = Bugünkü tutar ÷ DF(t)

Desteklenen faiz yöntemleri (birbirine karıştırılmaz):
    BASIT    : r nominal yıllık basit faiz.        DF = 1 / (1 + r·t/B)
    BILESIK  : r nominal yıllık, yılda m dönem.    DF = (1 + r/m)^(−m·t/B)
    EFEKTIF  : r efektif (bileşik) yıllık faiz.    DF = (1 + r)^(−t/B)

B gün esasıdır (360 veya 365).

Ticari iskonto (dış iskonto) ayrı bir kavramdır ve ayrı fonksiyondadır;
ürün analizinde KULLANILMAZ.

Oranlar bu modülde ONDALIK verilir (0,40 = %40). Yüzde → ondalık
dönüşümü yalnızca veri modeli katmanında, tek bir yerde yapılır.
"""

from __future__ import annotations

import math
from enum import Enum


class FaizYontemi(str, Enum):
    BASIT = "basit"
    BILESIK = "bilesik"
    EFEKTIF = "efektif"


GECERLI_GUN_ESASLARI = (360, 365)


def _kontrol(oran: float, gun: float, gun_esasi: int, donem: int) -> None:
    if oran < 0:
        raise ValueError("Faiz oranı negatif olamaz.")
    if gun < 0:
        raise ValueError("Gün sayısı negatif olamaz.")
    if gun_esasi not in GECERLI_GUN_ESASLARI:
        raise ValueError("Gün esası 360 veya 365 olmalıdır.")
    if donem < 1:
        raise ValueError("Bileşik dönem sayısı en az 1 olmalıdır.")


def iskonto_faktoru(
    oran: float,
    gun: float,
    yontem: FaizYontemi = FaizYontemi.BASIT,
    gun_esasi: int = 365,
    donem: int = 12,
) -> float:
    """t gün sonraki 1 TL'nin bugünkü değeri."""
    _kontrol(oran, gun, gun_esasi, donem)
    yil = gun / gun_esasi
    if yontem == FaizYontemi.BASIT:
        return 1.0 / (1.0 + oran * yil)
    if yontem == FaizYontemi.BILESIK:
        return (1.0 + oran / donem) ** (-donem * yil)
    if yontem == FaizYontemi.EFEKTIF:
        return (1.0 + oran) ** (-yil)
    raise ValueError(f"Bilinmeyen faiz yöntemi: {yontem}")


def bugunku_deger(tutar: float, oran: float, gun: float, **kw) -> float:
    """t gün sonra alınacak/ödenecek tutarın bugünkü değeri."""
    return tutar * iskonto_faktoru(oran, gun, **kw)


def gelecekteki_deger(tutar: float, oran: float, gun: float, **kw) -> float:
    """Bugünkü tutarın t gün sonraki değeri."""
    return tutar / iskonto_faktoru(oran, gun, **kw)


def efektif_yillik_oran(nominal_oran: float, donem: int) -> float:
    """Yılda `donem` kez bileşen nominal oranın efektif yıllık karşılığı."""
    _kontrol(nominal_oran, 0, 365, donem)
    return (1.0 + nominal_oran / donem) ** donem - 1.0


def ticari_iskonto_tutari(
    nominal_tutar: float, iskonto_orani: float, gun: float, gun_esasi: int = 365
) -> float:
    """Dış (ticari) iskonto: senet kırdırmada bankanın ödediği tutar.

    Ödenen = Nominal × (1 − d·t/B)

    DİKKAT: Bu, faiz oranıyla bugünkü değer hesabı DEĞİLDİR.
    Aynı oran için iç iskontodan (bugunku_deger) her zaman daha düşük sonuç verir.
    """
    _kontrol(iskonto_orani, gun, gun_esasi, 1)
    carpan = 1.0 - iskonto_orani * gun / gun_esasi
    if carpan <= 0:
        raise ValueError("Bu oran ve vadede ticari iskonto tutarı sıfır veya negatif olur.")
    return nominal_tutar * carpan


def tahsilat_gecikmesi_maliyeti(
    tutar: float, oran: float, planlanan_gun: float, gecikme_gun: float, **kw
) -> float:
    """Tahsilatın planlanandan `gecikme_gun` geç gelmesinin bugünkü değer kaybı."""
    if gecikme_gun < 0:
        raise ValueError("Gecikme günü negatif olamaz.")
    return bugunku_deger(tutar, oran, planlanan_gun, **kw) - bugunku_deger(
        tutar, oran, planlanan_gun + gecikme_gun, **kw
    )


def faktore_ulasilan_gun(
    hedef_faktor: float,
    oran: float,
    yontem: FaizYontemi = FaizYontemi.BASIT,
    gun_esasi: int = 365,
    donem: int = 12,
) -> float | None:
    """DF(t) = hedef_faktor eşitliğini sağlayan t gününü bulur (DF'nin tersi).

    Dönüş:
        float  -> gün sayısı
        math.inf -> oran sıfır ve hedef ≤ 1: her vade uygundur (sınırsız)
        None   -> hedef_faktor > 1: peşin bile yetmez (çözüm yok)
    """
    _kontrol(oran, 0, gun_esasi, donem)
    if hedef_faktor <= 0:
        raise ValueError("Hedef faktör pozitif olmalıdır.")
    if hedef_faktor > 1:
        return None
    if oran == 0:
        return math.inf
    if hedef_faktor == 1:
        return 0.0
    if yontem == FaizYontemi.BASIT:
        return (1.0 / hedef_faktor - 1.0) * gun_esasi / oran
    if yontem == FaizYontemi.BILESIK:
        return -gun_esasi * math.log(hedef_faktor) / (donem * math.log(1.0 + oran / donem))
    if yontem == FaizYontemi.EFEKTIF:
        return -gun_esasi * math.log(hedef_faktor) / math.log(1.0 + oran)
    raise ValueError(f"Bilinmeyen faiz yöntemi: {yontem}")


def yillik_esdeger_oran(
    oran: float, yontem: FaizYontemi = FaizYontemi.BASIT, gun_esasi: int = 365, donem: int = 12
) -> float:
    """Seçilen yöntemle 1 yıl (B gün) boyunca paranın maliyeti: 1/DF(B) − 1.

    Basit: r · Bileşik: (1 + r/m)^m − 1 · Efektif: r
    Stok gibi yıl boyunca bağlı kalan tutarların yıllık maliyetinde kullanılır.
    """
    return 1.0 / iskonto_faktoru(oran, gun_esasi, yontem=yontem, gun_esasi=gun_esasi, donem=donem) - 1.0


def ortuk_yillik_oran(
    faktor: float, gun: float, yontem: FaizYontemi = FaizYontemi.BASIT, gun_esasi: int = 365, donem: int = 12
) -> float:
    """DF(gun) = faktor eşitliğini sağlayan yıllık oran (oran cinsinden ters fonksiyon).

    Örnek: "%2 peşin indirim ya da 60 gün vade" teklifinin örtük faizi.
        Basit:   (1/f − 1) · B / t
        Bileşik: m · (f^(−B/(m·t)) − 1)
        Efektif: f^(−B/t) − 1
    """
    if gun <= 0:
        raise ValueError("Örtük oran için gün pozitif olmalıdır.")
    if not (0 < faktor <= 1):
        raise ValueError("Faktör 0 ile 1 arasında olmalıdır.")
    _kontrol(0.0, gun, gun_esasi, donem)
    if yontem == FaizYontemi.BASIT:
        return (1.0 / faktor - 1.0) * gun_esasi / gun
    if yontem == FaizYontemi.BILESIK:
        return donem * (faktor ** (-gun_esasi / (donem * gun)) - 1.0)
    if yontem == FaizYontemi.EFEKTIF:
        return faktor ** (-gun_esasi / gun) - 1.0
    raise ValueError(f"Bilinmeyen faiz yöntemi: {yontem}")
