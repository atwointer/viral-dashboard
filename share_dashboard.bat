@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
) else (
    set "PYTHON_CMD=python"
)

echo [1/3] Checking Python...
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo Python launcher was not found.
    echo Install Python first, then run this file again.
    pause
    exit /b 1
)

echo.
echo [2/3] Checking Streamlit...
%PYTHON_CMD% -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo Streamlit is not installed yet. Installing requirements once...
    %PYTHON_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Failed to install requirements.
        pause
        exit /b 1
    )
)

echo.
echo [3/3] Starting Streamlit for LAN sharing...
echo.
echo Open this dashboard on other PCs using:
ipconfig | findstr /R "IPv4"
echo Then use http://YOUR_IP:8501
echo.

start "" http://127.0.0.1:8501
%PYTHON_CMD% -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true

echo.
echo Dashboard stopped.
pause
