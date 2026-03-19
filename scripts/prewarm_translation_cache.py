import argparse
import asyncio
import json
import os
import sys
from typing import Dict, List, Set

from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.append(BACKEND_DIR)

from services.cache_service import CacheService
from services.glossary_service import GlossaryService
from services.translation_service import TranslationService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="批次翻譯所有英雄資料並預熱 backend/cache",
    )
    parser.add_argument(
        "--heroes",
        default="",
        help="只處理指定英雄（逗號分隔，例如: ana,mercy,reinhardt）",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="若英雄快取檔已存在則直接略過",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="單一英雄失敗時繼續處理下一位英雄",
    )
    return parser.parse_args()


def parse_hero_filter(raw: str) -> Set[str]:
    if not raw:
        return set()
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def load_master_data() -> List[Dict]:
    master_path = os.path.join(BASE_DIR, "data", "overwatch_master.json")
    with open(master_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)
    return master_data.get("heroes", [])


def build_services() -> TranslationService:
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("找不到 GEMINI_API_KEY，請先在 .env 設定。")

    glossary_service = GlossaryService(
        mapping_path=os.path.join(BASE_DIR, "data", "overwatch_mapping.json")
    )
    cache_service = CacheService(cache_dir=os.path.join(BACKEND_DIR, "cache"))
    return TranslationService(
        api_key=api_key,
        model_name="gemini-3.1-flash-lite-preview",
        glossary_service=glossary_service,
        cache_service=cache_service,
    )


async def main() -> int:
    args = parse_args()
    hero_filter = parse_hero_filter(args.heroes)
    heroes = load_master_data()
    translation_service = build_services()
    cache_dir = os.path.join(BACKEND_DIR, "cache")

    planned = []
    for hero in heroes:
        hero_id = str(hero.get("Hero", "")).strip().lower()
        if not hero_id:
            continue
        if hero_filter and hero_id not in hero_filter:
            continue
        planned.append((hero_id, hero))

    if not planned:
        print("沒有符合條件的英雄可處理。")
        return 0

    print(f"開始批次翻譯，共 {len(planned)} 位英雄。")
    if args.skip_existing:
        print("已啟用 --skip-existing：已有快取檔的英雄會直接略過。")

    ok_count = 0
    skip_count = 0
    failed: List[str] = []

    for idx, (hero_id, hero_data) in enumerate(planned, start=1):
        cache_path = os.path.join(cache_dir, f"{hero_id}.json")
        if args.skip_existing and os.path.exists(cache_path):
            skip_count += 1
            print(f"[{idx}/{len(planned)}] ⏭️  略過 {hero_id}（已有快取）")
            continue

        print(f"[{idx}/{len(planned)}] 🔄 翻譯 {hero_id} ...")
        try:
            result = await translation_service.translate_hero(hero_id, hero_data, "zh-TW")
            section_count = len(result.get("sections", {}))
            ok_count += 1
            print(f"[{idx}/{len(planned)}] ✅ 完成 {hero_id}（sections: {section_count}）")
        except Exception as e:
            failed.append(hero_id)
            print(f"[{idx}/{len(planned)}] ❌ 失敗 {hero_id}：{e}")
            if not args.continue_on_error:
                break

    print("\n=== 批次翻譯摘要 ===")
    print(f"成功: {ok_count}")
    print(f"略過: {skip_count}")
    print(f"失敗: {len(failed)}")
    if failed:
        print("失敗英雄: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
