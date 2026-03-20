@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "ROOT_DIR=%~dp0"
set "ROOT_DIR=%ROOT_DIR:~0,-1%"

set "DEFAULT_ENV=overwatch"
set "CONDA_EXE=%USERPROFILE%\miniconda3\Scripts\conda.exe"
if not exist "%CONDA_EXE%" (
  set "CONDA_EXE=conda"
)

set "PY_CMD="
set "HAS_UPDATE_TRANSLATIONS=N"

echo ==================================================
echo Overwatch Helper 一鍵互動更新工具
echo ==================================================
echo.

set /p ENV_NAME=請輸入 conda 環境名稱（預設：%DEFAULT_ENV%）: 
if "%ENV_NAME%"=="" set "ENV_NAME=%DEFAULT_ENV%"

set "PY_CMD=%CONDA_EXE% run -n %ENV_NAME% python"

echo.
echo 將使用 Python 指令：
echo   %PY_CMD%
echo.

call :ask_yes_no "是否執行【主資料更新】scripts/update_data.py？" "N"
set "RUN_UPDATE_DATA=!ANSWER!"
if /I "!RUN_UPDATE_DATA!"=="Y" (
  set "UPDATE_DATA_ARGS="

  call :ask_yes_no "Mobalytics 是否改用 Playwright（否則使用 Cloudflare）？" "N"
  if /I "!ANSWER!"=="Y" (
    set "UPDATE_DATA_ARGS=!UPDATE_DATA_ARGS! --mobalytics-method playwright"
  )

  set /p SMOKE_HERO=只抓單一英雄（可留空，例如 roadhog）: 
  if not "!SMOKE_HERO!"=="" (
    set "UPDATE_DATA_ARGS=!UPDATE_DATA_ARGS! --mobalytics-smoke-hero !SMOKE_HERO!"
  )

  call :ask_yes_no "是否包含 Gemini 補齊章節（--with-enrichment）？" "N"
  if /I "!ANSWER!"=="Y" (
    set "UPDATE_DATA_ARGS=!UPDATE_DATA_ARGS! --with-enrichment"
  )

  call :ask_yes_no "是否在主資料流程後產生靜態翻譯（--with-translations）？" "N"
  if /I "!ANSWER!"=="Y" (
    set "UPDATE_DATA_ARGS=!UPDATE_DATA_ARGS! --with-translations"
    set "HAS_UPDATE_TRANSLATIONS=Y"

    set /p UDT_HEROES=翻譯只處理指定英雄（逗號分隔，可留空）: 
    if not "!UDT_HEROES!"=="" (
      set "UPDATE_DATA_ARGS=!UPDATE_DATA_ARGS! --translation-heroes !UDT_HEROES!"
    )

    call :ask_yes_no "翻譯是否略過既有檔案（--translation-skip-existing）？" "Y"
    if /I "!ANSWER!"=="Y" (
      set "UPDATE_DATA_ARGS=!UPDATE_DATA_ARGS! --translation-skip-existing"
    )

    call :ask_yes_no "翻譯單一英雄失敗是否繼續（--translation-continue-on-error）？" "Y"
    if /I "!ANSWER!"=="Y" (
      set "UPDATE_DATA_ARGS=!UPDATE_DATA_ARGS! --translation-continue-on-error"
    )
  )
)

call :ask_yes_no "是否執行【低頻資產更新】scripts/update_assets.py？" "N"
set "RUN_UPDATE_ASSETS=!ANSWER!"
if /I "!RUN_UPDATE_ASSETS!"=="Y" (
  set "UPDATE_ASSETS_ARGS="

  call :ask_yes_no "下載圖片是否略過既有檔案（--skip-existing）？" "Y"
  if /I "!ANSWER!"=="Y" (
    set "UPDATE_ASSETS_ARGS=!UPDATE_ASSETS_ARGS! --skip-existing"
  )

  call :ask_yes_no "是否更新 maps 圖片（--update-map-images）？" "N"
  if /I "!ANSWER!"=="Y" (
    set "UPDATE_ASSETS_ARGS=!UPDATE_ASSETS_ARGS! --update-map-images"
  )

  call :ask_yes_no "是否更新 Fandom perks（--update-fandom-perks）？" "N"
  if /I "!ANSWER!"=="Y" (
    set "UPDATE_ASSETS_ARGS=!UPDATE_ASSETS_ARGS! --update-fandom-perks"
  )
)

