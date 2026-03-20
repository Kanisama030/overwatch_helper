"""
preview_gemini_enrichment.py
產生 Gemini 補齊前的對照報告（不會改寫 overwatch_master.json）。

用途：
1) 抽樣英雄（預設 5 位）
2) 顯示原始 section 6/6.1/6.2/8/8.1 內容
3) 顯示 AI 推論出的 best/worst maps 與 counters
"""

import argparse
import json
import os
from datetime import datetime
from typing import Dict, List

from enrich_master_with_gemini import (
    BASE_DIR,
    DEFAULT_MODEL,
    MASTER_PATH,
    MAPPING_PATH,
    build_lookup,
    build_prompt,
    call_gemini_with_retry,
    get_api_key,
    load_json,
    map_title_by_id,
    sanitize_model_output,
    section_by_id,
    section_children,
    section_content_text,
)


DEFAULT_SAMPLE_HEROES = ["domina", "zarya", "ana", "roadhog", "kiriko"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="預覽 Gemini 補齊結果（原始內容 vs AI 輸出），不寫回資料檔"
    )
    parser.add_argument(
        "--heroes",
        default=",".join(DEFAULT_SAMPLE_HEROES),
        help="要測試的英雄 id，逗號分隔（預設 5 位）",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini 模型（預設 {DEFAULT_MODEL}）",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(BASE_DIR, "data", "app", "gemini_preview_report.json"),
        help="輸出報告檔路徑",
    )
    parser.add_argument("--max-retries", type=int, default=3, help="Gemini 呼叫失敗重試次數")
    parser.add_argument(
        "--retry-base-seconds",
        type=float,
        default=1.5,
        help="重試指數退避基礎秒數",
    )
    return parser.parse_args()


def _existing_map_titles(guide: List[dict], parent_id: str) -> List[str]:
    children = section_children(guide, parent_id)
    return [str(c.get("title", "")).strip() for c in children if c.get("title")]


def _safe_section_text(guide: List[dict], sid: str) -> str:
    return section_content_text(guide, sid)


def _hero_by_id(master: dict, hero_id: str):
    for hero in master.get("heroes", []):
        if str(hero.get("Hero", "")).strip().lower() == hero_id:
            return hero
    return None


def build_report_item(
    hero: dict,
    lookup: dict,
    map_name_by_id: Dict[str, str],
    model: str,
    api_key: str,
    max_retries: int,
    retry_base_seconds: float,
) -> dict:
    hero_id = str(hero.get("Hero", "")).strip().lower()
    guide = hero.get("Guide") or []

    prompt = build_prompt(hero_id, guide, lookup)
    raw = call_gemini_with_retry(
        api_key=api_key,
        model=model,
        prompt=prompt,
        max_retries=max_retries,
        retry_base_seconds=retry_base_seconds,
    )
    best_ids, worst_ids, counter_ids = sanitize_model_output(raw, hero_id, lookup)

    return {
        "hero": hero_id,
        "original": {
            "section_6": {
                "title": (section_by_id(guide, "6") or {}).get("title", "Maps"),
                "content": _safe_section_text(guide, "6"),
            },
            "section_6_1": {
                "title": (section_by_id(guide, "6.1") or {}).get("title", "Best Maps"),
                "content": _safe_section_text(guide, "6.1"),
                "existing_children_titles": _existing_map_titles(guide, "6.1"),
            },
            "section_6_2": {
                "title": (section_by_id(guide, "6.2") or {}).get("title", "Worst Maps"),
                "content": _safe_section_text(guide, "6.2"),
                "existing_children_titles": _existing_map_titles(guide, "6.2"),
            },
            "section_8": {
                "title": (section_by_id(guide, "8") or {}).get("title", "How to Counter"),
                "content": _safe_section_text(guide, "8"),
            },
            "section_8_1": {
                "title": (section_by_id(guide, "8.1") or {}).get("title", "Specific Hero Counters"),
                "content": _safe_section_text(guide, "8.1"),
            },
        },
        "ai_output": {
            "best_maps": [{"id": mid, "name": map_name_by_id.get(mid, mid)} for mid in best_ids],
            "worst_maps": [{"id": mid, "name": map_name_by_id.get(mid, mid)} for mid in worst_ids],
            "counter_hero_ids": counter_ids,
            "raw_model_json": raw,
        },
    }


def main() -> None:
    args = parse_args()

    master = load_json(MASTER_PATH)
    mapping = load_json(MAPPING_PATH)
    lookup = build_lookup(mapping)
    map_name_by_id = map_title_by_id(mapping)
    api_key = get_api_key()

    wanted = [h.strip().lower() for h in args.heroes.split(",") if h.strip()]
    # 去重並保留順序
    deduped = []
    seen = set()
    for hid in wanted:
        if hid in seen:
            continue
        deduped.append(hid)
        seen.add(hid)

    result_items = []
    failures = []

    print("開始產生 Gemini 對照報告...")
    print(f"模型：{args.model}")
    print(f"英雄：{deduped}")

    for hero_id in deduped:
        hero = _hero_by_id(master, hero_id)
        if not hero:
            failures.append({"hero": hero_id, "error": "找不到該英雄於 overwatch_master.json"})
            print(f"[略過] {hero_id} - 找不到英雄")
            continue

        try:
            item = build_report_item(
                hero=hero,
                lookup=lookup,
                map_name_by_id=map_name_by_id,
                model=args.model,
                api_key=api_key,
                max_retries=args.max_retries,
                retry_base_seconds=args.retry_base_seconds,
            )
            result_items.append(item)
            print(f"[完成] {hero_id}")
        except Exception as e:
            failures.append({"hero": hero_id, "error": str(e)})
            print(f"[失敗] {hero_id} - {e}")

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": args.model,
        "heroes_requested": deduped,
        "success_count": len(result_items),
        "failure_count": len(failures),
        "failures": failures,
        "items": result_items,
    }

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n報告已輸出")
    print(args.output)


if __name__ == "__main__":
    main()
