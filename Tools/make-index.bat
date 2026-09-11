@echo off
rem ============================================================
rem  Case Creator - rebuild Cases/index.html
rem
rem  Double-click this file. It runs make-index.ps1 beside it,
rem  which lists every .zip in the Cases folder one level up and
rem  writes Cases/index.html.
rem
rem  Needed because Home Assistant's /local/ does not generate
rem  directory listings, and because Python's http.server stops
rem  generating one once index.html exists.
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
