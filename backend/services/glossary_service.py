"""Glossary 服務：載入與管理專有名詞對照表"""
import json
from typing import Dict, List


class GlossaryService:
    def __init__(self, mapping_path: str):
        self.mapping_path = mapping_path
        self.version = "v1"  # glossary 版本，變更時觸發重翻
        self._glossary = self._load_glossary()
    
    def _load_glossary(self) -> Dict[str, str]:
        """從 mapping.json 載入 en -> zh 對照表"""
        try:
            with open(self.mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
            
            glossary = {}
            
            # 英雄名稱
            for hero in mapping.get("heroes", []):
                en_name = hero.get("en")
                zh_name = hero.get("zh")
                if en_name and zh_name:
                    glossary[en_name] = zh_name
            
            # 地圖名稱
            for map_item in mapping.get("maps", []):
                en_name = map_item.get("en")
                zh_name = map_item.get("zh")
                if en_name and zh_name:
                    glossary[en_name] = zh_name
            
            # 模式名稱
            for mode in mapping.get("modes", []):
                en_name = mode.get("en")
                zh_name = mode.get("zh")
                if en_name and zh_name:
                    glossary[en_name] = zh_name

            # 通用術語
            for en_name, zh_name in mapping.get("terms", {}).items():
                if en_name and zh_name:
                    glossary[en_name] = zh_name
            
            return glossary
        except Exception as e:
            print(f"警告：無法載入 glossary：{e}")
            return {}
    
    def get_glossary_text(self) -> str:
        """取得 prompt 用的詞彙表文字"""
        if not self._glossary:
            return ""
        
        lines = ["## 專有名詞強制對照表（MUST USE）"]
        for en, zh in sorted(self._glossary.items()):
            lines.append(f"- {en} -> {zh}")
        
        return "\n".join(lines)
    
    def get_version(self) -> str:
        """取得 glossary 版本"""
        return self.version
    
    def translate_term(self, term: str) -> str:
        """直接翻譯專有名詞（不走 Gemini）"""
        return self._glossary.get(term, term)
