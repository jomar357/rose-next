@echo off
rem Stop the three Rose Next servers (game -> world -> login).
rem Log your character out in the client first: this closes the servers immediately.
setlocal
for %%S in (sho_gameserver.exe sho_worldserver.exe sho_loginserver.exe) do (
    "%SystemRoot%\System32\tasklist.exe" /FI "IMAGENAME eq %%S" 2>nul | "%SystemRoot%\System32\find.exe" /I "%%S" >nul && (
        echo Stopping %%S ...
        "%SystemRoot%\System32\taskkill.exe" /F /IM %%S >nul
    ) || (
        echo %%S is not running.
    )
)
echo Done.
"%SystemRoot%\System32\timeout.exe" /t 3 >nul
