@echo off
title BabyBoost - Starting Server...
color 1F
echo.
echo  ============================================
echo    BabyBoost ^| Starting Application...
echo  ============================================
echo.
:: Move to the folder where this .bat file lives
cd /d "%~dp0"
:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Please install Python and add it to PATH.
    echo.
    pause
    exit /b 1
)
:: Check requirements.txt exists
if not exist requirements.txt (
    echo  [ERROR] requirements.txt not found. Make sure it is in the same folder.
    echo.
    pause
    exit /b 1
)
:: Install dependencies using the same Python that will run the app
echo  Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt >nul 2>&1
echo  Launching app_local.py...
echo  Open your browser at: http://127.0.0.1:5000
echo.
echo  Press Ctrl+C to stop the server.
echo.
python app_local.py
echo.
echo  Server stopped.
pause
