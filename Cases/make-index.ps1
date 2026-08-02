# Rebuild index.html from the .zip files sitting next to this script.
# Handles &, spaces, #, %, apostrophes and other awkward filename characters.

$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = Join-Path $dir 'index.html'

$zips = Get-ChildItem -LiteralPath $dir -Filter '*.zip' -File |
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
if ($zips.Count -eq 0) {
  Write-Host 'WARNING: no .zip files found in this folder.' -ForegroundColor Yellow
  Write-Host "index.html was written but lists nothing."
} else {
  Write-Host ("Wrote index.html with " + $zips.Count + " case file(s):") -ForegroundColor Green
  foreach ($z in $zips) { Write-Host ('   ' + $z.Name) }
  Write-Host ''
  Write-Host 'Now copy index.html into your Home Assistant Cases folder.'
}
