"""
enrich_master_with_gemini.py
使用 Gemini API 讀取 overwatch_master.json 的指定章節內容，補齊：
1) 6.1.x Best Maps / 6.2.x Worst Maps
2) 8.2 Specific Hero Counters names（僅英雄 id 列表）

預設只補缺漏，不覆蓋既有內容。
"""

import argparse
import json
import os
import re
import time
from typing import Dict, List, Optional, Set, Tuple


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MASTER_PATH = os.path.join(DATA_DIR, "overwatch_master.json")
MAPPING_PATH = os.path.join(DATA_DIR, "overwatch_mapping.json")

DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_env_file_for_key(env_path: str, key: str) -> Optional[str]:
    if not os.path.exists(env_path):
        return None
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
    except Exception:
        return None
    return None


def get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key

    env_key = read_env_file_for_key(os.path.join(BASE_DIR, ".env"), "GEMINI_API_KEY")
    if env_key:
        return env_key

    raise RuntimeError("找不到 GEMINI_API_KEY。請先設定環境變數或在專案根目錄 .env 設定。")


def section_by_id(guide: List[dict], section_id: str) -> Optional[dict]:
    for sec in guide:
        if sec.get("id") == section_id:
            return sec
    return None


def section_index(guide: List[dict], section_id: str) -> int:
    for i, sec in enumerate(guide):
        if sec.get("id") == section_id:
            return i
    return -1


def section_children(guide: List[dict], parent_id: str) -> List[dict]:
    prefix = f"{parent_id}."
    parent_depth = parent_id.count(".") + 1
    result = []
    for sec in guide:
        sid = str(sec.get("id", ""))
        if sid.startswith(prefix) and sid.count(".") + 1 == parent_depth + 1:
            result.append(sec)
    return result


def section_content_text(guide: List[dict], section_id: str) -> str:
    sec = section_by_id(guide, section_id)
    if not sec:
        return ""
    content = sec.get("content") or []
    return "\n".join([str(x) for x in content if isinstance(x, str)]).strip()


def map_title_by_id(mapping: dict) -> Dict[str, str]:
    out = {}
    for m in mapping.get("maps", []):
        mid = str(m.get("id", "")).strip()
        en = str(m.get("en", "")).strip()
        if mid and en:
            out[mid] = en
    return out


def build_lookup(mapping: dict) -> dict:
    maps = mapping.get("maps", [])
    heroes = mapping.get("heroes", [])

    map_ids = {str(m.get("id", "")).strip() for m in maps if m.get("id")}
    mode_to_map_ids: Dict[str, List[str]] = {}
    for m in maps:
        mode = str(m.get("mode", "")).strip().lower()
        mid = str(m.get("id", "")).strip()
        if not mode or not mid:
            continue
        mode_to_map_ids.setdefault(mode, []).append(mid)

    hero_ids = {str(h.get("id", "")).strip() for h in heroes if h.get("id")}
    # 同時建立英文名稱索引，讓 prompt 可參考並提升辨識率。
    hero_en_by_id = {
        str(h.get("id", "")).strip(): str(h.get("en", "")).strip()
        for h in heroes
        if h.get("id")
    }

    subrole_to_hero_ids: Dict[str, List[str]] = {}
    for h in heroes:
        subrole = str(h.get("subrole", "")).strip().lower()
        hid = str(h.get("id", "")).strip()
        if not subrole or not hid:
            continue
        subrole_to_hero_ids.setdefault(subrole, []).append(hid)

    return {
        "map_ids": map_ids,
        "mode_to_map_ids": mode_to_map_ids,
        "hero_ids": hero_ids,
        "hero_en_by_id": hero_en_by_id,
        "subrole_to_hero_ids": subrole_to_hero_ids,
    }


def parse_json_from_response(text: str) -> dict:
    if not text:
        return {}
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        # 盡量從第一個 { 到最後一個 } 擷取 JSON
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
    return {}


