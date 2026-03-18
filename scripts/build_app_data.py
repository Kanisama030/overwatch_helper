"""
build_app_data.py
從現有資料產生前端所需的衍生資料檔，輸出至 data/app/ 目錄。
"""

import json
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
APP_DIR = os.path.join(DATA_DIR, "app")


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[錯誤] 無法讀取 {path}：{e}")
        return None


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_maps_index(mapping):
    """產生 maps_index.json"""
    result = []
    for m in mapping.get("maps", []):
        result.append({
            "id": m.get("id"),
            "en": m.get("en"),
            "zh": m.get("zh"),
            "mode": m.get("mode"),
            "thumbnail": None,
        })
    return result


def build_heroes_index(mapping, master):
    """產生 heroes_index.json，從 mapping 取 id，從 master 取 tier/default_stats"""
    # 建立 master 英雄 id（小寫）->資料 的查找表
    master_by_id = {str(h.get("name", "")).lower(): h for h in master.get("heroes", [])}

    result = []
    for hero_map in mapping.get("heroes", []):
        hero_id = hero_map.get("id", "")
        en_name = hero_map.get("en", "")
        master_hero = master_by_id.get(str(hero_id).lower())

        tier = None
        default_win_rate = None
        default_pick_rate = None

        if master_hero:
            tier = master_hero.get("tier")
            ds = master_hero.get("default_stats", {}) or {}
            default_win_rate = ds.get("win_rate")
            default_pick_rate = ds.get("pick_rate")

        # role 轉 Title Case（例如 TANK -> Tank）
        raw_role = hero_map.get("role", "")
        role = raw_role.title() if raw_role else raw_role

        result.append({
            "id": hero_id,
            "en": en_name,
            "zh": hero_map.get("zh"),
            "role": role,
            "tier": tier,
            "default_win_rate": default_win_rate,
            "default_pick_rate": default_pick_rate,
        })
    return result


def _get_guide_section(guide_list, section_id):
    """從 guide 清單取得特定 id 的區段"""
    for section in guide_list:
        if section.get("id") == section_id:
            return section
    return None


def _get_guide_section_by_title(guide_list, title_keywords):
    """從 guide 清單以 title 關鍵字尋找區段（不分大小寫）"""
    for section in guide_list:
        title = section.get("title", "")
        if any(kw.lower() in title.lower() for kw in title_keywords):
            return section
    return None


def _find_map_mentions(text, maps_list):
    """在文字中找出地圖名稱（不分大小寫），回傳 [map_id, ...]"""
    found = []
    for m in maps_list:
        en = m.get("en", "")
        if en and re.search(re.escape(en), text, re.IGNORECASE):
            found.append(m["id"])
    return found


def build_hero_map_recommendations(master, mapping):
    """產生 hero_map_recommendations.json"""
    maps_list = mapping.get("maps", [])
    map_heroes = mapping.get("heroes", [])
    mapping_ids = {str(h.get("id", "")).lower() for h in map_heroes}
    en_to_id = {str(h.get("en", "")).lower(): h.get("id", "") for h in map_heroes}
    result = {}

    for hero in master.get("heroes", []):
        hero_name = hero.get("name", "")
        guide = hero.get("guide", []) or []

        # 取 section id="6"（Maps）
        maps_section = _get_guide_section(guide, "6")
        best_maps = []
        worst_maps = []
        maps_summary = ""

        if maps_section:
            content = maps_section.get("content") or []
            if content:
                # maps_summary 取第一段的第一句
                first_para = content[0]
                first_sentence = re.split(r"(?<=[.!?])\s", first_para.strip())[0]
                maps_summary = first_sentence

                # 分析 best/worst
                # 先掃描全文，找出負面關鍵字之後的地圖歸為 worst
                full_text = "\n".join(content)
                worst_trigger = re.compile(
                    r"(struggle|struggles|worst|trouble|difficult)", re.IGNORECASE
                )

                for para in content:
                    para_mentions = _find_map_mentions(para, maps_list)
                    # 若段落含負面關鍵字，mention 的地圖歸 worst_maps
                    if worst_trigger.search(para):
                        for mid in para_mentions:
                            if mid not in worst_maps:
                                worst_maps.append(mid)
                    else:
                        for mid in para_mentions:
                            if mid not in best_maps:
                                best_maps.append(mid)

                # 從 best_maps 移除同時在 worst_maps 的項目
                best_maps = [m for m in best_maps if m not in worst_maps]

        # name 已改為 id；若遇舊資料再回退 en->id
        hero_key = hero_name.lower()
        if hero_key not in mapping_ids:
            hero_key = en_to_id.get(hero_name.lower(), hero_key)

        result[hero_key] = {
            "best_maps": best_maps,
            "worst_maps": worst_maps,
            "maps_summary": maps_summary,
        }

    return result


