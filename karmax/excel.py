"""Excel entegrasyonu: şablon üretme, yükleme/doğrulama ve sonuç dışa aktarma.

Güvenlik kuralları:
  * Yalnızca .xlsx (ZIP imzası kontrol edilir), en fazla 5 MB, en fazla 5.000 ürün satırı.
  * Formüller çalıştırılmaz; yalnızca hücrelerin kayıtlı değerleri okunur.
  * Dışa aktarmada metin hücreleri her zaman metin olarak yazılır (formül enjeksiyonu önlemi).
  * Hatalı satırlar sessizce düzeltilmez veya atlanmaz; her biri satır numarası ve nedeniyle raporlanır.
"""

from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass, field

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from pydantic import ValidationError

from karmax.hatalar import turkce_hatalar
from karmax.motor import AnalizParametreleri, UrunGirdisi
from karmax.motor.toplu import TopluSonuc

MAKS_DOSYA_BAYT = 5 * 1024 * 1024
MAKS_SATIR = 5000
URUN_SAYFASI = "Ürünler"
PARAMETRE_SAYFASI = "Parametreler"
ACIKLAMA_SAYFASI = "Açıklamalar"

LACIVERT = "3F4D6E"
NANE = "9EDCD0"


@dataclass(frozen=True)
class Sutun:
    alan: str
    baslik: str
    birim: str
    aciklama: str
    tur: str  # metin | ondalik | tamsayi | yuzde
    zorunlu: bool
    ornek: object
    varsayilan: object = None


SUTUNLAR = [
    Sutun("urun_kodu", "Ürün kodu", "metin", "Her ürün için benzersiz kod.", "metin", True, "TSH-001"),
    Sutun("urun_adi", "Ürün adı", "metin", "Ürünün adı.", "metin", False, "Pamuklu tişört"),
    Sutun("ilk_alis_maliyeti", "İlk alış maliyeti", "TL / birim, KDV hariç",
          "Stoktaki malın geçmişte alındığı birim maliyet.", "ondalik", True, 100),
    Sutun("yerine_koyma_maliyeti", "Bugünkü yeniden alış maliyeti", "TL / birim, KDV hariç",
          "Aynı malı bugün yeniden almanın birim maliyeti.", "ondalik", True, 120),
    Sutun("satis_fiyati", "Satış fiyatı", "TL / birim, KDV hariç", "Müşteriye satış fiyatı.", "ondalik", True, 130),
    Sutun("satis_miktari", "Satış miktarı", "adet", "Dönemde satılan miktar.", "ondalik", False, 500, 1),
    Sutun("tahsilat_vadesi_gun", "Müşteri tahsilat vadesi", "gün", "Müşterinin kaç gün sonra ödediği.",
          "tamsayi", False, 90, 0),
    Sutun("tedarikci_vadesi_gun", "Tedarikçi ödeme vadesi", "gün", "Yerine koyma alımının kaç gün sonra ödendiği.",
          "tamsayi", False, 0, 0),
    Sutun("ek_gider_birim", "Ek gider", "TL / birim", "Nakliye, komisyon gibi satışa bağlı giderler.",
          "ondalik", False, 0, 0),
    Sutun("hedef_kar_orani_yuzde", "Hedef kâr oranı", "%", "Maliyetin bugünkü değeri üzerinden. 30 yazın, %30 demektir.",
          "yuzde", False, 30, 30),
]

PARAMETRELER = [
    ("yillik_oran_yuzde", "Yıllık oran (%)", 40, "Paranın yıllık maliyeti. 40 yazın, %40 demektir."),
    ("faiz_yontemi", "Faiz yöntemi", "basit", "basit, bilesik veya efektif"),
    ("gun_esasi", "Gün esası", 365, "360 veya 365"),
    ("bilesik_donem", "Bileşik dönem (yılda)", 12, "Yalnızca bileşik yöntemde kullanılır."),
]


class ExcelYapiHatasi(ValueError):
    """Dosya bütünüyle okunamıyorsa (yanlış tür, eksik sayfa veya sütun)."""


