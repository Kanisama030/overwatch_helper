@echo off
setlocal
cd /d %~dp0

echo ============================================
echo   Overwatch Helper Data Updater
echo ============================================

:: 檢查 Conda 環境
echo [1/3] 正在啟用 Conda 環境 (overwatch)...
call conda activate overwatch
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 無法啟用 conda 環境 'overwatch'。請確認是否有安裝 Conda 且環境名稱正確。
    pause
    exit /b %ERRORLEVEL%
)

:: 執行更新腳本
echo [2/3] 正在啟動 Python 更新作業...
python update_data.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 更新過程中出錯。
    pause
    exit /b %ERRORLEVEL%
)

echo [3/3] 更新成功！
echo ============================================
echo   你可以關閉此視窗或按任意鍵退出。
pause