def build_counter_index(master, mapping):
    """產生 counter_index.json"""
    map_heroes = mapping.get("heroes", [])
    hero_names_en = [h.get("en", "") for h in map_heroes]
    mapping_ids = {str(h.get("id", "")).lower() for h in map_heroes}
    en_to_id = {str(h.get("en", "")).lower(): h.get("id", "") for h in map_heroes}
    result = {}

    for hero in master.get("heroes", []):
        hero_name = hero.get("name", "")
        guide = hero.get("guide", []) or []

        # 找 section id="1.1.2"（Play Against / Playing Against）
        play_against_section = _get_guide_section(guide, "1.1.2")
        play_against_summary = []
        if play_against_section:
            play_against_summary = play_against_section.get("content") or []

        # 找 section id="8"（How to Counter）
        counter_section = _get_guide_section(guide, "8")
        countered_by_mentions = []
        if counter_section:
            content_list = counter_section.get("content") or []
            full_text = "\n".join(content_list)
            for en_name in hero_names_en:
                if not en_name:
                    continue
                # 找 \n{HeroName}\n 或直接提及
                pattern = r"(\\n|\b)" + re.escape(en_name) + r"(\\n|\b)"
                if re.search(re.escape(en_name), full_text, re.IGNORECASE):
                    countered_by_mentions.append(en_name)

        # name 已改為 id；若遇舊資料再回退 en->id
        hero_key = hero_name.lower()
        if hero_key not in mapping_ids:
            hero_key = en_to_id.get(hero_name.lower(), hero_key)

        result[hero_key] = {
            "play_against_summary": play_against_summary,
            "countered_by_mentions": countered_by_mentions,
        }

    return result


def build_map_stats_for_hero(hero_name, stats_data):
    """從 overwatch_stats.json 取指定英雄的地圖勝率資料"""
    heroes_stats = stats_data.get("heroes_stats", {})

    # 嘗試完整名稱比對（大小寫不敏感）
    matched_key = None
    for key in heroes_stats:
        if key.lower() == hero_name.lower():
            matched_key = key
            break

    if not matched_key:
        return {}

    hero_data = heroes_stats[matched_key]

    # 優先使用 Quick Play，退而使用 Competitive
    play_mode_data = hero_data.get("Quick Play") or hero_data.get("Competitive") or {}
    all_data = play_mode_data.get("All", {})

    map_stats = {}
    for map_id, stat in all_data.items():
        if map_id == "all-maps":
            continue
        map_stats[map_id] = {
            "win_rate": stat.get("win_rate"),
            "pick_rate": stat.get("pick_rate"),
        }
    return map_stats


def build_app_ready_dataset(maps_index, heroes_index, map_recs, counter_idx, master, stats_data, mapping):
    """產生 app_ready_dataset.json"""
    # 建立 hero en name -> map_stats 查找
    # 利用 master heroes（有 default_stats）對應 stats
    heroes_out = []
    for hero_idx in heroes_index:
        hero_id = hero_idx["id"]
        en_name = hero_idx["en"]

        # 取地圖推薦
        map_rec = map_recs.get(hero_id, {"best_maps": [], "worst_maps": [], "maps_summary": ""})
        # 取反制資料
        counter = counter_idx.get(hero_id, {"play_against_summary": [], "countered_by_mentions": []})
        # 取地圖統計
        map_stats = build_map_stats_for_hero(en_name, stats_data)

        hero_entry = {
            **hero_idx,
            "map_recommendations": map_rec,
            "counter_data": counter,
            "map_stats": map_stats,
        }
        heroes_out.append(hero_entry)

    return {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "maps": maps_index,
        "heroes": heroes_out,
    }


def main():
    # 確保輸出目錄存在
    os.makedirs(APP_DIR, exist_ok=True)

    # 載入資料
    print("載入資料來源...")
    master = load_json(os.path.join(DATA_DIR, "overwatch_master.json"))
    mapping = load_json(os.path.join(DATA_DIR, "overwatch_mapping.json"))
    stats = load_json(os.path.join(DATA_DIR, "overwatch_stats.json"))

    if not master or not mapping or not stats:
        print("[失敗] 資料載入失敗，請確認來源檔案存在。")
        return

    # 1. maps_index.json
    print("產生 maps_index.json...")
    maps_index = build_maps_index(mapping)
    save_json(os.path.join(APP_DIR, "maps_index.json"), maps_index)
    print(f"  ✓ 共 {len(maps_index)} 張地圖")

    # 2. heroes_index.json
    print("產生 heroes_index.json...")
    heroes_index = build_heroes_index(mapping, master)
    save_json(os.path.join(APP_DIR, "heroes_index.json"), heroes_index)
    print(f"  ✓ 共 {len(heroes_index)} 位英雄")

    # 3. hero_map_recommendations.json
    print("產生 hero_map_recommendations.json...")
    map_recs = build_hero_map_recommendations(master, mapping)
    save_json(os.path.join(APP_DIR, "hero_map_recommendations.json"), map_recs)
    print(f"  ✓ 共 {len(map_recs)} 位英雄的地圖建議")

    # 4. counter_index.json
    print("產生 counter_index.json...")
    counter_idx = build_counter_index(master, mapping)
    save_json(os.path.join(APP_DIR, "counter_index.json"), counter_idx)
    print(f"  ✓ 共 {len(counter_idx)} 位英雄的反制資料")

    # 5. app_ready_dataset.json
    print("產生 app_ready_dataset.json...")
    app_dataset = build_app_ready_dataset(
        maps_index, heroes_index, map_recs, counter_idx, master, stats, mapping
    )
    save_json(os.path.join(APP_DIR, "app_ready_dataset.json"), app_dataset)
    hero_count = len(app_dataset["heroes"])
    map_count = len(app_dataset["maps"])
    print(f"  ✓ 整合資料集：{hero_count} 位英雄、{map_count} 張地圖")

    print("\n[成功] 所有衍生資料檔已產生於 data/app/ 目錄。")


if __name__ == "__main__":
    main()
