"""翻譯服務：整合 Gemini API 與快取"""
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
import google.generativeai as genai

from services.cache_service import CacheService
from services.glossary_service import GlossaryService


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
        self.prompt_version = "v2"  # prompt 版本，變更時觸發重翻
        
        # 設定 Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # 統計
        self._stats = {"gemini_calls": 0, "cache_hits": 0, "errors": 0}
    
    def _should_translate_with_gemini(self, section_id: str) -> bool:
        """
        判斷此 section 是否需要走 Gemini 翻譯
        
        不走 Gemini 的欄位：
        - 英雄名、地圖名、模式（直接用 mapping）
        - 空 content 或僅含圖片連結
        
        走 Gemini 的欄位：
        - 詳情長文（Overview, Strengths, Weaknesses, Play As/Against 等）
        """
        # 僅含 title 沒有 content 的 section 不翻譯
        # 短列表類的也可以走 Gemini（例如優缺點摘要）
        # 這裡採寬鬆策略：有實質文字內容就翻譯
        return True  # 預設都翻譯，交由 caller 過濾空內容
    
    def _extract_text_content(self, content_list: List) -> str:
        """從 content 列表提取純文字（移除圖片 markdown）"""
        if not content_list:
            return ""
        
        texts = []
        for item in content_list:
            if isinstance(item, str):
                # 移除圖片連結 ![](...)
                text = item
                import re
                text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
                text = text.strip()
                if text:
                    texts.append(text)
        
        return "\n".join(texts)
    
    def _build_translation_prompt(self, section_data: Dict, glossary_text: str) -> str:
        """建立翻譯 prompt"""
        section_id = section_data.get("id", "")
        title = section_data.get("title", "")
        content = section_data.get("content", [])
        
        content_text = self._extract_text_content(content)
        
        prompt = f"""你是專業的 Overwatch 遊戲內容翻譯員，負責將英文內容翻譯成繁體中文（台灣用語）。

{glossary_text}

## 翻譯規則
1. **專有名詞（有對照表）**：英雄名稱、地圖名稱、模式名稱必須使用上方對照表，不可自行翻譯。
2. **專有名詞（無對照表）**：僅針對未定義的專有名詞（例如 ability 名稱、perk 名稱），統一使用「中文（英文）」格式，中文在前、英文括號在後（例如：湧泉（Wellspring））。
3. **格式一致性**：不要輸出「英文（中文）」或只留英文；同一名詞在同一 section 內需維持一致寫法。
4. **語氣**：維持專業、清晰的遊戲攻略風格。
5. **格式**：保留原有的列表、段落結構。
6. **圖片連結**：保持原樣不翻譯（以 ![]() 開頭的）。

## 待翻譯內容

Section ID: {section_id}
Title: {title}

Content:
{content_text}

## 輸出格式
請以 JSON 格式輸出，結構如下：
{{
  "title": "翻譯後的標題",
  "content": ["翻譯後的段落1", "翻譯後的段落2", ...]
}}

注意：content 陣列中每個元素對應原文中的一個段落或列表項。若原文是 bullet list，請保留 "* " 開頭格式。
"""
        return prompt
    
    async def _call_gemini(self, prompt: str, retries: int = 3) -> Optional[Dict]:
        """呼叫 Gemini API 並解析 JSON 回應"""
        for attempt in range(retries):
            try:
                self._stats["gemini_calls"] += 1
                
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.3,
                        "top_p": 0.95,
                        "max_output_tokens": 2048,
                    },
                )
                
                # 解析 JSON
                text = response.text.strip()
                # 移除可能的 markdown code block 包裝
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
                time.sleep(1 * (attempt + 1))  # 指數退避
            
            except Exception as e:
                print(f"Gemini API 錯誤 (attempt {attempt+1}/{retries}): {e}")
                if attempt == retries - 1:
                    self._stats["errors"] += 1
                    return None
                time.sleep(2 * (attempt + 1))
        
        return None
    
    async def _translate_section(
        self,
        hero_id: str,
        section: Dict,
        glossary_text: str,
    ) -> Optional[Dict]:
        """翻譯單個 section"""
        section_id = section.get("id", "")
        content_list = section.get("content", [])
        
        # 提取文字內容
        content_text = self._extract_text_content(content_list)
        
        # 空內容直接跳過
        if not content_text or len(content_text.strip()) < 10:
            return None
        
        # 檢查快取
        cached = self.cache_service.get(
            hero_id=hero_id,
            section_id=section_id,
            content=content_text,
            prompt_version=self.prompt_version,
            glossary_version=self.glossary_service.get_version(),
        )
        
        if cached:
            self._stats["cache_hits"] += 1
            return cached
        
        # 快取未命中，呼叫 Gemini
        prompt = self._build_translation_prompt(section, glossary_text)
        translated = await self._call_gemini(prompt)
        
        if not translated:
            return None
        
        # 寫入快取
        translated_title = translated.get("title", section.get("title", ""))
        translated_content = translated.get("content", [])
        self.cache_service.set(
            hero_id=hero_id,
            section_id=section_id,
            content=content_text,
            translated_content=translated_content,
            translated_title=translated_title,
            prompt_version=self.prompt_version,
            glossary_version=self.glossary_service.get_version(),
        )
        
        return {
            "title": translated_title,
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
        """
        翻譯整個英雄資料
        
        Returns:
            {
                "hero_id": "ana",
                "locale": "zh-TW",
                "sections": {
                    "1": { "content": [...], "content_hash": "..." },
                    ...
                },
                "metadata": { ... }
            }
        """
        guide = hero_data.get("Guide", [])
        glossary_text = self.glossary_service.get_glossary_text()
        
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
        
        # 逐 section 翻譯
        for section in guide:
            section_id = section.get("id", "")
            if not section_id:
                continue
            
            # 只翻譯有內容的 section
            if not section.get("content"):
                continue
            
            translated = await self._translate_section(hero_id, section, glossary_text)
            if translated:
                result["sections"][section_id] = translated
        
        return result
    
    def get_stats(self) -> Dict:
        """取得翻譯統計"""
        return {
            "gemini_calls": self._stats["gemini_calls"],
            "cache_hits": self._stats["cache_hits"],
            "errors": self._stats["errors"],
        }
