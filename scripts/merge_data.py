import json
import pandas as pd
import os

def merge_overwatch_data():
    base_dir = os.path.dirname(__file__)
    raw_dir = os.path.join(base_dir, "..", "data", "raw")
    output_file = os.path.join(base_dir, "..", "data", "overwatch_master.json")

    # 1. 讀取 Mobalytics 資料
    m_path = os.path.join(raw_dir, "mobalytics_heroes.json")
    if not os.path.exists(m_path):
        print(f"找不到 Mobalytics 資料: {m_path}")
        return

    with open(m_path, 'r', encoding='utf-8') as f:
        mobalytics_data = json.load(f)

    # 2. 讀取 Blizzard 資料
    b_path = os.path.join(raw_dir, "blizzard_stats.csv")
    if not os.path.exists(b_path):
        print(f"找不到 Blizzard 資料: {b_path}")
        stats_df = pd.DataFrame()
    else:
        stats_df = pd.read_csv(b_path)

    # 3. 處理統計數據 (整理成 Hero -> Mode -> Tier)
    hero_stats_map = {}
    if not stats_df.empty:
        for _, row in stats_df.iterrows():
            h_name = row['Hero']
            mode = row['Mode']
            tier = row['Tier']
            
            if h_name not in hero_stats_map:
                hero_stats_map[h_name] = {}
            
            if mode not in hero_stats_map[h_name]:
                hero_stats_map[h_name][mode] = {}
            
            hero_stats_map[h_name][mode][tier] = {
                "win_rate": row['Win Rate (%)'],
                "pick_rate": row['Pick Rate (%)'],
                "role": row['Role']
            }

    # 4. 整合英雄資料
    master_heroes = []
    
    # 取得 Mobalytics 的所有英雄作為基準
    for moba_hero in mobalytics_data.get("heroes", []):
        hero_name = moba_hero.get("Hero")
        
        # 獲取該英雄的所有統計數據
        all_stats = hero_stats_map.get(hero_name, {})
        
        # 為了前端方便，直接把 "Quick Play" - "All" 提取出來作為預設顯示
        default_stats = all_stats.get("Quick Play", {}).get("All", {})
        if not default_stats and "Competitive" in all_stats:
             default_stats = all_stats.get("Competitive", {}).get("All", {})

        # 組合資料
        hero_combined = {
            "name": hero_name,
            "tier": moba_hero.get("Tier"),
            "role": default_stats.get("role", "UNKNOWN"),
            "default_stats": default_stats, # 方便預設顯示
            "all_stats": all_stats,         # 包含所有 Mode 和 Tier 的完整數據
            "guide": moba_hero.get("Guide", [])
        }
        master_heroes.append(hero_combined)

    # 5. 儲存大整合 JSON
    master_data = {
        "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "heroes": master_heroes,
        "meta_commentary": mobalytics_data.get("meta_commentary", [])
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 資料整合完成！已產生: {output_file}")

if __name__ == "__main__":
    merge_overwatch_data()