@dataclass
class SatirHatasi:
    satir: int
    urun_kodu: str | None
    alan: str | None
    mesaj: str
    deger: str | None = None


@dataclass
class YuklemeSonucu:
    parametreler: AnalizParametreleri
    urunler: list[tuple[int, UrunGirdisi]]
    hatalar: list[SatirHatasi] = field(default_factory=list)
    uyarilar: list[str] = field(default_factory=list)
    bos_satir_sayisi: int = 0
    okunan_satir_sayisi: int = 0


# ----------------------------------------------------------------- yardımcılar

def _normal(metin: object) -> str:
    """Başlık eşleştirme için: küçük harf, Türkçe harfler sadeleşmiş, yalnızca harf/rakam."""
    s = str(metin or "").strip().lower().replace("ı", "i")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\(.*?\)", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


BASLIK_HARITASI = {_normal(s.baslik): s for s in SUTUNLAR} | {_normal(s.alan): s for s in SUTUNLAR}


def sayi_coz(deger: object, yuzde_bicimli: bool = False) -> float:
    """Hücre değerini sayıya çevirir. '1.250,50', '1250.5', '40%', '%40' kabul edilir."""
    if isinstance(deger, bool):
        raise ValueError("sayı girilmeli")
    if isinstance(deger, (int, float)):
        return float(deger) * (100.0 if yuzde_bicimli else 1.0)
    metin = str(deger).strip().replace(" ", "").replace(" ", "").replace("TL", "").replace("tl", "")
    yuzde = "%" in metin
    metin = metin.replace("%", "")
    if not metin:
        raise ValueError("boş")
    if "," in metin and "." in metin:
        # Hangisi sondaysa ondalık ayırıcı odur
        if metin.rfind(",") > metin.rfind("."):
            metin = metin.replace(".", "").replace(",", ".")
        else:
            metin = metin.replace(",", "")
    elif "," in metin:
        if metin.count(",") > 1:
            raise ValueError(f"anlaşılamayan sayı '{deger}'")
        metin = metin.replace(",", ".")
    elif metin.count(".") > 1:
        metin = metin.replace(".", "")
    elif re.fullmatch(r"-?\d{1,3}\.\d{3}", metin):
        raise ValueError(
            f"belirsiz sayı '{deger}': binlik için noktasız ({metin.replace('.', '')}), "
            f"ondalık için virgülle ({metin.replace('.', ',')}) yazın"
        )
    try:
        sayi = float(metin)
    except ValueError:
        raise ValueError("sayı girilmeli") from None
    return sayi  # "%40" ve "40" aynı anlama gelir: yüzde sayı


def _ham_metin(deger: object) -> str:
    """Hücre değerini kullanıcının gördüğüne yakın metne çevirir: -5.0 → -5, 12.5 → 12,5."""
    if isinstance(deger, float):
        return f"{deger:g}".replace(".", ",") if abs(deger) < 1e15 else str(deger)
    return str(deger)


def _bos(deger: object) -> bool:
    return deger is None or (isinstance(deger, str) and not deger.strip())


def yaz(ws, satir: int, sutun: int, deger: object):
    """Hücreye değer yazar. Metin her zaman METİN olarak saklanır; '=' ile başlasa bile
    formül olarak çalışmaz (formül enjeksiyonu önlemi)."""
    hucre = ws.cell(row=satir, column=sutun, value=deger)
    if isinstance(deger, str):
        hucre.data_type = "s"
    return hucre


# ---------------------------------------------------------------------- şablon

