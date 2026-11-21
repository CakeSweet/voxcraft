param(
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Test-VBCableInstalled {
    $deviceNames = @()

    if (Get-Command -Name Get-PnpDevice -ErrorAction SilentlyContinue) {
        try {
            $deviceNames += @(
                Get-PnpDevice -ErrorAction Stop |
                    ForEach-Object { $_.FriendlyName }
            )
        } catch {
        }
    }

    if (Get-Command -Name Get-CimInstance -ErrorAction SilentlyContinue) {
        try {
            $deviceNames += @(
                Get-CimInstance -ClassName Win32_SoundDevice -ErrorAction Stop |
                    ForEach-Object { $_.Name }
            )
        } catch {
        }
    }

    return [bool]($deviceNames | Where-Object { $_ -match "VB-Audio Virtual Cable" })
}

if (Test-VBCableInstalled) {
    exit 0
}

if ($CheckOnly) {
    exit 1
}

$workDir = $null
$exitCode = 0
try {
    $workDir = Join-Path $env:TEMP ("VoxCraft_VBCable_" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null
    $zipPath = Join-Path $workDir "vbcable.zip"
    $urls = @(
        "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip",
        "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip",
        "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack.zip"
    )

    $downloaded = $false
    foreach ($url in $urls) {
        try {
            Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing -TimeoutSec 45
            if ((Test-Path $zipPath) -and ((Get-Item $zipPath).Length -gt 100000)) {
                $downloaded = $true
                break
            }
        } catch {
            Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
        }
    }

    if (-not $downloaded) {
        try {
            $response = Invoke-WebRequest -Uri "https://vb-audio.com/Cable/" -UseBasicParsing -TimeoutSec 20
            if ($response.Content -match '(https?://[^\s"''<>]*VBCABLE_Driver_Pack[^\s"''<>]*\.zip)') {
                Invoke-WebRequest -Uri $Matches[1] -OutFile $zipPath -UseBasicParsing -TimeoutSec 45
                if ((Test-Path $zipPath) -and ((Get-Item $zipPath).Length -gt 100000)) {
                    $downloaded = $true
                }
            }
        } catch {
        }
    }

    if (-not $downloaded) {
        throw "The VB-Audio Virtual Cable driver could not be downloaded."
    }

    $extractDir = Join-Path $workDir "extracted"
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
    $setupExe = Get-ChildItem -Path $extractDir -Recurse -Filter "VBCABLE_Setup_x64.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $setupExe) {
        $setupExe = Get-ChildItem -Path $extractDir -Recurse -Filter "VBCABLE_Setup*.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1
    }
    if (-not $setupExe) {
        throw "The downloaded package does not contain the VB-Cable installer."
    }

    $process = Start-Process -FilePath $setupExe.FullName -Verb RunAs -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "The VB-Cable installer returned exit code $($process.ExitCode)."
    }
    if (-not (Test-VBCableInstalled)) {
        throw "Windows did not detect VB-Audio Virtual Cable after installation."
    }
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    $exitCode = 1
} finally {
    if ($workDir -and (Test-Path -LiteralPath $workDir)) {
        Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

exit $exitCode
