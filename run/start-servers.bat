@echo off
rem Start the three Rose Next servers (login -> world -> game), each in its own window.
rem Uses the release build in bin\release and the local config dev\server\server.toml.
setlocal
set "ROOT=%~dp0.."
set "BIN=%ROOT%\bin\release"
set "CFG=%ROOT%\dev\server\server.toml"

if not exist "%BIN%\sho_gameserver.exe" (
    echo The servers are not built yet: %BIN%\sho_gameserver.exe is missing.
    echo See doc\ai\topics\project\local-setup-runbook.md
    pause
    exit /b 1
)
if not exist "%CFG%" (
    echo Missing server config: %CFG%
    echo Create it from doc\server.toml.example, see doc\ai\topics\project\local-setup-runbook.md
    pause
    exit /b 1
)

for %%S in (sho_loginserver.exe sho_worldserver.exe sho_gameserver.exe) do (
    "%SystemRoot%\System32\tasklist.exe" /FI "IMAGENAME eq %%S" 2>nul | "%SystemRoot%\System32\find.exe" /I "%%S" >nul && (
        echo %%S is already running. Run stop-servers.bat first if you want a clean restart.
        pause
        exit /b 0
    )
)

echo Starting login server...
start "Rose Login Server" /D "%BIN%" "%BIN%\sho_loginserver.exe" --config "%CFG%"
"%SystemRoot%\System32\ping.exe" -n 4 127.0.0.1 >nul

echo Starting world server...
start "Rose World Server" /D "%BIN%" "%BIN%\sho_worldserver.exe" --config "%CFG%"
"%SystemRoot%\System32\ping.exe" -n 4 127.0.0.1 >nul

echo Starting game server...
start "Rose Game Server" /D "%BIN%" "%BIN%\sho_gameserver.exe" --config "%CFG%"

echo.
echo All three servers are starting in their own windows.
echo The game server needs about 30 seconds to load every zone before you can log in.
echo Logs: dev\server\log\
"%SystemRoot%\System32\timeout.exe" /t 5 >nul