def sablon_olustur() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = URUN_SAYFASI
    baslik_font = Font(bold=True, color="FFFFFF")
    baslik_dolgu = PatternFill("solid", fgColor=LACIVERT)
    for i, s in enumerate(SUTUNLAR, start=1):
        h = ws.cell(row=1, column=i, value=s.baslik)
        h.font, h.fill = baslik_font, baslik_dolgu
        h.alignment = Alignment(wrap_text=True, vertical="center")
        not_metni = f"{s.aciklama}\nBirim: {s.birim}\n" + ("Zorunlu." if s.zorunlu else f"Boşsa: {s.varsayilan}")
        h.comment = Comment(not_metni, "Karmax")
        ws.column_dimensions[get_column_letter(i)].width = max(16, len(s.baslik) + 4)
    ws.row_dimensions[1].height = 34
    ws.freeze_panes = "A2"

    son = MAKS_SATIR + 1
    for i, s in enumerate(SUTUNLAR, start=1):
        harf = get_column_letter(i)
        aralik = f"{harf}2:{harf}{son}"
        if s.tur == "ondalik":
            alt = "0" if not s.zorunlu or s.alan == "ek_gider_birim" else "0.000001"
            dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1=alt, allow_blank=True)
        elif s.tur == "tamsayi":
            dv = DataValidation(type="whole", operator="between", formula1="0", formula2="3650", allow_blank=True)
        elif s.tur == "yuzde":
            dv = DataValidation(type="decimal", operator="between", formula1="0", formula2="1000", allow_blank=True)
        else:
            continue
        dv.error = f"{s.baslik}: geçerli bir sayı girin ({s.birim})."
        dv.errorTitle = "Geçersiz değer"
        dv.prompt = s.aciklama
        dv.promptTitle = s.baslik
        ws.add_data_validation(dv)
        dv.add(aralik)

    pw = wb.create_sheet(PARAMETRE_SAYFASI)
    for i, (b, gen) in enumerate([("Parametre", 26), ("Değer", 14), ("Açıklama", 60)], start=1):
        c = pw.cell(row=1, column=i, value=b)
        c.font, c.fill = baslik_font, baslik_dolgu
        pw.column_dimensions[get_column_letter(i)].width = gen
    for r, (_, etiket, deger, aciklama) in enumerate(PARAMETRELER, start=2):
        pw.cell(row=r, column=1, value=etiket).font = Font(bold=True)
        pw.cell(row=r, column=2, value=deger)
        pw.cell(row=r, column=3, value=aciklama)
    yontem_dv = DataValidation(type="list", formula1='"basit,bilesik,efektif"', allow_blank=False)
    gun_dv = DataValidation(type="list", formula1='"360,365"', allow_blank=False)
    pw.add_data_validation(yontem_dv)
    pw.add_data_validation(gun_dv)
    yontem_dv.add("B3")
    gun_dv.add("B4")

    aw = wb.create_sheet(ACIKLAMA_SAYFASI)
    aw.column_dimensions["A"].width = 32
    aw.column_dimensions["B"].width = 24
    aw.column_dimensions["C"].width = 70
    satirlar = [
        ("Karmax – Toplu ürün analizi şablonu", None, None),
        ("Decisora Danışmanlık A.Ş.", None, None),
        (None, None, None),
        ("Nasıl doldurulur?", None, None),
        ("1.", None, "'Ürünler' sayfasına her satıra bir ürün yazın. Başlık satırını değiştirmeyin."),
        ("2.", None, "'Parametreler' sayfasında paranın yıllık maliyetini ve hesap yöntemini girin."),
        ("3.", None, "Tutarlar birim başına, TL ve KDV hariç yazılır. Oranlar yüzde olarak yazılır: 40 = %40."),
        ("4.", None, "Ondalık için virgül veya nokta kullanabilirsiniz (12,5 veya 12.5)."),
        ("5.", None, "Dosyayı kaydedip Karmax'taki 'Toplu analiz' sekmesinden yükleyin."),
        (None, None, None),
        ("Sütun", "Birim", "Açıklama"),
    ] + [(s.baslik + (" *" if s.zorunlu else ""), s.birim, s.aciklama) for s in SUTUNLAR] + [
        (None, None, None),
        ("* işaretli sütunlar zorunludur.", None, None),
        (None, None, None),
        ("Örnek satır (Ürünler sayfasına kopyalayabilirsiniz):", None, None),
    ]
    for r, (a, b, c) in enumerate(satirlar, start=1):
        aw.cell(row=r, column=1, value=a)
        aw.cell(row=r, column=2, value=b)
        aw.cell(row=r, column=3, value=c)
    aw["A1"].font = Font(bold=True, size=14, color=LACIVERT)
    aw["A4"].font = Font(bold=True)
    for col in range(1, 4):
        aw.cell(row=11, column=col).font = Font(bold=True)
    ornek_baslik = len(satirlar) + 1
    for i, s in enumerate(SUTUNLAR, start=1):
        c = aw.cell(row=ornek_baslik, column=i, value=s.baslik)
        c.font, c.fill = Font(bold=True), PatternFill("solid", fgColor=NANE)
        aw.cell(row=ornek_baslik + 1, column=i, value=s.ornek)

    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


