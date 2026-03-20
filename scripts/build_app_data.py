"""
build_app_data.py
從現有資料產生前端所需的衍生資料檔，輸出至 data/app/ 目錄。
"""

import json
import os
import re
from datetime import datetime
from urllib.parse import quote

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


def build_heroes_index(mapping, master, stats):
    """產生 heroes_index.json，從 mapping 取 id，從 master 取 tier，從 stats 取 default win/pick rate"""
    # 建立 master 英雄 id（小寫）->資料 的查找表（相容新舊 key）
    master_by_id = {}
    for h in master.get("heroes", []):
        hero_key = str(h.get("Hero") or h.get("name", "")).lower()
        master_by_id[hero_key] = h

    result = []
    for hero_map in mapping.get("heroes", []):
        hero_id = hero_map.get("id", "")
        en_name = hero_map.get("en", "")
        master_hero = master_by_id.get(str(hero_id).lower())

        tier = None
        default_win_rate = None
        default_pick_rate = None

        if master_hero:
            # 讀取 Tier（相容舊鍵 tier）
            tier = master_hero.get("Tier") or master_hero.get("tier")

        # default_win_rate / pick_rate 改由 stats 取值
        # Quick Play -> All -> all-maps，若不存在則回退 Competitive
        heroes_stats = stats.get("heroes_stats", {})
        hero_stats = heroes_stats.get(en_name)
        if hero_stats:
            qp_all = hero_stats.get("Quick Play", {}).get("All", {}).get("all-maps", {})
            comp_all = hero_stats.get("Competitive", {}).get("All", {}).get("all-maps", {})
            default_win_rate = qp_all.get("win_rate") or comp_all.get("win_rate")
            default_pick_rate = qp_all.get("pick_rate") or comp_all.get("pick_rate")

        # role 來源改為 mapping 優先（維持 Title Case）
        raw_role = hero_map.get("role", "")
        role = raw_role if raw_role else raw_role

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


def _read_manifest(path):
    data = load_json(path)
    if isinstance(data, list):
        return data
    return []


def _build_asset_url_mapping(hero_manifest, map_manifest, guide_manifest):
    mapping = {}
    for item in (hero_manifest or []) + (map_manifest or []) + (guide_manifest or []):
        if not isinstance(item, dict):
            continue
        src = item.get("image_url")
        local_path = item.get("local_path")
        if src and local_path:
            normalized = str(local_path).replace("\\", "/")
            if not normalized.startswith("/"):
                normalized = f"/{normalized}"
            mapping[src] = normalized
    return mapping


def _rewrite_markdown_images(text, asset_url_mapping):
    if not text:
        return text

    pattern = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\".*?\")?\)")

    def _replace(match):
        alt = match.group(1)
        original_url = match.group(2)
        local_path = asset_url_mapping.get(original_url)
        if not local_path:
            return match.group(0)
        fallback = quote(original_url, safe="")
        return f"![{alt}]({local_path}#fallback={fallback})"

    return pattern.sub(_replace, text)


def _localize_guide_images(master, asset_url_mapping):
    heroes = master.get("heroes", [])
    for hero in heroes:
        guide = hero.get("Guide") or hero.get("guide") or []
        for section in guide:
            content = section.get("content") or []
            if not isinstance(content, list):
                continue
            section["content"] = [
                _rewrite_markdown_images(line, asset_url_mapping) if isinstance(line, str) else line
                for line in content
            ]
    return master


