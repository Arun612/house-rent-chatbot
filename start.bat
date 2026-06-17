@echo off
title RentChat — Starting Servers
echo ============================================
echo  RentChat - House Rent PDF Chatbot
echo ============================================
echo.

REM Start the FastAPI backend in a new window
echo [1/2] Starting FastAPI backend on http://localhost:8000 ...
start "RentChat Backend" cmd /k "cd /d "%~dp0backend" && uvicorn main:app --reload --port 8000 --host 0.0.0.0"

REM Wait a moment for the backend to boot
timeout /t 3 /nobreak > nul

REM Start a simple HTTP server for the frontend in a new window
echo [2/2] Starting frontend on http://localhost:3000 ...
start "RentChat Frontend" cmd /k "cd /d "%~dp0frontend" && python -m http.server 3000"

echo.
echo ============================================
echo  Both servers starting...
echo  Backend  : http://localhost:8000
echo  Frontend : http://localhost:3000
echo  API Docs : http://localhost:8000/docs
echo ============================================
echo.
echo Opening browser in 4 seconds...
timeout /t 4 /nobreak > nul
start http://localhost:3000
