import asyncio
import argparse
import os
import sys
import subprocess

DEFAULT_PLAYWRIGHT_WORKERS = 8
DEFAULT_CLOUDFLARE_WORKERS = 8

# 將 scrapers 路徑加入 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scrapers"))
# 不需要加入 scripts 目錄，因為 update.py 本身就在那裡
sys.path.append(os.path.dirname(__file__))

try:
    from scrape_mobalytics import scrape_mobalytics
    from scrape_mobalytics_cloudflare import scrape_mobalytics_cloudflare
    from scrape_blizzard import scrape_blizzard
    from merge_data import merge_overwatch_data, validate_and_fix_master_data
except ImportError as e:
    print(f"匯入模組失敗: {e}")
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description="更新 Overwatch 資料流程")
    parser.add_argument(
        "--mobalytics-method",
        choices=["cloudflare", "playwright"],
        default="cloudflare",
        help="Mobalytics 抓取方法（預設 cloudflare）",
    )
    parser.add_argument(
        "--mobalytics-smoke-hero",
        default=None,
        help="僅抓取單一英雄（例如 roadhog）",
    )
    parser.add_argument(
        "--mobalytics-workers",
        type=int,
        default=DEFAULT_CLOUDFLARE_WORKERS,
        help=f"Cloudflare 模式 worker 數（預設 {DEFAULT_CLOUDFLARE_WORKERS}）",
    )
    parser.add_argument(
        "--update-fandom-perks",
        action="store_true",
        help="額外執行 Fandom perks 更新（Cloudflare + Gemini）",
    )
    return parser.parse_args()


def run_update_mapping_assets():
    print("\n--- [5/6] 更新資產映射與 manifest（update_mapping_assets.py）---")
    result = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "update_mapping_assets.py")])
    if result.returncode != 0:
        print("⚠️  update_mapping_assets.py 執行失敗，將使用既有 manifest 繼續流程")


def run_download_master_guide_assets():
    print("\n--- [6/7] 下載 guide markdown 圖片資產（download_master_guide_assets.py）---")
    result = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "download_master_guide_assets.py")])
    if result.returncode != 0:
        print("⚠️  download_master_guide_assets.py 執行失敗，將使用外部圖片 URL 繼續流程")


def run_build_app_data():
    print("\n--- [7/7] 重建前端衍生資料（build_app_data.py）---")
    result = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "build_app_data.py")])
    if result.returncode != 0:
        print("⚠️  build_app_data.py 執行失敗，但資料更新已完成")


def run_update_fandom_perks():
    print("\n--- [額外] 更新 Fandom Perks（update_perks_from_fandom_cloudflare.py）---")
    result = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "update_perks_from_fandom_cloudflare.py")])
    if result.returncode != 0:
        print("⚠️  update_perks_from_fandom_cloudflare.py 執行失敗，將保留既有 perks 資料")


async def main():
    args = parse_args()
    worker_count = DEFAULT_PLAYWRIGHT_WORKERS
    print("🚀 開始全面更新 Overwatch 數據（含地圖維度）...")
    
    # 1. 抓取 Mobalytics (英雄指南與分級)
    if args.mobalytics_method == "cloudflare":
        print("\n--- [1/7] 抓取 Mobalytics 指南（Cloudflare Markdown，單線程） ---")
        await scrape_mobalytics_cloudflare(
            smoke_hero=args.mobalytics_smoke_hero,
            build_master=True,
            worker_count=args.mobalytics_workers,
        )
        print("\n--- [2/7] 抓取 Blizzard 數據（all-maps + 逐地圖, {worker_count} workers） ---")
        await scrape_blizzard(worker_count=worker_count)
        print("\n--- [3/7] Cloudflare 模式已直接輸出 overwatch_master.json，略過 merge_data ---")
        print("\n--- [4/7] Cloudflare 模式略過舊版 validate_and_fix_master_data ---")
        
        # 5/7. 更新資產與重建衍生資料
        run_update_mapping_assets()
        run_download_master_guide_assets()
        if args.update_fandom_perks:
            run_update_fandom_perks()
        run_build_app_data()
        
        print("\n✨ 全部更新流程已完成！")
        return
    else:
        print(f"\n--- [1/7] 抓取 Mobalytics 指南（Playwright，{worker_count} workers） ---")
        await scrape_mobalytics(worker_count=worker_count)
    
    # 2. 抓取 Blizzard Stats (勝率與登場率，包含 all-maps 與逐地圖)
    print(f"\n--- [2/7] 抓取 Blizzard 數據（all-maps + 逐地圖, {worker_count} workers） ---")
    await scrape_blizzard(worker_count=worker_count)
    
    # 3. 整合 JSON 大表與地圖維度統計
    print("\n--- [3/7] 正整合資料庫並輸出 overwatch_stats.json ---")
    merge_overwatch_data()

    # 4. 驗證整合輸出，能修就修；不可修才中止
    print("\n--- [4/7] 驗證輸出資料結構 ---")
    if not validate_and_fix_master_data(write_back=True):
        raise RuntimeError("資料結構驗證未通過，已中止流程。")
    
    # 5/7. 更新資產與重建衍生資料
    run_update_mapping_assets()
    run_download_master_guide_assets()
    if args.update_fandom_perks:
        run_update_fandom_perks()
    run_build_app_data()
    
    print("\n✨ 全部更新流程已完成！")

if __name__ == "__main__":
    asyncio.run(main())
