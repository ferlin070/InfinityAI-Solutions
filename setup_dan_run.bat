@echo off
title Multi-Agent AI Setup & Run
echo ==========================================
echo    MULTI-AGENT AI ORCHESTRATOR SETUP
echo ==========================================
echo.

echo [1/3] Menyemak pemasangan Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] Ralat: Python tidak dijumpai di komputer anda.
    echo.
    echo Sila buat perkara berikut:
    echo 1. Muat turun Python di: https://www.python.org/downloads/
    echo 2. Semasa install, PASTIKAN anda tick "Add Python to PATH".
    echo 3. Selepas install, buka semula fail ini.
    echo.
    pause
    exit
)

echo.
echo [2/3] Memasang library (Ini mungkin mengambil masa sebentar)...
python -m pip install -r requirements.txt

echo.
echo [3/3] Memulakan Server...
echo.
echo --------------------------------------------------
echo  SERVER AKAN BERMULA DI: http://localhost:8000
echo  (Sila buka alamat ini di browser anda)
echo --------------------------------------------------
echo.
python main.py
pause
