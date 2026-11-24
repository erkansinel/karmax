"""Karmax başlatıcı.

Karmax.bat tarafından çağrılır (doğrudan da çalıştırılabilir):
  1. Karmax zaten çalışıyorsa yalnızca tarayıcıyı açar.
  2. Değilse boş bir port bulur ve sunucuyu yalnızca bu bilgisayara açık başlatır.
  3. Sunucu hazır olunca tarayıcıyı otomatik açar.
Kapatmak için bu pencerede Ctrl + C'ye basın veya pencereyi kapatın.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ADRES = "127.0.0.1"  # yalnızca bu bilgisayardan erişilebilir
# 8000 gibi yaygın portlar başka projelerle çakışabilir; Karmax kendi aralığını kullanır.
PORTLAR = range(8737, 8788)


def karmax_calisiyor_mu(port: int) -> bool:
    """Bu portta KARMAX mı çalışıyor? Başka bir uygulamayı Karmax sanmamak için kimliğe bakılır."""
    try:
        with urllib.request.urlopen(f"http://{ADRES}:{port}/api/saglik", timeout=0.8) as y:
            veri = json.load(y)
            return veri.get("durum") == "ok" and veri.get("uygulama") == "karmax"
    except Exception:  # noqa: BLE001
        return False


def port_bos_mu(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if os.name != "nt":
            # macOS/Linux: yeni kapanmış (TIME_WAIT) portu dolu sanma. Windows'ta bu seçenek
            # kullanımdaki porta bağlanmaya izin verdiği için yalnızca diğer sistemlerde açılır.
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((ADRES, port))
            return True
        except OSError:
            return False


def hazir_olunca_ac(url: str, port: int) -> None:
    for _ in range(150):  # en fazla ~30 saniye
        if karmax_calisiyor_mu(port):
            webbrowser.open(url)
            print(f"  Tarayıcı açıldı: {url}\n  Açılmadıysa bu adresi tarayıcınıza yazın.\n")
            return
        time.sleep(0.2)
    print("  Sunucu 30 saniyede hazır olmadı. Yukarıdaki mesajları kontrol edin.")


def main() -> int:
    proje = Path(__file__).resolve().parent
    sys.path.insert(0, str(proje))

    print("\n  ============================================")
    print("   KARMAX  ·  Decisora Danışmanlık A.Ş.")
    print("  ============================================\n")

    for port in PORTLAR:
        if karmax_calisiyor_mu(port):
            url = f"http://{ADRES}:{port}/"
            print(f"  Karmax zaten çalışıyor. Tarayıcı açılıyor: {url}")
            webbrowser.open(url)
            time.sleep(2)
            return 0

    port = next((p for p in PORTLAR if port_bos_mu(p)), None)
    if port is None:
        print(f"  [HATA] {PORTLAR.start}-{PORTLAR.stop - 1} arasında boş port bulunamadı.")
        return 1

    url = f"http://{ADRES}:{port}/"
    if port != PORTLAR.start:
        print(f"  Not: {PORTLAR.start} numaralı port başka bir uygulama tarafından kullanılıyor.")
    print(f"  Karmax hazırlanıyor: {url}")
    print("  Kapatmak için bu pencerede Ctrl + C'ye basın veya pencereyi kapatın.\n")
    threading.Thread(target=hazir_olunca_ac, args=(url, port), daemon=True).start()

    import uvicorn

    try:
        uvicorn.run("karmax.api.main:app", host=ADRES, port=port, log_level="warning")
    except KeyboardInterrupt:
        pass
    print("\n  Karmax kapatıldı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
