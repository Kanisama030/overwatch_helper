import argparse
import json
import os
import sys
from urllib import error, request


API_URL_TEMPLATE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/markdown"
DEFAULT_URL = "https://overwatch.fandom.com/wiki/Perks"
DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "raw",
    "overwatch_fandom_perks.md",
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="使用 Cloudflare Browser Rendering API 將網頁轉成 Markdown 並存檔"
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="要轉換的網頁 URL")
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="輸出檔案路徑（預設 data/raw/overwatch_fandom_perks.md）",
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=0,
        help="Cloudflare API query cacheTTL（秒），0 代表停用快取",
    )
    return parser.parse_args()


def get_env_or_fail(name):
    value = os.getenv(name, "").strip()
    if not value:
        print(f"缺少環境變數: {name}")
        sys.exit(1)
    return value


def build_api_url(account_id, cache_ttl):
    base = API_URL_TEMPLATE.format(account_id=account_id)
    return f"{base}?cacheTTL={cache_ttl}"


def extract_markdown(api_json):
    result = api_json.get("result")
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("markdown", "content", "text", "data"):
            value = result.get(key)
            if isinstance(value, str):
                return value
    return ""


def fetch_markdown(account_id, api_token, page_url, cache_ttl):
    api_url = build_api_url(account_id, cache_ttl)
    payload = {
        "url": page_url,
        "gotoOptions": {"waitUntil": "networkidle2", "timeout": 60000},
        "bestAttempt": True,
    }
    req = request.Request(
        url=api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP 錯誤: {e.code}")
        print(body)
        sys.exit(1)
    except error.URLError as e:
        print(f"連線失敗: {e}")
        sys.exit(1)

    try:
        api_json = json.loads(raw)
    except json.JSONDecodeError:
        print("API 回傳非 JSON，原始內容如下:")
        print(raw[:2000])
        sys.exit(1)

    if not api_json.get("success", False):
        print("Cloudflare API 回傳失敗:")
        print(json.dumps(api_json, ensure_ascii=False, indent=2))
        sys.exit(1)

    markdown = extract_markdown(api_json)
    if not markdown.strip():
        print("API 成功但沒有取得 Markdown 內容，完整回應如下:")
        print(json.dumps(api_json, ensure_ascii=False, indent=2)[:5000])
        sys.exit(1)

    return markdown


def write_output(path, content):
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    return abs_path


def main():
    args = parse_args()
    account_id = get_env_or_fail("CLOUDFLARE_ACCOUNT_ID")
    api_token = get_env_or_fail("CLOUDFLARE_API_TOKEN")

    print(f"開始抓取: {args.url}")
    markdown = fetch_markdown(account_id, api_token, args.url, args.cache_ttl)
    output_path = write_output(args.output, markdown)
    print(f"完成，已輸出: {output_path}")


if __name__ == "__main__":
    main()
