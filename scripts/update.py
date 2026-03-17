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
    from merge_data import merge_overwatch_data
except ImportError as e:
    print(f"匯入模組失敗: {e}")
    sys.exit(1)

async def main():
    print("🚀 開始全面更新 Overwatch 數據...")
    
    # 1. 抓取 Mobalytics (英雄指南與分級)
    print("\n--- [1/3] 抓取 Mobalytics 指南 ---")
    await scrape_mobalytics()
    
    # 2. 抓取 Blizzard Stats (勝率與登場率)
    print("\n--- [2/3] 抓取 Blizzard 數據庫 ---")
    await scrape_blizzard()
    
    # 3. 整合 JSON 大表
    print("\n--- [3/3] 正整合資料庫中 ---")
    merge_overwatch_data()
    
    print("\n✨ 全部更新流程已完成！")

if __name__ == "__main__":
    asyncio.run(main())
