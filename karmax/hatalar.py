"""Doğrulama hatalarını Türkçe, kullanıcının anlayacağı mesajlara çevirir.

API ve Excel içe aktarma aynı çeviriyi kullanır.
"""

from __future__ import annotations

ALAN_ADLARI = {
    "satis_fiyati": "Satış fiyatı", "ilk_alis_maliyeti": "İlk alış maliyeti",
    "yerine_koyma_maliyeti": "Bugünkü yeniden alış maliyeti", "satis_miktari": "Satış miktarı",
    "tahsilat_vadesi_gun": "Müşteri tahsilat vadesi", "tedarikci_vadesi_gun": "Tedarikçi ödeme vadesi",
    "ek_gider_birim": "Ek gider", "hedef_kar_orani_yuzde": "Hedef kâr oranı", "urun_kodu": "Ürün kodu",
    "urun_adi": "Ürün adı", "yillik_oran_yuzde": "Yıllık oran", "bilesik_donem": "Bileşik dönem",
    "gun_esasi": "Gün esası", "faiz_yontemi": "Faiz yöntemi",
    "yillik_satilan_mal_maliyeti": "Yıllık satılan malın maliyeti", "ortalama_stok_tutari": "Ortalama stok tutarı",
    "tasima_maliyeti_orani_yuzde": "Taşıma maliyeti oranı", "alternatif_stok_gunleri": "Alternatif stok günleri",
    "fatura_tutari": "Fatura tutarı", "iskonto_yuzde": "Erken ödeme iskontosu", "vade_gun": "Vade",
    "kullanilan_tutar": "Kullanılan tutar", "yillik_faiz_yuzde": "Kredinin yıllık faizi", "vade_ay": "Vade (ay)",
    "pesin_masraf": "Peşin masraf", "ad": "Ad", "tur": "Tür", "miktar": "Miktar", "birim_maliyet": "Birim maliyet",
    "satilan_miktar": "Satılan miktar", "yontem": "Yöntem", "odeme_olasiligi_yuzde": "Ödeme olasılığı",
    "beklenen_gecikme_gun": "Beklenen gecikme",
}


def _sayi(v) -> str:
    """Sınır değerini Türkçe yazar: 0.0 → 0, 2.5 → 2,5."""
    try:
        return f"{float(v):g}".replace(".", ",")
    except (TypeError, ValueError):
        return str(v)


def turkce_kural(hata: dict) -> str:
    c = {k: _sayi(v) for k, v in (hata.get("ctx") or {}).items()}
    tur = hata.get("type", "")
    if tur == "greater_than":
        return f"{c.get('gt')} değerinden büyük olmalı"
    if tur == "greater_than_equal":
        return f"en az {c.get('ge')} olmalı"
    if tur == "less_than":
        return f"{c.get('lt')} değerinden küçük olmalı"
    if tur == "less_than_equal":
        return f"en fazla {c.get('le')} olabilir"
    if tur == "missing":
        return "zorunlu alan, boş bırakılamaz"
    if tur in ("float_type", "int_type", "float_parsing", "int_parsing"):
        return "sayı girilmeli"
    if tur == "int_from_float":
        return "tam sayı girilmeli"
    if tur == "string_too_short":
        return "boş bırakılamaz"
    if tur == "string_too_long":
        return f"en fazla {c.get('max_length')} karakter olabilir"
    if tur in ("literal_error", "enum"):
        return "listedeki seçeneklerden biri olmalı"
    if tur == "extra_forbidden":
        return "tanımsız alan, kabul edilmiyor"
    if tur in ("too_short", "too_long"):
        return "eleman sayısı uygun değil"
    if tur == "value_error":
        return str(hata.get("msg", "geçersiz değer")).removeprefix("Value error, ")
    return "geçersiz değer"


def alan_adi(alan: str | None) -> str:
    if alan is None:
        return "İstek"
    return ALAN_ADLARI.get(alan, alan)


def turkce_hatalar(hatalar: list[dict]) -> list[dict]:
    """Pydantic hata listesini {alan, konum, tur, mesaj} sözlüklerine çevirir."""
    sonuc = []
    for h in hatalar:
        konum = [str(x) for x in h.get("loc", []) if x != "body"]
        # Liste elemanlarında son konum bir sayı olabilir; anlamlı alan adını bul
        alan = next((k for k in reversed(konum) if not k.isdigit()), None)
        sonuc.append({"alan": alan, "konum": konum, "tur": h.get("type"),
                      "mesaj": f"{alan_adi(alan)}: {turkce_kural(h)}"})
    return sonuc
