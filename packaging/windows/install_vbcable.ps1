$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$workDir = Join-Path $env:TEMP "VoxCraft_VBCable"
if (Test-Path $workDir) {
    Remove-Item -Path $workDir -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $workDir -Force | Out-Null

$zipPath = Join-Path $workDir "vbcable.zip"
$urls = @(
    "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip",
    "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip",
    "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack.zip"
)

$downloaded = $false
foreach ($u in $urls) {
    try {
        Invoke-WebRequest -Uri $u -OutFile $zipPath -UseBasicParsing -TimeoutSec 45
        if ((Test-Path $zipPath) -and ((Get-Item $zipPath).Length -gt 100000)) {
            $downloaded = $true
            break
        }
    } catch {
        Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
    }
}

if (-not $downloaded) {
    try {
        $resp = Invoke-WebRequest -Uri "https://vb-audio.com/Cable/" -UseBasicParsing -TimeoutSec 20
        if ($resp.Content -match '(https?://[^\s"''<>]*VBCABLE_Driver_Pack[^\s"''<>]*\.zip)') {
            Invoke-WebRequest -Uri $Matches[1] -OutFile $zipPath -UseBasicParsing -TimeoutSec 45
            if ((Test-Path $zipPath) -and ((Get-Item $zipPath).Length -gt 100000)) {
                $downloaded = $true
            }
        }
    } catch {
    }
}

if ($downloaded) {
    try {
        $extractDir = Join-Path $workDir "extracted"
        Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
        $setupExe = Get-ChildItem -Path $extractDir -Recurse -Filter "VBCABLE_Setup_x64.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $setupExe) {
            $setupExe = Get-ChildItem -Path $extractDir -Recurse -Filter "VBCABLE_Setup*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        }
        if ($setupExe) {
            Start-Process -FilePath $setupExe.FullName -Verb RunAs -Wait
            exit 0
        }
    } catch {
    }
}

Start-Process "https://vb-audio.com/Cable/"
exit 0
