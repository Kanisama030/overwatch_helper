import json
import pandas as pd
import os


def pick_preferred_map_stats(map_stats):
    # 優先使用 all-maps，若不存在則退回第一筆可用地圖資料
    if not isinstance(map_stats, dict) or not map_stats:
        return {}
    if "all-maps" in map_stats:
        return map_stats["all-maps"]
    first_map_key = next(iter(map_stats.keys()))
    return map_stats.get(first_map_key, {})


def merge_overwatch_data():
    base_dir = os.path.dirname(__file__)
    raw_dir = os.path.join(base_dir, "..", "data", "raw")
    output_file = os.path.join(base_dir, "..", "data", "overwatch_master.json")
    output_stats_file = os.path.join(base_dir, "..", "data", "overwatch_stats.json")

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

    # 3. 處理統計數據 (整理成 Hero -> Mode -> Tier -> Map)
    hero_stats_map = {}
    if not stats_df.empty:
        for _, row in stats_df.iterrows():
            h_name = row['Hero']
            mode = row['Mode']
            tier = row['Tier']
            map_name = row['Map'] if 'Map' in stats_df.columns and pd.notna(row['Map']) else 'all-maps'
            
            if h_name not in hero_stats_map:
                hero_stats_map[h_name] = {}
            
            if mode not in hero_stats_map[h_name]:
                hero_stats_map[h_name][mode] = {}

            if tier not in hero_stats_map[h_name][mode]:
                hero_stats_map[h_name][mode][tier] = {}
            
            hero_stats_map[h_name][mode][tier][map_name] = {
                "win_rate": row['Win Rate (%)'],
                "pick_rate": row['Pick Rate (%)'],
                "role": row['Role']
            }

    # 4. 儲存完整地圖維度統計
    stats_data = {
        "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "heroes_stats": hero_stats_map
    }

    with open(output_stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, ensure_ascii=False, indent=2)

    # 5. 整合英雄資料
    master_heroes = []
    
    # 取得 Mobalytics 的所有英雄作為基準
    for moba_hero in mobalytics_data.get("heroes", []):
        hero_name = moba_hero.get("Hero")
        
        # 直接從地圖維度資料取 Quick Play / All / all-maps 作為預設顯示數值
        hero_map_stats = hero_stats_map.get(hero_name, {})
        default_stats = pick_preferred_map_stats(hero_map_stats.get("Quick Play", {}).get("All", {}))
        if not default_stats:
            default_stats = pick_preferred_map_stats(hero_map_stats.get("Competitive", {}).get("All", {}))

        # 組合資料（all_stats 已移至 overwatch_stats.json，master 只保留摘要）
        hero_combined = {
            "name": hero_name,
            "tier": moba_hero.get("Tier"),
            "role": default_stats.get("role", "UNKNOWN"),
            "default_stats": default_stats,
            "guide": moba_hero.get("Guide", [])
        }
        master_heroes.append(hero_combined)

    # 6. 儲存大整合 JSON
    master_data = {
        "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "heroes": master_heroes,
        "meta_commentary": mobalytics_data.get("meta_commentary", [])
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 資料整合完成！已產生: {output_file}")
    print(f"✅ 地圖維度統計已產生: {output_stats_file}")

if __name__ == "__main__":
    merge_overwatch_data()
