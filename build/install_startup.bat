@echo off
setlocal
cd /d "%~dp0"

set "EXE="
if exist "%cd%\dist\TeacherWidgets\TeacherWidgets.exe" (
  set "EXE=%cd%\dist\TeacherWidgets\TeacherWidgets.exe"
  set "WORKDIR=%cd%\dist\TeacherWidgets"
)
if not defined EXE if exist "%cd%\TeacherWidgets\TeacherWidgets.exe" (
  set "EXE=%cd%\TeacherWidgets\TeacherWidgets.exe"
  set "WORKDIR=%cd%\TeacherWidgets"
)
if not defined EXE (
  echo Built exe was not found. Run pyinstaller first.
  pause
  exit /b 1
)
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP%\TeacherWidgets.lnk"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%');" ^
  "$s.TargetPath='%EXE%';$s.WorkingDirectory='%WORKDIR%';" ^
  "$s.IconLocation='%EXE%,0';$s.WindowStyle=7;$s.Save()"
echo Startup shortcut created: %SHORTCUT%
pause