call :ask_yes_no "是否執行【前端資料建置同步】run_build.py？" "N"
set "RUN_BUILD_SYNC=!ANSWER!"
if /I "!RUN_BUILD_SYNC!"=="Y" (
  set "RUN_BUILD_ARGS="

  if /I "!HAS_UPDATE_TRANSLATIONS!"=="Y" (
    echo 已在主資料流程啟用靜態翻譯，run_build 將略過翻譯參數以避免重複執行。
  ) else (
    call :ask_yes_no "是否在 run_build 內產生靜態翻譯（--with-translations）？" "N"
    if /I "!ANSWER!"=="Y" (
      set "RUN_BUILD_ARGS=!RUN_BUILD_ARGS! --with-translations"

      set /p RBT_HEROES=翻譯只處理指定英雄（逗號分隔，可留空）: 
      if not "!RBT_HEROES!"=="" (
        set "RUN_BUILD_ARGS=!RUN_BUILD_ARGS! --translation-heroes !RBT_HEROES!"
      )

      call :ask_yes_no "翻譯是否略過既有檔案（--translation-skip-existing）？" "Y"
      if /I "!ANSWER!"=="Y" (
        set "RUN_BUILD_ARGS=!RUN_BUILD_ARGS! --translation-skip-existing"
      )

      call :ask_yes_no "翻譯單一英雄失敗是否繼續（--translation-continue-on-error）？" "Y"
      if /I "!ANSWER!"=="Y" (
        set "RUN_BUILD_ARGS=!RUN_BUILD_ARGS! --translation-continue-on-error"
      )
    )
  )
)

echo.
echo ==================================================
echo 執行摘要
echo ==================================================
echo 主資料更新: !RUN_UPDATE_DATA!
if /I "!RUN_UPDATE_DATA!"=="Y" echo 參數: !UPDATE_DATA_ARGS!
echo 低頻資產更新: !RUN_UPDATE_ASSETS!
if /I "!RUN_UPDATE_ASSETS!"=="Y" echo 參數: !UPDATE_ASSETS_ARGS!
echo 前端資料建置同步: !RUN_BUILD_SYNC!
if /I "!RUN_BUILD_SYNC!"=="Y" echo 參數: !RUN_BUILD_ARGS!
echo.

call :ask_yes_no "確認開始執行以上流程？" "Y"
if /I "!ANSWER!"=="N" (
  echo 已取消執行。
  goto :finish
)

pushd "%ROOT_DIR%"

if /I "!RUN_UPDATE_DATA!"=="Y" (
  echo.
  echo [執行中] scripts/update_data.py !UPDATE_DATA_ARGS!
  call %PY_CMD% "%ROOT_DIR%\scripts\update_data.py" !UPDATE_DATA_ARGS!
  if errorlevel 1 (
    echo [錯誤] update_data.py 執行失敗，流程中止。
    popd
    goto :finish
  )
)

if /I "!RUN_UPDATE_ASSETS!"=="Y" (
  echo.
  echo [執行中] scripts/update_assets.py !UPDATE_ASSETS_ARGS!
  call %PY_CMD% "%ROOT_DIR%\scripts\update_assets.py" !UPDATE_ASSETS_ARGS!
  if errorlevel 1 (
    echo [錯誤] update_assets.py 執行失敗，流程中止。
    popd
    goto :finish
  )
)

if /I "!RUN_BUILD_SYNC!"=="Y" (
  echo.
  echo [執行中] run_build.py !RUN_BUILD_ARGS!
  call %PY_CMD% "%ROOT_DIR%\run_build.py" !RUN_BUILD_ARGS!
  if errorlevel 1 (
    echo [錯誤] run_build.py 執行失敗，流程中止。
    popd
    goto :finish
  )
)

popd
echo.
echo 所有已勾選流程執行完成。

:finish
echo.
pause
exit /b

:ask_yes_no
set "QUESTION=%~1"
set "DEFAULT=%~2"

:ask_yes_no_loop
set "INPUT="
set /p INPUT=%QUESTION% [Y/N]（預設 %DEFAULT%）: 
if /I "%INPUT%"=="" set "INPUT=%DEFAULT%"

if /I "%INPUT%"=="Y" (
  set "ANSWER=Y"
  exit /b 0
)

if /I "%INPUT%"=="N" (
  set "ANSWER=N"
  exit /b 0
)

echo 請輸入 Y 或 N。
goto :ask_yes_no_loop
