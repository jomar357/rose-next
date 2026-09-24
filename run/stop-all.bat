@echo off
rem Close the client, then stop all three servers.
call "%~dp0stop-client.bat"
call "%~dp0stop-servers.bat"
