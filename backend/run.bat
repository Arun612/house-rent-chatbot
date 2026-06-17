@echo off
cd /d "%~dp0backend"
uvicorn main:app --reload --port 8000
