"""Plotly grafik tanımları (sunum katmanı).

Bu modül hesap YAPMAZ. Motorun ürettiği sonuç ve eğri verilerini
Plotly figürlerine çevirir. Tarayıcı bu JSON'u plotly.js ile yalnızca çizer.
"""

from __future__ import annotations

import json

import plotly.graph_objects as go

from karmax.motor.egriler import FiyatNoktasi, VadeNoktasi
from karmax.motor.modeller import UrunSonucu

# Decisora renkleri
LACIVERT = "#3f4d6e"
ARDUVAZ = "#7d86a6"
NANE_KOYU = "#2f8f7f"
NANE = "#9edcd0"
KAYIP = "#c0444a"
KAYIP_ZEMIN = "rgba(192, 68, 74, 0.08)"
CIZGI = "#e2e5ec"
YAZI = "#1f2638"
YAZI_2 = "#5a6380"

TL = ",.2f"


def _tl(deger: float, isaretli: bool = False) -> str:
    """Sayıyı Türkçe biçimde yazar: 1.234,56 TL (yalnızca biçimlendirme)."""
    metin = f"{deger:+,.2f}" if isaretli else f"{deger:,.2f}"
    return metin.replace(",", "X").replace(".", ",").replace("X", ".") + " TL"


def _ortak_yerlesim(baslik_x: str, baslik_y: str) -> dict:
    return dict(
        template=go.layout.Template(),  # Plotly'nin varsayılan teması yerine yalnızca Decisora stilleri
        separators=",.",  # Türkçe: ondalık virgül, binlik nokta
        font=dict(family="Montserrat, Segoe UI, system-ui, sans-serif", size=13, color=YAZI),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=64, r=20, t=16, b=56),
        height=340,
        hovermode="closest",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=CIZGI, font=dict(color=YAZI)),
        showlegend=False,
        xaxis=dict(title=dict(text=baslik_x, font=dict(color=YAZI_2, size=12)), gridcolor=CIZGI, zeroline=False,
                   linecolor=CIZGI, tickfont=dict(color=YAZI_2)),
        yaxis=dict(title=dict(text=baslik_y, font=dict(color=YAZI_2, size=12)), gridcolor=CIZGI, zeroline=False,
                   tickfont=dict(color=YAZI_2), tickformat=",.0f"),
    )


def _json(fig: go.Figure) -> dict:
    """Plotly'nin kendi kodlayıcısıyla JSON'a çevirir (NaN/sonsuz yazmaz)."""
    return json.loads(fig.to_json())


def selale_grafigi(sonuc: UrunSonucu) -> dict:
    adimlar = [sonuc.kopru[0]] + [a for a in sonuc.kopru[1:] if abs(a.tutar) > 1e-9]
    x = [a.ad for a in adimlar] + ["Ekonomik sonuç"]
    y = [a.tutar for a in adimlar] + [0]
    olcu = ["absolute"] + ["relative"] * (len(adimlar) - 1) + ["total"]
    aciklama = [a.aciklama for a in adimlar] + ["Tahsilatın bugünkü değeri − maliyetin bugünkü değeri"]
    metin = [_tl(v, isaretli=True) for v in y[:-1]] + [_tl(sonuc.ekonomik_sonuc, isaretli=True)]

    fig = go.Figure(
        go.Waterfall(
            x=x, y=y, measure=olcu, text=metin, textposition="outside", customdata=aciklama,
            textfont=dict(color=YAZI, size=12),
            connector=dict(line=dict(color=ARDUVAZ, width=1, dash="dot")),
            increasing=dict(marker=dict(color=NANE_KOYU)),
            decreasing=dict(marker=dict(color=KAYIP)),
            totals=dict(marker=dict(color=LACIVERT)),
            hovertemplate="<b>%{x}</b><br>%{text}<br>%{customdata}<extra></extra>",
        )
    )
    fig.update_layout(**_ortak_yerlesim("", "TL (birim)"))
    fig.add_hline(y=0, line=dict(color=YAZI_2, width=1))
    # Etiketler kesilmesin diye y ekseninde pay bırak
    seviyeler, toplam = [], 0.0
    for a in adimlar:
        toplam = a.tutar if a is adimlar[0] else toplam + a.tutar
        seviyeler.append(toplam)
    alt, ust = min(seviyeler + [0.0]), max(seviyeler + [0.0])
    pay = (ust - alt) * 0.15 or 1.0
    fig.update_yaxes(range=[alt - pay, ust + pay])
    return _json(fig)


