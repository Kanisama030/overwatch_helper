#!/usr/bin/env python3
"""
run_build.py
完整的前端資料建置流程：
1. 執行 scripts/download_master_guide_assets.py 下載 guide 圖片
2. 執行 scripts/build_app_data.py 產生衍生資料
3. （可選）執行 scripts/prewarm_translation_cache.py 產生靜態翻譯檔
4. 將 data/app/* 與 data/assets/* 同步到 frontend/public/data/
5. 提示是否需要重建前端
"""
import subprocess
import sys
import os
import shutil
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_APP_DIR = os.path.join(BASE_DIR, "data", "app")
FRONTEND_PUBLIC_DATA_DIR = os.path.join(BASE_DIR, "frontend", "public", "data")
DATA_ASSETS_DIR = os.path.join(BASE_DIR, "data", "assets")
FRONTEND_PUBLIC_ASSETS_DIR = os.path.join(BASE_DIR, "frontend", "public", "data", "assets")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建置前端資料並同步到 frontend/public/data")
    parser.add_argument(
        "--with-translations",
        action="store_true",
        help="執行翻譯預生成並輸出靜態翻譯檔（data/app/i18n/zh-TW）",
    )
    parser.add_argument(
        "--translation-heroes",
        default="",
        help="搭配 --with-translations 使用，只處理指定英雄（逗號分隔）",
    )
    parser.add_argument(
        "--translation-skip-existing",
        action="store_true",
        help="搭配 --with-translations 使用，若輸出檔存在則略過",
    )
    parser.add_argument(
        "--translation-continue-on-error",
        action="store_true",
        help="搭配 --with-translations 使用，單一英雄失敗時繼續",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print("🔧 開始建置前端資料...")
    
    # 1. 下載 guide 圖片資產（可失敗降級）
    print("\n--- [1/3] 下載 guide 圖片資產（download_master_guide_assets.py）---")
    guide_result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "scripts", "download_master_guide_assets.py")],
        cwd=BASE_DIR
    )
    if guide_result.returncode != 0:
        print("⚠️  download_master_guide_assets.py 執行失敗，將使用外部圖片 URL")

    # 2. 執行 build_app_data.py
    print("\n--- [2/4] 產生衍生資料（build_app_data.py）---")
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "scripts", "build_app_data.py")],
        cwd=BASE_DIR
    )
    if result.returncode != 0:
        print("❌ build_app_data.py 執行失敗")
        sys.exit(result.returncode)
    
    # 3. （可選）產生靜態翻譯檔
    if args.with_translations:
        print("\n--- [3/4] 產生靜態翻譯檔（prewarm_translation_cache.py）---")
        translation_cmd = [
            sys.executable,
            os.path.join(BASE_DIR, "scripts", "prewarm_translation_cache.py"),
        ]
        if args.translation_heroes:
            translation_cmd.extend(["--heroes", args.translation_heroes])
        if args.translation_skip_existing:
            translation_cmd.append("--skip-existing")
        if args.translation_continue_on_error:
            translation_cmd.append("--continue-on-error")
        translation_result = subprocess.run(translation_cmd, cwd=BASE_DIR)
        if translation_result.returncode != 0:
            print("❌ prewarm_translation_cache.py 執行失敗")
            sys.exit(translation_result.returncode)

    # 4. 將 data/app/* 同步到 frontend/public/data/
    print("\n--- [4/4] 同步資料到 frontend/public/data/ ---")
    os.makedirs(FRONTEND_PUBLIC_DATA_DIR, exist_ok=True)
    
    files_copied = 0
    dirs_synced = 0
    for filename in os.listdir(DATA_APP_DIR):
        src = os.path.join(DATA_APP_DIR, filename)
        dst = os.path.join(FRONTEND_PUBLIC_DATA_DIR, filename)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            files_copied += 1
            print(f"  ✓ 已同步 {filename}")
        elif os.path.isdir(src):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            dirs_synced += 1
            print(f"  ✓ 已同步目錄 {filename}/")

    # 同步 data/assets 到 frontend/public/data/assets（供 markdown 本地圖片使用）
    if os.path.isdir(DATA_ASSETS_DIR):
        if os.path.isdir(FRONTEND_PUBLIC_ASSETS_DIR):
            shutil.rmtree(FRONTEND_PUBLIC_ASSETS_DIR)
        shutil.copytree(DATA_ASSETS_DIR, FRONTEND_PUBLIC_ASSETS_DIR)
        print("  ✓ 已同步 data/assets -> frontend/public/data/assets")
    
    print(f"\n✅ 建置完成！共同步 {files_copied} 個檔案、{dirs_synced} 個目錄")
    print(f"\n提示：資料已準備好。若要重建前端，請執行：")
    print(f"  cd frontend && npm run build")


if __name__ == "__main__":
    main()
