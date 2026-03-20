import argparse
import asyncio
import json
import os
import sys
from typing import Dict, List, Set

from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSLATION_CACHE_DIR = os.path.join(BASE_DIR, "data", "cache", "translations")
WORKER_COUNT = 4

from translation_services.cache_service import CacheService
from translation_services.glossary_service import GlossaryService
from translation_services.translation_service import TranslationService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="批次翻譯所有英雄資料並輸出靜態翻譯檔",
    )
    parser.add_argument(
        "--heroes",
        default="",
        help="只處理指定英雄（逗號分隔，例如: ana,mercy,reinhardt）",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="若英雄輸出檔已存在則直接略過",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="單一英雄失敗時繼續處理下一位英雄",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(BASE_DIR, "data", "app", "i18n", "zh-TW"),
        help="靜態翻譯輸出目錄（預設 data/app/i18n/zh-TW）",
    )
    parser.add_argument(
        "--clear-output",
        action="store_true",
        help="開始前先清空輸出目錄中的舊 JSON 檔",
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
    cache_service = CacheService(cache_dir=TRANSLATION_CACHE_DIR)
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
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    if args.clear_output:
        for filename in os.listdir(output_dir):
            if filename.lower().endswith(".json"):
                try:
                    os.remove(os.path.join(output_dir, filename))
                except OSError:
                    pass

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

    print(f"開始批次翻譯，共 {len(planned)} 位英雄（{WORKER_COUNT} workers）。")
    if args.skip_existing:
        print("已啟用 --skip-existing：已有輸出檔的英雄會直接略過。")

    total = len(planned)
    semaphore = asyncio.Semaphore(WORKER_COUNT)
    stop_event = asyncio.Event()

    async def process_one(idx: int, hero_id: str, hero_data: Dict):
        output_path = os.path.join(output_dir, f"{hero_id}.json")
        if args.skip_existing and os.path.exists(output_path):
            print(f"[{idx}/{total}] ⏭️  略過 {hero_id}（已有輸出）")
            return ("skip", hero_id, "")

        print(f"[{idx}/{total}] 🔄 翻譯 {hero_id} ...")
        try:
            result = await translation_service.translate_hero(hero_id, hero_data, "zh-TW")
            section_count = len(result.get("sections", {}))
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[{idx}/{total}] ✅ 完成 {hero_id}（sections: {section_count}）")
            return ("ok", hero_id, "")
        except Exception as e:
            print(f"[{idx}/{total}] ❌ 失敗 {hero_id}：{e}")
            return ("fail", hero_id, str(e))

    async def run_item(idx: int, hero_id: str, hero_data: Dict):
        if stop_event.is_set():
            return ("aborted", hero_id, "")
        async with semaphore:
            if stop_event.is_set():
                return ("aborted", hero_id, "")
            status, item_hero_id, detail = await process_one(idx, hero_id, hero_data)
            if status == "fail" and not args.continue_on_error:
                stop_event.set()
            return (status, item_hero_id, detail)

    tasks = [
        asyncio.create_task(run_item(idx, hero_id, hero_data))
        for idx, (hero_id, hero_data) in enumerate(planned, start=1)
    ]
    results = await asyncio.gather(*tasks)

    ok_count = sum(1 for status, _, _ in results if status == "ok")
    skip_count = sum(1 for status, _, _ in results if status == "skip")
    failed = [hero_id for status, hero_id, _ in results if status == "fail"]
    aborted_count = sum(1 for status, _, _ in results if status == "aborted")

    print("\n=== 批次翻譯摘要 ===")
    print(f"成功: {ok_count}")
    print(f"略過: {skip_count}")
    print(f"失敗: {len(failed)}")
    if aborted_count:
        print(f"未執行: {aborted_count}（因錯誤提前停止）")
    if failed:
        print("失敗英雄: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
