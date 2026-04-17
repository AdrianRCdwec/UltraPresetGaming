param(
    [string]$Ruta = ".",
    [string]$Salida = $(Join-Path $PSScriptRoot "structure.txt"),
    [string[]]$ExcluirDirectorios = @(".venv", "__pycache__", ".vscode", ".git"),
    [switch]$f
)

if ([string]::IsNullOrWhiteSpace($Ruta)) {
    $Ruta = "."
}
$RutaCompleta = (Resolve-Path $Ruta).Path

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
                # Si el switch -f está presente, devolvemos $true y el archivo se incluye
                -not $f.IsPresent
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