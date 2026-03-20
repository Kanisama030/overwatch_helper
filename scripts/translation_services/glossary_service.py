"""Glossary 服務：載入與管理專有名詞對照表"""
import json
from typing import Dict


class GlossaryService:
    def __init__(self, mapping_path: str):
        self.mapping_path = mapping_path
        self.version = "v1"
        self._glossary = self._load_glossary()
    
    def _load_glossary(self) -> Dict[str, str]:
        try:
            with open(self.mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
            
            glossary = {}
            
            for hero in mapping.get("heroes", []):
                en_name = hero.get("en")
                zh_name = hero.get("zh")
                if en_name and zh_name:
                    glossary[en_name] = zh_name
            
            for map_item in mapping.get("maps", []):
                en_name = map_item.get("en")
                zh_name = map_item.get("zh")
                if en_name and zh_name:
                    glossary[en_name] = zh_name
            
            for mode in mapping.get("modes", []):
                en_name = mode.get("en")
                zh_name = mode.get("zh")
                if en_name and zh_name:
                    glossary[en_name] = zh_name

            for en_name, zh_name in mapping.get("terms", {}).items():
                if en_name and zh_name:
                    glossary[en_name] = zh_name
            
            return glossary
        except Exception as e:
            print(f"警告：無法載入 glossary：{e}")
            return {}
    
    def get_glossary_text(self) -> str:
        if not self._glossary:
            return ""
        
        lines = ["## 專有名詞強制對照表（MUST USE）"]
        for en, zh in sorted(self._glossary.items()):
            lines.append(f"- {en} -> {zh}")
        
        return "\n".join(lines)
    
    def get_version(self) -> str:
        return self.version

