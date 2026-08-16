@echo off
setlocal
cd /d "%~dp0.."

rem ---- pick python ----
set "PY=python"
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo Python not found. Install Python 3.10-3.12 from python.org and check "Add to PATH".
    pause
    exit /b 1
  )
  set "PY=py -3"
)

if not exist .venv (
  echo Creating virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 ( echo venv creation failed & pause & exit /b 1 )
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r build\requirements.txt
if errorlevel 1 ( echo pip install failed & pause & exit /b 1 )

echo Running self-test...
".venv\Scripts\python.exe" app\main.py --selftest
if errorlevel 1 ( echo SELFTEST FAILED & pause & exit /b 1 )

echo Building icon...
".venv\Scripts\python.exe" build\make_icon.py
if errorlevel 1 ( echo icon build failed & pause & exit /b 1 )

echo Building TimeApp.exe (this takes a few minutes)...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name TimeApp --icon build\app.ico ^
  --collect-submodules comtypes --collect-submodules truststore app\main.py
if errorlevel 1 ( echo PyInstaller failed & pause & exit /b 1 )

echo.
echo ==========================================
echo   Ready: %cd%\dist\TimeApp.exe
echo ==========================================
pause
