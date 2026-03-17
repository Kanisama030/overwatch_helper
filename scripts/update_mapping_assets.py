import json
import os
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

ROLE_MAP = {
    "damage": "Damage",
    "support": "Support",
    "tank": "Tank",
}

MODE_MAP = {
    "控制": "Control",
    "護送": "Escort",
    "閃擊點": "Flashpoint",
    "混合": "Hybrid",
    "推進": "Push",
}

# 依照你提供的官方 rates 下拉內容建立地圖清單（暫不處理地圖縮圖）
MAPS_FROM_RATES = [
    ("控制", "ilios", "伊利歐斯"),
    ("控制", "nepal", "尼泊爾"),
    ("控制", "lijiang-tower", "灕江天塔"),
    ("控制", "oasis", "綠洲城"),
    ("控制", "samoa", "薩摩亞"),
    ("控制", "busan", "釜山"),
    ("護送", "route-66", "66號公路"),
    ("護送", "havana", "哈瓦那"),
    ("護送", "junkertown", "垃圾鎮"),
    ("護送", "dorado", "多拉多"),
    ("護送", "watchpoint-gibraltar", "捍衛者基地：直布羅陀"),
    ("護送", "circuit-royal", "皇家賽道"),
    ("護送", "rialto", "里亞爾托"),
    ("護送", "shambali-monastery", "香巴里僧院"),
    ("閃擊點", "aatlis", "埃特利斯"),
    ("閃擊點", "new-junk-city", "新垃圾城"),
    ("閃擊點", "suravasa", "蘇拉瓦薩"),
    ("混合", "midtown", "中城區"),
    ("混合", "numbani", "努巴尼"),
    ("混合", "kings-row", "國王大道"),
    ("混合", "hollywood", "好萊塢"),
    ("混合", "paraiso", "帕拉伊索"),
    ("混合", "eichenwalde", "愛西瓦德"),
    ("混合", "blizzard-world", "暴雪樂園"),
    ("推進", "esperanca", "希望之城"),
    ("推進", "new-queen-street", "新皇后街"),
    ("推進", "runasapi", "盧納薩庇"),
    ("推進", "colosseo", "羅馬競技場"),
]


def slug_to_name(slug: str) -> str:
    parts = slug.split("-")
    return " ".join(p.capitalize() for p in parts)


def read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_heroes(html: str):
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    for a in soup.select("a.hero-card[href*='/heroes/']"):
        href = a.get("href", "")
        m = re.search(r"/heroes/([^/]+)/?$", href)
        if not m:
            continue
        hero_id = m.group(1)
        heading = a.select_one("h2[slot='heading']")
        name = heading.get_text(strip=True) if heading else ""
        role_raw = (a.get("data-role") or "").strip().lower()
        role = ROLE_MAP.get(role_raw, "Damage")
        image_el = a.select_one("blz-image.heroCardPortrait")
        image_src = (image_el.get("src") if image_el else "") or ""
        result[hero_id] = {
            "name": name,
            "role": role,
            "image": image_src,
        }
    return result


