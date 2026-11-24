"""Karmax REST API (FastAPI).

Bu katman yalnızca:
  1. Gelen veriyi Pydantic ile doğrular (hataları Türkçe döndürür),
  2. Hesaplama motorunu çağırır,
  3. Grafik katmanından Plotly figürlerini alır,
  4. Girdi ve sonucu kayıt altına alır (önizleme hariç),
  5. Sonucu JSON veya Excel olarak döndürür.
Hiçbir finansal hesaplama burada yapılmaz.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import plotly
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from karmax import excel, grafikler
from karmax.hatalar import turkce_hatalar
from karmax.kayit import VARSAYILAN_YOL, AnalizKaydi
from karmax.motor import MOTOR_SURUMU, AnalizParametreleri, UrunGirdisi, UrunSonucu, urun_analiz_et
from karmax.motor.finansman import (
    ErkenOdemeGirdisi,
    ErkenOdemeSonucu,
    FinansmanGirdisi,
    FinansmanSonucu,
    erken_odeme_analiz_et,
    finansman_karsilastir,
)
from karmax.motor.fiyatlama import FiyatlamaGirdisi, FiyatlamaSonucu, fiyat_senaryolari
from karmax.motor.stok import StokGirdisi, StokSonucu, stok_analiz_et
from karmax.motor.toplu import toplu_analiz
from karmax.motor.yerine_koyma import MaliyetGirdisi, MaliyetSonucu, maliyet_hesapla

ARAYUZ_KLASORU = Path(__file__).resolve().parent.parent.parent / "arayuz"
PLOTLY_JS = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ------------------------------------------------------------- istek/yanıtlar

class UrunAnaliziIstegi(BaseModel):
    parametreler: AnalizParametreleri
    urun: UrunGirdisi


class UrunAnaliziYaniti(BaseModel):
    kayit_id: int | None
    sonuc: UrunSonucu
    grafikler: dict


class StokIstegi(BaseModel):
    parametreler: AnalizParametreleri
    stok: StokGirdisi


class StokYaniti(BaseModel):
    kayit_id: int
    sonuc: StokSonucu
    grafik: dict


class ErkenOdemeIstegi(BaseModel):
    parametreler: AnalizParametreleri
    girdi: ErkenOdemeGirdisi


class ErkenOdemeYaniti(BaseModel):
    kayit_id: int
    sonuc: ErkenOdemeSonucu


class FinansmanIstegi(BaseModel):
    parametreler: AnalizParametreleri
    girdi: FinansmanGirdisi


class FinansmanYaniti(BaseModel):
    kayit_id: int
    sonuc: FinansmanSonucu
    grafik: dict


class FiyatlamaIstegi(BaseModel):
    parametreler: AnalizParametreleri
    girdi: FiyatlamaGirdisi


class FiyatlamaYaniti(BaseModel):
    kayit_id: int
    sonuc: FiyatlamaSonucu
    grafik: dict


class MaliyetYaniti(BaseModel):
    kayit_id: int
    sonuc: MaliyetSonucu


def _hata(mesaj: str, durum: int = 422) -> HTTPException:
    return HTTPException(status_code=durum, detail=[{"alan": None, "konum": [], "tur": "is_kurali", "mesaj": mesaj}])


def _guvenli(fonksiyon, *args):
    """Motorun iş kuralı hatalarını (ValueError) kullanıcıya Türkçe 422 olarak döndürür."""
    try:
        return fonksiyon(*args)
    except ValueError as e:
        raise _hata(str(e)) from None


def uygulama_olustur(veritabani_yolu: Path | str | None = None) -> FastAPI:
    app = FastAPI(
        title="Karmax API",
        description="Decisora Danışmanlık A.Ş. – KOBİ finansal karar motoru",
        version=MOTOR_SURUMU,
    )
    kayit = AnalizKaydi(veritabani_yolu or os.environ.get("KARMAX_DB", VARSAYILAN_YOL))
    app.state.kayit = kayit

    def kaydet(tur: str, girdi: BaseModel | dict, sonuc: BaseModel | dict) -> int:
        g = girdi.model_dump(mode="json") if isinstance(girdi, BaseModel) else girdi
        s = sonuc.model_dump(mode="json") if isinstance(sonuc, BaseModel) else sonuc
        return kayit.kaydet(tur=tur, motor_surumu=MOTOR_SURUMU, girdi=g, sonuc=s)

    @app.exception_handler(RequestValidationError)
    async def dogrulama_hatasi(_: Request, hata: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": turkce_hatalar(hata.errors())})

    # ---------------------------------------------------------------- genel

    @app.get("/api/saglik")
    def saglik() -> dict:
        return {"durum": "ok", "motor_surumu": MOTOR_SURUMU}

    @app.get("/api/analizler/{kayit_id}")
    def analiz_getir(kayit_id: int) -> dict:
        veri = kayit.getir(kayit_id)
        if veri is None:
            raise HTTPException(status_code=404, detail="Bu numarayla kayıtlı analiz bulunamadı.")
        return veri

    # ------------------------------------------------- Modül 1–2: ürün analizi

    def _urun(istek: UrunAnaliziIstegi) -> tuple[UrunSonucu, dict]:
        sonuc = urun_analiz_et(istek.urun, istek.parametreler)
        return sonuc, grafikler.grafik_paketi(istek.urun, istek.parametreler, sonuc)

    @app.post("/api/urun-analizi", response_model=UrunAnaliziYaniti)
    def urun_analizi(istek: UrunAnaliziIstegi) -> UrunAnaliziYaniti:
        """Hesaplar, grafikleri üretir ve analizi KAYDEDER."""
        sonuc, g = _urun(istek)
        return UrunAnaliziYaniti(kayit_id=kaydet("urun_analizi", istek, sonuc), sonuc=sonuc, grafikler=g)

    @app.post("/api/onizleme", response_model=UrunAnaliziYaniti)
    def onizleme(istek: UrunAnaliziIstegi) -> UrunAnaliziYaniti:
        """Kaydırma çubukları için: hesaplar ve grafikleri üretir, KAYDETMEZ."""
        sonuc, g = _urun(istek)
        return UrunAnaliziYaniti(kayit_id=None, sonuc=sonuc, grafikler=g)

    # ------------------------------------------------------- Modül 3: maliyet

    @app.post("/api/maliyet-yontemi", response_model=MaliyetYaniti)
    def maliyet_yontemi(girdi: MaliyetGirdisi) -> MaliyetYaniti:
        sonuc = _guvenli(maliyet_hesapla, girdi)
        return MaliyetYaniti(kayit_id=kaydet("maliyet_yontemi", girdi, sonuc), sonuc=sonuc)

    # --------------------------------------------------------- Modül 4: stok

    @app.post("/api/stok-analizi", response_model=StokYaniti)
    def stok_analizi(istek: StokIstegi) -> StokYaniti:
        sonuc = _guvenli(stok_analiz_et, istek.stok, istek.parametreler)
        return StokYaniti(kayit_id=kaydet("stok_analizi", istek, sonuc), sonuc=sonuc,
                          grafik=grafikler.stok_grafigi(sonuc.senaryolar))

    # ---------------------------------------------------- Modül 5: finansman

    @app.post("/api/finansman/erken-odeme", response_model=ErkenOdemeYaniti)
    def erken_odeme(istek: ErkenOdemeIstegi) -> ErkenOdemeYaniti:
        sonuc = _guvenli(erken_odeme_analiz_et, istek.girdi, istek.parametreler)
        return ErkenOdemeYaniti(kayit_id=kaydet("erken_odeme", istek, sonuc), sonuc=sonuc)

    @app.post("/api/finansman/karsilastir", response_model=FinansmanYaniti)
    def finansman(istek: FinansmanIstegi) -> FinansmanYaniti:
        sonuc = _guvenli(finansman_karsilastir, istek.girdi, istek.parametreler)
        return FinansmanYaniti(kayit_id=kaydet("finansman", istek, sonuc), sonuc=sonuc,
                               grafik=grafikler.finansman_grafigi(sonuc))

    # ----------------------------------------- Modül 6–7: fiyat ve tahsilat riski

    @app.post("/api/fiyat-senaryolari", response_model=FiyatlamaYaniti)
    def fiyat(istek: FiyatlamaIstegi) -> FiyatlamaYaniti:
        sonuc = _guvenli(fiyat_senaryolari, istek.girdi, istek.parametreler)
        return FiyatlamaYaniti(kayit_id=kaydet("fiyat_senaryolari", istek, sonuc), sonuc=sonuc,
                               grafik=grafikler.senaryo_grafigi(sonuc))

    # ------------------------------------------------ Excel ve toplu analiz

    @app.get("/api/excel/sablon")
    def excel_sablon() -> Response:
        return Response(
            content=excel.sablon_olustur(), media_type=XLSX,
            headers={"Content-Disposition": "attachment; filename=karmax-sablon.xlsx"},
        )

    @app.post("/api/toplu-analiz")
    async def toplu(dosya: UploadFile = File(...)) -> dict:
        icerik = await dosya.read(excel.MAKS_DOSYA_BAYT + 1)
        try:
            yukleme = excel.excel_oku(icerik)
        except excel.ExcelYapiHatasi as e:
            raise _hata(str(e)) from None
        sonuc = toplu_analiz([u for _, u in yukleme.urunler], yukleme.parametreler)
        girdi_kaydi, sonuc_kaydi = excel.toplu_kayit_verisi(yukleme, sonuc)
        girdi_kaydi["dosya_adi"] = dosya.filename
        kayit_id = kaydet("toplu_analiz", girdi_kaydi, sonuc_kaydi)
        return {
            "kayit_id": kayit_id,
            "parametreler": yukleme.parametreler.model_dump(mode="json"),
            **sonuc_kaydi,
            "grafik": grafikler.karsilastirma_grafigi(sonuc.sonuclar) if sonuc.sonuclar else None,
        }

    @app.get("/api/toplu-analiz/{kayit_id}/excel")
    def toplu_excel(kayit_id: int) -> Response:
        veri = kayit.getir(kayit_id)
        if veri is None or veri["tur"] != "toplu_analiz":
            raise HTTPException(status_code=404, detail="Bu numarayla kayıtlı toplu analiz bulunamadı.")
        ad = f"karmax-sonuc-{kayit_id}.xlsx"
        return Response(
            content=excel.sonuc_excel_olustur(veri), media_type=XLSX,
            headers={"Content-Disposition": f"attachment; filename={ad}; filename*=UTF-8''{quote(ad)}"},
        )

    # -------------------------------------------------------------- arayüz

    @app.get("/kutuphane/plotly.min.js", include_in_schema=False)
    def plotly_js() -> FileResponse:
        # Python Plotly paketinin içindeki plotly.js: sürümler her zaman eşleşir, internet gerekmez.
        return FileResponse(PLOTLY_JS, media_type="application/javascript")

    if ARAYUZ_KLASORU.exists():
        app.mount("/statik", StaticFiles(directory=ARAYUZ_KLASORU), name="statik")

        @app.get("/", include_in_schema=False)
        def ana_sayfa() -> FileResponse:
            return FileResponse(ARAYUZ_KLASORU / "index.html")

    return app


app = uygulama_olustur()
