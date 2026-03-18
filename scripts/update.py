import asyncio
import os
import sys

# 將 scrapers 路徑加入 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scrapers"))
# 不需要加入 scripts 目錄，因為 update.py 本身就在那裡
sys.path.append(os.path.dirname(__file__))

try:
    from scrape_mobalytics import scrape_mobalytics
    from scrape_blizzard import scrape_blizzard
    from merge_data import merge_overwatch_data, validate_and_fix_master_data
except ImportError as e:
    print(f"匯入模組失敗: {e}")
    sys.exit(1)

async def main():
    worker_count = 8
    print("🚀 開始全面更新 Overwatch 數據（含地圖維度）...")
    
    # 1. 抓取 Mobalytics (英雄指南與分級)
    print(f"\n--- [1/4] 抓取 Mobalytics 指南（{worker_count} workers） ---")
    await scrape_mobalytics(worker_count=worker_count)
    
    # 2. 抓取 Blizzard Stats (勝率與登場率，包含 all-maps 與逐地圖)
    print(f"\n--- [2/4] 抓取 Blizzard 數據（all-maps + 逐地圖, {worker_count} workers） ---")
    await scrape_blizzard(worker_count=worker_count)
    
    # 3. 整合 JSON 大表與地圖維度統計
    print("\n--- [3/4] 正整合資料庫並輸出 overwatch_stats.json ---")
    merge_overwatch_data()

    # 4. 驗證整合輸出，能修就修；不可修才中止
    print("\n--- [4/4] 驗證輸出資料結構 ---")
    if not validate_and_fix_master_data(write_back=True):
        raise RuntimeError("資料結構驗證未通過，已中止流程。")
    
    print("\n✨ 全部更新流程已完成！")

if __name__ == "__main__":
    asyncio.run(main())
