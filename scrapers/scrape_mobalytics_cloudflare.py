import asyncio
import json
import os
import re
import unicodedata
from urllib import error, request


TIER_LIST_URL = "https://mobalytics.gg/overwatch/tier-lists/standard"
CF_MARKDOWN_ENDPOINT = "https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/markdown"
MAX_RETRY_404_422 = 3
RETRY_DELAY_SECONDS = 2
NOISE_LINE_PREFIXES = (
    "[![Mobalytics]",
    "[![League of Legends]",
    "[![Teamfight Tactics]",
    "[![Diablo 4]",
    "[![Path of Exile",
    "[![Destiny 2]",
    "[![Marathon]",
    "[![Slay the Spire 2]",
    "[![Deadlock]",
    "[![Overwatch]",
    "[![Borderlands 4]",
    "[![Valorant]",
    "[![Arknights: Endfield]",
    "[![Elden Ring Nightreign]",
    "[![Monster Hunter Wilds]",
    "[![The Bazaar]",
    "[![Hades 2]",
    "[![Marvel Rivals]",
    "[![Zenless Zone Zero]",
    "[![2XKO]",
    "[![Riftbound]",
    "[DOWNLOAD APP]",
    "[News]",
    "sign in",
    "![support]",
    "[Provide feedback]",
    "[![menu]",
    "[![Home]",
    "[![Profile]",
    "[![Heroes]",
    "[![Tier Lists]",
    "[![Stadium Builds]",
    "[![Guides]",
    "![Mobalytics]",
)


