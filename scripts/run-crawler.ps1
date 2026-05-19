param(
    [switch]$s,
    [switch]$d
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    param(
        [string]$StartPath
    )

    $current = Get-Item $StartPath

    while ($null -ne $current) {
        $backendPath = Join-Path $current.FullName "backend"
        $readmePath  = Join-Path $current.FullName "README.md"
        $scriptsPath = Join-Path $current.FullName "scripts"

        if ((Test-Path $backendPath) -and (Test-Path $readmePath) -and (Test-Path $scriptsPath)) {
            return $current.FullName
        }

        $parentPath = Split-Path $current.FullName -Parent
        if ([string]::IsNullOrWhiteSpace($parentPath) -or $parentPath -eq $current.FullName) {
            break
        }

        $current = Get-Item $parentPath
    }

    throw "No se ha encontrado la raíz del repositorio."
}

try {
    $repoRoot = Get-RepoRoot -StartPath $PSScriptRoot
}
catch {
    $repoRoot = Get-RepoRoot -StartPath (Get-Location).Path
}

$backendPath = Join-Path $repoRoot "backend"

Push-Location $backendPath

$venvActivate = Join-Path $backendPath ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    $venvActivate = Join-Path $backendPath "venv\Scripts\Activate.ps1"
}

if (-not (Test-Path $venvActivate)) {
    Pop-Location
    throw "No se encontró el entorno virtual en backend\.venv ni en backend\venv."
}

& $venvActivate

if ($d.IsPresent) {
    $env:SCRAPER_DEBUG      = "true"
    $env:SCRAPER_SECUENCIAL = "true"
    Write-Host "Modo debug activado: ejecución secuencial con navegador visible." -ForegroundColor Cyan
}
elseif ($s.IsPresent) {
    $env:SCRAPER_DEBUG      = "false"
    $env:SCRAPER_SECUENCIAL = "true"
    Write-Host "Modo secuencial activado." -ForegroundColor Yellow
}
else {
    $env:SCRAPER_DEBUG      = "false"
    $env:SCRAPER_SECUENCIAL = "false"
    Write-Host "Modo normal activado." -ForegroundColor Green
}

Write-Host "Repositorio: $repoRoot" -ForegroundColor DarkGray
Write-Host "Backend: $backendPath"  -ForegroundColor DarkGray
Write-Host "Lanzando crawler..."    -ForegroundColor Magenta

$env:PYTHONPATH = $backendPath
python .\scrapper_app\main_crawler.py

Pop-Location