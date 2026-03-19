import hashlib
import json
import os
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MASTER_PATH = os.path.join(DATA_DIR, "overwatch_master.json")
GUIDE_ASSETS_DIR = os.path.join(DATA_DIR, "assets", "guide")
GUIDE_MANIFEST_PATH = os.path.join(GUIDE_ASSETS_DIR, "manifest.json")
IMG_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\".*?\")?\)")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _extract_image_urls(master):
    urls = set()
    for hero in master.get("heroes", []):
        guide = hero.get("Guide") or hero.get("guide") or []
        for section in guide:
            for line in (section.get("content") or []):
                if not isinstance(line, str):
                    continue
                for match in IMG_PATTERN.findall(line):
                    if match.startswith("http://") or match.startswith("https://"):
                        urls.add(match)
    return sorted(urls)


def _filename_for_url(url):
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1].lower()
    if not ext or len(ext) > 6:
        ext = ".png"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return f"{digest}{ext}"


def download_assets(urls):
    os.makedirs(GUIDE_ASSETS_DIR, exist_ok=True)
    manifest = []
    for url in urls:
        filename = _filename_for_url(url)
        local_path = os.path.join(GUIDE_ASSETS_DIR, filename)
        local_rel = f"data/assets/guide/{filename}"
        status = "ok"
        if not os.path.exists(local_path):
            try:
                req = Request(url, headers=HEADERS)
                with urlopen(req, timeout=30) as resp:
                    data = resp.read()
                with open(local_path, "wb") as f:
                    f.write(data)
            except Exception as e:
                print(f"下載失敗: {url} ({e})")
                status = "failed"
                local_rel = ""
        manifest.append(
            {
                "image_url": url,
                "local_path": local_rel,
                "status": status,
            }
        )
    return manifest


def main():
    master = load_json(MASTER_PATH)
    urls = _extract_image_urls(master)
    if not urls:
        print("未找到 guide markdown 圖片 URL")
        save_json(GUIDE_MANIFEST_PATH, [])
        return

    print(f"找到 {len(urls)} 個 guide 圖片 URL，開始下載...")
    manifest = download_assets(urls)
    save_json(GUIDE_MANIFEST_PATH, manifest)
    ok_count = sum(1 for m in manifest if m["status"] == "ok")
    fail_count = sum(1 for m in manifest if m["status"] != "ok")
    print(f"✅ guide 圖片下載完成: {ok_count} 成功, {fail_count} 失敗")
    print(f"✅ manifest: {GUIDE_MANIFEST_PATH}")


if __name__ == "__main__":
    main()