# ---------------------------------------------------------------------- okuma

def _parametreleri_oku(wb) -> AnalizParametreleri:
    if PARAMETRE_SAYFASI not in wb.sheetnames:
        raise ExcelYapiHatasi(f"'{PARAMETRE_SAYFASI}' sayfası bulunamadı. Lütfen Karmax şablonunu kullanın.")
    ws = wb[PARAMETRE_SAYFASI]
    etiketler = {_normal(etiket): alan for alan, etiket, _, _ in PARAMETRELER}
    ham: dict[str, object] = {}
    for satir in ws.iter_rows(min_row=2, max_col=2, values_only=True):
        if not satir or _bos(satir[0]):
            continue
        alan = etiketler.get(_normal(satir[0]))
        if alan:
            ham[alan] = satir[1] if len(satir) > 1 else None
    eksik = [etiket for alan, etiket, _, _ in PARAMETRELER if alan not in ham or _bos(ham[alan])]
    if eksik:
        raise ExcelYapiHatasi("Parametreler sayfasında eksik değer: " + ", ".join(eksik))
    try:
        veri = {
            "yillik_oran_yuzde": sayi_coz(ham["yillik_oran_yuzde"]),
            "faiz_yontemi": _normal(ham["faiz_yontemi"]),
            "gun_esasi": int(sayi_coz(ham["gun_esasi"])),
            "bilesik_donem": int(sayi_coz(ham["bilesik_donem"])),
        }
        return AnalizParametreleri(**veri)
    except ValueError as e:
        if isinstance(e, ValidationError):
            mesajlar = "; ".join(h["mesaj"] for h in turkce_hatalar(e.errors()))
        else:
            mesajlar = str(e)
        raise ExcelYapiHatasi(f"Parametreler sayfasında hata: {mesajlar}") from None


