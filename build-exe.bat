@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
set "TESS=C:\Program Files\Tesseract-OCR"

if not exist "%PY%" (
  echo Δεν βρέθηκε το .venv. Τρέξε το bat μέσα από τον φάκελο του Metafrasi.
  pause
  exit /b 1
)

if not exist "models\translate-en_el-1_9\model\model.bin" (
  echo Λείπει το μοντέλο μετάφρασης στον φάκελο models.
  pause
  exit /b 1
)

if not exist "%TESS%\tesseract.exe" (
  echo Λείπει το Tesseract OCR από το "%TESS%".
  pause
  exit /b 1
)

echo Εγκατάσταση PyInstaller...
"%PY%" -m pip install pyinstaller
if errorlevel 1 goto fail

echo Αντιγραφή Tesseract και μοντέλου μετάφρασης...
if exist "bundle\tesseract" rmdir /s /q "bundle\tesseract"
mkdir "bundle\tesseract\tessdata"
copy /y "%TESS%\tesseract.exe" "bundle\tesseract\" >nul
copy /y "%TESS%\*.dll" "bundle\tesseract\" >nul
copy /y "%TESS%\tessdata\eng.traineddata" "bundle\tesseract\tessdata\" >nul
if errorlevel 1 goto fail

if not exist "metafrasi.ico" (
  echo Λείπει το metafrasi.ico στον φάκελο του προγράμματος.
  pause
  exit /b 1
)

if exist "dist\Metafrash.exe" del /f /q "dist\Metafrash.exe"
if exist "dist\Metafrasi.exe" del /f /q "dist\Metafrasi.exe"
echo Δημιουργία του προγράμματος. Μπορεί να πάρει μερικά λεπτά...
"%PY%" -m PyInstaller --noconfirm --clean --windowed --onedir --name Metafrasi ^
  --icon "metafrasi.ico" ^
  --add-data "metafrasi.ico;." ^
  --add-data "models\translate-en_el-1_9;models\translate-en_el-1_9" ^
  --add-data "bundle\tesseract;tesseract" ^
  --hidden-import ctranslate2 ^
  --hidden-import sentencepiece ^
  --hidden-import bettercam ^
  --hidden-import comtypes ^
  --hidden-import comtypes.client ^
  --hidden-import numpy ^
  --hidden-import PIL ^
  --hidden-import PIL.ImageGrab ^
  --hidden-import pytesseract ^
  --collect-all ctranslate2 ^
  --collect-all sentencepiece ^
  --collect-submodules bettercam ^
  main.py
if errorlevel 1 goto fail

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo Εγκατάσταση του Inno Setup για τον installer...
  winget install --id JRSoftware.InnoSetup --exact --accept-package-agreements --accept-source-agreements --silent
  if errorlevel 1 goto fail
  if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
  if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
  if not exist "%ISCC%" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)
if not exist "%ISCC%" (
  echo Το πρόγραμμα φτιάχτηκε στον φάκελο dist\Metafrasi
  echo Ο installer δεν δημιουργήθηκε γιατί λείπει το Inno Setup.
  pause
  exit /b 1
)

echo Δημιουργία installer...
"%ISCC%" "%~dp0installer.iss"
if errorlevel 1 goto fail

echo.
echo Έτοιμο: %~dp0dist\Metafrasi-Setup.exe
echo Τρέξε αυτό για εγκατάσταση. Έχει μέσα τη μετάφραση και το Tesseract.
pause
exit /b 0

:fail
echo.
echo Η δημιουργία του exe απέτυχε.
pause
exit /b 1
