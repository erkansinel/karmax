"""Toplu (çoklu ürün) analiz ve işletme özeti.

Her ürün Modül 1 ile ayrı ayrı hesaplanır; bu modül yalnızca toplar ve sıralar.
"""

from __future__ import annotations

from pydantic import BaseModel

from .modeller import AnalizParametreleri, UrunGirdisi, UrunSonucu
from .urun_analizi import urun_analiz_et


class TopluOzet(BaseModel):
    urun_sayisi: int
    toplam_ciro: float
    toplam_muhasebe_brut_kari: float
    toplam_ekonomik_sonuc: float
    gizli_fark: float  # muhasebe kârı − ekonomik sonuç
    zarar_eden_urun_sayisi: int
    zarar_eden_urunlerin_toplam_kaybi: float
    en_kotu_urunler: list[str]
    en_iyi_urunler: list[str]


class TopluSonuc(BaseModel):
    ozet: TopluOzet
    sonuclar: list[UrunSonucu]  # toplam ekonomik sonuca göre kötüden iyiye sıralı


def toplu_analiz(urunler: list[UrunGirdisi], p: AnalizParametreleri) -> TopluSonuc:
    sonuclar = sorted((urun_analiz_et(u, p) for u in urunler), key=lambda s: s.toplam_ekonomik_sonuc)
    ciro = sum(u.satis_fiyati * u.satis_miktari for u in urunler)
    muhasebe = sum(s.toplam_muhasebe_brut_kari for s in sonuclar)
    ekonomik = sum(s.toplam_ekonomik_sonuc for s in sonuclar)
    zarar = [s for s in sonuclar if s.toplam_ekonomik_sonuc < 0]
    return TopluSonuc(
        ozet=TopluOzet(
            urun_sayisi=len(sonuclar),
            toplam_ciro=ciro,
            toplam_muhasebe_brut_kari=muhasebe,
            toplam_ekonomik_sonuc=ekonomik,
            gizli_fark=muhasebe - ekonomik,
            zarar_eden_urun_sayisi=len(zarar),
            zarar_eden_urunlerin_toplam_kaybi=sum(s.toplam_ekonomik_sonuc for s in zarar),
            en_kotu_urunler=[s.urun_kodu for s in sonuclar[:5] if s.toplam_ekonomik_sonuc < 0],
            en_iyi_urunler=[s.urun_kodu for s in reversed(sonuclar[-5:]) if s.toplam_ekonomik_sonuc > 0],
        ),
        sonuclar=sonuclar,
    )
