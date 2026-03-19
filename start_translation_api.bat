@echo off
REM 啟動 Overwatch Helper 翻譯 API 服務

echo ========================================
echo Overwatch Helper Translation API
echo ========================================
echo.
echo Starting FastAPI server on http://127.0.0.1:8888
echo Press Ctrl+C to stop the server
echo.

cd /d "%~dp0backend"
C:\Users\Kani\miniconda3\Scripts\conda.exe run -n overwatch uvicorn main:app --host 127.0.0.1 --port 8888 --reload