def excel_oku(icerik: bytes) -> YuklemeSonucu:
    if len(icerik) > MAKS_DOSYA_BAYT:
        raise ExcelYapiHatasi(f"Dosya çok büyük. En fazla {MAKS_DOSYA_BAYT // (1024 * 1024)} MB yüklenebilir.")
    if not icerik.startswith(b"PK"):
        raise ExcelYapiHatasi("Dosya .xlsx biçiminde değil. Lütfen Excel'de 'Excel Çalışma Kitabı (.xlsx)' olarak kaydedin.")
    try:
        wb = load_workbook(io.BytesIO(icerik), data_only=True)  # formüller çalıştırılmaz
    except Exception:  # noqa: BLE001 - bozuk dosyanın türü önemli değil
        raise ExcelYapiHatasi("Dosya açılamadı. Bozuk olabilir veya .xlsx değildir.") from None

    if URUN_SAYFASI not in wb.sheetnames:
        raise ExcelYapiHatasi(f"'{URUN_SAYFASI}' sayfası bulunamadı. Lütfen Karmax şablonunu kullanın.")
    parametreler = _parametreleri_oku(wb)
    ws = wb[URUN_SAYFASI]

    basliklar = [c.value for c in ws[1]]
    sutun_konumu: dict[str, int] = {}
    uyarilar: list[str] = []
    for i, b in enumerate(basliklar):
        if _bos(b):
            continue
        s = BASLIK_HARITASI.get(_normal(b))
        if s is None:
            uyarilar.append(f"Tanınmayan sütun yok sayıldı: '{b}'")
        elif s.alan in sutun_konumu:
            raise ExcelYapiHatasi(f"'{s.baslik}' sütunu birden fazla kez var.")
        else:
            sutun_konumu[s.alan] = i
    eksik = [s.baslik for s in SUTUNLAR if s.zorunlu and s.alan not in sutun_konumu]
    if eksik:
        raise ExcelYapiHatasi("Zorunlu sütun eksik: " + ", ".join(eksik))
    for s in SUTUNLAR:
        if not s.zorunlu and s.alan not in sutun_konumu:
            uyarilar.append(f"'{s.baslik}' sütunu yok; tüm ürünler için {s.varsayilan} kabul edildi.")

    sonuc = YuklemeSonucu(parametreler=parametreler, urunler=[], uyarilar=uyarilar)
    adaylar: list[tuple[int, UrunGirdisi]] = []
    for satir_no, hucreler in enumerate(ws.iter_rows(min_row=2), start=2):
        degerler = {s.alan: hucreler[sutun_konumu[s.alan]] for s in SUTUNLAR
                    if s.alan in sutun_konumu and sutun_konumu[s.alan] < len(hucreler)}
        if all(_bos(c.value) for c in degerler.values()):
            sonuc.bos_satir_sayisi += 1
            continue
        sonuc.okunan_satir_sayisi += 1
        if sonuc.okunan_satir_sayisi > MAKS_SATIR:
            raise ExcelYapiHatasi(f"En fazla {MAKS_SATIR} ürün satırı yüklenebilir.")

        kod_hucre = degerler.get("urun_kodu")
        kod = None if kod_hucre is None or _bos(kod_hucre.value) else str(kod_hucre.value).strip()
        veri: dict[str, object] = {}
        satir_hatali = False
        for s in SUTUNLAR:
            hucre = degerler.get(s.alan)
            deger = None if hucre is None else hucre.value
            if _bos(deger):
                if s.zorunlu:
                    sonuc.hatalar.append(SatirHatasi(satir_no, kod, s.alan, f"{s.baslik}: boş bırakılamaz"))
                    satir_hatali = True
                elif s.varsayilan is not None:
                    veri[s.alan] = s.varsayilan
                continue
            if s.tur == "metin":
                veri[s.alan] = str(deger).strip()
                continue
            try:
                yuzde_bicimli = s.tur == "yuzde" and "%" in (hucre.number_format or "")
                sayi = sayi_coz(deger, yuzde_bicimli)
                if s.tur == "tamsayi":
                    if abs(sayi - round(sayi)) > 1e-9:
                        raise ValueError("tam sayı girilmeli")
                    sayi = int(round(sayi))
                veri[s.alan] = sayi
            except ValueError as e:
                sonuc.hatalar.append(SatirHatasi(satir_no, kod, s.alan, f"{s.baslik}: {e}", str(deger)))
                satir_hatali = True
        ham = {a: (None if c is None or c.value is None else _ham_metin(c.value)) for a, c in degerler.items()}
        bildirilen = {h.alan for h in sonuc.hatalar if h.satir == satir_no}
        try:
            urun = UrunGirdisi(**veri)
            if not satir_hatali:
                adaylar.append((satir_no, urun))
        except ValidationError as e:
            # Ayrıştırma hatası verilmiş alanlar için ikinci kez "eksik" hatası yazma
            for h in turkce_hatalar(e.errors()):
                if h["alan"] in bildirilen:
                    continue
                sutun = next((s for s in SUTUNLAR if s.alan == h["alan"]), None)
                kural = h["mesaj"].split(": ", 1)[-1]
                mesaj = f"{sutun.baslik}: {kural}" if sutun else h["mesaj"]
                sonuc.hatalar.append(SatirHatasi(satir_no, kod, h["alan"], mesaj, ham.get(h["alan"])))

    # Mükerrer ürün kodları: hiçbiri sessizce seçilmez, hepsi hata olarak raporlanır
    konumlar: dict[str, list[int]] = {}
    for satir_no, u in adaylar:
        konumlar.setdefault(u.urun_kodu.casefold(), []).append(satir_no)
    for satir_no, u in adaylar:
        satirlar = konumlar[u.urun_kodu.casefold()]
        if len(satirlar) > 1:
            diger = ", ".join(str(x) for x in satirlar if x != satir_no)
            sonuc.hatalar.append(SatirHatasi(satir_no, u.urun_kodu, "urun_kodu",
                                             f"Mükerrer ürün kodu (aynı kod {diger}. satırda da var)", u.urun_kodu))
        else:
            sonuc.urunler.append((satir_no, u))
    sonuc.hatalar.sort(key=lambda h: (h.satir, h.alan or ""))
    if sonuc.okunan_satir_sayisi == 0:
        raise ExcelYapiHatasi("'Ürünler' sayfasında hiç ürün satırı yok.")
    return sonuc