def ensure_unique_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def sanitize_model_output(payload: dict, hero_id: str, lookup: dict) -> Tuple[List[str], List[str], List[str]]:
    map_ids: Set[str] = lookup["map_ids"]
    mode_to_map_ids: Dict[str, List[str]] = lookup["mode_to_map_ids"]
    hero_ids: Set[str] = lookup["hero_ids"]
    subrole_to_hero_ids: Dict[str, List[str]] = lookup["subrole_to_hero_ids"]

    best_map_ids = [str(x).strip().lower() for x in payload.get("best_map_ids", []) if isinstance(x, str)]
    worst_map_ids = [str(x).strip().lower() for x in payload.get("worst_map_ids", []) if isinstance(x, str)]
    best_modes = [str(x).strip().lower() for x in payload.get("best_modes", []) if isinstance(x, str)]
    worst_modes = [str(x).strip().lower() for x in payload.get("worst_modes", []) if isinstance(x, str)]

    best: List[str] = [mid for mid in best_map_ids if mid in map_ids]
    worst: List[str] = [mid for mid in worst_map_ids if mid in map_ids]

    for mode in best_modes:
        best.extend(mode_to_map_ids.get(mode, []))
    for mode in worst_modes:
        worst.extend(mode_to_map_ids.get(mode, []))

    best = ensure_unique_keep_order(best)
    worst = ensure_unique_keep_order(worst)
    best = [mid for mid in best if mid not in set(worst)]

    counter_hero_ids = [
        str(x).strip().lower() for x in payload.get("counter_hero_ids", []) if isinstance(x, str)
    ]
    counter_subroles = [
        str(x).strip().lower() for x in payload.get("counter_subroles", []) if isinstance(x, str)
    ]
    counters: List[str] = [hid for hid in counter_hero_ids if hid in hero_ids]
    for sr in counter_subroles:
        counters.extend(subrole_to_hero_ids.get(sr, []))

    counters = ensure_unique_keep_order(counters)
    counters = [hid for hid in counters if hid != hero_id]

    return best, worst, counters


def upsert_section(guide: List[dict], section_id: str, title: str, after_candidates: List[str]) -> dict:
    sec = section_by_id(guide, section_id)
    if sec:
        if not sec.get("title"):
            sec["title"] = title
        return sec

    insert_idx = -1
    for sid in after_candidates:
        idx = section_index(guide, sid)
        if idx > insert_idx:
            insert_idx = idx

    new_sec = {"id": section_id, "title": title}
    if insert_idx >= 0:
        guide.insert(insert_idx + 1, new_sec)
    else:
        guide.append(new_sec)
    return new_sec


def replace_children_sections(
    guide: List[dict],
    parent_id: str,
    title_by_map_id: Dict[str, str],
    map_ids: List[str],
    only_missing: bool,
    force: bool,
) -> bool:
    existing_children = section_children(guide, parent_id)
    has_existing_children = len(existing_children) > 0

    if only_missing and has_existing_children and not force:
        return False

    if force and has_existing_children:
        existing_ids = {c.get("id") for c in existing_children}
        guide[:] = [sec for sec in guide if sec.get("id") not in existing_ids]

    if not map_ids:
        return False

    # 計算插入位置：放在 parent 區塊後方（含既有直接子節點之後）。
    parent_idx = section_index(guide, parent_id)
    if parent_idx == -1:
        return False

    insert_idx = parent_idx
    depth = parent_id.count(".") + 1
    for idx in range(parent_idx + 1, len(guide)):
        sid = str(guide[idx].get("id", ""))
        if not sid.startswith(parent_id + "."):
            break
        if sid.count(".") + 1 == depth + 1:
            insert_idx = idx

    changed = False
    next_num = 1
    for map_id in map_ids:
        child_id = f"{parent_id}.{next_num}"
        next_num += 1
        title = title_by_map_id.get(map_id, map_id)
        guide.insert(
            insert_idx + 1,
            {
                "id": child_id,
                "title": title,
                "content": ["ai generated"],
            },
        )
        insert_idx += 1
        changed = True

    return changed


def should_fill_maps(guide: List[dict], only_missing: bool, force: bool) -> Tuple[bool, bool]:
    best_children = section_children(guide, "6.1")
    worst_children = section_children(guide, "6.2")

    if force:
        return True, True
    if only_missing:
        return len(best_children) == 0, len(worst_children) == 0
    return True, True


def should_fill_counter_names(guide: List[dict], only_missing: bool, force: bool) -> bool:
    sec = section_by_id(guide, "8.2")
    if force:
        return True
    if only_missing:
        if not sec:
            return True
        content = sec.get("content")
        return not isinstance(content, list) or len(content) == 0
    return True


