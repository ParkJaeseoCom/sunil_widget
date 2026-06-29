@echo off
setlocal
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP%\TeacherWidgets.lnk"
if exist "%SHORTCUT%" (
  del "%SHORTCUT%"
  echo Startup shortcut removed.
) else (
  echo Startup shortcut was not found.
)
pause