def download_hero_images(hero_rows, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    manifest = []
    for hero in hero_rows:
        hero_id = hero["id"]
        image_url = hero.get("_image", "")
        local_rel = ""
        if image_url:
            parsed = urlparse(image_url)
            ext = os.path.splitext(parsed.path)[1].lower() or ".png"
            filename = f"{hero_id}{ext}"
            local_path = os.path.join(output_dir, filename)
            try:
                r = requests.get(image_url, headers=HEADERS, timeout=30)
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(r.content)
                local_rel = f"data/assets/heroes/{filename}"
            except Exception as e:
                print(f"下載英雄縮圖失敗 {hero_id}: {e}")

        manifest.append(
            {
                "id": hero_id,
                "en": hero["en"],
                "zh": hero["zh"],
                "image_url": image_url,
                "local_path": local_rel,
            }
        )

    return manifest


def build_maps(existing_maps):
    en_by_id = {m.get("id"): m.get("en") for m in existing_maps}
    maps = []
    for mode_zh, map_id, zh_name in MAPS_FROM_RATES:
        en_name = en_by_id.get(map_id) or slug_to_name(map_id)
        maps.append(
            {
                "id": map_id,
                "en": en_name,
                "zh": zh_name,
                "mode": MODE_MAP[mode_zh],
            }
        )
    return maps


def fetch_overfast_maps() -> dict:
    """從 OverFast API 取得所有地圖資訊，回傳 key -> screenshot_url 字典。"""
    resp = requests.get("https://overfast-api.tekrop.fr/maps", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return {item["key"]: item["screenshot"] for item in resp.json()}


def download_map_images(map_rows: list, screenshot_by_key: dict, output_dir: str) -> list:
    """依照 mapping 地圖清單從 OverFast 下載縮圖，回傳 manifest 清單。"""
    os.makedirs(output_dir, exist_ok=True)
    manifest = []
    for m in map_rows:
        map_id = m["id"]
        image_url = screenshot_by_key.get(map_id, "")
        local_rel = ""
        status = "ok"
        if image_url:
            filename = f"{map_id}.jpg"
            local_path = os.path.join(output_dir, filename)
            try:
                r = requests.get(image_url, headers=HEADERS, timeout=30)
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(r.content)
                local_rel = f"data/assets/maps/{filename}"
            except Exception as e:
                print(f"下載地圖縮圖失敗 {map_id}: {e}")
                status = "failed"
        else:
            print(f"OverFast 無對應縮圖: {map_id}")
            status = "missing"
        manifest.append(
            {
                "id": map_id,
                "en": m["en"],
                "zh": m["zh"],
                "mode": m["mode"],
                "source": "overfast",
                "image_url": image_url,
                "local_path": local_rel,
                "status": status,
            }
        )
    return manifest


def main():
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "..", "data")
    mapping_path = os.path.join(data_dir, "overwatch_mapping.json")
    hero_assets_dir = os.path.join(data_dir, "assets", "heroes")
    hero_manifest_path = os.path.join(hero_assets_dir, "manifest.json")
    map_assets_dir = os.path.join(data_dir, "assets", "maps")
    map_manifest_path = os.path.join(map_assets_dir, "manifest.json")

    mapping = read_json(mapping_path)
    existing_heroes = mapping.get("heroes", [])
    existing_maps = mapping.get("maps", [])

    zh_html = fetch_html("https://overwatch.blizzard.com/zh-tw/heroes/")
    en_html = fetch_html("https://overwatch.blizzard.com/en-us/heroes/")
    zh_heroes = parse_heroes(zh_html)
    en_heroes = parse_heroes(en_html)

    existing_en = {h.get("id"): h.get("en", "") for h in existing_heroes}
    existing_order = [h.get("id") for h in existing_heroes if h.get("id")]

    merged_by_id = {}
    for hero_id, zh in zh_heroes.items():
        en_name = en_heroes.get(hero_id, {}).get("name") or existing_en.get(hero_id) or slug_to_name(hero_id)
        merged_by_id[hero_id] = {
            "id": hero_id,
            "en": en_name,
            "zh": zh.get("name") or en_name,
            "role": zh.get("role", "Damage"),
            "_image": zh.get("image", ""),
        }

    for hero_id, en in en_heroes.items():
        if hero_id not in merged_by_id:
            en_name = en.get("name") or existing_en.get(hero_id) or slug_to_name(hero_id)
            merged_by_id[hero_id] = {
                "id": hero_id,
                "en": en_name,
                "zh": en_name,
                "role": en.get("role", "Damage"),
                "_image": en.get("image", ""),
            }

    ordered_ids = [hid for hid in existing_order if hid in merged_by_id]
    for hid in sorted(merged_by_id.keys()):
        if hid not in ordered_ids:
            ordered_ids.append(hid)

    heroes = [merged_by_id[hid] for hid in ordered_ids]
    maps = build_maps(existing_maps)

    manifest = download_hero_images(heroes, hero_assets_dir)
    write_json(hero_manifest_path, manifest)

    for hero in heroes:
        hero.pop("_image", None)

    mapping["heroes"] = heroes
    mapping["maps"] = maps
    write_json(mapping_path, mapping)

    # 下載地圖縮圖
    print("\n--- 下載地圖縮圖 (OverFast API) ---")
    screenshot_by_key = fetch_overfast_maps()
    map_manifest = download_map_images(maps, screenshot_by_key, map_assets_dir)
    write_json(map_manifest_path, map_manifest)
    ok_count = sum(1 for m in map_manifest if m["status"] == "ok")
    fail_count = sum(1 for m in map_manifest if m["status"] != "ok")

    print(f"✅ 已更新英雄資料: {len(heroes)} 位")
    print(f"✅ 已更新地圖資料: {len(maps)} 張")
    print(f"✅ 已下載英雄縮圖並輸出清單: {hero_manifest_path}")
    print(f"✅ 地圖縮圖: {ok_count} 張成功, {fail_count} 張失敗/缺少")
    print(f"✅ 已輸出地圖縮圖清單: {map_manifest_path}")


if __name__ == "__main__":
    main()
