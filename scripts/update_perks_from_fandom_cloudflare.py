import argparse
import json
import os
import re
import sys
from urllib import error, request
from urllib.parse import urlparse

import requests


API_URL_TEMPLATE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/markdown"
HTML_API_URL_TEMPLATE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/content"
DEFAULT_URL = "https://overwatch.fandom.com/wiki/Perks"
DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_MARKDOWN_PATH = os.path.join(DATA_DIR, "raw", "overwatch_fandom_perks.md")
RAW_HTML_PATH = os.path.join(DATA_DIR, "raw", "overwatch_fandom_perks.html")
DEFAULT_MAPPING_PATH = os.path.join(DATA_DIR, "overwatch_mapping.json")
DEFAULT_ASSETS_DIR = os.path.join(DATA_DIR, "assets", "perks")
DEFAULT_MANIFEST_PATH = os.path.join(DEFAULT_ASSETS_DIR, "manifest.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="使用 Cloudflare + Gemini 更新 overwatch_mapping 的 perks（含說明與圖片）"
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Perks 頁面 URL")
    parser.add_argument("--cache-ttl", type=int, default=0, help="Cloudflare API cacheTTL（秒）")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini 模型名稱")
    parser.add_argument("--mapping-path", default=DEFAULT_MAPPING_PATH, help="overwatch_mapping.json 路徑")
    parser.add_argument("--raw-markdown-output", default=RAW_MARKDOWN_PATH, help="原始 markdown 輸出路徑")
    parser.add_argument("--raw-html-output", default=RAW_HTML_PATH, help="原始 html 輸出路徑")
    parser.add_argument("--assets-dir", default=DEFAULT_ASSETS_DIR, help="perks 圖片下載目錄")
    parser.add_argument("--manifest-path", default=DEFAULT_MANIFEST_PATH, help="perks 圖片 manifest 路徑")
    parser.add_argument("--skip-image-download", action="store_true", help="只更新 mapping，不下載圖片")
    parser.add_argument("--skip-existing", action="store_true", help="下載圖片時若檔案已存在則略過")
    parser.add_argument("--dry-run", action="store_true", help="僅預覽，不寫回 mapping 與 manifest")
    return parser.parse_args()


def read_env_file_for_key(env_path, key):
    if not os.path.exists(env_path):
        return None
    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip().strip('"').strip("'")
    return None


def get_env_or_fail(name):
    value = os.getenv(name, "").strip()
    if value:
        return value
    env_value = read_env_file_for_key(os.path.join(BASE_DIR, ".env"), name)
    if env_value:
        return env_value
    print(f"缺少環境變數: {name}")
    sys.exit(1)


def build_api_url(account_id, cache_ttl):
    base = API_URL_TEMPLATE.format(account_id=account_id)
    return f"{base}?cacheTTL={cache_ttl}"


def build_html_api_url(account_id, cache_ttl):
    base = HTML_API_URL_TEMPLATE.format(account_id=account_id)
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


def fetch_markdown_with_cloudflare(account_id, api_token, page_url, cache_ttl):
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
        with request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Cloudflare HTTP 錯誤 {e.code}: {body[:1500]}") from e
    except error.URLError as e:
        raise RuntimeError(f"Cloudflare 連線失敗: {e}") from e

    try:
        api_json = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Cloudflare API 回傳非 JSON: {raw[:1000]}") from e

    if not api_json.get("success", False):
        raise RuntimeError(f"Cloudflare API 回傳失敗: {json.dumps(api_json, ensure_ascii=False)[:1500]}")

    markdown = extract_markdown(api_json)
    if not markdown.strip():
        raise RuntimeError("Cloudflare API 成功但沒有取得 markdown 內容")
    return markdown


def extract_html(api_json):
    result = api_json.get("result")
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("content", "html", "text", "data"):
            value = result.get(key)
            if isinstance(value, str):
                return value
    return ""


def fetch_html_with_cloudflare(account_id, api_token, page_url, cache_ttl):
    api_url = build_html_api_url(account_id, cache_ttl)
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
        with request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Cloudflare HTML HTTP 錯誤 {e.code}: {body[:1500]}") from e
    except error.URLError as e:
        raise RuntimeError(f"Cloudflare HTML 連線失敗: {e}") from e

    try:
        api_json = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Cloudflare HTML API 回傳非 JSON: {raw[:1000]}") from e

    if not api_json.get("success", False):
        raise RuntimeError(f"Cloudflare HTML API 回傳失敗: {json.dumps(api_json, ensure_ascii=False)[:1500]}")

    html = extract_html(api_json)
    if not html.strip():
        raise RuntimeError("Cloudflare HTML API 成功但沒有取得 html 內容")
    return html


def fetch_html_direct(page_url):
    resp = requests.get(
        page_url,
        headers={
            **HEADERS,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.text


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_text(path, content):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def parse_json_from_response(text):
    if not text:
        return {}
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
    return {}


def normalize_name(name):
    return re.sub(r"\s+", " ", str(name or "").strip().lower())


def strip_html_for_llm(html):
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_wikia_image_urls(html, limit=1200):
    urls = re.findall(r"https://static\.wikia\.nocookie\.net/[^\s\"')]+", html)
    dedup = []
    seen = set()
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        dedup.append(u)
        if len(dedup) >= limit:
            break
    return dedup


def sanitize_perk_item(item):
    if not isinstance(item, dict):
        return None
    name = str(item.get("name", "")).strip()
    if not name:
        return None
    description = str(item.get("description", "")).strip()
    image_url = str(item.get("image_url", "")).strip()
    return {"name": name, "description": description, "image_url": image_url}


def sanitize_model_payload(payload, valid_hero_ids):
    out = {}
    heroes = payload.get("heroes", [])
    if not isinstance(heroes, list):
        return out
    for hero in heroes:
        if not isinstance(hero, dict):
            continue
        hero_id = str(hero.get("hero_id", "")).strip().lower()
        if hero_id not in valid_hero_ids:
            continue
        minor_raw = hero.get("minor_perks", [])
        major_raw = hero.get("major_perks", [])
        if not isinstance(minor_raw, list):
            minor_raw = []
        if not isinstance(major_raw, list):
            major_raw = []
        minor = [x for x in (sanitize_perk_item(p) for p in minor_raw) if x]
        major = [x for x in (sanitize_perk_item(p) for p in major_raw) if x]
        out[hero_id] = {"minor perks": minor, "major perks": major}
    return out


def call_gemini_extract_for_hero(markdown, html, hero_id, hero_en, expected_minor_names, expected_major_names, model):
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise RuntimeError("缺少 google-genai 套件。請先執行：pip install google-genai") from e

    api_key = get_env_or_fail("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    expected_minor_json = json.dumps(expected_minor_names, ensure_ascii=False)
    expected_major_json = json.dumps(expected_major_names, ensure_ascii=False)
    html_text = strip_html_for_llm(html)
    html_text = html_text[:160000]
    markdown = markdown[:160000]
    image_candidates = extract_wikia_image_urls(html)
    image_candidates_text = "\n".join(image_candidates[:800])
    prompt = (
        "你是資料抽取器。請從以下 Overwatch Fandom Perks 的 markdown 與 html 內容，抽取單一英雄的 perk 名稱、說明、圖片 URL。\n"
        "注意：來源文字可能包含大量導覽與廣告雜訊，只抽取真正屬於英雄 perks 的資料。\n"
        "圖片 URL 優先使用來源中符合 perk 的靜態圖片連結，不要填入無關 logo/廣告/社群圖。\n"
        "若無法確認就不要猜，請保留 name 但 description/image_url 可留空字串。\n"
        "name 請盡量使用 expected 名稱；若來源有新版名稱才改用新版。\n"
        "只回傳這位英雄，不要輸出其他英雄。\n"
        "回傳必須是 JSON，格式如下：\n"
        "{\n"
        f'  "hero_id": "{hero_id}",\n'
        '  "minor_perks": [{"name":"Groggy","description":"...","image_url":"https://..."}],\n'
        '  "major_perks": [{"name":"Headhunter","description":"...","image_url":"https://..."}]\n'
        "}\n\n"
        f"目標英雄：hero_id={hero_id}, 英文名={hero_en}\n"
        f"expected minor perk names: {expected_minor_json}\n"
        f"expected major perk names: {expected_major_json}\n\n"
        f"候選圖片 URL（從 html 擷取）:\n{image_candidates_text}\n\n"
        f"markdown 內容如下：\n{markdown}\n\n"
        f"html 文字化內容如下：\n{html_text}"
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )
    return parse_json_from_response(getattr(response, "text", ""))


def call_gemini_extract(markdown, html, heroes, model):
    out = {}
    for idx, hero in enumerate(heroes, start=1):
        hero_id = hero["hero_id"]
        hero_en = hero["en"]
        expected_minor = hero["expected_minor"]
        expected_major = hero["expected_major"]
        print(f"[Gemini {idx}/{len(heroes)}] 抽取 {hero_id} ...")
        payload = call_gemini_extract_for_hero(
            markdown=markdown,
            html=html,
            hero_id=hero_id,
            hero_en=hero_en,
            expected_minor_names=expected_minor,
            expected_major_names=expected_major,
            model=model,
        )
        if not isinstance(payload, dict):
            continue
        normalized = sanitize_model_payload({"heroes": [payload]}, {hero_id})
        if hero_id in normalized:
            out[hero_id] = normalized[hero_id]
    return out


def slugify_filename(text):
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "perk"


def merge_perks(existing_group, extracted_group):
    existing_group = existing_group if isinstance(existing_group, list) else []
    extracted_group = extracted_group if isinstance(extracted_group, list) else []
    extracted_by_name = {normalize_name(p.get("name", "")): p for p in extracted_group if p.get("name")}

    merged = []
    used = set()
    for item in existing_group:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        key = normalize_name(name)
        picked = extracted_by_name.get(key)
        merged_item = {"name": name}
        old_desc = str(item.get("description", "")).strip()
        old_img = str(item.get("image", "")).strip()
        if picked:
            if picked.get("description"):
                merged_item["description"] = picked["description"]
            elif old_desc:
                merged_item["description"] = old_desc
            if picked.get("image_url"):
                merged_item["_image_url"] = picked["image_url"]
            if old_img:
                merged_item["image"] = old_img
            used.add(key)
        else:
            if old_desc:
                merged_item["description"] = old_desc
            if old_img:
                merged_item["image"] = old_img
        merged.append(merged_item)

    for perk in extracted_group:
        key = normalize_name(perk.get("name", ""))
        if not key or key in used:
            continue
        item = {"name": perk["name"]}
        if perk.get("description"):
            item["description"] = perk["description"]
        if perk.get("image_url"):
            item["_image_url"] = perk["image_url"]
        merged.append(item)
    return merged


def merge_to_mapping(mapping, extracted_by_hero):
    heroes = mapping.get("heroes", [])
    changed_heroes = 0
    for hero in heroes:
        if not isinstance(hero, dict):
            continue
        hero_id = str(hero.get("id", "")).strip().lower()
        extracted = extracted_by_hero.get(hero_id)
        if not extracted:
            continue
        old_perks = hero.get("perks") if isinstance(hero.get("perks"), dict) else {}
        old_minor = old_perks.get("minor perks", [])
        old_major = old_perks.get("major perks", [])

        new_minor = merge_perks(old_minor, extracted.get("minor perks", []))
        new_major = merge_perks(old_major, extracted.get("major perks", []))
        hero["perks"] = {"minor perks": new_minor, "major perks": new_major}
        changed_heroes += 1
    return changed_heroes


def pick_ext_from_url(url):
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    return ext if ext in {".png", ".jpg", ".jpeg", ".webp", ".gif"} else ".png"


def download_perk_images(mapping, assets_dir, skip_existing=False):
    os.makedirs(assets_dir, exist_ok=True)
    manifest = []
    for hero in mapping.get("heroes", []):
        hero_id = str(hero.get("id", "")).strip().lower()
        if not hero_id:
            continue
        perks = hero.get("perks") or {}
        for group_key in ("minor perks", "major perks"):
            group = perks.get(group_key, [])
            group_slug = "minor" if group_key == "minor perks" else "major"
            if not isinstance(group, list):
                continue
            for perk in group:
                if not isinstance(perk, dict):
                    continue
                perk_name = str(perk.get("name", "")).strip()
                image_url = str(perk.get("_image_url", "") or perk.get("image_url", "")).strip()
                local_path = ""
                status = "missing"
                if image_url:
                    ext = pick_ext_from_url(image_url)
                    filename = f"{hero_id}_{group_slug}_{slugify_filename(perk_name)}{ext}"
                    abs_path = os.path.join(assets_dir, filename)
                    try:
                        if skip_existing and os.path.exists(abs_path):
                            status = "skipped"
                        else:
                            resp = requests.get(image_url, headers=HEADERS, timeout=30)
                            resp.raise_for_status()
                            with open(abs_path, "wb") as f:
                                f.write(resp.content)
                            status = "ok"
                        local_path = f"data/assets/perks/{filename}"
                        perk["image"] = local_path
                    except Exception as e:
                        status = f"failed: {e}"
                manifest.append(
                    {
                        "hero_id": hero_id,
                        "group": group_key,
                        "name": perk_name,
                        "image_url": image_url,
                        "local_path": local_path,
                        "status": status,
                    }
                )
    return manifest


def cleanup_perk_url_fields(mapping):
    for hero in mapping.get("heroes", []):
        if not isinstance(hero, dict):
            continue
        perks = hero.get("perks") or {}
        for group_key in ("minor perks", "major perks"):
            group = perks.get(group_key, [])
            if not isinstance(group, list):
                continue
            for perk in group:
                if not isinstance(perk, dict):
                    continue
                perk.pop("_image_url", None)
                perk.pop("image_url", None)


def main():
    args = parse_args()

    mapping = load_json(args.mapping_path)
    heroes = mapping.get("heroes", [])
    hero_meta = []
    valid_hero_ids = set()
    for hero in heroes:
        if not isinstance(hero, dict):
            continue
        hero_id = str(hero.get("id", "")).strip().lower()
        en_name = str(hero.get("en", "")).strip()
        if not hero_id:
            continue
        valid_hero_ids.add(hero_id)
        perks = hero.get("perks") if isinstance(hero.get("perks"), dict) else {}
        minor = perks.get("minor perks", []) if isinstance(perks.get("minor perks", []), list) else []
        major = perks.get("major perks", []) if isinstance(perks.get("major perks", []), list) else []
        expected_minor = [str(x.get("name", "")).strip() for x in minor if isinstance(x, dict) and str(x.get("name", "")).strip()]
        expected_major = [str(x.get("name", "")).strip() for x in major if isinstance(x, dict) and str(x.get("name", "")).strip()]
        hero_meta.append(
            {
                "hero_id": hero_id,
                "en": en_name,
                "expected_minor": expected_minor,
                "expected_major": expected_major,
            }
        )

    account_id = get_env_or_fail("CLOUDFLARE_ACCOUNT_ID")
    api_token = get_env_or_fail("CLOUDFLARE_API_TOKEN")

    print(f"開始抓取 Perks 頁面: {args.url}")
    markdown = fetch_markdown_with_cloudflare(account_id, api_token, args.url, args.cache_ttl)
    try:
        html = fetch_html_direct(args.url)
    except Exception as e:
        print(f"直接抓 html 失敗，改用 Cloudflare HTML API: {e}")
        html = fetch_html_with_cloudflare(account_id, api_token, args.url, args.cache_ttl)
    save_text(args.raw_markdown_output, markdown)
    save_text(args.raw_html_output, html)
    print(f"已輸出原始 markdown: {os.path.abspath(args.raw_markdown_output)}")
    print(f"已輸出原始 html: {os.path.abspath(args.raw_html_output)}")

    print(f"開始 Gemini 抽取（model={args.model}）...")
    raw_payload = call_gemini_extract(markdown=markdown, html=html, heroes=hero_meta, model=args.model)
    extracted_by_hero = raw_payload
    print(f"Gemini 抽取英雄數: {len(extracted_by_hero)}")

    changed_heroes = merge_to_mapping(mapping, extracted_by_hero)
    print(f"已更新 perks 英雄數: {changed_heroes}")

    manifest = []
    if not args.skip_image_download:
        print("開始下載 perks 圖片...")
        manifest = download_perk_images(mapping, args.assets_dir, skip_existing=args.skip_existing)
        ok_count = sum(1 for x in manifest if x["status"] == "ok")
        skip_count = sum(1 for x in manifest if x["status"] == "skipped")
        print(f"圖片下載完成: {ok_count} 成功, {skip_count} 略過, {len(manifest) - ok_count - skip_count} 其他")
    cleanup_perk_url_fields(mapping)

    if args.dry_run:
        print("dry-run 模式：不寫入 mapping 與 manifest。")
        return

    save_json(args.mapping_path, mapping)
    print(f"已寫回 mapping: {os.path.abspath(args.mapping_path)}")
    if not args.skip_image_download:
        save_json(args.manifest_path, manifest)
        print(f"已輸出 manifest: {os.path.abspath(args.manifest_path)}")


if __name__ == "__main__":
    main()
