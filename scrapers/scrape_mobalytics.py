import json
import asyncio
from playwright.async_api import async_playwright
import os
import re
import unicodedata


def _normalize_slug(text):
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = ascii_text.lower().replace(".", "").replace(":", "").replace(" ", "-")
    cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned


def _absolute_mobalytics_url(href):
    if not href:
        return ""
    return "https://mobalytics.gg" + href if href.startswith("/") else href


def _normalize_lookup_key(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower().strip()
    lowered = re.sub(r"[\s\.\-_:]+", "", lowered)
    return lowered


def _load_mapping_perks():
    mapping_file = os.path.join(os.path.dirname(__file__), "..", "data", "overwatch_mapping.json")
    try:
        with open(mapping_file, "r", encoding="utf-8") as f:
            mapping_data = json.load(f)
    except Exception as e:
        print(f"[警告] 無法載入 mapping perks: {e}")
        return {}

    perk_lookup = {}
    for hero in mapping_data.get("heroes", []):
        perks = hero.get("perks")
        if not isinstance(perks, dict):
            continue
        key = _normalize_lookup_key(hero.get("en", ""))
        if not key:
            continue
        minor = [p.get("name", "") for p in perks.get("minor perks", []) if isinstance(p, dict)]
        major = [p.get("name", "") for p in perks.get("major perks", []) if isinstance(p, dict)]
        if len(minor) >= 2 and len(major) >= 2:
            perk_lookup[key] = {
                "minor": [minor[0], minor[1]],
                "major": [major[0], major[1]],
            }
    return perk_lookup


PERK_IDS = ["5", "5.1", "5.1.1", "5.1.2", "5.2", "5.2.1", "5.2.2"]
PERK_DEFAULT_TITLES = {
    "5": "Perks",
    "5.1": "Minor Perks",
    "5.2": "Major Perks",
}


def _to_content_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _merge_section(dst, src):
    src_title = str(src.get("title", "") or "").strip()
    if not dst["title"] and src_title:
        dst["title"] = src_title
    for line in _to_content_list(src.get("content")):
        if line not in dst["content"]:
            dst["content"].append(line)


def _looks_like_perk_title(text):
    value = str(text or "").strip()
    if not value or len(value) > 60:
        return False
    if any(ch in value for ch in [".", "!", "?", ":", ";"]):
        return False
    return bool(re.search(r"[A-Za-z]", value))


def _repair_perk_branch(perk_sections, parent_id, first_id, second_id):
    parent = perk_sections[parent_id]
    first = perk_sections[first_id]
    second = perk_sections[second_id]

    parent_content = _to_content_list(parent.get("content"))
    first_content = _to_content_list(first.get("content"))
    second_content = _to_content_list(second.get("content"))

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
    first_content = _to_content_list(first.get("content"))
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

    # 從父節點內容拆分兩個 Perk（常見格式: title1, desc..., title2, desc...）
    parent_content = _to_content_list(parent.get("content"))
    if parent_content and (not first.get("title") or not second.get("title")):
        title_positions = []
        first_title_lower = str(first.get("title", "")).strip().lower()
        second_title_lower = str(second.get("title", "")).strip().lower()
        for idx, line in enumerate(parent_content):
            if not _looks_like_perk_title(line):
                continue
            lower = line.strip().lower()
            if lower in {first_title_lower, second_title_lower} and (first_title_lower or second_title_lower):
                continue
            title_positions.append((idx, line.strip()))

        # 補 title
        if not first.get("title") and title_positions:
            first["title"] = title_positions[0][1]
        if not second.get("title"):
            for _, title in title_positions:
                if title.lower() != str(first.get("title", "")).strip().lower():
                    second["title"] = title
                    break

        # 依 title 出現位置拆 content
        if first.get("title"):
            indices = []
            for idx, line in enumerate(parent_content):
                lower = line.strip().lower()
                if lower == str(first.get("title", "")).strip().lower():
                    indices.append(("first", idx))
                elif second.get("title") and lower == str(second.get("title", "")).strip().lower():
                    indices.append(("second", idx))
            indices.sort(key=lambda x: x[1])

            if indices:
                first_idx = next((i for tag, i in indices if tag == "first"), None)
                second_idx = next((i for tag, i in indices if tag == "second"), None)
                if first_idx is not None:
                    if second_idx is not None and second_idx > first_idx:
                        first_chunk = parent_content[first_idx + 1:second_idx]
                        second_chunk = parent_content[second_idx + 1:]
                    else:
                        first_chunk = parent_content[first_idx + 1:]
                        second_chunk = []

                    if first_chunk and not _to_content_list(first.get("content")):
                        first["content"] = first_chunk
                    if second_chunk and not _to_content_list(second.get("content")):
                        second["content"] = second_chunk


def _normalize_guide_perks(guide):
    if not isinstance(guide, list):
        return []

    perk_sections = {pid: {"id": pid, "title": PERK_DEFAULT_TITLES.get(pid, ""), "content": []} for pid in PERK_IDS}
    non_perk_sections = []
    first_perk_index = None

    def _map_perk_id(sid):
        parts = sid.split(".")
        if not parts or parts[0] != "5":
            return None
        if len(parts) == 1:
            return "5"
        if len(parts) == 2:
            return "5.1" if parts[1] == "1" else "5.2"
        branch = parts[1]
        leaf = parts[2]
        if branch == "1":
            return "5.1.1" if leaf == "1" else "5.1.2"
        return "5.2.1" if leaf == "1" else "5.2.2"

    for section in guide:
        if not isinstance(section, dict):
            continue
        sid = str(section.get("id", "")).strip()
        if sid.startswith("5"):
            if first_perk_index is None:
                first_perk_index = len(non_perk_sections)
            mapped_id = _map_perk_id(sid)
            if mapped_id in perk_sections:
                _merge_section(perk_sections[mapped_id], section)
        else:
            non_perk_sections.append(section)

    _repair_perk_branch(perk_sections, "5.1", "5.1.1", "5.1.2")
    _repair_perk_branch(perk_sections, "5.2", "5.2.1", "5.2.2")

    # 某些頁面會把 5.1.2 誤編到 5.2（例如 Roadhog 的 Shrapnel Launcher）
    minor_second = perk_sections["5.1.2"]
    major_parent = perk_sections["5.2"]
    if not str(minor_second.get("title", "")).strip():
        major_content = _to_content_list(major_parent.get("content"))
        if major_content and str(perk_sections["5.2.1"].get("title", "")).strip():
            if _looks_like_perk_title(major_content[0]):
                minor_second["title"] = major_content[0].strip()
                minor_second["content"] = major_content[1:]
                major_parent["content"] = []

    fixed_perks = []
    for pid in PERK_IDS:
        section = perk_sections[pid]
        if not section["title"]:
            section["title"] = PERK_DEFAULT_TITLES.get(pid, "")
        if not section["content"]:
            section.pop("content", None)
        fixed_perks.append(section)

    if first_perk_index is None:
        return non_perk_sections + fixed_perks
    return non_perk_sections[:first_perk_index] + fixed_perks + non_perk_sections[first_perk_index:]


def _extract_perk_contents_from_parent(parent_content, expected_names):
    lines = _to_content_list(parent_content)
    names = [str(n or "").strip() for n in expected_names]
    result = {names[0]: [], names[1]: []}
    if len(names) < 2 or not lines:
        return result

    norm_lines = [_normalize_lookup_key(x) for x in lines]
    idx1 = next((i for i, value in enumerate(norm_lines) if value == _normalize_lookup_key(names[0])), None)
    idx2 = next((i for i, value in enumerate(norm_lines) if value == _normalize_lookup_key(names[1])), None)

    if idx1 is not None and idx2 is not None:
        if idx1 < idx2:
            result[names[0]] = [x for x in lines[idx1 + 1:idx2] if x.strip()]
            result[names[1]] = [x for x in lines[idx2 + 1:] if x.strip()]
        else:
            result[names[1]] = [x for x in lines[idx2 + 1:idx1] if x.strip()]
            result[names[0]] = [x for x in lines[idx1 + 1:] if x.strip()]
    elif idx1 is not None:
        result[names[0]] = [x for x in lines[idx1 + 1:] if x.strip()]
    elif idx2 is not None:
        result[names[1]] = [x for x in lines[idx2 + 1:] if x.strip()]
    return result


def _apply_mapping_perks(hero_name, guide, perk_lookup):
    hero_key = _normalize_lookup_key(hero_name)
    expected = perk_lookup.get(hero_key)
    if not expected or not isinstance(guide, list):
        return guide

    by_id = {str(section.get("id", "")): section for section in guide if isinstance(section, dict)}
    required = ["5.1.1", "5.1.2", "5.2.1", "5.2.2"]
    for sid in required:
        if sid not in by_id:
            new_section = {"id": sid, "title": "", "content": []}
            guide.append(new_section)
            by_id[sid] = new_section

    minor_names = expected["minor"]
    major_names = expected["major"]
    by_id["5.1.1"]["title"] = minor_names[0]
    by_id["5.1.2"]["title"] = minor_names[1]
    by_id["5.2.1"]["title"] = major_names[0]
    by_id["5.2.2"]["title"] = major_names[1]

    minor_parent = by_id.get("5.1", {})
    major_parent = by_id.get("5.2", {})
    minor_from_parent = _extract_perk_contents_from_parent(minor_parent.get("content"), minor_names)
    major_from_parent = _extract_perk_contents_from_parent(major_parent.get("content"), major_names)

    # 支援錯位：minor 第二個名稱偶爾出現在 major parent
    minor_from_major_parent = _extract_perk_contents_from_parent(major_parent.get("content"), minor_names)

    branch_targets = [
        ("5.1.1", minor_names[0], minor_from_parent.get(minor_names[0], [])),
        ("5.1.2", minor_names[1], minor_from_parent.get(minor_names[1], []) or minor_from_major_parent.get(minor_names[1], [])),
        ("5.2.1", major_names[0], major_from_parent.get(major_names[0], [])),
        ("5.2.2", major_names[1], major_from_parent.get(major_names[1], [])),
    ]

    for sid, title, fallback_content in branch_targets:
        section = by_id[sid]
        section["title"] = title
        content = _to_content_list(section.get("content"))
        if not content and fallback_content:
            section["content"] = fallback_content
        elif content:
            section["content"] = content
        else:
            section["content"] = []

    # 父層僅保留分類標題，避免與 5.x.x 內容重複
    for parent_id in ["5.1", "5.2"]:
        if parent_id in by_id and isinstance(by_id[parent_id], dict):
            by_id[parent_id].pop("content", None)
    return guide

async def scrape_mobalytics(worker_count=8):
    os.makedirs('dataset', exist_ok=True)
    
    all_data = {
        "heroes": [],
        "meta_commentary": []
    }
    
    hero_map = {} 

    perk_lookup = _load_mapping_perks()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. Scrape the standard tier list page
        print("Navigating to Mobalytics Standard Tier List...")
        try:
            await page.goto("https://mobalytics.gg/overwatch/tier-lists/standard", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5) 
        except Exception as e:
            print(f"Error loading tier list page: {e}")
            
        print("Extracting tier list and commentary data...")
        tier_data = await page.evaluate('''() => {
            const TARGET_CLASS = 'x1exxlbk';
            const tierDivs = Array.from(document.querySelectorAll('div')).filter(d => 
                ['S','A','B','C','D'].includes(d.innerText.trim()) && d.classList.contains(TARGET_CLASS)
            );
            
            let result = {};
            tierDivs.forEach(div => {
                let tier = div.innerText.trim();
                let container = div;
                while(container && container.parentElement && container.tagName !== 'MAIN') {
                    const potentialHeroes = container.innerText.trim().split('\\n').filter(t => t.length > 2 && !['S','A','B','C','D'].includes(t));
                    if (potentialHeroes.length > 3) {
                        potentialHeroes.forEach(h => {
                            if (h !== tier) result[h] = tier;
                        });
                        break;
                    }
                    container = container.parentElement;
                }
            });
            return result;
        }''')
        
        print(f"✅ Tiers detected for {len(tier_data)} heroes.")

        meta_commentary = await page.evaluate('''() => {
            let sections = [];
            const headings = document.querySelectorAll('h2, h3');
            let currentMeta = null;
            
            for (let h of headings) {
                let text = h.innerText.trim();
                if (text.endsWith(' Commentary') || text === 'Tiers Explained' || text === 'Overview') {
                    if (currentMeta) sections.push(currentMeta);
                    currentMeta = { category: text, heroes: [] };
                } else if (currentMeta && h.tagName === 'H3') {
                    let heroName = text.split('\\n')[0];
                    let paragraphs = [];
                    let next = h.nextElementSibling;
                    while(next && next.tagName === 'P') {
                        paragraphs.push(next.innerText.trim());
                        next = next.nextElementSibling;
                    }
                    if (paragraphs.length > 0) currentMeta.heroes.push({ name: heroName, text: paragraphs });
                } else if (currentMeta && h.tagName === 'H2' && !text.endsWith(' Commentary')) {
                    sections.push(currentMeta);
                    currentMeta = null;
                }
            }
            if (currentMeta) sections.push(currentMeta);
            return sections;
        }''')
        all_data["meta_commentary"] = meta_commentary

        for hero_name, tier in tier_data.items():
            hero_map[hero_name] = {
                "Hero": hero_name,
                "Tier": tier,
                "Guide": []
            }

        # 2. Scrape guide pages
        print("Finding hero guide links...")
        try:
            await page.goto("https://mobalytics.gg/overwatch/heroes", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)
        except Exception: pass
            
        hero_links = await page.evaluate('''() => {
            const links = document.querySelectorAll('a[href*="/heroes/"]');
            let result = {};
            for (let link of links) {
                let name = link.innerText.trim().split('\\n')[0]; 
                let href = link.getAttribute('href');
                if (name && (href.includes('-guide') || href.includes('/heroes/'))) {
                    result[name] = href;
                }
            }
            return result;
        }''')
        
        heroes_to_scrape = list(hero_map.keys())
        if not heroes_to_scrape:
            heroes_to_scrape = list(hero_links.keys())

        for hero in heroes_to_scrape:
            if hero not in hero_map:
                hero_map[hero] = {"Hero": hero, "Tier": "Unknown", "Guide": []}

        worker_count = max(1, int(worker_count))
        print(f"使用 {worker_count} 個 worker 並行抓取英雄指南...")

        async def scrape_single_hero(hero):
            hero_slug = _normalize_slug(hero)
            candidate_urls = []
            if hero in hero_links:
                candidate_urls.append(_absolute_mobalytics_url(hero_links[hero]))
            candidate_urls.append(f"https://mobalytics.gg/overwatch/heroes/{hero_slug}-guide")
            candidate_urls.append(f"https://mobalytics.gg/overwatch/{hero_slug}-guide")
            candidate_urls = list(dict.fromkeys([u for u in candidate_urls if u]))

            print(f"Scraping DEDUPLICATED guide for: {hero}")
            full_guide = []
            worker_page = await browser.new_page()

            try:
                for url in candidate_urls:
                    try:
                        response = await worker_page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(1.5)

                        status = response.status if response else None
                        is_not_found = await worker_page.evaluate('''() => {
                            const text = (document.body?.innerText || "").toLowerCase();
                            const title = (document.title || "").toLowerCase();
                            return text.includes("the page you are looking for is not found")
                                || title.includes("not found");
                        }''')
                        if (status is not None and status >= 400) or is_not_found:
                            print(f"  [跳過] 連結無效 ({status if status is not None else 'N/A'}): {url}")
                            continue

                        full_guide = await worker_page.evaluate('''(heroName) => {
                        const main = document.querySelector('main');
                        if (!main) return [];
                        
                        const elements = Array.from(main.querySelectorAll(
                            'h2, h3, h4, p, li, [id^="node-portal-"], span[data-testid="static-data-widget"] span.xirccme.xggjnk3'
                        ));
                        let flattened = [];
                        let counters = [0, 0, 0]; 
                        
                        // Track seen content to avoid repeats across the guide
                        let globalSeen = new Set();
                        
                        for (let el of elements) {
                            let text = el.innerText.trim();
                            if (!text || ['Privacy Policy', 'Terms of Service', 'Table of Contents'].includes(text)) continue;
                            
                            // Noise filter for specific unwanted strings
                            if (text.startsWith("In this Overwatch") && text.includes("guide")) continue;

                            const tag = el.tagName;
                            if (tag.startsWith('H')) {
                                const level = parseInt(tag.substring(1));
                                const adjustedLevel = level - 1; // H2 -> 1, H3 -> 2, H4 -> 3
                                if (adjustedLevel < 1 || adjustedLevel > 3) continue;

                                counters[adjustedLevel-1]++;
                                for (let i = adjustedLevel; i < 3; i++) counters[i] = 0;
                                
                                const id = counters.slice(0, adjustedLevel).join('.');
                                
                                let cleanTitle = text.replace(heroName + ' ', '').replace(heroName, '').trim();
                                if (!cleanTitle) cleanTitle = text; 
                                
                                flattened.push({
                                    id: id,
                                    title: cleanTitle,
                                    content: []
                                });
                            } else {
                                if (flattened.length === 0) continue; 
                                
                                const lastSection = flattened[flattened.length - 1];
                                
                                // SMART DEDUPLICATION:
                                // 1. Skip if exactly same as any previously seen text
                                if (globalSeen.has(text)) continue;
                                
                                // 2. Skip if it's a substring of the previously added line in THIS section
                                if (lastSection.content.length > 0) {
                                    let prev = lastSection.content[lastSection.content.length - 1];
                                    if (prev.includes(text) || text.includes(prev)) {
                                       // If new text is longer, replace the previous one
                                       if (text.length > prev.length) {
                                           lastSection.content[lastSection.content.length - 1] = text;
                                           globalSeen.add(text);
                                       }
                                       continue;
                                    }
                                }
                                
                                lastSection.content.push(text);
                                globalSeen.add(text);
                            }
                        }
                        
                        return flattened.map(section => {
                            if (section.content && section.content.length === 0) {
                                delete section.content;
                            }
                            return section;
                        }).filter(section => section.title || (section.content && section.content.length > 0));
                    }''', hero)
                        full_guide = _normalize_guide_perks(full_guide)
                        full_guide = _apply_mapping_perks(hero, full_guide, perk_lookup)
                        print(f"  [成功] 使用指南連結: {url}")
                        break
                    except Exception as e:
                        print(f"  [錯誤] 嘗試 {url} 失敗: {e}")
                        continue
            finally:
                await worker_page.close()

            if not full_guide:
                print(f"  [提示] {hero} 找不到有效指南頁，Guide 設為空陣列。")
            return {"Hero": hero, "Tier": hero_map[hero]["Tier"], "Guide": full_guide}

        semaphore = asyncio.Semaphore(worker_count)

        async def scrape_with_limit(hero):
            async with semaphore:
                return await scrape_single_hero(hero)

        tasks = [asyncio.create_task(scrape_with_limit(hero)) for hero in heroes_to_scrape]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for hero, result in zip(heroes_to_scrape, results):
            if isinstance(result, Exception):
                print(f"  [錯誤] {hero} worker 執行失敗: {result}")
                continue
            hero_map[hero] = result
                
        await browser.close()
        
        all_data["heroes"] = list(hero_map.values())
        
        if all_data["heroes"]:
            out_file = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "mobalytics_heroes.json")
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            print(f"\n✅ Successfully saved cleaned, deduplicated, and substring-filtered guide to {out_file}")
            return all_data
        else:
            print("No data collected!")
            return None

if __name__ == "__main__":
    asyncio.run(scrape_mobalytics())