def _find_map_mentions(text, maps_list):
    """在文字中找出地圖名稱（不分大小寫），回傳 [map_id, ...]"""
    found = []
    for m in maps_list:
        en = m.get("en", "")
        if not en:
            continue
        # 使用單詞邊界匹配，處理特殊字符（如 : 和 '）
        # 將地圖名中的特殊字符也 escape
        pattern = r"\b" + re.escape(en) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            if m["id"] not in found:
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
        # 相容新舊 key：Hero / name
        hero_name = hero.get("Hero") or hero.get("name", "")
        guide = hero.get("Guide") or hero.get("guide", []) or []

        # 取 section id="6"（Maps）的完整陳述文字
        maps_section = _get_guide_section(guide, "6")
        best_maps = []
        worst_maps = []
        maps_summary = ""

        if maps_section:
            # maps_summary 改為 section 6 的完整陳述文字
            content = maps_section.get("content") or []
            maps_summary = "\n".join(content)

        # 從 guide 扁平結構中找 6.1.1~6.1.3 生成 best_maps（從 title 和 content 找地圖名）
        for sec_id in ["6.1.1", "6.1.2", "6.1.3"]:
            sec = _get_guide_section(guide, sec_id)
            if sec:
                # 從 title 找地圖
                title_text = sec.get("title", "")
                title_mentions = _find_map_mentions(title_text, maps_list)
                for mid in title_mentions:
                    if mid not in best_maps:
                        best_maps.append(mid)
                # 從 content 找地圖
                sec_content = "\n".join(sec.get("content") or [])
                content_mentions = _find_map_mentions(sec_content, maps_list)
                for mid in content_mentions:
                    if mid not in best_maps:
                        best_maps.append(mid)

        # 從 guide 扁平結構中找 6.2.1~6.2.3 生成 worst_maps（從 title 和 content 找地圖名）
        for sec_id in ["6.2.1", "6.2.2", "6.2.3"]:
            sec = _get_guide_section(guide, sec_id)
            if sec:
                # 從 title 找地圖
                title_text = sec.get("title", "")
                title_mentions = _find_map_mentions(title_text, maps_list)
                for mid in title_mentions:
                    if mid not in worst_maps:
                        worst_maps.append(mid)
                # 從 content 找地圖
                sec_content = "\n".join(sec.get("content") or [])
                content_mentions = _find_map_mentions(sec_content, maps_list)
                for mid in content_mentions:
                    if mid not in worst_maps:
                        worst_maps.append(mid)

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
    """產生 counter_index.json，擴充輸出欄位（向後相容）"""
    map_heroes = mapping.get("heroes", [])
    hero_names_en = [h.get("en", "") for h in map_heroes]
    mapping_ids = {str(h.get("id", "")).lower() for h in map_heroes}
    en_to_id = {str(h.get("en", "")).lower(): h.get("id", "") for h in map_heroes}
    result = {}

    for hero in master.get("heroes", []):
        # 相容新舊 key：Hero / name
        hero_name = hero.get("Hero") or hero.get("name", "")
        guide = hero.get("Guide") or hero.get("guide", []) or []

        # 新欄位：play_as <- section 1.1.1
        play_as_section = _get_guide_section(guide, "1.1.1")
        play_as = []
        if play_as_section:
            play_as = play_as_section.get("content") or []

        # 新欄位：play_against <- section 1.1.2（完整內容）
        play_against_section = _get_guide_section(guide, "1.1.2")
        play_against = []
        play_against_summary = []
        if play_against_section:
            play_against = play_against_section.get("content") or []
            play_against_summary = play_against  # 保留舊欄位作 fallback

        # 新欄位：specific_counters_81 <- section 8.1 content（扁平結構）
        specific_counters_81 = []
        specific_counters_82 = []
        section_81 = _get_guide_section(guide, "8.1")
        section_82 = _get_guide_section(guide, "8.2")
        if section_81:
            specific_counters_81 = section_81.get("content") or []
        if section_82:
            specific_counters_82 = section_82.get("content") or []

        # 新欄位：Team Comp Synergies（section 7 或 7.1）
        team_comp_section = _get_guide_section(guide, "7") or _get_guide_section(guide, "7.1")
        team_comp_synergies = (team_comp_section or {}).get("content") or []

        # 新欄位：Strengths And Weaknesses Summarized（section 2）
        strengths_weaknesses_summarized = []
        section_2 = _get_guide_section(guide, "2")
        if section_2:
            strengths_weaknesses_summarized = section_2.get("content") or []

        # 新欄位：Strengths And Weaknesses Explained（section 3 + 子節點）
        section_3 = _get_guide_section(guide, "3")
        strengths_weaknesses_explained = {
            "overview": (section_3 or {}).get("content") or [],
            "strengths": [],
            "weaknesses": [],
        }
        for sec in guide:
            sec_id = sec.get("id", "")
            if not sec_id.startswith("3."):
                continue
            section_item = {
                "id": sec_id,
                "title": sec.get("title", ""),
                "content": sec.get("content") or [],
            }
            if sec_id.startswith("3.1"):
                strengths_weaknesses_explained["strengths"].append(section_item)
            elif sec_id.startswith("3.2"):
                strengths_weaknesses_explained["weaknesses"].append(section_item)

        # 保留舊欄位：countered_by_mentions（從 section 8 提取英雄名稱）
        counter_section = _get_guide_section(guide, "8")
        countered_by_mentions = []
        if counter_section:
            content_list = counter_section.get("content") or []
            full_text = "\n".join(content_list)
            for en_name in hero_names_en:
                if not en_name:
                    continue
                if re.search(re.escape(en_name), full_text, re.IGNORECASE):
                    countered_by_mentions.append(en_name)

        # name 已改為 id；若遇舊資料再回退 en->id
        hero_key = hero_name.lower()
        if hero_key not in mapping_ids:
            hero_key = en_to_id.get(hero_name.lower(), hero_key)

        result[hero_key] = {
            # 新欄位
            "play_as": play_as,
            "play_against": play_against,
            "specific_counters_81": specific_counters_81,
            "specific_counters_82": specific_counters_82,
            "team_comp_synergies": team_comp_synergies,
            "strengths_weaknesses_summarized": strengths_weaknesses_summarized,
            "strengths_weaknesses_explained": strengths_weaknesses_explained,
            # 保留舊欄位作 fallback
            "play_against_summary": play_against_summary,
            "countered_by_mentions": countered_by_mentions,
        }

    return result