def build_prompt(hero_id: str, guide: List[dict], lookup: dict) -> str:
    text_6 = section_content_text(guide, "6")
    text_61 = section_content_text(guide, "6.1")
    text_62 = section_content_text(guide, "6.2")
    text_8 = section_content_text(guide, "8")
    text_81 = section_content_text(guide, "8.1")

    map_catalog = []
    for mode, mids in lookup["mode_to_map_ids"].items():
        map_catalog.append({"mode": mode, "map_ids": mids})

    heroes_for_prompt = [
        {"id": hid, "en": lookup["hero_en_by_id"].get(hid, "")}
        for hid in sorted(list(lookup["hero_ids"]))
    ]

    subrole_catalog = [
        {"subrole": sr, "hero_ids": ids}
        for sr, ids in sorted(lookup["subrole_to_hero_ids"].items(), key=lambda x: x[0])
    ]

    return (
        "You are an Overwatch structured data extractor. "
        "Read the provided text and return JSON only (no extra prose).\n\n"
        f"Target hero id: {hero_id}\n\n"
        "Task A (Maps):\n"
        "- Read section 6, 6.1, and 6.2 content.\n"
        "- Output best_map_ids and worst_map_ids (map ids only).\n"
        "- If text mentions only a mode (for example: Control) without specific map names, put it in best_modes or worst_modes.\n"
        "- If a statement is neutral or mixed, infer whether it leans favorable or unfavorable for this hero and classify accordingly.\n"
        "- Do not be overly strict: include reasonable, text-supported inferences.\n"
        "- If the same map appears in both best and worst, keep it in worst.\n"
        "- If evidence is weak, you may leave it out. Do not invent maps.\n\n"
        "Task B (Counters):\n"
        "- Read section 8 and 8.1 content.\n"
        "- Output counter_hero_ids (hero ids only).\n"
        "- Do semantic judgment: not every hero mention is a true counter. Include only heroes that are actually described/implied as effective counters.\n"
        "- If a subrole is described as countering this hero, output that subrole in counter_subroles. But don't output subroles if that subrole doesn't actually exist in the description.\n"
        "- Ignore broad role-level statements (Tank/Damage/Support) because they are too coarse.\n"
        "- Do not include the target hero itself.\n"
        "- Do not be overly strict: include plausible counters when the text meaning supports it.\n\n"
        "Available map modes and ids:\n"
        f"{json.dumps(map_catalog, ensure_ascii=False)}\n\n"
        "Available heroes:\n"
        f"{json.dumps(heroes_for_prompt, ensure_ascii=False)}\n\n"
        "Available subrole mapping:\n"
        f"{json.dumps(subrole_catalog, ensure_ascii=False)}\n\n"
        "section 6 content:\n"
        f"{text_6}\n\n"
        "section 6.1 content:\n"
        f"{text_61}\n\n"
        "section 6.2 content:\n"
        f"{text_62}\n\n"
        "section 8 content:\n"
        f"{text_8}\n\n"
        "section 8.1 content:\n"
        f"{text_81}\n\n"
        "Return exactly this JSON shape:\n"
        "{\n"
        '  "best_map_ids": ["midtown"],\n'
        '  "worst_map_ids": ["new-junk-city"],\n'
        '  "best_modes": ["control"],\n'
        '  "worst_modes": [],\n'
        '  "counter_hero_ids": ["bastion"],\n'
        '  "counter_subroles": ["flanker"]\n'
        "}\n"
    )


def call_gemini_with_retry(
    api_key: str,
    model: str,
    prompt: str,
    max_retries: int,
    retry_base_seconds: float,
) -> dict:
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise RuntimeError(
            "缺少 google-genai 套件。請先執行：pip install google-genai"
        ) from e

    client = genai.Client(api_key=api_key)
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=1.0,
                    response_mime_type="application/json",
                ),
            )
            text = getattr(response, "text", "")
            return parse_json_from_response(text)
        except Exception as e:
            last_err = e
            if attempt >= max_retries:
                break
            sleep_s = retry_base_seconds * (2 ** attempt)
            time.sleep(sleep_s)
    raise RuntimeError(f"Gemini 呼叫失敗：{last_err}")


