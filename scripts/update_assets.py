import argparse
import os
import subprocess
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="更新 Overwatch 低頻資產流程")
    parser.add_argument(
        "--update-map-images",
        action="store_true",
        help="更新 maps 圖片（預設不更新）",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="下載 hero/map/perk 圖片時，檔案已存在則略過（預設啟用）",
    )
    parser.add_argument(
        "--update-fandom-perks",
        action="store_true",
        help="更新 Fandom perks（名稱/說明/圖片）",
    )
    return parser.parse_args()


def run_update_mapping_assets(args):
    print("\n--- [1/3] 更新 mapping 與 hero/map manifest（update_mapping_assets.py）---")
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "update_mapping_assets.py")]
    if args.skip_existing:
        cmd.append("--skip-existing")
    if args.update_map_images:
        cmd.append("--update-map-images")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("⚠️  update_mapping_assets.py 執行失敗，將使用既有 mapping/manifest 繼續")


def run_update_fandom_perks(args):
    if not args.update_fandom_perks:
        print("\n--- [2/3] 略過 Fandom perks 更新（可用 --update-fandom-perks 啟用）---")
        return
    print("\n--- [2/3] 更新 Fandom perks（update_perks_from_fandom_cloudflare.py）---")
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "update_perks_from_fandom_cloudflare.py")]
    if args.skip_existing:
        cmd.append("--skip-existing")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("⚠️  update_perks_from_fandom_cloudflare.py 執行失敗，將保留既有 perks 資料")


def run_download_master_guide_assets():
    print("\n--- [3/3] 下載 guide markdown 圖片資產（download_master_guide_assets.py）---")
    result = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "download_master_guide_assets.py")])
    if result.returncode != 0:
        print("⚠️  download_master_guide_assets.py 執行失敗，將使用外部圖片 URL")


def main():
    args = parse_args()
    print("🚀 開始更新 Overwatch 低頻資產流程...")
    run_update_mapping_assets(args)
    run_update_fandom_perks(args)
    run_download_master_guide_assets()
    print("\n✨ 資產更新流程已完成！")


if __name__ == "__main__":
    main()
