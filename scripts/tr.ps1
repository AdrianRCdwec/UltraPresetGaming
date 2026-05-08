param(
    [string]$Salida = $(Join-Path (Join-Path (Split-Path $PSScriptRoot -Parent) "docs") "structure.txt"),
    [string[]]$ExcluirDirectorios = @(".venv", "__pycache__", ".vscode", ".git", ".clinerules"),
    [switch]$f
)

$RutaCompleta = (Get-Location).Path

function Get-TreeAscii {
    param(
        [string]$Directorio,
        [string]$Prefijo = "",
        [string[]]$ExcluirDirectorios,
        [switch]$f
    )

    $items = Get-ChildItem -LiteralPath $Directorio -Force |
        Where-Object {
            if ($_.PSIsContainer) {
                $_.Name -notin $ExcluirDirectorios
            }
            else {
                (-not $f.IsPresent) -and
                ($_.Extension -ne ".jpg") -and
                ($_.Extension -ne ".png") -and
                ($_.Extension -ne ".webp") -and
                ($_.Extension -ne ".xhtml")
            }
        } |
        Sort-Object @{ Expression = { -not $_.PSIsContainer } }, Name

    for ($i = 0; $i -lt $items.Count; $i++) {
        $item = $items[$i]
        $esUltimo = ($i -eq $items.Count - 1)

        $rama = if ($esUltimo) { "`-- " } else { "|-- " }
        $linea = $Prefijo + $rama + $item.Name
        $linea

        if ($item.PSIsContainer) {
            $nuevoPrefijo = if ($esUltimo) { $Prefijo + "    " } else { $Prefijo + "|   " }

            Get-TreeAscii -Directorio $item.FullName `
                            -Prefijo $nuevoPrefijo `
                            -ExcluirDirectorios $ExcluirDirectorios `
                            -f:$f.IsPresent
        }
    }
}

$resultado = @()
$resultado += "."
$resultado += Get-TreeAscii -Directorio $RutaCompleta `
                            -ExcluirDirectorios $ExcluirDirectorios `
                            -f:$f.IsPresent

$resultado | Set-Content -Path $Salida -Encoding UTF8

Write-Host "Tree generado en $Salida"