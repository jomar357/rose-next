@echo off
rem Close every running Rose Next client.
"%SystemRoot%\System32\tasklist.exe" /FI "IMAGENAME eq rosenext.exe" 2>nul | "%SystemRoot%\System32\find.exe" /I "rosenext.exe" >nul && (
    "%SystemRoot%\System32\taskkill.exe" /F /IM rosenext.exe >nul
    echo Client closed.
) || (
    echo The client is not running.
)
"%SystemRoot%\System32\timeout.exe" /t 2 >nul