def vade_grafigi(sonuc: UrunSonucu, noktalar: list[VadeNoktasi], tahsilat_gun: int) -> dict:
    gunler = [n.gun for n in noktalar]
    bd = [n.tahsilat_bugunku_degeri for n in noktalar]
    eko = [n.ekonomik_sonuc for n in noktalar]
    son_gun = gunler[-1]
    M = sonuc.maliyetin_bugunku_degeri

    fig = go.Figure()
    if sonuc.maksimum_vade_durumu == "pesin_bile_zarar":
        fig.add_vrect(x0=0, x1=son_gun, fillcolor=KAYIP_ZEMIN, line_width=0)
    elif sonuc.maksimum_vade_durumu == "sinirli" and sonuc.maksimum_vade_gun < son_gun:
        fig.add_vrect(x0=sonuc.maksimum_vade_gun, x1=son_gun, fillcolor=KAYIP_ZEMIN, line_width=0,
                      annotation_text="zarar bölgesi", annotation_position="top right",
                      annotation_font=dict(color=KAYIP, size=12))
    fig.add_trace(go.Scatter(
        x=[0, son_gun], y=[M, M], mode="lines", line=dict(color=YAZI_2, width=1.5, dash="dash"),
        name="Maliyetin bugünkü değeri", hovertemplate=f"Maliyetin bugünkü değeri: %{{y:{TL}}} TL<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=gunler, y=bd, customdata=eko, mode="lines", line=dict(color=LACIVERT, width=2.5),
        name="Tahsilatın bugünkü değeri",
        hovertemplate=(f"<b>%{{x}} gün vade</b><br>Tahsilatın bugünkü değeri: %{{y:{TL}}} TL"
                       f"<br>Ekonomik sonuç: %{{customdata:+{TL}}} TL<extra></extra>"),
    ))
    if sonuc.maksimum_vade_durumu == "sinirli" and sonuc.maksimum_vade_gun <= son_gun:
        fig.add_trace(go.Scatter(
            x=[sonuc.maksimum_vade_gun], y=[M], mode="markers+text",
            marker=dict(size=11, color="#ffffff", line=dict(color=YAZI, width=2)),
            text=[f"başabaş: {sonuc.maksimum_vade_gun:.0f} gün"],
            textposition="top left" if sonuc.tahsilat_bugunku_degeri < M else "bottom left",
            textfont=dict(color=YAZI, size=12),
            hovertemplate=f"En uzun vade: %{{x:,.1f}} gün<extra></extra>",
        ))
    renk = NANE_KOYU if sonuc.ekonomik_sonuc >= 0 else KAYIP
    fig.add_trace(go.Scatter(
        x=[tahsilat_gun], y=[sonuc.tahsilat_bugunku_degeri], mode="markers+text",
        marker=dict(size=12, color=renk, line=dict(color="#ffffff", width=2)),
        text=[f"senin vaden: {tahsilat_gun} gün"],
        textposition="bottom right" if sonuc.tahsilat_bugunku_degeri < M else "top right",
        textfont=dict(color=YAZI, size=12),
        hovertemplate=f"Senin vaden: %{{x}} gün<br>Bugünkü değer: %{{y:{TL}}} TL<extra></extra>",
    ))
    fig.update_layout(**_ortak_yerlesim("Müşteri tahsilat vadesi (gün)", "TL (birim)"))
    fig.update_xaxes(range=[0, son_gun])
    return _json(fig)


def _nokta(noktalar: list[FiyatNoktasi], fiyat: float) -> FiyatNoktasi:
    """Motorun ürettiği eğriden verilen fiyattaki noktayı bulur (hesap yapmaz)."""
    return min(noktalar, key=lambda n: abs(n.satis_fiyati - fiyat))


