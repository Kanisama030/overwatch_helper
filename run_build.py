#!/usr/bin/env python3
"""
run_build.py
完整的前端資料建置流程：
1. 執行 scripts/download_master_guide_assets.py 下載 guide 圖片
2. 執行 scripts/build_app_data.py 產生衍生資料
3. 將 data/app/* 與 data/assets/* 同步到 frontend/public/data/
4. 提示是否需要重建前端
"""
import subprocess
import sys
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_APP_DIR = os.path.join(BASE_DIR, "data", "app")
FRONTEND_PUBLIC_DATA_DIR = os.path.join(BASE_DIR, "frontend", "public", "data")
DATA_ASSETS_DIR = os.path.join(BASE_DIR, "data", "assets")
FRONTEND_PUBLIC_ASSETS_DIR = os.path.join(BASE_DIR, "frontend", "public", "data", "assets")


def main():
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
    print("\n--- [2/3] 產生衍生資料（build_app_data.py）---")
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "scripts", "build_app_data.py")],
        cwd=BASE_DIR
    )
    if result.returncode != 0:
        print("❌ build_app_data.py 執行失敗")
        sys.exit(result.returncode)
    
    # 3. 將 data/app/* 同步到 frontend/public/data/
    print("\n--- [3/3] 同步資料到 frontend/public/data/ ---")
    os.makedirs(FRONTEND_PUBLIC_DATA_DIR, exist_ok=True)
    
    files_copied = 0
    for filename in os.listdir(DATA_APP_DIR):
        src = os.path.join(DATA_APP_DIR, filename)
        dst = os.path.join(FRONTEND_PUBLIC_DATA_DIR, filename)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            files_copied += 1
            print(f"  ✓ 已同步 {filename}")

    # 同步 data/assets 到 frontend/public/data/assets（供 markdown 本地圖片使用）
    if os.path.isdir(DATA_ASSETS_DIR):
        if os.path.isdir(FRONTEND_PUBLIC_ASSETS_DIR):
            shutil.rmtree(FRONTEND_PUBLIC_ASSETS_DIR)
        shutil.copytree(DATA_ASSETS_DIR, FRONTEND_PUBLIC_ASSETS_DIR)
        print("  ✓ 已同步 data/assets -> frontend/public/data/assets")
    
    print(f"\n✅ 建置完成！共同步 {files_copied} 個檔案")
    print(f"\n提示：資料已準備好。若要重建前端，請執行：")
    print(f"  cd frontend && npm run build")


if __name__ == "__main__":
    main()
