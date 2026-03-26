import json
import os
import re
import unicodedata

import pandas as pd


ALLOWED_PERKS_IDS = ["5", "5.1", "5.1.1", "5.1.2", "5.2", "5.2.1", "5.2.2"]
NOT_FOUND_MARKERS = [
    "the page you are looking for is not found",
    "page you are looking for is not found",
]


def pick_preferred_map_stats(map_stats):
    # 優先使用 all-maps，若不存在則退回第一筆可用地圖資料
    if not isinstance(map_stats, dict) or not map_stats:
        return {}
    if "all-maps" in map_stats:
        return map_stats["all-maps"]
    first_map_key = next(iter(map_stats.keys()))
    return map_stats.get(first_map_key, {})


def _normalize_lookup_key(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower().strip()
    lowered = re.sub(r"[\s\.\-_:]+", "", lowered)
    return lowered


def _fallback_id_from_name(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower().strip()
    lowered = re.sub(r"[^\w\s-]", "", lowered)
    lowered = lowered.replace("_", "-")
    lowered = re.sub(r"\s+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered).strip("-")
    return lowered or "unknown-hero"


def _resolve_perk_absorb_target(section_id):
    sid = str(section_id or "")
    if sid.startswith("5.1"):
        return "5.1.2"
    if sid.startswith("5.2"):
        return "5.2.2"
    return "5.2.2"


def _normalize_content_list(value):
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _merge_section(target, source):
    source_title = str(source.get("title", "") or "")
    if not target["title"] and source_title:
        target["title"] = source_title

    source_content = _normalize_content_list(source.get("content"))
    for line in source_content:
        if line not in target["content"]:
            target["content"].append(line)


def _looks_like_perk_title(text):
    value = str(text or "").strip()
    if not value or len(value) > 60:
        return False
    if any(ch in value for ch in [".", "!", "?", ":", ";"]):
        return False
    return bool(re.search(r"[A-Za-z]", value))


def _repair_perk_branch(perks_sections, parent_id, first_id, second_id):
    parent = perks_sections[parent_id]
    first = perks_sections[first_id]
    second = perks_sections[second_id]

    parent_content = _normalize_content_list(parent.get("content"))
    first_content = _normalize_content_list(first.get("content"))
    second_content = _normalize_content_list(second.get("content"))

    # 常見錯位：第一個 Perk 名稱與描述被塞進父節點，第一個子節點其實是第二個 Perk
    if (
        parent_content
        and _looks_like_perk_title(parent_content[0])
        and first.get("title")
        and not second.get("title")
        and str(parent_content[0]).strip().lower() != str(first.get("title", "")).strip().lower()
    ):
        inferred_first_title = parent_content[0].strip()
        inferred_first_content = parent_content[1:]
        original_second_title = str(first.get("title", "")).strip()
        original_second_content = list(first_content)

        split_first_content = []
        split_second_content = []
        switched = False
        for line in original_second_content:
            lowered = line.lower()
            if original_second_title and original_second_title.lower() in lowered:
                switched = True
            elif "recommended minor perk" in lowered:
                switched = True

            if switched:
                split_second_content.append(line)
            else:
                split_first_content.append(line)

        if inferred_first_content:
            first["content"] = inferred_first_content
            second["content"] = original_second_content
        else:
            if split_first_content:
                first["content"] = split_first_content
                second["content"] = split_second_content
            else:
                first["content"] = []
                second["content"] = original_second_content

        first["title"] = inferred_first_title
        second["title"] = original_second_title
        parent["content"] = []

    # 若第二個子節點仍缺標題，盡量從內容推斷
    if not second.get("title") and second_content:
        for line in second_content:
            if _looks_like_perk_title(line):
                second["title"] = line.strip()
                second["content"] = [c for c in second_content if c != line]
                break

    # 若第二個子節點缺標題，嘗試從第一個子節點內容中擷取（例如: "The best tip for Extra Edge ...")
    first_content = _normalize_content_list(first.get("content"))
    if not second.get("title") and first.get("title") and first_content:
        split_index = None
        inferred_second_title = None
        for idx, line in enumerate(first_content):
            match = re.search(r"\bfor ([A-Z][A-Za-z0-9'\-]*(?: [A-Z][A-Za-z0-9'\-]*){0,3})\b", line)
            if not match:
                continue
            candidate = match.group(1).strip()
            if candidate.lower() == str(first.get("title", "")).strip().lower():
                continue
            inferred_second_title = candidate
            split_index = idx
            break

        if inferred_second_title and split_index is not None:
            before = first_content[:split_index]
            after = first_content[split_index:]
            if after:
                first["content"] = before
                second["title"] = inferred_second_title
                second["content"] = after


def fix_perks_structure(guide):
    if not isinstance(guide, list):
        guide = []

    perks_sections = {
        sid: {"id": sid, "title": "", "content": []}
        for sid in ALLOWED_PERKS_IDS
    }
    fixes = {
        "absorbed_ids": [],
        "added_missing_ids": [],
        "removed_invalid_ids": [],
    }

    non_perks_sections = []
    first_perks_insert_index = None

    for section in guide:
        if not isinstance(section, dict):
            continue
        sid = str(section.get("id", "")).strip()
        if sid.startswith("5"):
            if first_perks_insert_index is None:
                first_perks_insert_index = len(non_perks_sections)

            if sid in perks_sections:
                _merge_section(perks_sections[sid], section)
            else:
                target_id = _resolve_perk_absorb_target(sid)
                _merge_section(perks_sections[target_id], section)
                fixes["absorbed_ids"].append(f"{sid}->{target_id}")
                fixes["removed_invalid_ids"].append(sid)
        else:
            non_perks_sections.append(section)

    for sid in ALLOWED_PERKS_IDS:
        if not any(str((s or {}).get("id", "")).strip() == sid for s in guide if isinstance(s, dict)):
            fixes["added_missing_ids"].append(sid)

    _repair_perk_branch(perks_sections, "5.1", "5.1.1", "5.1.2")
    _repair_perk_branch(perks_sections, "5.2", "5.2.1", "5.2.2")

    fixed_perks = [perks_sections[sid] for sid in ALLOWED_PERKS_IDS]

    if first_perks_insert_index is None:
        fixed_guide = non_perks_sections + fixed_perks
    else:
        fixed_guide = (
            non_perks_sections[:first_perks_insert_index]
            + fixed_perks
            + non_perks_sections[first_perks_insert_index:]
        )
    return fixed_guide, fixes


def _guide_contains_not_found(guide):
    for section in guide if isinstance(guide, list) else []:
        if not isinstance(section, dict):
            continue
        title = str(section.get("title", "") or "").lower()
        content_text = " ".join(_normalize_content_list(section.get("content"))).lower()
        all_text = f"{title} {content_text}"
        if any(marker in all_text for marker in NOT_FOUND_MARKERS):
            return True
    return False


def sanitize_guide(guide):
    if _guide_contains_not_found(guide):
        return [], {"guide_cleared_404": True, "perks": None}

    fixed_guide, perk_fixes = fix_perks_structure(guide)
    has_perk_fix = any(perk_fixes[key] for key in perk_fixes)
    return fixed_guide, {"guide_cleared_404": False, "perks": perk_fixes if has_perk_fix else None}


def _build_hero_mapping_lookup(mapping):
    lookup = {}
    ids = set()
    for hero in mapping.get("heroes", []):
        hero_id = str(hero.get("id", "")).strip()
        if not hero_id:
            continue
        ids.add(hero_id.lower())
        en_name = hero.get("en", "")
        lookup[_normalize_lookup_key(en_name)] = hero_id
        lookup[_normalize_lookup_key(hero_id)] = hero_id
    return lookup, ids


def validate_and_fix_master_data(master_file=None, mapping_file=None, write_back=True):
    base_dir = os.path.dirname(__file__)
    if master_file is None:
        master_file = os.path.join(base_dir, "..", "data", "overwatch_master.json")
    if mapping_file is None:
        mapping_file = os.path.join(base_dir, "..", "data", "overwatch_mapping.json")

    if not os.path.exists(master_file):
        print(f"[驗證失敗] 找不到 master 檔案: {master_file}")
        return False
    if not os.path.exists(mapping_file):
        print(f"[驗證失敗] 找不到 mapping 檔案: {mapping_file}")
        return False

    with open(master_file, "r", encoding="utf-8") as f:
        master_data = json.load(f)
    with open(mapping_file, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    _, id_set = _build_hero_mapping_lookup(mapping)

    changed = False
    heroes = master_data.get("heroes", [])
    for hero in heroes:
        hero_name = str(hero.get("name", "")).strip()
        if hero_name.lower() not in id_set:
            print(f"[驗證失敗] hero.name 非 mapping.id: {hero_name}")
            return False

        fixed_guide, fix_info = sanitize_guide(hero.get("guide", []))
        if fixed_guide != hero.get("guide", []):
            hero["guide"] = fixed_guide
            changed = True
            if fix_info["guide_cleared_404"]:
                print(f"[修復] {hero_name}: Guide 命中 404 內容，已清空。")
            if fix_info["perks"]:
                print(f"[修復] {hero_name}: Perks 修復 {fix_info['perks']}")

    if changed and write_back:
        with open(master_file, "w", encoding="utf-8") as f:
            json.dump(master_data, f, ensure_ascii=False, indent=2)
        print("[驗證] overwatch_master.json 已自動修復並覆寫。")
    else:
        print("[驗證] overwatch_master.json 結構檢查完成。")
    return True


def _build_hero_stats_map_from_df(stats_df):
    hero_stats_map = {}
    if stats_df.empty:
        return hero_stats_map

    for _, row in stats_df.iterrows():
        h_name = row["Hero"]
        mode = row["Mode"]
        tier = row["Tier"]
        map_name = row["Map"] if "Map" in stats_df.columns and pd.notna(row["Map"]) else "all-maps"

        if h_name not in hero_stats_map:
            hero_stats_map[h_name] = {}

        if mode not in hero_stats_map[h_name]:
            hero_stats_map[h_name][mode] = {}

        if tier not in hero_stats_map[h_name][mode]:
            hero_stats_map[h_name][mode][tier] = {}

        hero_stats_map[h_name][mode][tier][map_name] = {
            "win_rate": row["Win Rate (%)"],
            "pick_rate": row["Pick Rate (%)"],
            "role": row["Role"],
        }

    return hero_stats_map


def build_overwatch_stats_from_blizzard_csv(raw_csv_path=None, output_stats_file=None):
    base_dir = os.path.dirname(__file__)
    if raw_csv_path is None:
        raw_csv_path = os.path.join(base_dir, "..", "data", "raw", "blizzard_stats.csv")
    if output_stats_file is None:
        output_stats_file = os.path.join(base_dir, "..", "data", "overwatch_stats.json")

    if not os.path.exists(raw_csv_path):
        print(f"[警告] 找不到 Blizzard 資料: {raw_csv_path}，略過更新 overwatch_stats.json")
        return False

    stats_df = pd.read_csv(raw_csv_path)
    hero_stats_map = _build_hero_stats_map_from_df(stats_df)
    stats_data = {
        "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "heroes_stats": hero_stats_map,
    }

    with open(output_stats_file, "w", encoding="utf-8") as f:
        json.dump(stats_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 已更新 Blizzard 統計: {output_stats_file}")
    return True


def merge_overwatch_data():
    base_dir = os.path.dirname(__file__)
    raw_dir = os.path.join(base_dir, "..", "data", "raw")
    output_file = os.path.join(base_dir, "..", "data", "overwatch_master.json")
    output_stats_file = os.path.join(base_dir, "..", "data", "overwatch_stats.json")
    mapping_file = os.path.join(base_dir, "..", "data", "overwatch_mapping.json")

    # 1. 讀取 Mobalytics 資料
    m_path = os.path.join(raw_dir, "mobalytics_heroes.json")
    if not os.path.exists(m_path):
        print(f"找不到 Mobalytics 資料: {m_path}")
        return

    with open(m_path, "r", encoding="utf-8") as f:
        mobalytics_data = json.load(f)

    # 2. 讀取 Blizzard 資料
    b_path = os.path.join(raw_dir, "blizzard_stats.csv")
    if not os.path.exists(b_path):
        print(f"找不到 Blizzard 資料: {b_path}")
        stats_df = pd.DataFrame()
    else:
        stats_df = pd.read_csv(b_path)

    # 3. 讀取 mapping（for name=id）
    if not os.path.exists(mapping_file):
        print(f"找不到 mapping 資料: {mapping_file}")
        return
    with open(mapping_file, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)
    hero_lookup, hero_id_set = _build_hero_mapping_lookup(mapping_data)

    # 4. 處理統計數據 (整理成 Hero -> Mode -> Tier -> Map)
    hero_stats_map = _build_hero_stats_map_from_df(stats_df)

    # 5. 儲存完整地圖維度統計
    stats_data = {
        "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "heroes_stats": hero_stats_map,
    }

    with open(output_stats_file, "w", encoding="utf-8") as f:
        json.dump(stats_data, f, ensure_ascii=False, indent=2)

    # 6. 整合英雄資料
    master_heroes = []
    used_ids = set()

    for moba_hero in mobalytics_data.get("heroes", []):
        hero_name = str(moba_hero.get("Hero", "")).strip()
        lookup_key = _normalize_lookup_key(hero_name)
        hero_id = hero_lookup.get(lookup_key)
        if not hero_id:
            fallback_id = _fallback_id_from_name(hero_name)
            candidate_id = fallback_id
            suffix = 2
            while candidate_id.lower() in hero_id_set or candidate_id.lower() in used_ids:
                candidate_id = f"{fallback_id}-{suffix}"
                suffix += 1
            hero_id = candidate_id
            print(f"[警告] 找不到 mapping 對應: {hero_name}，改用 fallback id: {hero_id}")

        used_ids.add(hero_id.lower())

        # 直接從地圖維度資料取 Quick Play / All / all-maps 作為預設顯示數值
        hero_map_stats = hero_stats_map.get(hero_name, {})
        default_stats = pick_preferred_map_stats(hero_map_stats.get("Quick Play", {}).get("All", {}))
        if not default_stats:
            default_stats = pick_preferred_map_stats(hero_map_stats.get("Competitive", {}).get("All", {}))

        fixed_guide, fix_info = sanitize_guide(moba_hero.get("Guide", []))
        if fix_info["guide_cleared_404"]:
            print(f"[修復] {hero_name}: Guide 命中 404 內容，已清空。")
        if fix_info["perks"]:
            print(f"[修復] {hero_name}: Perks 修復 {fix_info['perks']}")

        hero_combined = {
            "name": hero_id,
            "tier": moba_hero.get("Tier"),
            "role": default_stats.get("role", "UNKNOWN"),
            "default_stats": default_stats,
            "guide": fixed_guide,
        }
        master_heroes.append(hero_combined)

    # 7. 儲存大整合 JSON
    master_data = {
        "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "heroes": master_heroes,
        "meta_commentary": mobalytics_data.get("meta_commentary", []),
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)

    validate_ok = validate_and_fix_master_data(output_file, mapping_file, write_back=True)
    if not validate_ok:
        raise RuntimeError("overwatch_master.json 驗證失敗，請檢查 mapping 與合併規則。")

    print(f"✅ 資料整合完成！已產生: {output_file}")
    print(f"✅ 地圖維度統計已產生: {output_stats_file}")


if __name__ == "__main__":
    merge_overwatch_data()
