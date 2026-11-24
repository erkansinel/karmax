@echo off
setlocal
cd /d "%~dp0"
title Karmax - Decisora Danismanlik A.S.

echo.
echo   Karmax baslatiliyor...
echo.

if not exist "requirements.txt" (
  echo   [HATA] Bu dosya Karmax klasorunun icinde olmali.
  echo   Karmax.bat, requirements.txt ile ayni klasorde durmalidir.
  goto :hata
)

rem --- 1. Python 3.11 veya ustunu bul -------------------------------------
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY goto :python_yok

rem --- 2. Sanal ortam (eksikse veya bozuksa yeniden olustur) --------------
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
  if errorlevel 1 (
    echo   Eski sanal ortam uygun degil, yeniden olusturuluyor...
    rmdir /s /q ".venv"
  )
)
if not exist ".venv\Scripts\python.exe" (
  if exist ".venv" rmdir /s /q ".venv"
  echo   Ilk kurulum: sanal ortam olusturuluyor...
  %PY% -m venv .venv
  if errorlevel 1 goto :hata
)

rem --- 3. Paketler (yalnizca ilk seferde veya requirements.txt degisince) --
fc /b "requirements.txt" ".venv\karmax-kurulu.txt" >nul 2>&1
if errorlevel 1 (
  echo   Gerekli paketler kuruluyor. Ilk seferde 1-3 dakika surebilir...
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
  if errorlevel 1 (
    echo.
    echo   [HATA] Paketler kurulamadi. Internet baglantinizi kontrol edin.
    goto :hata
  )
  copy /y "requirements.txt" ".venv\karmax-kurulu.txt" >nul
)

rem --- 4. Karmax'i baslat ve tarayiciyi ac ---------------------------------
".venv\Scripts\python.exe" baslat.py
if errorlevel 1 goto :hata
exit /b 0

:python_yok
echo   [HATA] Python 3.11 veya ustu bulunamadi.
echo.
echo   1. https://www.python.org/downloads/ adresinden Python'u indirin.
echo   2. Kurulumun ilk ekraninda "Add python.exe to PATH" kutusunu isaretleyin.
echo   3. Kurulum bitince Karmax.bat dosyasina tekrar cift tiklayin.
echo.
pause
exit /b 1

:hata
echo.
echo   Karmax baslatilamadi. Bu penceredeki mesajlari Decisora'ya iletin.
echo.
pause
exit /b 1
