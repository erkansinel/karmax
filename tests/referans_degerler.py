"""Referans beklenen değerler.

Bu sayılar Karmax motoru ÇALIŞTIRILMADAN, Python'un `fractions.Fraction`
(tam kesirli aritmetik) modülüyle ayrıca hesaplanmıştır. Motorun kodu
bu dosyayı üretmek için kullanılmamıştır.

Temel senaryo:
    İlk alış maliyeti         100 TL
    Yerine koyma maliyeti     120 TL (bugün peşin ödenir)
    Satış fiyatı              130 TL
    Paranın maliyeti          yıllık %40, basit faiz, 365 gün esası
    Hedef kâr oranı           %30 (maliyetin bugünkü değeri üzerinden)
"""

TOLERANS = 0.005  # ±0,5 kuruş

TEMEL = dict(ilk_alis=100.0, yerine_koyma=120.0, satis=130.0, oran_yuzde=40.0)

# vade günü -> (tahsilatın bugünkü değeri, ekonomik sonuç, vade maliyeti)
VADE_TABLOSU = {
    0: (130.000000, 10.000000, 0.000000),
    30: (125.862069, 5.862069, 4.137931),
    60: (121.979434, 1.979434, 8.020566),
    90: (118.329177, -1.670823, 11.670823),
}

GUN_ESASI_360_90_GUN = (118.181818, -1.818182)

BASABAS_FIYATI_90_GUN = 131.835616
HEDEF_FIYAT_90_GUN_YUZDE30 = 171.386301
MAKS_VADE_BASIT = 76.041667

BRUT_KAR = 30.0
KAR_ORANI_MALIYET = 0.300000   # 30 / 100
BRUT_KAR_MARJI = 0.230769      # 30 / 130

# Faiz yöntemleri, 130 TL, 90 gün, %40, 365 gün esası
BILESIK_AYLIK_BD = 117.979692      # (1 + 0,40/12)^(−12·90/365)
EFEKTIF_BD = 119.649746            # 1,40^(−90/365)
EFEKTIF_YILLIK_AYLIK_BILESIK = 0.482126
MAKS_VADE_BILESIK_AYLIK = 74.249634
MAKS_VADE_EFEKTIF = 86.829120

# Tedarikçi 60 gün vade verirse (tahsilat 90 gün)
TEDARIKCI_60_BD_YERINE_KOYMA = 112.596401
TEDARIKCI_60_EKONOMIK = 5.732776

# Ticari (dış) iskonto: 130 TL senet, %40, 90 gün
TICARI_ISKONTO_TUTARI = 117.178082
