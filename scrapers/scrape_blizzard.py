import json
import asyncio
import re
from playwright.async_api import async_playwright
import pandas as pd
import os

def parse_map_ids_from_html(html):
    # 從頁面 HTML 嘗試解析 map 參數（保留給除錯與相容用途）
    if not html:
        return []

    matches = re.findall(r"[?&]map=([a-z0-9-]+)", html)
    ordered = []
    seen = set()
    for map_id in matches:
        if map_id not in seen:
            seen.add(map_id)
            ordered.append(map_id)
    return ordered


async def load_map_ids(page=None):
    # 地圖清單固定由 data/overwatch_mapping.json 讀取
    mapping_file = os.path.join(os.path.dirname(__file__), "..", "data", "overwatch_mapping.json")
    with open(mapping_file, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)

    ids = []
    for item in mapping_data.get("maps", []):
        map_id = item.get("id")
        if map_id:
            ids.append(map_id)
    return ids


async def fetch_tier_data(page, mode, rq_val, tier_name, map_id, tier_val=None):
    url = f"https://overwatch.blizzard.com/en-us/rates/?input=PC&map={map_id}&region=Asia&role=All&rq={rq_val}"
    if rq_val == 2 and tier_val:
        url += f"&tier={tier_val}"
    else:
        url += "&tier=All"
        
    print(f"抓取中 -> 模式: {mode}, 階級: {tier_name}, 地圖: {map_id} -> URL: {url}")
    
    # 放寬頁面載入逾時，避免網站偶發慢速導致失敗
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"開啟頁面失敗 {url}: {e}")
        return []
    
    table_locator = page.locator('blz-data-table.herostats-data-table')
    try:
        await table_locator.wait_for(state="attached", timeout=30000)
    except Exception as e:
        print(f"資料表載入失敗 {mode} {tier_name} {map_id}: {e}")
        return []
    
    # 稍等片刻，確保 allrows 屬性已完成注入
    await asyncio.sleep(1)
    
    allrows_str = await table_locator.get_attribute('allrows')
    if not allrows_str:
        print(f"找不到 allrows 屬性: {mode} {tier_name} {map_id}")
        return []
        
    rows_data = json.loads(allrows_str)
    print(f"成功載入 {len(rows_data)} 筆英雄資料: {mode} {tier_name} {map_id}")
    
    data = []
    for row in rows_data:
        hero_name = row.get("cells", {}).get("name", "")
        hero_role = row.get("hero", {}).get("role", "")
        win_rate = row.get("cells", {}).get("winrate", 0)
        pick_rate = row.get("cells", {}).get("pickrate", 0)
        
        data.append({
            "Mode": mode,
            "Tier": tier_name,
            "Map": map_id,
            "Hero": hero_name,
            "Role": hero_role,
            "Win Rate (%)": win_rate,
            "Pick Rate (%)": pick_rate
        })
    return data

async def scrape_blizzard():
    # 確保輸出資料夾存在
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    os.makedirs(out_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        map_ids = await load_map_ids(page)
        all_maps = ["all-maps"] + [m for m in map_ids if m != "all-maps"]

        all_data = []
        
        # 1. Quick Play (All) - 逐地圖抓取
        for map_id in all_maps:
            qp_data = await fetch_tier_data(
                page,
                "Quick Play",
                rq_val=0,
                tier_name="All",
                map_id=map_id,
                tier_val="All",
            )
            all_data.extend(qp_data)
        
        # 2. Competitive - 9 個 Tier，逐地圖抓取
        tiers = [
            ("Bronze", "Bronze"),
            ("Silver", "Silver"),
            ("Gold", "Gold"),
            ("Platinum", "Platinum"),
            ("Diamond", "Diamond"),
            ("Master", "Master"),
            ("Grandmaster", "Grandmaster"),
            ("Champion", "Champion"),
            ("All", "All")
        ]
        
        for tier_val, tier_name in tiers:
            for map_id in all_maps:
                comp_data = await fetch_tier_data(
                    page,
                    "Competitive",
                    rq_val=2,
                    tier_name=tier_name,
                    map_id=map_id,
                    tier_val=tier_val,
                )
                all_data.extend(comp_data)
            
        await browser.close()
        
        if all_data:
            # 3. 儲存 CSV（含 Map 欄位）
            df = pd.DataFrame(all_data)
            out_file = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "blizzard_stats.csv")
            df.to_csv(out_file, index=False)
            print(f"資料已寫入: {out_file}")
            return all_data
        else:
            print("未蒐集到任何資料。")
            return None

if __name__ == "__main__":
    asyncio.run(scrape_blizzard())