# ------------------------------------------------------------- sonuç dosyası

SONUC_SUTUNLARI = [
    ("urun_kodu", "Ürün kodu", None),
    ("urun_adi", "Ürün adı", None),
    ("satis_miktari", "Satış miktarı", "#,##0.##"),
    ("muhasebe_brut_kari", "Muhasebe brüt kârı (birim)", "#,##0.00"),
    ("kar_orani_maliyet_uzerinden", "Kâr oranı (maliyet üzerinden)", "0.0%"),
    ("brut_kar_marji_satis_uzerinden", "Brüt kâr marjı (satış üzerinden)", "0.0%"),
    ("yerine_koyma_kari", "Yeniden alış maliyetine göre kâr (birim)", "#,##0.00"),
    ("vade_maliyeti", "Vade maliyeti (birim)", "#,##0.00"),
    ("tedarikci_vadesi_kazanci", "Tedarikçi vadesi kazancı (birim)", "#,##0.00"),
    ("ekonomik_sonuc", "Ekonomik sonuç (birim)", "#,##0.00"),
    ("ekonomik_kar_orani", "Ekonomik kâr oranı", "0.0%"),
    ("basabas_satis_fiyati", "Başabaş satış fiyatı", "#,##0.00"),
    ("hedef_satis_fiyati", "Hedef satış fiyatı", "#,##0.00"),
    ("maksimum_vade_gun", "En uzun vade (gün)", "#,##0.0"),
    ("toplam_muhasebe_brut_kari", "Toplam muhasebe brüt kârı", "#,##0.00"),
    ("toplam_ekonomik_sonuc", "Toplam ekonomik sonuç", "#,##0.00"),
]

VADE_DURUMU = {"sinirsiz": "Sınırsız (faiz sıfır)", "pesin_bile_zarar": "Peşin satışta bile zarar"}


def _baslik_yaz(ws, basliklar: list[str]) -> None:
    for i, b in enumerate(basliklar, start=1):
        c = ws.cell(row=1, column=i, value=b)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=LACIVERT)
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = max(14, min(34, len(b) + 2))
    ws.row_dimensions[1].height = 36
    ws.freeze_panes = "A2"


