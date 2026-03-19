"""快取服務：管理翻譯結果的持久化快取"""
import json
import hashlib
import os
from typing import Optional, Dict
from datetime import datetime
import threading


class CacheService:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Single-flight 去重：同 key 並發時只執行一次
        self._in_flight: Dict[str, threading.Event] = {}
        self._in_flight_lock = threading.Lock()
        
        # 快取統計
        self._stats = {"hits": 0, "misses": 0, "errors": 0}
    
    def _get_cache_path(self, hero_id: str) -> str:
        """取得英雄快取檔路徑"""
        return os.path.join(self.cache_dir, f"{hero_id}.json")
    
    def _compute_content_hash(self, content: str) -> str:
        """計算內容 hash（正規化後）"""
        # 正規化：移除多餘空白、統一換行
        normalized = " ".join(content.split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    
    def _make_cache_key(
        self,
        hero_id: str,
        section_id: str,
        content_hash: str,
        prompt_version: str,
        glossary_version: str,
    ) -> str:
        """建立快取 key"""
        key_parts = [hero_id, section_id, content_hash, prompt_version, glossary_version]
        return "|".join(key_parts)
    
    def get(
        self,
        hero_id: str,
        section_id: str,
        content: str,
        prompt_version: str,
        glossary_version: str,
    ) -> Optional[Dict]:
        """
        取得快取
        
        Returns:
            {"content": [...], "content_hash": "...", "timestamp": "..."}
            若不存在或失效則回傳 None
        """
        try:
            cache_path = self._get_cache_path(hero_id)
            if not os.path.exists(cache_path):
                self._stats["misses"] += 1
                return None
            
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            content_hash = self._compute_content_hash(content)
            cache_key = self._make_cache_key(
                hero_id, section_id, content_hash, prompt_version, glossary_version
            )
            
            section_cache = cache_data.get("sections", {}).get(section_id)
            if not section_cache:
                self._stats["misses"] += 1
                return None
            
            # 驗證 hash 與版本
            if (
                section_cache.get("content_hash") == content_hash
                and section_cache.get("prompt_version") == prompt_version
                and section_cache.get("glossary_version") == glossary_version
                and isinstance(section_cache.get("title"), str)
                and section_cache.get("title", "").strip() != ""
            ):
                self._stats["hits"] += 1
                return section_cache
            
            self._stats["misses"] += 1
            return None
        
        except Exception as e:
            print(f"快取讀取錯誤: {e}")
            self._stats["errors"] += 1
            return None
    
    def set(
        self,
        hero_id: str,
        section_id: str,
        content: str,
        translated_content: list,
        translated_title: str,
        prompt_version: str,
        glossary_version: str,
    ) -> None:
        """寫入快取"""
        try:
            cache_path = self._get_cache_path(hero_id)
            
            # 讀取現有快取
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
            else:
                cache_data = {"hero_id": hero_id, "sections": {}}
            
            content_hash = self._compute_content_hash(content)
            
            # 更新 section 快取
            cache_data["sections"][section_id] = {
                "title": translated_title,
                "content": translated_content,
                "content_hash": content_hash,
                "prompt_version": prompt_version,
                "glossary_version": glossary_version,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            
            # 寫入檔案
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            print(f"快取寫入錯誤: {e}")
            self._stats["errors"] += 1
    
    def get_stats(self) -> Dict:
        """取得快取統計"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "errors": self._stats["errors"],
            "hit_rate": f"{hit_rate:.2%}",
        }
    
    def invalidate_hero(self, hero_id: str) -> bool:
        """手動失效指定英雄的快取"""
        try:
            cache_path = self._get_cache_path(hero_id)
            if os.path.exists(cache_path):
                os.remove(cache_path)
                return True
            return False
        except Exception as e:
            print(f"快取失效錯誤: {e}")
            return False
