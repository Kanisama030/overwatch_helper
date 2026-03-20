import argparse
import asyncio
import os
import subprocess
import sys

DEFAULT_PLAYWRIGHT_WORKERS = 8
DEFAULT_CLOUDFLARE_WORKERS = 8

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scrapers"))
sys.path.append(os.path.dirname(__file__))


def parse_args():
    parser = argparse.ArgumentParser(description="更新 Overwatch 主資料流程")
    parser.add_argument(
        "--mobalytics-method",
        choices=["cloudflare", "playwright"],
        default="cloudflare",
        help="Mobalytics 抓取方法（預設 cloudflare）",
    )
    parser.add_argument(
        "--mobalytics-smoke-hero",
        default=None,
        help="僅抓取單一英雄（例如 roadhog）",
    )
    parser.add_argument(
        "--mobalytics-workers",
        type=int,
        default=DEFAULT_CLOUDFLARE_WORKERS,
        help=f"Cloudflare 模式 worker 數（預設 {DEFAULT_CLOUDFLARE_WORKERS}）",
    )
    parser.add_argument(
        "--with-enrichment",
        action="store_true",
        help="執行 enrich_master_with_gemini.py 補齊章節",
    )
    parser.add_argument(
        "--with-translations",
        action="store_true",
        help="更新流程末尾執行翻譯預生成（data/app/i18n/zh-TW）",
    )
    parser.add_argument(
        "--translation-heroes",
        default="",
        help="搭配 --with-translations 使用，只處理指定英雄（逗號分隔）",
    )
    parser.add_argument(
        "--translation-skip-existing",
        action="store_true",
        help="搭配 --with-translations 使用，若輸出檔存在則略過",
    )
    parser.add_argument(
        "--translation-continue-on-error",
        action="store_true",
        help="搭配 --with-translations 使用，單一英雄失敗時繼續",
    )
    return parser.parse_args()


def run_enrichment():
    print("\n--- [額外] 補齊章節（enrich_master_with_gemini.py）---")
    result = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "enrich_master_with_gemini.py")])
    if result.returncode != 0:
        print("⚠️  enrich_master_with_gemini.py 執行失敗，將保留既有內容繼續流程")


def run_build_app_data():
    print("\n--- [主流程] 重建前端衍生資料（build_app_data.py）---")
    result = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "build_app_data.py")])
    if result.returncode != 0:
        print("⚠️  build_app_data.py 執行失敗，但主資料更新已完成")


def run_prewarm_translation_cache(args):
    print("\n--- [額外] 產生靜態翻譯檔（prewarm_translation_cache.py）---")
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "prewarm_translation_cache.py")]
    if args.translation_heroes:
        cmd.extend(["--heroes", args.translation_heroes])
    if args.translation_skip_existing:
        cmd.append("--skip-existing")
    if args.translation_continue_on_error:
        cmd.append("--continue-on-error")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("⚠️  prewarm_translation_cache.py 執行失敗，將保留既有翻譯檔")


async def main():
    args = parse_args()
    worker_count = DEFAULT_PLAYWRIGHT_WORKERS
    print("🚀 開始更新 Overwatch 主資料流程...")
    try:
        from scrape_mobalytics import scrape_mobalytics
        from scrape_mobalytics_cloudflare import scrape_mobalytics_cloudflare
        from scrape_blizzard import scrape_blizzard
        from merge_data import merge_overwatch_data, validate_and_fix_master_data
    except ImportError as e:
        print(f"匯入模組失敗: {e}")
        raise SystemExit(1)

    if args.mobalytics_method == "cloudflare":
        print("\n--- [1/4] 抓取 Mobalytics 指南（Cloudflare Markdown） ---")
        await scrape_mobalytics_cloudflare(
            smoke_hero=args.mobalytics_smoke_hero,
            build_master=True,
            worker_count=args.mobalytics_workers,
        )
        print(f"\n--- [2/4] 抓取 Blizzard 數據（all-maps + 逐地圖, {worker_count} workers） ---")
        await scrape_blizzard(worker_count=worker_count)
        print("\n--- [3/4] Cloudflare 模式已直接輸出 overwatch_master.json，略過 merge_data ---")
    else:
        print(f"\n--- [1/4] 抓取 Mobalytics 指南（Playwright，{worker_count} workers） ---")
        await scrape_mobalytics(worker_count=worker_count)
        print(f"\n--- [2/4] 抓取 Blizzard 數據（all-maps + 逐地圖, {worker_count} workers） ---")
        await scrape_blizzard(worker_count=worker_count)
        print("\n--- [3/4] 整合資料並驗證輸出 ---")
        merge_overwatch_data()
        if not validate_and_fix_master_data(write_back=True):
            raise RuntimeError("資料結構驗證未通過，已中止流程。")

    if args.with_enrichment:
        run_enrichment()

    run_build_app_data()
    if args.with_translations:
        run_prewarm_translation_cache(args)

    print("\n✨ 主資料更新流程已完成！")


if __name__ == "__main__":
    asyncio.run(main())
