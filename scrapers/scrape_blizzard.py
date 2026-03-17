import json
import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import os

async def fetch_tier_data(page, mode, rq_val, tier_name, tier_val=None):
    url = f"https://overwatch.blizzard.com/en-us/rates/?input=PC&map=all-maps&region=Asia&role=All&rq={rq_val}"
    if rq_val == 2 and tier_val:
        url += f"&tier={tier_val}"
    else:
        url += "&tier=All"
        
    print(f"Fetching data for Mode: {mode}, Tier: {tier_name} -> URL: {url}")
    
    # Increase the timeout for goto
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"Error navigating to {url}: {e}")
        return []
    
    table_locator = page.locator('blz-data-table.herostats-data-table')
    try:
        await table_locator.wait_for(state="attached", timeout=30000)
    except Exception as e:
        print(f"Failed to load data for {mode} {tier_name}: {e}")
        return []
    
    # Give it a tiny bit of time to ensure attributes are hydrated
    await asyncio.sleep(1)
    
    allrows_str = await table_locator.get_attribute('allrows')
    if not allrows_str:
        print(f"No allrows attribute found for {mode} {tier_name}")
        return []
        
    rows_data = json.loads(allrows_str)
    print(f"Successfully loaded {len(rows_data)} hero records for {mode} {tier_name}")
    
    data = []
    for row in rows_data:
        hero_name = row.get("cells", {}).get("name", "")
        hero_role = row.get("hero", {}).get("role", "")
        win_rate = row.get("cells", {}).get("winrate", 0)
        pick_rate = row.get("cells", {}).get("pickrate", 0)
        
        data.append({
            "Mode": mode,
            "Tier": tier_name,
            "Hero": hero_name,
            "Role": hero_role,
            "Win Rate (%)": win_rate,
            "Pick Rate (%)": pick_rate
        })
    return data

async def scrape_blizzard():
    # Make sure output directory exists
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    os.makedirs(out_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        all_data = []
        
        # 1. Quick Play Data
        qp_data = await fetch_tier_data(page, "Quick Play", rq_val=0, tier_name="All", tier_val="All")
        all_data.extend(qp_data)
        
        # 2. Competitive Data - Various Tiers
        # Blizzard tiers in URL: Bronze, Silver, Gold, Platinum, Diamond, Master, Grandmaster, Champion
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
            comp_data = await fetch_tier_data(page, "Competitive", rq_val=2, tier_name=tier_name, tier_val=tier_val)
            all_data.extend(comp_data)
            
        await browser.close()
        
        if all_data:
            # 3. Save to CSV
            df = pd.DataFrame(all_data)
            out_file = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "blizzard_stats.csv")
            df.to_csv(out_file, index=False)
            print(f"Data saved to {out_file}")
            return all_data
        else:
            print("No data was collected.")
            return None

if __name__ == "__main__":
    asyncio.run(scrape_blizzard())
