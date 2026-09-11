# ==============================================================================
#  Case Creator - rebuild Cases/index.html
#
#  PURPOSE
#    Writes Cases/index.html listing every .zip in the Cases folder. The apps
#    read that file to discover cases on any server that does not generate a
#    directory listing - Home Assistant's /local/ never does, and Python's
#    http.server stops doing so the moment this file exists.
#
#  WHEN TO RUN
#    After adding, renaming or deleting a .zip by hand, and before copying
#    files up to Home Assistant. Case Creator rebuilds this file itself after
#    every save when folder access is granted, so day to day you rarely need it.
#
#  PREREQUISITES
#    Windows PowerShell 5.1 or later. No modules, no network access.
#    Run it by double-clicking make-index.bat, which sits beside this file.
#
#  SAFETY
#    Reads filenames only - the zips are never opened. Writes exactly one file,
#    Cases/index.html. Deletes nothing. Stops on the first error.
# ==============================================================================

$ErrorActionPreference = 'Stop'

# ===== USER SETTINGS ==========================================================
# Folder holding the case .zip files.
#
# The default resolves to the Cases folder one level up from this script, i.e.
# the layout the README describes:
#
#     <install>\Tools\make-index.ps1     <- this file
#     <install>\Cases\*.zip              <- the target
#
# If you keep your cases elsewhere, replace the whole line with a literal path:
#     $CasesFolder = 'D:\SomewhereElse\Cases'
$CasesFolder = Join-Path (Split-Path -Parent $PSScriptRoot) 'Cases'
# ==============================================================================

if (-not (Test-Path -LiteralPath $CasesFolder -PathType Container)) {
  Write-Host ''
  Write-Host 'ERROR: cases folder not found.' -ForegroundColor Red
  Write-Host ("  Looked in: " + $CasesFolder)
  Write-Host ''
  Write-Host 'This script expects to live in a Tools folder beside Cases. If you'
  Write-Host 'moved it, edit $CasesFolder near the top of make-index.ps1.'
  exit 1
}

$out  = Join-Path $CasesFolder 'index.html'
$zips = Get-ChildItem -LiteralPath $CasesFolder -Filter '*.zip' -File |
        Sort-Object { $_.Name }

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add('<!DOCTYPE html>')
$lines.Add('<html>')
$lines.Add('<head><meta charset="utf-8"><title>Cases</title></head>')
$lines.Add('<body>')
$lines.Add('<h1>Index of Cases/</h1>')
$lines.Add('<ul>')

foreach ($z in $zips) {
  $name = $z.Name
  # href: percent-encode everything unsafe, so & # % ? and spaces survive the trip
  $href = [uri]::EscapeDataString($name)
  # visible text: HTML-escape so & and <> render correctly
  $text = [System.Net.WebUtility]::HtmlEncode($name)
  $lines.Add('  <li><a href="' + $href + '">' + $text + '</a></li>')
}

$lines.Add('</ul>')
$lines.Add('</body>')
$lines.Add('</html>')

# UTF-8 without BOM
$enc = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($out, ($lines -join "`r`n"), $enc)

Write-Host ''
Write-Host ('Cases folder: ' + $CasesFolder) -ForegroundColor Cyan
if ($zips.Count -eq 0) {
  Write-Host 'WARNING: no .zip files found in that folder.' -ForegroundColor Yellow
  Write-Host 'index.html was written but lists nothing - check the path above.'
} else {
  Write-Host ("Wrote index.html with " + $zips.Count + " case file(s):") -ForegroundColor Green
  foreach ($z in $zips) { Write-Host ('   ' + $z.Name) }
  Write-Host ''
  Write-Host 'If you publish to Home Assistant, copy index.html up along with any'
  Write-Host 'new or changed .zip files.'
}
