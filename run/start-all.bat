@echo off
rem Start the servers, wait for the game server to load, then start the client.
setlocal
call "%~dp0start-servers.bat"
"%SystemRoot%\System32\tasklist.exe" /FI "IMAGENAME eq sho_gameserver.exe" 2>nul | "%SystemRoot%\System32\find.exe" /I "sho_gameserver.exe" >nul || exit /b 1
echo Waiting 30 seconds for the game server to finish loading...
"%SystemRoot%\System32\ping.exe" -n 31 127.0.0.1 >nul
call "%~dp0start-client.bat"