def _normalize_lookup_key(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower().strip()
    lowered = re.sub(r"[\s\.\-_:]+", "", lowered)
    return lowered


def _normalize_slug(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = ascii_text.lower().replace(".", "").replace(":", "").replace(" ", "-")
    cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned


def _unescape_markdown(text):
    return re.sub(r"\\([\\`*_{}\[\]()#+\-.!>~|])", r"\1", text)


def _is_not_found_markdown(markdown_text):
    text = str(markdown_text or "").lower()
    markers = [
        "# 404",
        "## the page you are looking for is not found",
        "the page you are looking for is not found",
    ]
    return any(marker in text for marker in markers)


def _merge_section(target, source):
    source_title = str(source.get("title", "") or "").strip()
    if source_title and not target["title"]:
        target["title"] = source_title
    for line in source.get("content", []) or []:
        if line not in target["content"]:
            target["content"].append(line)


def _load_mapping():
    mapping_path = os.path.join(os.path.dirname(__file__), "..", "data", "overwatch_mapping.json")
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    hero_lookup = {}
    slug_lookup = {}
    valid_ids = set()
    id_to_en = {}
    perk_lookup = {}
    for hero in mapping.get("heroes", []):
        hero_id = str(hero.get("id", "")).strip()
        en_name = str(hero.get("en", "")).strip()
        if not hero_id:
            continue
        valid_ids.add(hero_id)
        id_to_en[hero_id] = en_name or hero_id
        hero_lookup[_normalize_lookup_key(hero_id)] = hero_id
        hero_lookup[_normalize_lookup_key(en_name)] = hero_id
        slug_lookup[_normalize_slug(hero_id)] = hero_id
        slug_lookup[_normalize_slug(en_name)] = hero_id

        perks = hero.get("perks")
        if isinstance(perks, dict):
            minor = [p.get("name", "") for p in perks.get("minor perks", []) if isinstance(p, dict)]
            major = [p.get("name", "") for p in perks.get("major perks", []) if isinstance(p, dict)]
            if len(minor) >= 2 and len(major) >= 2:
                perk_lookup[hero_id] = {
                    "minor": [minor[0], minor[1]],
                    "major": [major[0], major[1]],
                }
    return hero_lookup, slug_lookup, id_to_en, perk_lookup, valid_ids


def _extract_link_titles(line):
    return [match.strip() for match in re.findall(r"\)([^\]\(]+)\]\(", line)]


def _extract_hero_ids_from_tier_line(line, hero_lookup, slug_lookup):
    urls = re.findall(r"\]\((https?://[^)]+)\)", line)
    result = []
    for url in urls:
        match = re.search(r"/overwatch/(?:heroes/)?([a-z0-9-]+)-guide", url)
        if not match:
            continue
        slug = match.group(1).strip().lower()
        hero_id = slug_lookup.get(slug) or hero_lookup.get(_normalize_lookup_key(slug))
        if hero_id:
            result.append(hero_id)
    return result


def parse_tier_map(markdown_text, hero_lookup, slug_lookup):
    lines = markdown_text.splitlines()
    tier_map = {}
    current_tier = None

    for raw_line in lines:
        line = raw_line.strip()
        heading_match = re.match(r"^##\s+([SABCD])\s*(?:\(|$)", line, re.IGNORECASE)
        if heading_match:
            current_tier = heading_match.group(1).upper()
            continue
        if line.startswith("## "):
            current_tier = None
            continue
        if not current_tier:
            continue

        for hero_id in _extract_hero_ids_from_tier_line(line, hero_lookup, slug_lookup):
            tier_map[hero_id] = current_tier
    return tier_map


def parse_meta_commentary_full(markdown_text, hero_lookup, slug_lookup):
    lines = markdown_text.splitlines()
    sections = []
    current_section = None
    current_hero = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("## "):
            heading = line[3:].strip()
            if heading.endswith("Commentary"):
                if current_section is not None:
                    sections.append(current_section)
                current_section = {"category": heading, "heros": []}
                current_hero = None
            else:
                if current_section is not None:
                    sections.append(current_section)
                current_section = None
                current_hero = None
            continue

        if current_section is None:
            continue

        if line.startswith("### "):
            hero_name = line[4:].strip()
            hero_id = hero_lookup.get(_normalize_lookup_key(hero_name))
            if not hero_id:
                hero_id = slug_lookup.get(_normalize_slug(hero_name), _normalize_slug(hero_name))
            current_hero = {"names": hero_id, "text": []}
            current_section["heros"].append(current_hero)
            continue

        if current_hero is not None and not line.startswith("#"):
            current_hero["text"].append(_unescape_markdown(line))

    if current_section is not None:
        sections.append(current_section)
    return sections


def parse_meta_commentary_compat(markdown_text, hero_lookup):
    lines = markdown_text.splitlines()
    category = None
    current = None
    tank_heroes = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading == "Tank Commentary":
                category = "Tank Commentary"
                current = None
            elif heading == "DPS Commentary":
                break
            elif heading in ("Support Commentary", "Tiers Explained", "Table of Contents"):
                break
            else:
                category = None
            continue
        if category != "Tank Commentary":
            continue

        if line.startswith("### "):
            if len(tank_heroes) >= 2:
                break
            hero_name = line[4:].strip()
            hero_id = hero_lookup.get(_normalize_lookup_key(hero_name), _normalize_slug(hero_name))
            current = {"names": hero_id, "text": []}
            tank_heroes.append(current)
            continue

        if current is not None and not line.startswith("#"):
            current["text"].append(_unescape_markdown(line))

    return [
        {"category": "Tank Commentary", "heros": tank_heroes},
        {"category": "DPS Commentary", "heros": []},
    ]


def _normalize_perk_sections(sections, hero_id, perk_lookup):
    mapped_perks = perk_lookup.get(hero_id)

    perk_targets = {
        "5": {"id": "5", "title": "Perks", "content": []},
        "5.1": {"id": "5.1", "title": "Minor Perks", "content": []},
        "5.1.1": {"id": "5.1.1", "title": "", "content": []},
        "5.1.2": {"id": "5.1.2", "title": "", "content": []},
        "5.2": {"id": "5.2", "title": "Major Perks", "content": []},
        "5.2.1": {"id": "5.2.1", "title": "", "content": []},
        "5.2.2": {"id": "5.2.2", "title": "", "content": []},
    }

    def map_perk_id(section):
        sid = str(section.get("id", "")).strip()
        title = str(section.get("title", "")).strip().lower()
        normalized_title = _normalize_lookup_key(title)
        minor_names = mapped_perks["minor"] if mapped_perks else ["", ""]
        major_names = mapped_perks["major"] if mapped_perks else ["", ""]
        if sid == "5":
            return "5"
        if sid == "5.1":
            if "minor" not in title and mapped_perks:
                if normalized_title == _normalize_lookup_key(minor_names[0]):
                    return "5.1.1"
                if normalized_title == _normalize_lookup_key(minor_names[1]):
                    return "5.1.2"
                return "5.1.1"
            return "5.1"
        if sid == "5.1.1":
            return "5.1.1"
        if sid == "5.1.2":
            return "5.1.2"
        if sid == "5.2":
            if "major" in title:
                return "5.2"
            if mapped_perks:
                if normalized_title == _normalize_lookup_key(major_names[0]):
                    return "5.2.1"
                if normalized_title == _normalize_lookup_key(major_names[1]):
                    return "5.2.2"
                if normalized_title == _normalize_lookup_key(minor_names[1]):
                    return "5.1.2"
            return "5.2.1"
        if sid == "5.2.1":
            return "5.2.1"
        if sid == "5.2.2":
            return "5.2.2"
        if sid == "5.3":
            return "5.2"
        if sid == "5.3.1":
            return "5.2.1"
        if sid == "5.3.2":
            return "5.2.2"
        return None

    for section in sections:
        target_id = map_perk_id(section)
        if target_id and target_id in perk_targets:
            _merge_section(perk_targets[target_id], section)

    raw_titles = {
        sid: str(perk_targets[sid].get("title", "") or "").strip()
        for sid in ["5.1.1", "5.1.2", "5.2.1", "5.2.2"]
    }
    raw_contents = {
        sid: list(perk_targets[sid].get("content", []) or [])
        for sid in ["5.1.1", "5.1.2", "5.2.1", "5.2.2"]
    }
    raw_parent_contents = {
        "5.1": list(perk_targets["5.1"].get("content", []) or []),
        "5.2": list(perk_targets["5.2"].get("content", []) or []),
    }

    def split_parent_by_titles(lines, first_name, second_name):
        first = []
        second = []
        bucket = None
        first_norm = _normalize_lookup_key(first_name)
        second_norm = _normalize_lookup_key(second_name)
        for line in lines:
            normalized_line = _normalize_lookup_key(str(line).replace("*", " ").replace("_", " "))
            if normalized_line == first_norm:
                bucket = "first"
                continue
            if normalized_line == second_norm:
                bucket = "second"
                continue
            if bucket == "first":
                first.append(line)
            elif bucket == "second":
                second.append(line)
        return first, second

    def split_first_content_by_second_title(first_section, second_section, second_name):
        first_content = list(first_section.get("content", []) or [])
        if not first_content or second_section.get("content"):
            return
        marker_idx = None
        second_norm = _normalize_lookup_key(second_name)
        for idx, line in enumerate(first_content):
            normalized = _normalize_lookup_key(str(line).replace("*", " ").replace("_", " "))
            if normalized == second_norm:
                marker_idx = idx
                break
        if marker_idx is not None:
            second_section["content"] = first_content[marker_idx + 1:]
            first_section["content"] = first_content[:marker_idx]

    if mapped_perks:
        perk_targets["5.1.1"]["title"] = mapped_perks["minor"][0]
        perk_targets["5.1.2"]["title"] = mapped_perks["minor"][1]
        perk_targets["5.2.1"]["title"] = mapped_perks["major"][0]
        perk_targets["5.2.2"]["title"] = mapped_perks["major"][1]

        minor_first_name = mapped_perks["minor"][0]
        minor_second_name = mapped_perks["minor"][1]
        minor_first = perk_targets["5.1.1"]
        minor_second = perk_targets["5.1.2"]
        major_first_name = mapped_perks["major"][0]
        major_second_name = mapped_perks["major"][1]
        major_first = perk_targets["5.2.1"]
        major_second = perk_targets["5.2.2"]

        # 先用原始 section title 對齊 mapping（可處理順序顛倒）
        for branch, first_name, second_name, first_id, second_id in [
            ("5.1", minor_first_name, minor_second_name, "5.1.1", "5.1.2"),
            ("5.2", major_first_name, major_second_name, "5.2.1", "5.2.2"),
        ]:
            first_bucket = []
            second_bucket = []
            for sid in [first_id, second_id]:
                raw_title_norm = _normalize_lookup_key(raw_titles.get(sid, ""))
                if raw_title_norm == _normalize_lookup_key(first_name):
                    first_bucket.extend(raw_contents.get(sid, []))
                elif raw_title_norm == _normalize_lookup_key(second_name):
                    second_bucket.extend(raw_contents.get(sid, []))
                else:
                    if sid == first_id:
                        first_bucket.extend(raw_contents.get(sid, []))
                    else:
                        second_bucket.extend(raw_contents.get(sid, []))

            parent_first, parent_second = split_parent_by_titles(
                raw_parent_contents.get(branch, []), first_name, second_name
            )
            if parent_first:
                first_bucket.extend(parent_first)
            if parent_second:
                second_bucket.extend(parent_second)

            perk_targets[first_id]["content"] = first_bucket
            perk_targets[second_id]["content"] = second_bucket

        split_first_content_by_second_title(minor_first, minor_second, minor_second_name)
        split_first_content_by_second_title(major_first, major_second, major_second_name)

        # 從所有 raw 區塊依標題比對回填（可處理分支錯置與順序顛倒）
        raw_blocks = []
        for sid in ["5.1.1", "5.1.2", "5.2.1", "5.2.2"]:
            raw_title = raw_titles.get(sid, "")
            raw_content = list(raw_contents.get(sid, []))
            if raw_title and raw_content:
                raw_blocks.append((raw_title, raw_content))

        def refill_by_title(target_key, expected_name):
            target = perk_targets[target_key]
            if target.get("content"):
                return
            expected_norm = _normalize_lookup_key(expected_name)
            for raw_title, raw_content in raw_blocks:
                raw_norm = _normalize_lookup_key(str(raw_title).replace("*", " ").replace("_", " "))
                if raw_norm == expected_norm and raw_content:
                    target["content"] = list(raw_content)
                    return

        refill_by_title("5.1.1", minor_first_name)
        refill_by_title("5.1.2", minor_second_name)
        refill_by_title("5.2.1", major_first_name)
        refill_by_title("5.2.2", major_second_name)

        # 若 minor 第二個 Perk 仍無內容，嘗試從 5.1 父節點拆分
        if not minor_second.get("content") and perk_targets["5.1"].get("content"):
            parent_content = list(perk_targets["5.1"].get("content", []))
            idx1 = None
            idx2 = None
            for idx, line in enumerate(parent_content):
                normalized = _normalize_lookup_key(line)
                if idx1 is None and normalized == _normalize_lookup_key(minor_first_name):
                    idx1 = idx
                if idx2 is None and normalized == _normalize_lookup_key(minor_second_name):
                    idx2 = idx
            if idx1 is not None and idx2 is not None and idx2 > idx1:
                if not minor_first.get("content"):
                    minor_first["content"] = parent_content[idx1 + 1:idx2]
                minor_second["content"] = parent_content[idx2 + 1:]

        if not major_second.get("content") and perk_targets["5.2"].get("content"):
            parent_content = list(perk_targets["5.2"].get("content", []))
            idx1 = None
            idx2 = None
            for idx, line in enumerate(parent_content):
                normalized = _normalize_lookup_key(line)
                if idx1 is None and normalized == _normalize_lookup_key(major_first_name):
                    idx1 = idx
                if idx2 is None and normalized == _normalize_lookup_key(major_second_name):
                    idx2 = idx
            if idx1 is not None and idx2 is not None and idx2 > idx1:
                if not major_first.get("content"):
                    major_first["content"] = parent_content[idx1 + 1:idx2]
                major_second["content"] = parent_content[idx2 + 1:]

        # 最終保底：同分支若其中一個空，借用另一個內容避免空陣列
        if not minor_first.get("content") and minor_second.get("content"):
            minor_first["content"] = list(minor_second.get("content", []))
        if not minor_second.get("content") and minor_first.get("content"):
            minor_second["content"] = list(minor_first.get("content", []))
        if not major_first.get("content") and major_second.get("content"):
            major_first["content"] = list(major_second.get("content", []))
        if not major_second.get("content") and major_first.get("content"):
            major_second["content"] = list(major_first.get("content", []))

    perk_targets["5.1"].pop("content", None)
    perk_targets["5.2"].pop("content", None)
    for sid in ["5", "5.1.1", "5.1.2", "5.2.1", "5.2.2"]:
        if not perk_targets[sid].get("content"):
            perk_targets[sid].pop("content", None)

    return [perk_targets[key] for key in ["5", "5.1", "5.1.1", "5.1.2", "5.2", "5.2.1", "5.2.2"]]


def _extract_map_item(line):
    text = str(line or "").strip()
    if not text.startswith("* "):
        return None
    if text.startswith("* *"):
        return None
    item = text[2:].strip()
    if not item:
        return None
    for separator in [" - ", " — ", ": "]:
        if separator in item:
            name, detail = item.split(separator, 1)
            name = name.strip()
            detail = detail.strip()
            if name and detail:
                return name, [detail]
    return item, []


def _expand_map_parent(parent_section):
    parent_id = str(parent_section.get("id", "")).strip()
    lines = list(parent_section.get("content", []) or [])
    intro_lines = []
    child_sections = []
    seen_item = False

    for line in lines:
        parsed = _extract_map_item(line)
        if parsed:
            seen_item = True
            title, content = parsed
            child_sections.append(
                {
                    "id": f"{parent_id}.{len(child_sections) + 1}",
                    "title": title,
                    "content": content,
                }
            )
            continue
        if seen_item and child_sections:
            child_sections[-1]["content"].append(str(line))
        else:
            intro_lines.append(str(line))

    if intro_lines:
        parent_section["content"] = intro_lines
    else:
        parent_section.pop("content", None)
    return child_sections


def _normalize_maps_sections(sections):
    normalized = [dict(section) for section in sections]

    for parent_id, title in (("6.1", "Best Maps"), ("6.2", "Worst Maps")):
        parent_index = next(
            (idx for idx, section in enumerate(normalized) if str(section.get("id", "")) == parent_id),
            None,
        )
        if parent_index is not None:
            normalized[parent_index]["title"] = title

    for parent_id in ("6.1", "6.2"):
        parent_index = next(
            (idx for idx, section in enumerate(normalized) if str(section.get("id", "")) == parent_id),
            None,
        )
        if parent_index is None:
            continue
        has_children = any(str(section.get("id", "")).startswith(f"{parent_id}.") for section in normalized)
        if has_children:
            continue
        children = _expand_map_parent(normalized[parent_index])
        if children:
            normalized[parent_index + 1:parent_index + 1] = children

    return normalized


def parse_hero_guide(markdown_text, hero_name, hero_id, perk_lookup):
    lines = markdown_text.splitlines()
    sections = []
    counters = [0, 0, 0]
    start_parsing = False

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("## Table of Contents"):
            break
        if not start_parsing:
            if stripped.startswith("## "):
                start_parsing = True
            else:
                continue
        if any(stripped.startswith(prefix) for prefix in NOISE_LINE_PREFIXES):
            continue
        if stripped in {"Back to top", "Advertisement"} or stripped.startswith("Remove Ads"):
            continue
        if stripped.startswith("To pick up a draggable item"):
            continue
        if stripped.startswith("![](https://u.openx.net/"):
            continue

        heading_match = re.match(r"^(#{2,4})\s+(.*)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            title = _unescape_markdown(title)
            title = title.replace(hero_name, "").replace("Overwatch ", "").strip()
            title = re.sub(r"\s{2,}", " ", title).strip()
            e_match = re.match(r"^E:\s*(.+)$", title)
            if e_match:
                title = f"[E]:\u00A0{e_match.group(1).strip()}"
            if not title:
                title = _unescape_markdown(heading_match.group(2).strip())

            adjusted = level - 1
            if 1 <= adjusted <= 3:
                counters[adjusted - 1] += 1
                for i in range(adjusted, 3):
                    counters[i] = 0
                section_id = ".".join(str(x) for x in counters[:adjusted])
                sections.append({"id": section_id, "title": title, "content": []})
            continue

        if not sections:
            continue
        current = sections[-1]
        content_line = _unescape_markdown(line)
        current["content"].append(content_line)

    # 修正特例：有些頁面會把 8.1 產成 8.0.1（例如 Specific Hero Counters）
    for section in sections:
        if str(section.get("id", "")) == "8.0.1":
            section["id"] = "8.1"

    cleaned = []
    for section in sections:
        copied = {"id": section["id"], "title": section["title"]}
        content = section.get("content", [])
        if content:
            copied["content"] = content
        cleaned.append(copied)

    first_perk_index = next((idx for idx, s in enumerate(cleaned) if str(s.get("id", "")).startswith("5")), None)
    non_perks = [s for s in cleaned if not str(s.get("id", "")).startswith("5")]
    perk_sections = [s for s in cleaned if str(s.get("id", "")).startswith("5")]
    normalized_perks = _normalize_perk_sections(perk_sections, hero_id, perk_lookup)
    if first_perk_index is None:
        return _normalize_maps_sections(non_perks + normalized_perks)
    merged = non_perks[:first_perk_index] + normalized_perks + non_perks[first_perk_index:]
    return _normalize_maps_sections(merged)


def convert_markdown_pair_to_payload(hero_markdown, tier_markdown, hero_id_hint=None):
    hero_lookup, slug_lookup, id_to_en, perk_lookup, _ = _load_mapping()
    tier_map = parse_tier_map(tier_markdown, hero_lookup, slug_lookup)
    meta_commentary = parse_meta_commentary_compat(tier_markdown, hero_lookup)

    hero_id = hero_id_hint or "unknown-hero"
    hero_name = id_to_en.get(hero_id, hero_id)
    guide = parse_hero_guide(hero_markdown, hero_name, hero_id, perk_lookup)
    payload = {
        "heroes": [{"Hero": hero_id, "Tier": tier_map.get(hero_id, "Unknown"), "Guide": guide}],
        "meta_commentary": meta_commentary,
    }
    return payload


def _cf_fetch_markdown(url, account_id, api_token):
    endpoint = CF_MARKDOWN_ENDPOINT.format(account_id=account_id)
    body = {
        "url": url,
        "gotoOptions": {"waitUntil": "domcontentloaded", "timeout": 60000},
        "waitForTimeout": 8000,
        "rejectRequestPattern": [
            "/^.*\\.(png|jpg|jpeg|gif|webp|svg|ico|woff|woff2|ttf|otf)$/i",
            "/^.*(googletagmanager|google-analytics|doubleclick|hotjar|segment|sentry).*/i",
        ],
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }
    req = request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=120) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw)
    if not parsed.get("success"):
        raise RuntimeError(f"Cloudflare API 回傳失敗: {parsed}")
    result = parsed.get("result", "")
    if not isinstance(result, str):
        raise RuntimeError("Cloudflare API result 不是字串")
    return result


def _write_text(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


async def scrape_mobalytics_cloudflare(smoke_hero=None, build_master=False, worker_count=1):
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not account_id or not api_token:
        raise RuntimeError("缺少 CLOUDFLARE_ACCOUNT_ID 或 CLOUDFLARE_API_TOKEN")

    raw_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    md_dir = os.path.join(raw_dir, "mobalytics_markdown")
    out_file = os.path.join(raw_dir, "mobalytics_heroes.json")

    hero_lookup, slug_lookup, id_to_en, perk_lookup, valid_ids = _load_mapping()

    async def fetch_markdown(url):
        return await asyncio.to_thread(_cf_fetch_markdown, url, account_id, api_token)

    print("抓取 tier_list_standard markdown...")
    try:
        tier_markdown = await fetch_markdown(TIER_LIST_URL)
    except error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="ignore")
        except Exception:
            detail = ""
        raise RuntimeError(f"抓取 tier list 失敗 HTTP {e.code}: {detail[:300]}")
    _write_text(os.path.join(md_dir, "tier_list_standard.md"), tier_markdown)

    tier_map = parse_tier_map(tier_markdown, hero_lookup, slug_lookup)
    meta_commentary = parse_meta_commentary_full(tier_markdown, hero_lookup, slug_lookup)
    hero_ids = [hid for hid in tier_map.keys() if hid in valid_ids]
    if smoke_hero:
        hero_ids = [smoke_hero]

    worker_count = max(1, int(worker_count))
    print(f"Cloudflare 並行 worker 數: {worker_count}")
    semaphore = asyncio.Semaphore(worker_count)

    async def scrape_single_hero(hero_id):
        hero_name = id_to_en.get(hero_id, hero_id)
        slug = _normalize_slug(hero_name)
        candidate_urls = [
            f"https://mobalytics.gg/overwatch/heroes/{slug}-guide",
            f"https://mobalytics.gg/overwatch/{slug}-guide",
        ]

        markdown = ""
        for candidate in candidate_urls:
            for attempt in range(1, MAX_RETRY_404_422 + 1):
                try:
                    candidate_markdown = await fetch_markdown(candidate)
                    if _is_not_found_markdown(candidate_markdown):
                        if attempt < MAX_RETRY_404_422:
                            print(f"  [重試] {hero_id} {candidate} 命中 404 內容（第 {attempt}/{MAX_RETRY_404_422} 次）")
                            await asyncio.sleep(RETRY_DELAY_SECONDS)
                            continue
                        print(f"  [跳過] {hero_id} {candidate} 命中 404 頁面內容")
                        break
                    markdown = candidate_markdown
                    break
                except error.HTTPError as e:
                    detail = ""
                    try:
                        detail = e.read().decode("utf-8", errors="ignore")
                    except Exception:
                        detail = ""
                    should_retry = e.code in (404, 422) and attempt < MAX_RETRY_404_422
                    if should_retry:
                        print(f"  [重試] {hero_id} {candidate} HTTP {e.code}（第 {attempt}/{MAX_RETRY_404_422} 次）")
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
                        continue
                    if detail:
                        print(f"  [跳過] {hero_id} {candidate} HTTP {e.code} {detail[:180]}")
                    else:
                        print(f"  [跳過] {hero_id} {candidate} HTTP {e.code}")
                    break
                except Exception as e:
                    print(f"  [跳過] {hero_id} {candidate} 錯誤: {e}")
                    break
            if markdown:
                break

        if markdown:
            _write_text(os.path.join(md_dir, f"hero_{hero_id}.md"), markdown)
            guide = parse_hero_guide(markdown, hero_name, hero_id, perk_lookup)
        else:
            guide = []

        print(f"完成英雄: {hero_id}")
        return {"Hero": hero_id, "Tier": tier_map.get(hero_id, "Unknown"), "Guide": guide}

    async def scrape_with_limit(hero_id):
        async with semaphore:
            return await scrape_single_hero(hero_id)

    tasks = [asyncio.create_task(scrape_with_limit(hero_id)) for hero_id in hero_ids]
    heroes = await asyncio.gather(*tasks)

    payload = {"heroes": heroes, "meta_commentary": meta_commentary}
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出 {out_file}")

    if build_master:
        master_file = os.path.join(os.path.dirname(__file__), "..", "data", "overwatch_master.json")
        with open(master_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print("✅ 已更新 data/overwatch_master.json（Cloudflare 轉換格式）")
    return payload


if __name__ == "__main__":
    asyncio.run(scrape_mobalytics_cloudflare(build_master=True))
