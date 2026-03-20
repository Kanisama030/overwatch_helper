"""翻譯服務：整合 Gemini API 與快取"""
import json
import time
import os
import asyncio
import re
from urllib.parse import quote
from typing import Dict, List, Optional
from datetime import datetime
import google.generativeai as genai

from .cache_service import CacheService
from .glossary_service import GlossaryService


class TranslationService:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        glossary_service: GlossaryService,
        cache_service: CacheService,
    ):
        self.model_name = model_name
        self.glossary_service = glossary_service
        self.cache_service = cache_service
        self.prompt_version = "v7"
        self.asset_url_mapping = self._load_guide_asset_mapping()
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        self._stats = {"gemini_calls": 0, "cache_hits": 0, "errors": 0}

    def _load_mapping(self) -> Dict:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            mapping_path = os.path.join(base_dir, "data", "overwatch_mapping.json")
            with open(mapping_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _load_perks_index(self) -> Dict:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidates = [
            os.path.join(base_dir, "data", "app", "perks_index.json"),
            os.path.join(base_dir, "frontend", "public", "data", "perks_index.json"),
        ]
        merged: Dict = {}
        for perks_path in candidates:
            try:
                with open(perks_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    continue
                for hero_id, hero_perks in data.items():
                    if not isinstance(hero_perks, dict):
                        continue
                    target = merged.setdefault(hero_id, {"minor": [], "major": []})
                    for perk_type in ("minor", "major"):
                        src_list = hero_perks.get(perk_type, []) or []
                        if not isinstance(src_list, list):
                            continue
                        by_id = {
                            str(item.get("id")): item
                            for item in target.get(perk_type, [])
                            if isinstance(item, dict) and item.get("id")
                        }
                        for item in src_list:
                            if not isinstance(item, dict) or not item.get("id"):
                                continue
                            key = str(item.get("id"))
                            existing = by_id.get(key)
                            if not existing:
                                target[perk_type].append(dict(item))
                                by_id[key] = target[perk_type][-1]
                                continue
                            if not existing.get("description") and item.get("description"):
                                existing["description"] = item.get("description")
                            if not existing.get("name") and item.get("name"):
                                existing["name"] = item.get("name")
                            if not existing.get("image") and item.get("image"):
                                existing["image"] = item.get("image")
            except Exception:
                continue
        return merged

    def _load_guide_asset_mapping(self) -> Dict[str, str]:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        manifest_path = os.path.join(base_dir, "data", "assets", "guide", "manifest.json")
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            if not isinstance(manifest, list):
                return {}
            mapping: Dict[str, str] = {}
            for item in manifest:
                if not isinstance(item, dict):
                    continue
                src = item.get("image_url")
                local_path = item.get("local_path")
                if not src or not local_path:
                    continue
                normalized = str(local_path).replace("\\", "/")
                if not normalized.startswith("/"):
                    normalized = f"/{normalized}"
                mapping[str(src)] = normalized
            return mapping
        except Exception:
            return {}

    def _rewrite_markdown_images_to_local(self, text: str) -> str:
        if not text:
            return text
        pattern = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\".*?\")?\)")

        def _replace(match: re.Match) -> str:
            alt = match.group(1)
            original_url = match.group(2)
            if "#fallback=" in original_url:
                return match.group(0)
            local_path = self.asset_url_mapping.get(original_url)
            if not local_path:
                return match.group(0)
            fallback = quote(original_url, safe="")
            return f"![{alt}]({local_path}#fallback={fallback})"

        return pattern.sub(_replace, text)
    
    def _prepare_content_with_image_tokens(self, content_list: List) -> tuple[List[str], List[Dict[str, str]]]:
        if not content_list:
            return [], []

        prepared_texts: List[str] = []
        token_maps: List[Dict[str, str]] = []
        image_pattern = re.compile(r'!\[[^\]]*\]\([^)]+\)')

        for item in content_list:
            if not isinstance(item, str):
                continue
            text = item.strip()
            if not text:
                continue

            image_map: Dict[str, str] = {}

            def repl(match: re.Match) -> str:
                token = f"[[__OWH_IMG_{len(image_map) + 1}__]]"
                image_map[token] = match.group(0)
                return token

            tokenized_text = image_pattern.sub(repl, text)
            prepared_texts.append(tokenized_text)
            token_maps.append(image_map)

        return prepared_texts, token_maps

    def _restore_images_from_tokens(self, text: str, token_map: Dict[str, str]) -> str:
        restored = text
        for token, markdown_image in token_map.items():
            restored = restored.replace(token, markdown_image)
        return restored

    def _restore_translated_content(
        self,
        translated_content: List,
        source_texts: List[str],
        token_maps: List[Dict[str, str]],
    ) -> List[str]:
        restored_content: List[str] = []
        translated_list = translated_content if isinstance(translated_content, list) else []

        for idx, source_text in enumerate(source_texts):
            token_map = token_maps[idx] if idx < len(token_maps) else {}
            translated_text = ""
            if idx < len(translated_list) and isinstance(translated_list[idx], str):
                translated_text = translated_list[idx].strip()

            if token_map:
                if any(token not in translated_text for token in token_map):
                    translated_text = source_text
                restored_content.append(self._restore_images_from_tokens(translated_text, token_map))
                continue

            restored_content.append(translated_text or source_text)

        return restored_content

    def _build_translation_prompt(self, section_data: Dict, glossary_text: str, content_text: str) -> str:
        section_id = section_data.get("id", "")
        title = section_data.get("title", "")
        
        description = section_data.get("description", "")
        prompt = f"""你是專業的 Overwatch 遊戲內容翻譯員，負責將英文內容翻譯成繁體中文（台灣用語）。

{glossary_text}

## 翻譯規則
1. **專有名詞（有對照表）**：英雄名稱、地圖名稱、模式名稱必須使用上方對照表，不可自行翻譯。
2. **專有名詞（無對照表）**：僅針對未定義的專有名詞（例如 ability 名稱、perk 名稱），統一使用「中文（英文）」格式，中文在前、英文括號在後（例如：湧泉（Wellspring））。
3. **格式一致性**：不要輸出「英文（中文）」或只留英文；同一名詞在同一 section 內需維持一致寫法。
4. **語氣**：維持專業、清晰的遊戲攻略風格。
5. **格式**：保留原有的列表、段落結構。
6. **圖片 token**：若原文出現形如 [[__OWH_IMG_1__]] 的 token，必須逐字保留，不可刪除或改寫。

## 待翻譯內容

Section ID: {section_id}
Title: {title}
Description: {description}

Content:
{content_text}

## 輸出格式
請以 JSON 格式輸出，結構如下：
{{
  "title": "翻譯後的標題",
  "description": "翻譯後的描述（若無可為空字串）",
  "content": ["翻譯後的段落1", "翻譯後的段落2", ...]
}}

注意：content 陣列中每個元素對應原文中的一個段落或列表項。若原文是 bullet list，請保留 "* " 開頭格式。
"""
        return prompt
    
    async def _call_gemini(self, prompt: str, retries: int = 3) -> Optional[Dict]:
        for attempt in range(retries):
            try:
                self._stats["gemini_calls"] += 1
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config={
                        "temperature": 0.3,
                        "top_p": 0.95,
                        "max_output_tokens": 2048,
                    },
                )
                
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                
                result = json.loads(text)
                return result
            
            except json.JSONDecodeError as e:
                print(f"JSON 解析失敗 (attempt {attempt+1}/{retries}): {e}")
                if attempt == retries - 1:
                    self._stats["errors"] += 1
                    return None
                await asyncio.sleep(1 * (attempt + 1))
            
            except Exception as e:
                print(f"Gemini API 錯誤 (attempt {attempt+1}/{retries}): {e}")
                if attempt == retries - 1:
                    self._stats["errors"] += 1
                    return None
                await asyncio.sleep(2 * (attempt + 1))
        
        return None

    async def _translate_short_text(self, text: str) -> str:
        source = str(text or "").strip()
        if not source:
            return ""
        prompt = f"""請將以下英文翻譯成繁體中文（台灣用語），只輸出 JSON：
{{
  "text": "翻譯結果"
}}

英文：
{source}
"""
        result = await self._call_gemini(prompt)
        if not isinstance(result, dict):
            return ""
        return str(result.get("text", "")).strip()
    
    async def _translate_section(
        self,
        hero_id: str,
        section: Dict,
        glossary_text: str,
    ) -> Optional[Dict]:
        section_id = section.get("id", "")
        content_list = section.get("content", [])
        source_description = str(section.get("description", "")).strip()
        prepared_texts, token_maps = self._prepare_content_with_image_tokens(content_list)
        content_text = "\n".join(prepared_texts)
        
        if not content_text or len(content_text.strip()) < 10:
            return None
        
        cached = self.cache_service.get(
            hero_id=hero_id,
            section_id=section_id,
            content=content_text,
            prompt_version=self.prompt_version,
            glossary_version=self.glossary_service.get_version(),
        )
        
        if cached:
            cached_description = str(cached.get("description", "")).strip()
            if not (source_description and not cached_description):
                self._stats["cache_hits"] += 1
                return cached
        
        prompt = self._build_translation_prompt(section, glossary_text, content_text)
        translated = await self._call_gemini(prompt)
        
        if not translated:
            return None
        
        translated_title = translated.get("title", section.get("title", ""))
        translated_description = str(translated.get("description", "")).strip() if source_description else ""
        if source_description and not translated_description:
            translated_description = await self._translate_short_text(source_description)
        if source_description and not translated_description:
            translated_description = source_description
        translated_content = self._restore_translated_content(
            translated.get("content", []),
            prepared_texts,
            token_maps,
        )
        translated_content = [
            self._rewrite_markdown_images_to_local(line) if isinstance(line, str) else line
            for line in translated_content
        ]
        self.cache_service.set(
            hero_id=hero_id,
            section_id=section_id,
            content=content_text,
            translated_content=translated_content,
            translated_title=translated_title,
            translated_description=translated_description,
            prompt_version=self.prompt_version,
            glossary_version=self.glossary_service.get_version(),
        )
        
        return {
            "title": translated_title,
            "description": translated_description,
            "content": translated_content,
            "content_hash": self.cache_service._compute_content_hash(content_text),
            "prompt_version": self.prompt_version,
            "glossary_version": self.glossary_service.get_version(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    
    async def translate_hero(
        self,
        hero_id: str,
        hero_data: Dict,
        locale: str,
    ) -> Dict:
        guide = hero_data.get("Guide", [])
        glossary_text = self.glossary_service.get_glossary_text()
        mapping = self._load_mapping()
        perks_index = self._load_perks_index()
        hero_mapping = None
        for h in mapping.get("heroes", []):
            if str(h.get("id", "")).lower() == hero_id.lower() or str(h.get("en", "")).lower() == hero_id.lower():
                hero_mapping = h
                break
        perk_sections = {}
        if hero_mapping and isinstance(hero_mapping.get("perks"), dict):
            for perk in hero_mapping.get("perks", {}).get("minor perks", []) or []:
                if isinstance(perk, dict) and perk.get("name"):
                    perk_sections[perk.get("name")] = perk
            for perk in hero_mapping.get("perks", {}).get("major perks", []) or []:
                if isinstance(perk, dict) and perk.get("name"):
                    perk_sections[perk.get("name")] = perk
        if not perk_sections:
            hero_perks = perks_index.get(hero_id, {})
            for perk in (hero_perks.get("minor", []) or []) + (hero_perks.get("major", []) or []):
                if isinstance(perk, dict) and perk.get("id"):
                    perk_sections[str(perk.get("id"))] = perk
        
        result = {
            "hero_id": hero_id,
            "locale": locale,
            "sections": {},
            "metadata": {
                "prompt_version": self.prompt_version,
                "glossary_version": self.glossary_service.get_version(),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        }
        
        for section in guide:
            section_id = section.get("id", "")
            if not section_id:
                continue

            if section_id in {"5.1.1", "5.1.2", "5.2.1", "5.2.2"}:
                perk_data = perk_sections.get(section.get("title", "")) or perk_sections.get(section_id)
                if perk_data:
                    section["title"] = perk_data.get("name", section.get("title", ""))
                    description = str(perk_data.get("description") or "").strip()
                    if description:
                        section["description"] = description
            
            if not section.get("content"):
                continue
            
            translated = await self._translate_section(hero_id, section, glossary_text)
            if translated:
                result["sections"][section_id] = translated
        
        return result