def build_perks_index(master, mapping):
    """產生 perks_index.json，從 section 5 提取 perks 資料"""
    def _normalize_perk_key(text):
        return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())

    def _normalize_asset_path(path):
        if not path:
            return None
        normalized = str(path).replace("\\", "/").strip()
        if not normalized:
            return None
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        return normalized

    mapping_ids = {str(h.get("id", "")).lower() for h in mapping.get("heroes", [])}
    en_to_id = {str(h.get("en", "")).lower(): h.get("id", "") for h in mapping.get("heroes", [])}
    mapping_by_id = {str(h.get("id", "")).lower(): h for h in mapping.get("heroes", [])}
    mapping_by_en = {str(h.get("en", "")).lower(): h for h in mapping.get("heroes", [])}
    result = {}

    for hero in master.get("heroes", []):
        hero_name = hero.get("Hero") or hero.get("name", "")
        guide = hero.get("Guide") or hero.get("guide", []) or []

        # 提取 minor perks (5.1.1, 5.1.2)
        minor_perks = []
        for sec_id in ["5.1.1", "5.1.2"]:
            sec = _get_guide_section(guide, sec_id)
            if sec:
                content = sec.get("content", []) or []
                content_text = "\n".join(content).lower()
                is_recommended = ("recommended" in content_text and "minor" in content_text)
                minor_perks.append({
                    "id": sec.get("id", ""),
                    "title": sec.get("title", ""),
                    "content": content,
                    "recommended_flag": is_recommended,
                    "recommended_reason": "Recommended Minor Perk" if is_recommended else None,
                })

        # 提取 major perks (5.2.1, 5.2.2)
        major_perks = []
        for sec_id in ["5.2.1", "5.2.2"]:
            sec = _get_guide_section(guide, sec_id)
            if sec:
                content = sec.get("content", []) or []
                content_text = "\n".join(content).lower()
                is_recommended = ("recommended" in content_text and "major" in content_text)
                major_perks.append({
                    "id": sec.get("id", ""),
                    "title": sec.get("title", ""),
                    "content": content,
                    "recommended_flag": is_recommended,
                    "recommended_reason": "Recommended Major Perk" if is_recommended else None,
                })

        # name 已改為 id；若遇舊資料再回退 en->id
        hero_key = hero_name.lower()
        if hero_key not in mapping_ids:
            hero_key = en_to_id.get(hero_name.lower(), hero_key)
        hero_mapping = mapping_by_id.get(hero_key) or mapping_by_en.get(hero_name.lower()) or {}
        hero_mapping_perks = hero_mapping.get("perks", {}) if isinstance(hero_mapping, dict) else {}

        minor_mapping_list = hero_mapping_perks.get("minor perks", []) if isinstance(hero_mapping_perks, dict) else []
        major_mapping_list = hero_mapping_perks.get("major perks", []) if isinstance(hero_mapping_perks, dict) else []

        minor_mapping_by_key = {
            _normalize_perk_key(item.get("name")): item
            for item in minor_mapping_list
            if isinstance(item, dict) and item.get("name")
        }
        major_mapping_by_key = {
            _normalize_perk_key(item.get("name")): item
            for item in major_mapping_list
            if isinstance(item, dict) and item.get("name")
        }

        for idx, perk in enumerate(minor_perks):
            mapping_item = (
                minor_mapping_by_key.get(_normalize_perk_key(perk.get("title")))
                or (minor_mapping_list[idx] if idx < len(minor_mapping_list) and isinstance(minor_mapping_list[idx], dict) else {})
            )
            mapped_name = mapping_item.get("name", "") if isinstance(mapping_item, dict) else ""
            mapped_description = mapping_item.get("description") if isinstance(mapping_item, dict) else None
            mapped_image = _normalize_asset_path(mapping_item.get("image")) if isinstance(mapping_item, dict) else None
            perk["name"] = mapped_name or perk.get("title", "")
            perk["title"] = mapped_name or perk.get("title", "")
            perk["description"] = mapped_description if mapped_description else None
            perk["image"] = mapped_image

        for idx, perk in enumerate(major_perks):
            mapping_item = (
                major_mapping_by_key.get(_normalize_perk_key(perk.get("title")))
                or (major_mapping_list[idx] if idx < len(major_mapping_list) and isinstance(major_mapping_list[idx], dict) else {})
            )
            mapped_name = mapping_item.get("name", "") if isinstance(mapping_item, dict) else ""
            mapped_description = mapping_item.get("description") if isinstance(mapping_item, dict) else None
            mapped_image = _normalize_asset_path(mapping_item.get("image")) if isinstance(mapping_item, dict) else None
            perk["name"] = mapped_name or perk.get("title", "")
            perk["title"] = mapped_name or perk.get("title", "")
            perk["description"] = mapped_description if mapped_description else None
            perk["image"] = mapped_image

        result[hero_key] = {
            "minor": minor_perks,
            "major": major_perks,
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


def build_mode_rank_stats(heroes_index, stats_data):
    """產生 mode_rank_stats.json：hero_id -> mode -> rank -> map_id -> {win_rate, pick_rate}"""
    heroes_stats = stats_data.get("heroes_stats", {})
    stats_key_map = {str(k).lower(): k for k in heroes_stats.keys()}
    competitive_ranks = [
        "All",
        "Bronze",
        "Silver",
        "Gold",
        "Platinum",
        "Diamond",
        "Master",
        "Grandmaster",
        "Champion",
    ]

    result = {}
    for hero_idx in heroes_index:
        hero_id = hero_idx.get("id")
        en_name = str(hero_idx.get("en", "")).lower()
        matched_key = stats_key_map.get(en_name)
        hero_stats = heroes_stats.get(matched_key, {}) if matched_key else {}

        hero_entry = {
            "Quick Play": {"All": {}},
            "Competitive": {rank: {} for rank in competitive_ranks},
        }

        for mode, ranks in (("Quick Play", ["All"]), ("Competitive", competitive_ranks)):
            mode_data = hero_stats.get(mode, {})
            for rank in ranks:
                rank_data = mode_data.get(rank, {})
                map_stats = {}
                for map_id, stat in rank_data.items():
                    if map_id == "all-maps" or not isinstance(stat, dict):
                        continue
                    map_stats[map_id] = {
                        "win_rate": stat.get("win_rate"),
                        "pick_rate": stat.get("pick_rate"),
                    }
                hero_entry[mode][rank] = map_stats

        result[hero_id] = hero_entry

    return result


def build_app_ready_dataset(maps_index, heroes_index, map_recs, counter_idx, perks_idx, master, stats_data, mapping):
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
        # 取 perks 資料
        perks = perks_idx.get(hero_id, {"minor": [], "major": []})
        # 取地圖統計
        map_stats = build_map_stats_for_hero(en_name, stats_data)

        hero_entry = {
            **hero_idx,
            "map_recommendations": map_rec,
            "counter_data": counter,
            "perks": perks,
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
    hero_manifest = _read_manifest(os.path.join(DATA_DIR, "assets", "heroes", "manifest.json"))
    map_manifest = _read_manifest(os.path.join(DATA_DIR, "assets", "maps", "manifest.json"))
    guide_manifest = _read_manifest(os.path.join(DATA_DIR, "assets", "guide", "manifest.json"))

    if not master or not mapping or not stats:
        print("[失敗] 資料載入失敗，請確認來源檔案存在。")
        return

    asset_url_mapping = _build_asset_url_mapping(hero_manifest, map_manifest, guide_manifest)
    master = _localize_guide_images(master, asset_url_mapping)

    # 1. maps_index.json
    print("產生 maps_index.json...")
    maps_index = build_maps_index(mapping)
    save_json(os.path.join(APP_DIR, "maps_index.json"), maps_index)
    print(f"  ✓ 共 {len(maps_index)} 張地圖")

    # 2. heroes_index.json
    print("產生 heroes_index.json...")
    heroes_index = build_heroes_index(mapping, master, stats)
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

    # 5. perks_index.json
    print("產生 perks_index.json...")
    perks_idx = build_perks_index(master, mapping)
    save_json(os.path.join(APP_DIR, "perks_index.json"), perks_idx)
    print(f"  ✓ 共 {len(perks_idx)} 位英雄的 Perks 資料")

    # 6. app_ready_dataset.json
    print("產生 app_ready_dataset.json...")
    app_dataset = build_app_ready_dataset(
        maps_index, heroes_index, map_recs, counter_idx, perks_idx, master, stats, mapping
    )
    save_json(os.path.join(APP_DIR, "app_ready_dataset.json"), app_dataset)
    hero_count = len(app_dataset["heroes"])
    map_count = len(app_dataset["maps"])
    print(f"  ✓ 整合資料集：{hero_count} 位英雄、{map_count} 張地圖")

    # 7. mode_rank_stats.json
    print("產生 mode_rank_stats.json...")
    mode_rank_stats = build_mode_rank_stats(heroes_index, stats)
    save_json(os.path.join(APP_DIR, "mode_rank_stats.json"), mode_rank_stats)
    print(f"  ✓ 共 {len(mode_rank_stats)} 位英雄的模式/牌位地圖統計")

    print("\n[成功] 所有衍生資料檔已產生於 data/app/ 目錄。")


if __name__ == "__main__":
    main()
