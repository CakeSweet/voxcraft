@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   VoxCraft Studio - Gerador de Executavel e Instalador
echo ============================================================
echo.

set "PY_CMD="
where python >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=python"
) else (
    where py >nul 2>&1
    if %errorlevel%==0 (
        set "PY_CMD=py -3"
    )
)

if "%PY_CMD%"=="" (
    echo [ERRO] Python 3 nao encontrado no PATH.
    echo Instale o Python 3.10+ em https://www.python.org/downloads/ e marque "Add Python to PATH".
    pause
    exit /b 1
)

echo [1/4] Instalando dependencias e PyInstaller...
%PY_CMD% -m pip install --upgrade pip
%PY_CMD% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

echo.
echo [2/4] Limpando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist\VoxCraftStudio" rmdir /s /q "dist\VoxCraftStudio"
if not exist "Output" mkdir "Output"

echo.
echo [3/4] Compilando executavel nativo (PyInstaller)...
%PY_CMD% -m PyInstaller --noconfirm --clean --windowed ^
    --name "VoxCraftStudio" ^
    --icon="assets\voxcraft.ico" ^
    --add-data "assets;assets" ^
    --hidden-import=pystray._win32 ^
    --hidden-import=PIL._tkinter_finder ^
    --collect-all customtkinter ^
    app.py

if errorlevel 1 (
    echo [ERRO] Falha ao compilar o executavel com PyInstaller.
    pause
    exit /b 1
)

echo.
echo [4/4] Gerando instalador Windows...
set "ISCC_EXE="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if "%ISCC_EXE%"=="" (
    for /f "delims=" %%I in ('where ISCC 2^>nul') do set "ISCC_EXE=%%I"
)

if not "%ISCC_EXE%"=="" (
    "%ISCC_EXE%" installer.iss
    if errorlevel 1 (
        echo [ERRO] Falha ao compilar o instalador com Inno Setup.
        pause
        exit /b 1
    )
    echo.
    echo ============================================================
    echo   SUCESSO! Instalador criado em:
    echo   Output\VoxCraftStudio_Setup.exe
    echo ============================================================
) else (
    echo [AVISO] Inno Setup 6 nao encontrado. Gerando pacote portatil ZIP...
    powershell -NoProfile -Command "Compress-Archive -Path 'dist\VoxCraftStudio\*' -DestinationPath 'Output\VoxCraftStudio_Portatil.zip' -Force"
    echo.
    echo ============================================================
    echo   Executavel pronto em: dist\VoxCraftStudio\VoxCraftStudio.exe
    echo   Pacote portatil ZIP em: Output\VoxCraftStudio_Portatil.zip
    echo.
    echo   Para gerar o instalador Setup.exe classico, instale o Inno Setup 6
    echo   (https://jrsoftware.org/isdl.php) e execute este script novamente.
    echo ============================================================
)

pause
