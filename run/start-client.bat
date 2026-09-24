@echo off
rem Start the Rose Next client from Exes\ (the folder with data.idx + rose.vfs),
rem connecting to the local servers. Copies a newer build from bin\release first.
setlocal
set "ROOT=%~dp0.."
set "BIN=%ROOT%\bin\release"
set "GAME=%ROOT%\Exes"

if not exist "%GAME%\data.idx" (
    echo Game data is missing: %GAME%\data.idx
    echo See doc\ai\topics\project\local-setup-runbook.md
    pause
    exit /b 1
)

rem rosenext.exe and znzin.dll must always be deployed as a pair.
if exist "%BIN%\rosenext.exe" (
    for %%F in (rosenext.exe znzin.dll triggervfs.dll d3dx9_43.dll discord_game_sdk.dll) do (
        if exist "%BIN%\%%F" "%SystemRoot%\System32\xcopy.exe" /D /Y /Q "%BIN%\%%F" "%GAME%\" >nul
    )
)
if not exist "%GAME%\rosenext.exe" (
    echo The client is not built yet: %BIN%\rosenext.exe is missing.
    pause
    exit /b 1
)

"%SystemRoot%\System32\tasklist.exe" /FI "IMAGENAME eq sho_gameserver.exe" 2>nul | "%SystemRoot%\System32\find.exe" /I "sho_gameserver.exe" >nul || (
    echo Warning: the game server is not running. Start run\start-servers.bat first.
    "%SystemRoot%\System32\timeout.exe" /t 5 >nul
)

echo Starting the client...
start "" /D "%GAME%" "%GAME%\rosenext.exe" --server 127.0.0.1