def fiyat_grafigi(sonuc: UrunSonucu, noktalar: list[FiyatNoktasi], mevcut_fiyat: float) -> dict:
    x = [n.satis_fiyati for n in noktalar]
    y = [n.ekonomik_sonuc for n in noktalar]
    fig = go.Figure()
    fig.add_hrect(y0=min(y + [0]), y1=0, fillcolor=KAYIP_ZEMIN, line_width=0)
    fig.add_hline(y=0, line=dict(color=YAZI_2, width=1))
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines", line=dict(color=LACIVERT, width=2.5),
        hovertemplate=f"Satış fiyatı: %{{x:{TL}}} TL<br>Ekonomik sonuç: %{{y:+{TL}}} TL<extra></extra>",
    ))
    basabas = _nokta(noktalar, sonuc.basabas_satis_fiyati)
    hedef = _nokta(noktalar, sonuc.hedef_satis_fiyati)
    for n, ad, dolgu, kenar, konum in [
        (basabas, "başabaş", "#ffffff", YAZI, "bottom right"),
        (hedef, "hedef", NANE, NANE_KOYU, "top left"),
    ]:
        fig.add_trace(go.Scatter(
            x=[n.satis_fiyati], y=[n.ekonomik_sonuc], mode="markers+text",
            marker=dict(size=11, color=dolgu, line=dict(color=kenar, width=2)),
            text=[f"{ad}: {_tl(n.satis_fiyati)}"], textposition=konum, textfont=dict(color=YAZI, size=12),
            hovertemplate=f"{ad.capitalize()}: %{{x:{TL}}} TL<br>Ekonomik sonuç: %{{y:+{TL}}} TL<extra></extra>",
        ))
    renk = NANE_KOYU if sonuc.ekonomik_sonuc >= 0 else KAYIP
    fig.add_trace(go.Scatter(
        x=[mevcut_fiyat], y=[sonuc.ekonomik_sonuc], mode="markers+text",
        marker=dict(size=12, color=renk, line=dict(color="#ffffff", width=2)),
        text=["senin fiyatın"], textposition="bottom right" if sonuc.ekonomik_sonuc >= 0 else "top left",
        textfont=dict(color=YAZI, size=12),
        hovertemplate=f"Senin fiyatın: %{{x:{TL}}} TL<br>Ekonomik sonuç: %{{y:+{TL}}} TL<extra></extra>",
    ))
    fig.update_layout(**_ortak_yerlesim("Satış fiyatı (TL, KDV hariç)", "Ekonomik sonuç (TL, birim)"))
    fig.update_xaxes(range=[x[0], x[-1]], tickformat=",.0f")
    return _json(fig)


def grafik_paketi(urun, parametreler, sonuc: UrunSonucu) -> dict:
    """Bir ürün analizi için üç grafiği birlikte üretir."""
    from karmax.motor.egriler import fiyat_araligi, fiyat_egrisi, vade_egrisi, vade_ekseni_ust_siniri

    ust_gun = vade_ekseni_ust_siniri(sonuc, urun.tahsilat_vadesi_gun)
    alt_f, ust_f = fiyat_araligi(sonuc, urun.satis_fiyati)
    fiyat_noktalari = fiyat_egrisi(
        urun, parametreler, alt_f, ust_f,
        ek_fiyatlar=(sonuc.basabas_satis_fiyati, sonuc.hedef_satis_fiyati, urun.satis_fiyati),
    )
    return {
        "selale": selale_grafigi(sonuc),
        "vade": vade_grafigi(sonuc, vade_egrisi(urun, parametreler, ust_gun), urun.tahsilat_vadesi_gun),
        "fiyat": fiyat_grafigi(sonuc, fiyat_noktalari, urun.satis_fiyati),
    }


# ----------------------------------------------------------------- Faz 4–6

def karsilastirma_grafigi(sonuclar: list[UrunSonucu], en_fazla: int = 25) -> dict:
    """Ürün bazında toplam muhasebe kârı ile toplam ekonomik sonuç (kötüden iyiye)."""
    secilen = sonuclar[:en_fazla] if len(sonuclar) > en_fazla else sonuclar
    etiket = [f"{s.urun_kodu} · {s.urun_adi}"[:40] if s.urun_adi else s.urun_kodu for s in secilen]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=etiket, x=[s.toplam_muhasebe_brut_kari for s in secilen], orientation="h", name="Muhasebe brüt kârı",
        marker=dict(color=ARDUVAZ), hovertemplate=f"%{{y}}<br>Muhasebe: %{{x:{TL}}} TL<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=etiket, x=[s.toplam_ekonomik_sonuc for s in secilen], orientation="h", name="Ekonomik sonuç (yeşil kâr, kırmızı zarar)",
        marker=dict(color=[NANE_KOYU if s.toplam_ekonomik_sonuc >= 0 else KAYIP for s in secilen]),
        hovertemplate=f"%{{y}}<br>Ekonomik: %{{x:+{TL}}} TL<extra></extra>",
    ))
    yerlesim = _ortak_yerlesim("Toplam (TL)", "")
    yerlesim.update(
        barmode="group", bargap=0.25, bargroupgap=0.08, showlegend=True,
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(color=YAZI_2)),
        height=max(320, 70 + 46 * len(secilen)), margin=dict(l=180, r=24, t=40, b=56),
    )
    fig.update_layout(**yerlesim)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)", tickformat=None)
    fig.update_xaxes(tickformat=",.0f")
    fig.add_vline(x=0, line=dict(color=YAZI_2, width=1))
    return _json(fig)


