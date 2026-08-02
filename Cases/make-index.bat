@echo off
rem ============================================================
rem  Case Creator - rebuild Cases/index.html
rem
rem  Double-click this file. It lists every .zip sitting next to
rem  it and writes index.html, which Home Assistant needs because
rem  /local/ does not generate directory listings.
rem
rem  Then copy index.html into your HA Cases folder.
rem ============================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make-index.ps1"

if errorlevel 1 (
  echo.
  echo Something went wrong - see the message above.
)
echo.
pause
