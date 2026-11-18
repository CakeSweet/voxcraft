@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   VoxCraft Studio - Instalacao Rapida (Python + Atalhos)
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
    echo Baixe o Python 3.10+ em https://www.python.org/downloads/ e marque "Add Python to PATH".
    pause
    exit /b 1
)

echo [1/3] Instalando dependencias do VoxCraft Studio...
%PY_CMD% -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

echo.
echo [2/3] Localizando pythonw.exe para abrir sem janela de console...
for /f "delims=" %%P in ('%PY_CMD% -c "import os, sys; p = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'); print(p if os.path.exists(p) else sys.executable)"') do set "PYTHONW_EXE=%%P"

echo.
echo [3/3] Criando atalhos na Area de Trabalho e Menu Iniciar...
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
    "$startMenu = Join-Path ([Environment]::GetFolderPath('Programs')) 'VoxCraft Studio'; " ^
    "New-Item -ItemType Directory -Force -Path $startMenu | Out-Null; " ^
    "foreach ($dir in @($desktop, $startMenu)) { " ^
    "  $lnk = $ws.CreateShortcut((Join-Path $dir 'VoxCraft Studio.lnk')); " ^
    "  $lnk.TargetPath = '%PYTHONW_EXE%'; " ^
    "  $lnk.Arguments = '\"%APP_DIR%\app.py\"'; " ^
    "  $lnk.WorkingDirectory = '%APP_DIR%'; " ^
    "  $lnk.IconLocation = '%APP_DIR%\assets\voxcraft.ico'; " ^
    "  $lnk.Description = 'VoxCraft Studio - Modulador de Voz em Tempo Real'; " ^
    "  $lnk.Save(); " ^
    "}"

echo.
echo ============================================================
echo   VoxCraft Studio instalado com sucesso!
echo   Atalho criado na Area de Trabalho e no Menu Iniciar.
echo   Iniciando o VoxCraft Studio agora...
echo ============================================================
start "" "%PYTHONW_EXE%" "%APP_DIR%\app.py"
timeout /t 2 >nul
