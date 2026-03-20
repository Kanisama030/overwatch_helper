@echo off
REM 已改為純靜態翻譯流程（不再啟動 API）

echo ========================================
echo Overwatch Helper Static Translation
echo ========================================
echo.
echo Backend API 執行層已移除。
echo 目前請改用預生成靜態翻譯檔流程：
echo   python run_build.py --with-translations --translation-skip-existing
echo.

cd /d "%~dp0"
C:\Users\Kani\miniconda3\Scripts\conda.exe run -n overwatch python run_build.py --with-translations --translation-skip-existing