def process_hero(
    hero: dict,
    lookup: dict,
    title_by_map_id: Dict[str, str],
    api_key: str,
    model: str,
    only_missing: bool,
    force: bool,
    dry_run: bool,
    max_retries: int,
    retry_base_seconds: float,
) -> Tuple[bool, dict]:
    hero_id = str(hero.get("Hero", "")).strip().lower()
    guide = hero.get("Guide") or []
    if not hero_id or not isinstance(guide, list):
        return False, {"hero": hero_id, "reason": "缺少 Hero 或 Guide 結構不正確"}

    need_best, need_worst = should_fill_maps(guide, only_missing=only_missing, force=force)
    need_counter_names = should_fill_counter_names(guide, only_missing=only_missing, force=force)

    if not (need_best or need_worst or need_counter_names):
        return False, {"hero": hero_id, "reason": "已具備資料，略過"}

    prompt = build_prompt(hero_id, guide, lookup)
    raw = call_gemini_with_retry(
        api_key=api_key,
        model=model,
        prompt=prompt,
        max_retries=max_retries,
        retry_base_seconds=retry_base_seconds,
    )
    best_ids, worst_ids, counter_ids = sanitize_model_output(raw, hero_id, lookup)

    changed = False

    # 確保 6.1 / 6.2 section 存在。
    upsert_section(guide, "6.1", "Best Maps", ["6"])
    upsert_section(guide, "6.2", "Worst Maps", ["6.1", "6"])

    if need_best:
        changed = replace_children_sections(
            guide,
            parent_id="6.1",
            title_by_map_id=title_by_map_id,
            map_ids=best_ids,
            only_missing=only_missing,
            force=force,
        ) or changed

    if need_worst:
        changed = replace_children_sections(
            guide,
            parent_id="6.2",
            title_by_map_id=title_by_map_id,
            map_ids=worst_ids,
            only_missing=only_missing,
            force=force,
        ) or changed

    if need_counter_names:
        sec_82 = upsert_section(guide, "8.2", "Specific Hero Counters names", ["8.1", "8"])
        # 8.2 只輸出英雄 id 列表。
        sec_82["content"] = counter_ids
        changed = True

    if dry_run:
        return changed, {
            "hero": hero_id,
            "best_map_ids": best_ids,
            "worst_map_ids": worst_ids,
            "counter_hero_ids": counter_ids,
            "dry_run": True,
        }

    return changed, {
        "hero": hero_id,
        "best_map_ids": best_ids,
        "worst_map_ids": worst_ids,
        "counter_hero_ids": counter_ids,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="使用 Gemini 補齊 overwatch_master.json 的 Maps 與 Counter 名單"
    )
    parser.add_argument("--hero", default=None, help="只處理單一英雄 id（例如 domina）")
    parser.add_argument(
        "--only-missing",
        action="store_true",
        default=True,
        help="只補缺漏（預設啟用）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="強制覆蓋既有 6.1/6.2 子項與 8.2 content",
    )
    parser.add_argument("--dry-run", action="store_true", help="只顯示變更預覽，不寫回檔案")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini 模型（預設 {DEFAULT_MODEL}）")
    parser.add_argument("--max-retries", type=int, default=3, help="Gemini 呼叫失敗重試次數")
    parser.add_argument(
        "--retry-base-seconds",
        type=float,
        default=1.5,
        help="重試指數退避基礎秒數",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    master = load_json(MASTER_PATH)
    mapping = load_json(MAPPING_PATH)

    lookup = build_lookup(mapping)
    title_by_map_id = map_title_by_id(mapping)

    heroes = master.get("heroes", [])
    if not isinstance(heroes, list):
        raise RuntimeError("overwatch_master.json 的 heroes 結構不是陣列")

    target_heroes = heroes
    if args.hero:
        target = str(args.hero).strip().lower()
        target_heroes = [h for h in heroes if str(h.get("Hero", "")).strip().lower() == target]
        if not target_heroes:
            raise RuntimeError(f"找不到英雄 id: {target}")

    api_key = get_api_key()

    changed_count = 0
    failed_count = 0

    print("開始執行 Gemini 補齊流程...")
    print(f"模型：{args.model}")
    print(f"目標英雄數：{len(target_heroes)}")
    print(f"模式：{'dry-run' if args.dry_run else 'write'}")

    for hero in target_heroes:
        hero_id = str(hero.get("Hero", "")).strip().lower()
        try:
            changed, detail = process_hero(
                hero=hero,
                lookup=lookup,
                title_by_map_id=title_by_map_id,
                api_key=api_key,
                model=args.model,
                only_missing=args.only_missing,
                force=args.force,
                dry_run=args.dry_run,
                max_retries=args.max_retries,
                retry_base_seconds=args.retry_base_seconds,
            )
            if changed:
                changed_count += 1
            if detail.get("reason") == "已具備資料，略過":
                print(f"[略過] {hero_id} - 已具備資料")
            else:
                print(
                    f"[完成] {hero_id} best={detail.get('best_map_ids', [])} "
                    f"worst={detail.get('worst_map_ids', [])} counters={detail.get('counter_hero_ids', [])}"
                )
        except Exception as e:
            failed_count += 1
            print(f"[失敗] {hero_id}：{e}")

    if not args.dry_run:
        save_json(MASTER_PATH, master)
        print(f"\n已寫回：{MASTER_PATH}")

    print("\n執行完成")
    print(f"變更英雄數：{changed_count}")
    print(f"失敗英雄數：{failed_count}")


if __name__ == "__main__":
    main()