def stok_grafigi(senaryolar) -> dict:
    x = [f"{s.stok_gunu:g} gün".replace(".", ",") if s.stok_gunu == int(s.stok_gunu)
         else f"{s.stok_gunu:.1f} gün".replace(".", ",") for s in senaryolar]
    x = [e + (" (mevcut)" if s.mevcut_durum else "") for e, s in zip(x, senaryolar)]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x, y=[s.yillik_finansman_maliyeti for s in senaryolar], name="Finansman maliyeti",
        marker=dict(color=[LACIVERT if s.mevcut_durum else ARDUVAZ for s in senaryolar]),
        hovertemplate=f"%{{x}}<br>Finansman: %{{y:{TL}}} TL<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=x, y=[s.yillik_tasima_maliyeti for s in senaryolar], name="Taşıma maliyeti",
        marker=dict(color=NANE), hovertemplate=f"%{{x}}<br>Taşıma: %{{y:{TL}}} TL<extra></extra>",
    ))
    yerlesim = _ortak_yerlesim("Ortalama stok günü", "Yıllık maliyet (TL)")
    yerlesim.update(barmode="stack", showlegend=True,
                    legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(color=YAZI_2)),
                    margin=dict(l=80, r=20, t=40, b=56))
    fig.update_layout(**yerlesim)
    return _json(fig)


def finansman_grafigi(sonuc) -> dict:
    """Alternatiflerin efektif yıllık maliyeti ve işletme oranına göre BD maliyeti."""
    adlar = [a.ad for a in sonuc.alternatifler]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=adlar, y=[a.efektif_yillik_maliyet * 100 for a in sonuc.alternatifler],
        marker=dict(color=[LACIVERT if a.ad == sonuc.en_dusuk_efektif_maliyet else ARDUVAZ
                           for a in sonuc.alternatifler]),
        text=[f"%{a.efektif_yillik_maliyet * 100:.2f}".replace(".", ",") for a in sonuc.alternatifler],
        textposition="outside", textfont=dict(color=YAZI),
        hovertemplate="%{x}<br>Efektif yıllık maliyet: %{text}<extra></extra>",
    ))
    yerlesim = _ortak_yerlesim("", "Efektif yıllık maliyet (%)")
    fig.update_layout(**yerlesim)
    ust = max(a.efektif_yillik_maliyet * 100 for a in sonuc.alternatifler)
    fig.update_yaxes(range=[0, ust * 1.2 or 1], tickformat=",.0f")
    return _json(fig)


def senaryo_grafigi(sonuc) -> dict:
    adlar = [s.ad for s in sonuc.senaryolar]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=adlar, y=[s.ekonomik_sonuc for s in sonuc.senaryolar], name="Ekonomik sonuç",
        marker=dict(color=[NANE_KOYU if s.ekonomik_sonuc >= 0 else KAYIP for s in sonuc.senaryolar]),
        text=[_tl(s.ekonomik_sonuc, isaretli=True) for s in sonuc.senaryolar], textposition="outside",
        textfont=dict(color=YAZI), hovertemplate="%{x}<br>Ekonomik sonuç: %{text}<extra></extra>",
    ))
    risk_var = sonuc.risk.odeme_olasiligi_yuzde < 100 or sonuc.risk.beklenen_gecikme_gun > 0
    if risk_var:
        fig.add_trace(go.Bar(
            x=adlar, y=[s.riskli_ekonomik_sonuc for s in sonuc.senaryolar], name="Tahsilat riskiyle",
            marker=dict(color=ARDUVAZ, pattern=dict(shape="/", fgcolor="#ffffff", size=6)),
            text=[_tl(s.riskli_ekonomik_sonuc, isaretli=True) for s in sonuc.senaryolar], textposition="outside",
            textfont=dict(color=YAZI), hovertemplate="%{x}<br>Riskli sonuç: %{text}<extra></extra>",
        ))
    yerlesim = _ortak_yerlesim("", "Ekonomik sonuç (TL, birim)")
    yerlesim.update(barmode="group", showlegend=risk_var,
                    legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(color=YAZI_2)),
                    margin=dict(l=64, r=20, t=40, b=48))
    fig.update_layout(**yerlesim)
    degerler = [s.ekonomik_sonuc for s in sonuc.senaryolar] + (
        [s.riskli_ekonomik_sonuc for s in sonuc.senaryolar] if risk_var else [])
    alt, ust = min(degerler + [0]), max(degerler + [0])
    pay = (ust - alt) * 0.18 or 1
    fig.update_yaxes(range=[alt - pay, ust + pay])
    fig.add_hline(y=0, line=dict(color=YAZI_2, width=1))
    return _json(fig)