def sonuc_excel_olustur(kayit: dict) -> bytes:
    """Saklanmış bir toplu analiz kaydından sonuç dosyası üretir (yeniden hesaplama yapmaz)."""
    girdi, sonuc = kayit["girdi"], kayit["sonuc"]
    ozet, p = sonuc["ozet"], girdi["parametreler"]
    wb = Workbook()

    ws = wb.active
    ws.title = "Özet"
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 22
    satirlar = [
        ("Karmax – Toplu ürün analizi", None, None),
        ("Decisora Danışmanlık A.Ş.", None, None),
        (f"Analiz no: {kayit['id']} · {kayit['olusturma']} · motor sürümü {kayit['motor_surumu']}", None, None),
        (None, None, None),
        ("Paranın yıllık maliyeti (%)", p["yillik_oran_yuzde"], "0.00"),
        ("Faiz yöntemi", p["faiz_yontemi"], None),
        ("Gün esası", p["gun_esasi"], None),
        (None, None, None),
        ("Analiz edilen ürün", ozet["urun_sayisi"], "0"),
        ("Hatalı satır", len({h["satir"] for h in sonuc["hatalar"]}), "0"),
        ("Toplam ciro (TL)", ozet["toplam_ciro"], "#,##0.00"),
        ("Toplam muhasebe brüt kârı (TL)", ozet["toplam_muhasebe_brut_kari"], "#,##0.00"),
        ("Toplam ekonomik sonuç (TL)", ozet["toplam_ekonomik_sonuc"], "#,##0.00"),
        ("Gizli fark: muhasebe − ekonomik (TL)", ozet["gizli_fark"], "#,##0.00"),
        ("Ekonomik olarak zarar eden ürün", ozet["zarar_eden_urun_sayisi"], "0"),
        ("Zarar eden ürünlerin toplam kaybı (TL)", ozet["zarar_eden_urunlerin_toplam_kaybi"], "#,##0.00"),
        (None, None, None),
        ("Varsayımlar", None, None),
    ] + [(v, None, None) for v in (sonuc["sonuclar"][0]["varsayimlar"] if sonuc["sonuclar"] else [])]
    for r, (a, b, bicim) in enumerate(satirlar, start=1):
        yaz(ws, r, 1, a)
        cb = yaz(ws, r, 2, b)
        if bicim:
            cb.number_format = bicim
    ws["A1"].font = Font(bold=True, size=14, color=LACIVERT)
    ws["A18"].font = Font(bold=True)

    rs = wb.create_sheet("Sonuçlar")
    _baslik_yaz(rs, [b for _, b, _ in SONUC_SUTUNLARI] + ["Vade durumu"])
    for r, s in enumerate(sonuc["sonuclar"], start=2):
        for c, (alan, _, bicim) in enumerate(SONUC_SUTUNLARI, start=1):
            deger = s.get(alan)
            hucre = yaz(rs, r, c, deger)
            if bicim and isinstance(deger, (int, float)):
                hucre.number_format = bicim
            if alan in ("ekonomik_sonuc", "toplam_ekonomik_sonuc") and isinstance(deger, (int, float)) and deger < 0:
                hucre.font = Font(color="C0444A", bold=True)
        rs.cell(row=r, column=len(SONUC_SUTUNLARI) + 1,
                value=VADE_DURUMU.get(s["maksimum_vade_durumu"], "Sınırlı"))

    hs = wb.create_sheet("Hatalar")
    _baslik_yaz(hs, ["Excel satırı", "Ürün kodu", "Alan", "Hata", "Girilen değer"])
    hs.column_dimensions["D"].width = 60
    if not sonuc["hatalar"]:
        hs.cell(row=2, column=1, value="Hatalı satır yok.")
    for r, h in enumerate(sonuc["hatalar"], start=2):
        for c, v in enumerate([h["satir"], h["urun_kodu"], h["alan"], h["mesaj"], h["deger"]], start=1):
            yaz(hs, r, c, v)

    if sonuc.get("uyarilar"):
        us = wb.create_sheet("Uyarılar")
        _baslik_yaz(us, ["Uyarı"])
        us.column_dimensions["A"].width = 90
        for r, u in enumerate(sonuc["uyarilar"], start=2):
            yaz(us, r, 1, u)

    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


def toplu_kayit_verisi(y: YuklemeSonucu, t: TopluSonuc) -> tuple[dict, dict]:
    """Kaydedilecek girdi ve sonuç sözlüklerini hazırlar."""
    girdi = {
        "parametreler": y.parametreler.model_dump(mode="json"),
        "urunler": [{"satir": n, **u.model_dump(mode="json")} for n, u in y.urunler],
    }
    sonuc = {
        "ozet": t.ozet.model_dump(mode="json"),
        "sonuclar": [s.model_dump(mode="json") for s in t.sonuclar],
        "hatalar": [h.__dict__ for h in y.hatalar],
        "uyarilar": y.uyarilar,
        "okunan_satir_sayisi": y.okunan_satir_sayisi,
        "bos_satir_sayisi": y.bos_satir_sayisi,
    }
    return girdi, sonuc
