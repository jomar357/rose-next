@echo off
rem Create a game account in the local database (asks for name, password and access level).
setlocal
set "PWSH=pwsh.exe"
where pwsh.exe >nul 2>nul || set "PWSH=%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe"
"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0create-account.ps1"
pause
