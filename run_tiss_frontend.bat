@echo off
title TISS Auto-Anmelden Frontend

echo ========================================
echo     TISS Auto-Anmelden Web Frontend
echo ========================================
echo.

echo Current directory: %CD%
echo.

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from python.org
    echo Make sure to check "Add Python to PATH" during installation
    goto :end
)

echo Python found! Checking version...
python --version

echo.
echo Checking required files...

if not exist "flask_backend.py" (
    echo ERROR: flask_backend.py not found
    goto :end
)
echo Found: flask_backend.py

if not exist "tiss_auto_anmelden.py" (
    echo ERROR: tiss_auto_anmelden.py not found
    goto :end
)
echo Found: tiss_auto_anmelden.py

if not exist "templates\index.html" (
    echo ERROR: templates\index.html not found
    goto :end
)
echo Found: templates\index.html

echo.
echo All files found! Installing required packages...
pip install flask selenium requests beautifulsoup4 --quiet --disable-pip-version-check

echo.
echo Starting Flask server...
echo Open your browser and go to: http://127.0.0.1:5000
echo.
echo Keep this window open while using the web interface
echo Press Ctrl+C to stop the server
echo.

python flask_backend.py

:end
echo.
echo Press any key to exit...
pause >nul